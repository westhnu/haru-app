"""S3 Vector Store 인덱스 생성 (T-401.5-B).

Titan Embeddings v2 차원(1024), float32, cosine 거리.
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

INDEX_NAME = "haru-glossary"
# Titan Embeddings v2 출력 차원 (실측 반영).
EMBED_DIMENSION = 1024
DATA_TYPE = "float32"
DISTANCE_METRIC = "cosine"


def _vector_bucket_name(account_id: str) -> str:
    return f"haru-kb-vectors-{account_id}"


def _existing_arn(s3v: Any, bucket: str, index: str) -> str | None:
    try:
        resp = s3v.get_index(vectorBucketName=bucket, indexName=index)
        return str(resp["index"]["indexArn"])
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code", "") in (
            "NotFoundException",
            "ResourceNotFoundException",
        ):
            return None
        raise


def run(dry_run: bool = True, s3v: Any | None = None, sts: Any | None = None) -> bool:
    account_id = resolve_account_id(dry_run, sts=sts)
    bucket = _vector_bucket_name(account_id)
    if dry_run:
        logger.info(
            "create_step",
            resource_type="vector_index",
            resource_id=INDEX_NAME,
            dry_run=True,
            result="would_create",
        )
        print(f"[dry-run] 생성 예정 index: {INDEX_NAME} in {bucket}")
        print(f"  dimension={EMBED_DIMENSION}, dataType={DATA_TYPE}, metric={DISTANCE_METRIC}")
        print("→ 생성 후 .env에 추가: HARU_KB_S3_VECTOR_INDEX_ARN=<arn>")
        return True
    s3v = s3v or get_s3vectors_client()
    existing = _existing_arn(s3v, bucket, INDEX_NAME)
    if existing:
        logger.info(
            "create_step",
            resource_type="vector_index",
            resource_id=INDEX_NAME,
            dry_run=False,
            result="already_exists",
        )
        arn = existing
    else:
        s3v.create_index(
            vectorBucketName=bucket,
            indexName=INDEX_NAME,
            dimension=EMBED_DIMENSION,
            dataType=DATA_TYPE,
            distanceMetric=DISTANCE_METRIC,
        )
        arn = _existing_arn(s3v, bucket, INDEX_NAME) or ""
        logger.info(
            "create_step",
            resource_type="vector_index",
            resource_id=INDEX_NAME,
            dry_run=False,
            result="created",
        )
    print(f"index: {INDEX_NAME}")
    print(f"→ .env에 추가: HARU_KB_S3_VECTOR_INDEX_ARN={arn}")
    return True


def main(argv: list[str] | None = None) -> int:
    dry_run = parse_dry_run("vector index 생성", argv)
    _ = get_settings()
    return 0 if run(dry_run=dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
