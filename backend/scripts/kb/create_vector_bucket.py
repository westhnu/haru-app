"""S3 Vector Store의 vector bucket 생성 (T-401.5-A).

`s3vectors.create_vector_bucket(name="haru-kb-vectors-{account_id}")`.
--dry-run(기본) 무호출, --apply로만 실제 생성. 이미 있으면 skip.
"""

import sys
from typing import Any

import structlog
from botocore.exceptions import ClientError

from app.config import get_settings
from app.services.bedrock_client import get_s3vectors_client
from scripts._cli import parse_dry_run, resolve_account_id

logger = structlog.get_logger(__name__)


def _bucket_name(account_id: str) -> str:
    return f"haru-kb-vectors-{account_id}"


def _existing_arn(s3v: Any, name: str) -> str | None:
    try:
        resp = s3v.get_vector_bucket(vectorBucketName=name)
        return str(resp["vectorBucket"]["vectorBucketArn"])
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code", "") in (
            "NotFoundException",
            "ResourceNotFoundException",
        ):
            return None
        raise


def run(dry_run: bool = True, s3v: Any | None = None, sts: Any | None = None) -> bool:
    account_id = resolve_account_id(dry_run, sts=sts)
    name = _bucket_name(account_id)
    if dry_run:
        logger.info(
            "create_step",
            resource_type="vector_bucket",
            resource_id=name,
            dry_run=True,
            result="would_create",
        )
        print(f"[dry-run] 생성 예정 vector bucket: {name}")
        print("→ 생성 후 .env에 추가: HARU_KB_VECTOR_BUCKET_ARN=<arn>")
        return True
    s3v = s3v or get_s3vectors_client()
    existing = _existing_arn(s3v, name)
    if existing:
        logger.info(
            "create_step",
            resource_type="vector_bucket",
            resource_id=name,
            dry_run=False,
            result="already_exists",
        )
        arn = existing
    else:
        s3v.create_vector_bucket(vectorBucketName=name)
        arn = _existing_arn(s3v, name) or ""
        logger.info(
            "create_step",
            resource_type="vector_bucket",
            resource_id=name,
            dry_run=False,
            result="created",
        )
    print(f"vector bucket: {name}")
    print(f"→ .env에 추가: HARU_KB_VECTOR_BUCKET_ARN={arn}")
    return True


def main(argv: list[str] | None = None) -> int:
    dry_run = parse_dry_run("vector bucket 생성", argv)
    _ = get_settings()
    return 0 if run(dry_run=dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
