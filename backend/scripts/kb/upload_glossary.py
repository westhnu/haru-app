"""용어별 .txt 파일을 데이터소스 S3 버킷에 업로드 (T-403, KI-015 재설계).

backend/data/kb/terms/term_*.txt → s3://{HARU_KB_S3_BUCKET}/glossary/term_NNN.txt
per-file md5 멱등: 원격 ETag(single-part는 md5)와 같으면 skip, 다르면 put_object.
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

LOCAL_DIR = BACKEND_DIR / "data" / "kb" / "terms"
S3_PREFIX = "glossary/"
EXPECTED_MIN_FILES = 1


def _local_files() -> list[Path]:
    return sorted(LOCAL_DIR.glob("term_*.txt"))


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _remote_etag(s3: Any, bucket: str, key: str) -> str | None:
    try:
        resp = s3.head_object(Bucket=bucket, Key=key)
        return str(resp.get("ETag", "")).strip('"')
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code", "") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def _upload_one(s3: Any, bucket: str, path: Path) -> str:
    key = f"{S3_PREFIX}{path.name}"
    if _remote_etag(s3, bucket, key) == _md5(path):
        return "skipped_unchanged"
    s3.put_object(Bucket=bucket, Key=key, Body=path.read_bytes())
    return "uploaded"


def run(dry_run: bool = True, s3: Any | None = None, bucket: str | None = None) -> bool:
    bucket = bucket if bucket is not None else get_settings().haru_kb_s3_bucket
    files = _local_files()
    if not bucket:
        print("HARU_KB_S3_BUCKET 미설정 — 먼저 create_s3_bucket.py --apply 후 .env 설정 필요")
        return True
    if len(files) < EXPECTED_MIN_FILES:
        print(f"로컬 .txt 없음({LOCAL_DIR}) — 먼저 convert_glossary.py --apply 실행 필요")
        return False
    if dry_run:
        total_bytes = sum(f.stat().st_size for f in files)
        print(f"[dry-run] {len(files)} files would be uploaded (0 skipped)")
        print(f"  대상: s3://{bucket}/{S3_PREFIX}term_NNN.txt, 총 {total_bytes:,} bytes")
        return True
    s3 = s3 or get_s3_client()
    uploaded = skipped = 0
    for path in files:
        result = _upload_one(s3, bucket, path)
        uploaded += result == "uploaded"
        skipped += result == "skipped_unchanged"
    logger.info("glossary_uploaded", uploaded=uploaded, skipped=skipped, total=len(files))
    print(f"uploaded {uploaded}, skipped {skipped}, total {len(files)}")
    return True


def main(argv: list[str] | None = None) -> int:
    dry_run = parse_dry_run("용어 .txt S3 업로드", argv)
    return 0 if run(dry_run=dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
