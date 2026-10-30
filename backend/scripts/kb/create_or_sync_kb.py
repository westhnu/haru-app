"""Bedrock Knowledge Base 생성 및 데이터소스 sync (T-404 + T-405).

--create: S3_VECTORS 스토리지로 KB + S3 데이터소스 생성.
--sync:   데이터소스 ingestion job 시작 후 완료까지 폴링 (kb_admin_service 재활용).
둘 다 지정 가능. --dry-run(기본) 무호출, --apply로만 실제 수행.
KB 생성에는 IAM Role(BEDROCK_KB_ROLE_ARN)이 필요하며, 없으면 안내 후 종료한다.
"""

import argparse
import sys
from typing import Any

import structlog

from app.config import Settings, get_settings
from app.services.bedrock_client import get_bedrock_agent_client
from app.services.kb_admin_service import KbAdminService
from scripts._cli import resolve_account_id

logger = structlog.get_logger(__name__)

KB_NAME = "haru-glossary-kb"
DS_NAME = "haru-glossary-s3"
EMBED_MODEL_ARN = "arn:aws:bedrock:ap-northeast-2::foundation-model/amazon.titan-embed-text-v2:0"
INCLUSION_PREFIX = "glossary/"
INDEX_NAME = "haru-glossary"

ROLE_GUIDE = """먼저 IAM Role을 수동 생성해야 합니다. 필요 권한:
- bedrock:InvokeModel (Titan Embeddings)
- s3:GetObject, s3:ListBucket on arn:aws:s3:::haru-kb-data-{account}/*
- s3vectors:QueryVectors, s3vectors:PutVectors, s3vectors:DeleteVectors
- Trust Policy: Service=bedrock.amazonaws.com
생성 후 ARN을 .env의 BEDROCK_KB_ROLE_ARN에 설정하세요."""


def _kb_config() -> dict[str, Any]:
    return {
        "type": "VECTOR",
        "vectorKnowledgeBaseConfiguration": {"embeddingModelArn": EMBED_MODEL_ARN},
    }


def _storage_config(settings: Settings) -> dict[str, Any]:
    # KI-010: indexArn과 indexName을 함께 보내면 ValidationException.
    # indexArn에 인덱스 식별이 포함되므로 indexName은 전달하지 않는다.
    return {
        "type": "S3_VECTORS",
        "s3VectorsConfiguration": {
            "vectorBucketArn": settings.haru_kb_vector_bucket_arn,
            "indexArn": settings.haru_kb_s3_vector_index_arn,
        },
    }


def _data_source_config(account_id: str, settings: Settings) -> dict[str, Any]:
    bucket_arn = f"arn:aws:s3:::{settings.haru_kb_s3_bucket}"
    return {
        "name": DS_NAME,
        "s3Configuration": {
            "bucketArn": bucket_arn,
            "inclusionPrefixes": [INCLUSION_PREFIX],
        },
        "chunkingConfiguration": {"chunkingStrategy": "NONE"},
    }


def _find_kb_by_name(agent: Any, name: str) -> str | None:
    """동명 KB가 이미 있으면 그 ID를 돌려준다 (페이지네이션)."""
    paginator = agent.get_paginator("list_knowledge_bases")
    for page in paginator.paginate():
        for summary in page.get("knowledgeBaseSummaries", []):
            if summary.get("name") == name:
                return str(summary["knowledgeBaseId"])
    return None


def _find_ds_by_name(agent: Any, kb_id: str, name: str) -> str | None:
    """KB 안에 동명 데이터소스가 있으면 그 ID를 돌려준다 (페이지네이션)."""
    paginator = agent.get_paginator("list_data_sources")
    for page in paginator.paginate(knowledgeBaseId=kb_id):
        for summary in page.get("dataSourceSummaries", []):
            if summary.get("name") == name:
                return str(summary["dataSourceId"])
    return None


def _ensure_kb(agent: Any, settings: Settings) -> str:
    existing = _find_kb_by_name(agent, KB_NAME)
    if existing:
        logger.info(
            "create_step",
            resource_type="knowledge_base",
            resource_id=existing,
            dry_run=False,
            result="already_exists",
        )
        print(f"KB already_exists, reusing: {existing}")
        return existing
    kb = agent.create_knowledge_base(
        name=KB_NAME,
        roleArn=settings.bedrock_kb_role_arn,
        knowledgeBaseConfiguration=_kb_config(),
        storageConfiguration=_storage_config(settings),
    )
    kb_id: str = kb["knowledgeBase"]["knowledgeBaseId"]
    logger.info(
        "create_step",
        resource_type="knowledge_base",
        resource_id=kb_id,
        dry_run=False,
        result="created",
    )
    return kb_id


