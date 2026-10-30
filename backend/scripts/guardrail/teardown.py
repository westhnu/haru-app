"""Guardrail 리소스 teardown (T-452).

get_guardrail로 존재를 확인한 뒤 delete_guardrail로 모든 버전을 삭제한다.
--dry-run(기본)은 삭제 대상만 출력하고 AWS를 호출하지 않는다. 실삭제는 --confirm 필수.
guardrail_id가 비어 있거나 NotFound면 '지울 것 없음'으로 성공 처리한다.
"""

import argparse
import sys
from typing import Any

import structlog
from botocore.exceptions import ClientError

from app.config import Settings, get_settings
from app.services.bedrock_client import get_bedrock_client

logger = structlog.get_logger(__name__)

NOT_FOUND_CODES: frozenset[str] = frozenset({"ResourceNotFoundException", "NotFoundException"})


def _is_not_found(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code", "") in NOT_FOUND_CODES


def _log_step(resource_id: str, dry_run: bool, result: str) -> None:
    logger.info(
        "teardown_step",
        resource_type="guardrail",
        resource_id=resource_id,
        dry_run=dry_run,
        result=result,
    )


def _guardrail_exists(bedrock: Any, guardrail_id: str) -> bool:
    try:
        bedrock.get_guardrail(guardrailIdentifier=guardrail_id)
        return True
    except ClientError as exc:
        if _is_not_found(exc):
            return False
        raise


def run_teardown(settings: Settings, dry_run: bool = True, bedrock: Any | None = None) -> bool:
    guardrail_id = settings.bedrock_guardrail_id
    if not guardrail_id:
        _log_step("", dry_run, "skip_empty")
        return True
    bedrock = bedrock or get_bedrock_client()
    try:
        if not _guardrail_exists(bedrock, guardrail_id):
            _log_step(guardrail_id, dry_run, "already_absent")
            return True
        if dry_run:
            _log_step(guardrail_id, dry_run, "would_delete")
            return True
        bedrock.delete_guardrail(guardrailIdentifier=guardrail_id)
        _log_step(guardrail_id, dry_run, "deleted")
    except ClientError as exc:
        return _handle_error(guardrail_id, exc)
    return True


def _handle_error(guardrail_id: str, exc: ClientError) -> bool:
    if _is_not_found(exc):
        _log_step(guardrail_id, False, "already_absent")
        return True
    logger.error(
        "teardown_failed",
        resource_type="guardrail",
        resource_id=guardrail_id,
        error_code=exc.response.get("Error", {}).get("Code", "unknown"),
    )
    return False


def _parse_args(argv: list[str] | None = None) -> bool:
    parser = argparse.ArgumentParser(description="Guardrail teardown")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="삭제 대상만 출력 (기본)")
    group.add_argument("--confirm", action="store_true", help="실제 삭제 수행")
    args = parser.parse_args(argv)
    return not args.confirm


def main(argv: list[str] | None = None) -> int:
    dry_run = _parse_args(argv)
    ok = run_teardown(get_settings(), dry_run=dry_run)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
