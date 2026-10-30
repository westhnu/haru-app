"""scripts 내부 공통 CLI 헬퍼 (app 계층 아님, scripts 전용).

생성 스크립트가 공유하는 --dry-run/--apply 파싱과 account_id 조회를 모은다.
dry-run은 어떤 AWS도 호출하지 않으므로 account_id는 placeholder를 쓴다.
"""

import argparse
from typing import Any

ACCOUNT_PLACEHOLDER = "{account_id}"


def parse_dry_run(description: str, argv: list[str] | None = None) -> bool:
    """--apply가 명시된 경우에만 False(실행). 그 외(생략·--dry-run)는 True(dry-run)."""
    parser = argparse.ArgumentParser(description=description)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="생성 대상만 출력 (기본)")
    group.add_argument("--apply", action="store_true", help="실제 생성 수행")
    args = parser.parse_args(argv)
    return not args.apply


def resolve_account_id(dry_run: bool, sts: Any | None = None) -> str:
    """dry-run이면 placeholder, apply면 STS로 실제 account_id 조회."""
    if dry_run:
        return ACCOUNT_PLACEHOLDER
    import boto3

    client = sts or boto3.client("sts")
    identity: dict[str, Any] = client.get_caller_identity()
    return str(identity["Account"])