def _ensure_data_source(agent: Any, kb_id: str, account_id: str, settings: Settings) -> str:
    existing = _find_ds_by_name(agent, kb_id, DS_NAME)
    if existing:
        logger.info(
            "create_step",
            resource_type="data_source",
            resource_id=existing,
            dry_run=False,
            result="already_exists",
        )
        print(f"dataSource already_exists, reusing: {existing}")
        return existing
    ds = agent.create_data_source(knowledgeBaseId=kb_id, **_split_ds(account_id, settings))
    ds_id: str = ds["dataSource"]["dataSourceId"]
    logger.info(
        "create_step",
        resource_type="data_source",
        resource_id=ds_id,
        dry_run=False,
        result="created",
    )
    return ds_id


def _create_kb(agent: Any, account_id: str, settings: Settings) -> str:
    kb_id = _ensure_kb(agent, settings)
    ds_id = _ensure_data_source(agent, kb_id, account_id, settings)
    print(f"KB: {kb_id} / dataSource: {ds_id}")
    print(f"→ .env에 추가: BEDROCK_KB_ID={kb_id}")
    return kb_id


def _split_ds(account_id: str, settings: Settings) -> dict[str, Any]:
    cfg = _data_source_config(account_id, settings)
    name = cfg.pop("name")
    return {
        "name": name,
        "dataSourceConfiguration": {"type": "S3", "s3Configuration": cfg["s3Configuration"]},
        "vectorIngestionConfiguration": {"chunkingConfiguration": cfg["chunkingConfiguration"]},
    }


def _do_create(dry_run: bool, agent: Any, account_id: str, settings: Settings) -> bool:
    if dry_run:
        logger.info(
            "create_step",
            resource_type="knowledge_base",
            resource_id=KB_NAME,
            dry_run=True,
            result="would_create",
        )
        print(f"[dry-run] 생성 예정 KB: {KB_NAME} (S3_VECTORS, Titan v2, chunking=NONE)")
        print("  (apply 시 list_knowledge_bases로 동명 KB 존재 확인 후 없으면 생성)")
        print(f"  vectorBucketArn={settings.haru_kb_vector_bucket_arn or '<미설정>'}")
        print(f"  indexArn={settings.haru_kb_s3_vector_index_arn or '<미설정>'}")
        print("  (indexName 미전달 — indexArn에 포함, KI-010)")
        print(f"  dataSource: s3://{settings.haru_kb_s3_bucket or '<미설정>'}/{INCLUSION_PREFIX}")
        print("→ 생성 후 .env에 추가: BEDROCK_KB_ID=<id>")
        return True
    if not settings.bedrock_kb_role_arn:
        print(ROLE_GUIDE.replace("{account}", account_id))
        return False
    _create_kb(agent, account_id, settings)
    return True


def _do_sync(dry_run: bool, agent: Any, settings: Settings) -> bool:
    if dry_run:
        logger.info(
            "create_step",
            resource_type="ingestion_job",
            resource_id=settings.bedrock_kb_id or "<미설정>",
            dry_run=True,
            result="would_sync",
        )
        print(f"[dry-run] sync 예정: KB={settings.bedrock_kb_id or '<미설정>'}")
        return True
    admin = KbAdminService(settings, agent_client=agent)
    job_id = admin.start_sync(settings.bedrock_kb_id, _resolve_ds_id(agent, settings))
    status = admin.poll_sync(settings.bedrock_kb_id, job_id)
    print(f"sync 완료: job={job_id} status={status}")
    return status == "COMPLETE"


def _resolve_ds_id(agent: Any, settings: Settings) -> str:
    resp = agent.list_data_sources(knowledgeBaseId=settings.bedrock_kb_id)
    return str(resp["dataSourceSummaries"][0]["dataSourceId"])


def run(
    dry_run: bool = True,
    do_create: bool = False,
    do_sync: bool = False,
    agent: Any | None = None,
    sts: Any | None = None,
    settings: Settings | None = None,
) -> bool:
    settings = settings or get_settings()
    account_id = resolve_account_id(dry_run, sts=sts)
    agent = agent or (None if dry_run else get_bedrock_agent_client())
    results: list[bool] = []
    if do_create:
        results.append(_do_create(dry_run, agent, account_id, settings))
    if do_sync:
        results.append(_do_sync(dry_run, agent, settings))
    if not results:
        print("아무 모드도 지정되지 않음 (--create / --sync 중 하나 이상 필요)")
        return False
    return all(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KB 생성·sync")
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--sync", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    ok = run(dry_run=not args.apply, do_create=args.create, do_sync=args.sync)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
