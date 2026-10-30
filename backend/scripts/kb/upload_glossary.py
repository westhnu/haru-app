"""glossary.jsonl을 데이터소스 S3 버킷에 업로드 (T-403).

s3://{HARU_KB_S3_BUCKET}/glossary/glossary.jsonl 로 올린다.
md5 비교로 idempotent — 원격 ETag와 로컬 md5가 같으면 skip.
--dry-run(기본) 무호출, --apply로만 실제 업로드.
"""

import hashlib
import sys
from pathlib import Path
from typing import Any

import structlog
from botocore.exceptions import ClientError

from app.config import BACKEND_DIR, get_settings
from app.services.bedrock_client import get_s3_client
from scripts._cli import parse_dry_run

logger = structlog.get_logger(__name__)

LOCAL_PATH = BACKEND_DIR / "data" / "kb" / "glossary.jsonl"
S3_KEY = "glossary/glossary.jsonl"


def _local_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _remote_etag(s3: Any, bucket: str, key: str) -> str | None:
    try:
        resp = s3.head_object(Bucket=bucket, Key=key)
        return str(resp.get("ETag", "")).strip('"')
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code", "") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def run(dry_run: bool = True, s3: Any | None = None, bucket: str | None = None) -> bool:
    bucket = bucket if bucket is not None else get_settings().haru_kb_s3_bucket
    if not bucket:
        print("HARU_KB_S3_BUCKET 미설정 — 먼저 create_s3_bucket.py --apply 후 .env 설정 필요")
        return True
    if not LOCAL_PATH.exists():
        print(f"{LOCAL_PATH} 없음 — 먼저 convert_glossary.py 실행 필요")
        return False
    if dry_run:
        logger.info(
            "create_step",
            resource_type="s3_object",
            resource_id=S3_KEY,
            dry_run=True,
            result="would_upload",
        )
        print(f"[dry-run] 업로드 예정: {LOCAL_PATH} → s3://{bucket}/{S3_KEY}")
        print("→ 다음 단계: create_or_sync_kb.py --create --apply")
        return True
    s3 = s3 or get_s3_client()
    local_md5 = _local_md5(LOCAL_PATH)
    if _remote_etag(s3, bucket, S3_KEY) == local_md5:
        logger.info(
            "create_step",
            resource_type="s3_object",
            resource_id=S3_KEY,
            dry_run=False,
            result="already_current",
        )
        print(f"동일 md5 — skip: s3://{bucket}/{S3_KEY}")
    else:
        s3.upload_file(str(LOCAL_PATH), bucket, S3_KEY)
        logger.info(
            "create_step",
            resource_type="s3_object",
            resource_id=S3_KEY,
            dry_run=False,
            result="uploaded",
        )
        print(f"업로드 완료: s3://{bucket}/{S3_KEY}")
    print("→ 다음 단계: create_or_sync_kb.py --create --apply")
    return True


def main(argv: list[str] | None = None) -> int:
    dry_run = parse_dry_run("glossary.jsonl S3 업로드", argv)
    return 0 if run(dry_run=dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
