"""데이터소스용 일반 S3 버킷 생성 (T-401).

버킷명 `haru-kb-data-{account_id}-ap-northeast-2`, versioning + SSE-S3 + public access 전면 차단.
--dry-run(기본)은 무호출, --apply로만 실제 생성. 이미 있으면 skip (idempotent).
"""

import sys
from typing import Any

import structlog
from botocore.exceptions import ClientError

from app.config import get_settings
from app.services.bedrock_client import get_s3_client
from scripts._cli import parse_dry_run, resolve_account_id

logger = structlog.get_logger(__name__)
REGION = "ap-northeast-2"


def _bucket_name(account_id: str) -> str:
    return f"haru-kb-data-{account_id}-{REGION}"


def _exists(s3: Any, bucket: str) -> bool:
    try:
        s3.head_bucket(Bucket=bucket)
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code", "") in ("404", "NoSuchBucket", "NotFound"):
            return False
        raise


def _create_bucket(s3: Any, bucket: str) -> None:
    s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": REGION})
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )


def run(dry_run: bool = True, s3: Any | None = None, sts: Any | None = None) -> bool:
    account_id = resolve_account_id(dry_run, sts=sts)
    bucket = _bucket_name(account_id)
    if dry_run:
        logger.info(
            "create_step",
            resource_type="s3_bucket",
            resource_id=bucket,
            dry_run=True,
            result="would_create",
        )
        print(f"[dry-run] 생성 예정 S3 버킷: {bucket} (versioning + SSE-S3 + public block)")
        print(f"→ 생성 후 .env에 추가: HARU_KB_S3_BUCKET={bucket}")
        return True
    s3 = s3 or get_s3_client()
    if _exists(s3, bucket):
        logger.info(
            "create_step",
            resource_type="s3_bucket",
            resource_id=bucket,
            dry_run=False,
            result="already_exists",
        )
        print(f"이미 존재: {bucket} (skip)")
    else:
        _create_bucket(s3, bucket)
        logger.info(
            "create_step",
            resource_type="s3_bucket",
            resource_id=bucket,
            dry_run=False,
            result="created",
        )
        print(f"생성 완료: {bucket}")
    print(f"→ .env에 추가: HARU_KB_S3_BUCKET={bucket}")
    return True


def main(argv: list[str] | None = None) -> int:
    dry_run = parse_dry_run("데이터소스용 S3 버킷 생성", argv)
    _ = get_settings()
    return 0 if run(dry_run=dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
