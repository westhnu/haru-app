"""Knowledge Base 스택 teardown (T-451).

생성의 역순으로 삭제한다: KB → vector index → vector bucket → S3 객체 → S3 버킷.
--dry-run(기본)은 삭제 대상만 출력하고 AWS를 호출하지 않는다. 실삭제는 --confirm 필수.
리소스가 없거나(NotFound) 설정값이 비어 있으면 '지울 것 없음'으로 성공 처리한다.
"""

import argparse
import sys
from typing import Any

import structlog
from botocore.exceptions import ClientError

from app.config import Settings, get_settings
from app.services.bedrock_client import (
    get_bedrock_agent_client,
    get_s3_client,
    get_s3vectors_client,
)

logger = structlog.get_logger(__name__)

# NotFound 류는 이미 없는 것이므로 성공으로 간주한다.
NOT_FOUND_CODES: frozenset[str] = frozenset(
    {"ResourceNotFoundException", "NotFoundException", "NoSuchBucket", "404"}
)


def _is_not_found(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code", "") in NOT_FOUND_CODES


def _log_step(resource_type: str, resource_id: str, dry_run: bool, result: str) -> None:
    logger.info(
        "teardown_step",
        resource_type=resource_type,
        resource_id=resource_id,
        dry_run=dry_run,
        result=result,
    )


def _delete_knowledge_base(agent: Any, kb_id: str, dry_run: bool) -> bool:
    if not kb_id:
        _log_step("knowledge_base", "", dry_run, "skip_empty")
        return True
    if dry_run:
        _log_step("knowledge_base", kb_id, dry_run, "would_delete")
        return True
    try:
        agent.delete_knowledge_base(knowledgeBaseId=kb_id)
        _log_step("knowledge_base", kb_id, dry_run, "deleted")
    except ClientError as exc:
        return _handle_error("knowledge_base", kb_id, exc)
    return True


def _delete_vector_index(s3v: Any, bucket_arn: str, index_arn: str, dry_run: bool) -> bool:
    if not index_arn:
        _log_step("vector_index", "", dry_run, "skip_empty")
        return True
    if dry_run:
        _log_step("vector_index", index_arn, dry_run, "would_delete")
        return True
    try:
        s3v.delete_index(indexArn=index_arn)
        _log_step("vector_index", index_arn, dry_run, "deleted")
    except ClientError as exc:
        return _handle_error("vector_index", index_arn, exc)
    return True


def _delete_vector_bucket(s3v: Any, bucket_arn: str, dry_run: bool) -> bool:
    if not bucket_arn:
        _log_step("vector_bucket", "", dry_run, "skip_empty")
        return True
    if dry_run:
        _log_step("vector_bucket", bucket_arn, dry_run, "would_delete")
        return True
    try:
        s3v.delete_vector_bucket(vectorBucketArn=bucket_arn)
        _log_step("vector_bucket", bucket_arn, dry_run, "deleted")
    except ClientError as exc:
        return _handle_error("vector_bucket", bucket_arn, exc)
    return True


def _empty_data_bucket(s3: Any, bucket: str, dry_run: bool) -> bool:
    if not bucket:
        _log_step("s3_objects", "", dry_run, "skip_empty")
        return True
    # dry-run은 어떤 AWS API도 호출하지 않는다 — 객체 조회(list)조차 생략한다.
    if dry_run:
        _log_step("s3_objects", bucket, dry_run, "would_delete")
        return True
    try:
        keys = _list_all_keys(s3, bucket)
    except ClientError as exc:
        return _handle_error("s3_objects", bucket, exc)
    return _delete_keys(s3, bucket, keys)


def _list_all_keys(s3: Any, bucket: str) -> list[str]:
    keys: list[str] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def _delete_keys(s3: Any, bucket: str, keys: list[str]) -> bool:
    try:
        # delete_objects는 요청당 최대 1000개. 1000개씩 끊어 보낸다.
        for start in range(0, len(keys), 1000):
            batch = [{"Key": k} for k in keys[start : start + 1000]]
            if batch:
                s3.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        _log_step("s3_objects", f"{bucket} ({len(keys)} objects)", False, "deleted")
    except ClientError as exc:
        return _handle_error("s3_objects", bucket, exc)
    return True


def _delete_data_bucket(s3: Any, bucket: str, dry_run: bool) -> bool:
    if not bucket:
        _log_step("s3_bucket", "", dry_run, "skip_empty")
        return True
    if dry_run:
        _log_step("s3_bucket", bucket, dry_run, "would_delete")
        return True
    try:
        s3.delete_bucket(Bucket=bucket)
        _log_step("s3_bucket", bucket, dry_run, "deleted")
    except ClientError as exc:
        return _handle_error("s3_bucket", bucket, exc)
    return True


def _handle_error(resource_type: str, resource_id: str, exc: ClientError) -> bool:
    if _is_not_found(exc):
        _log_step(resource_type, resource_id, False, "already_absent")
        return True
    logger.error(
        "teardown_failed",
        resource_type=resource_type,
        resource_id=resource_id,
        error_code=exc.response.get("Error", {}).get("Code", "unknown"),
    )
    return False


def run_teardown(
    settings: Settings,
    dry_run: bool = True,
    agent: Any | None = None,
    s3v: Any | None = None,
    s3: Any | None = None,
) -> bool:
    """역순 삭제를 수행한다. 모든 단계 성공 시 True."""
    agent = agent or get_bedrock_agent_client()
    s3v = s3v or get_s3vectors_client()
    s3 = s3 or get_s3_client()
    bucket = settings.haru_kb_s3_bucket
    vector_bucket = settings.haru_kb_vector_bucket_arn
    index = settings.haru_kb_s3_vector_index_arn
    results = [
        _delete_knowledge_base(agent, settings.bedrock_kb_id, dry_run),
        _delete_vector_index(s3v, vector_bucket, index, dry_run),
        _delete_vector_bucket(s3v, vector_bucket, dry_run),
        _empty_data_bucket(s3, bucket, dry_run),
        _delete_data_bucket(s3, bucket, dry_run),
    ]
    return all(results)


def _parse_args(argv: list[str] | None = None) -> bool:
    parser = argparse.ArgumentParser(description="KB 스택 teardown (역순 삭제)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="삭제 대상만 출력 (기본)")
    group.add_argument("--confirm", action="store_true", help="실제 삭제 수행")
    args = parser.parse_args(argv)
    # --confirm이 명시된 경우에만 실삭제. 그 외(플래그 생략 포함)는 dry-run.
    return not args.confirm


def main(argv: list[str] | None = None) -> int:
    dry_run = _parse_args(argv)
    ok = run_teardown(get_settings(), dry_run=dry_run)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
