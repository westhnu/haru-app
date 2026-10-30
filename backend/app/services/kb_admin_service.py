"""Bedrock Knowledge Base 동기화·상태 조회 서비스 (tasks T-202).

설계 drift: tasks.md가 가정한 BedrockClient.start_kb_sync/poll_kb_sync는 여기(KbAdminService)로
이관했다. RAG 호출은 rag_service가, KB 관리(sync/poll/describe)는 이 모듈이 담당한다.

Phase 2에서는 KB_ID가 비면 Fake 분기로 동작하고 실제 bedrock-agent 호출은 하지 않는다.
Phase 5에서 실호출(start_ingestion_job / get_ingestion_job / get_knowledge_base)을 붙이고,
boto3 예외를 services.exceptions의 Bedrock 예외 3종으로 변환한다.
"""

import time
from typing import Any

import structlog
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.bedrock_client import get_bedrock_agent_client
from app.services.exceptions import BedrockNotAvailableError, BedrockRetrievalError

# Ingestion job 폴링 기본값. design.md 하네스: KB sync 타임아웃 600초.
DEFAULT_SYNC_TIMEOUT_S = 600
POLL_INTERVAL_S = 15
COMPLETE_STATUS = "COMPLETE"
FAILED_STATUSES: frozenset[str] = frozenset({"FAILED"})
# Fake 분기(KB_ID 미설정)에서 돌려주는 고정값.
MOCK_INGESTION_JOB_ID = "mock-job"
MOCK_STATUS = COMPLETE_STATUS

logger = structlog.get_logger(__name__)


class KbStatus(BaseModel):
    kb_id: str
    status: str
    last_sync_at: str | None = None
    indexed_chunks: int | None = None
    is_mock: bool = False


class KbAdminService:
    def __init__(self, settings: Settings, agent_client: Any | None = None) -> None:
        self._settings = settings
        self._client = agent_client

    def _is_fake(self, kb_id: str = "") -> bool:
        # KB_ID가 비면 실제 리소스가 없으므로 호출 자체를 하지 않는다 (원칙 2).
        # KI-011: fresh create->sync는 settings엔 아직 없지만 방금 만든 kb_id를 인자로 받는다.
        # 전달된 kb_id가 있으면 실제 리소스가 존재하므로 fake로 보지 않는다.
        return not (kb_id or self._settings.bedrock_kb_id)

    def start_sync(self, kb_id: str, data_source_id: str) -> str:
        if self._is_fake(kb_id):
            logger.info("kb_sync_mock", kb_id=kb_id or "none")
            return MOCK_INGESTION_JOB_ID
        client = self._client or get_bedrock_agent_client()
        try:
            response = client.start_ingestion_job(
                knowledgeBaseId=kb_id, dataSourceId=data_source_id
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error("kb_sync_start_failed", error_type=type(exc).__name__)
            raise BedrockRetrievalError("KB sync 시작 실패") from exc
        job_id: str = response["ingestionJob"]["ingestionJobId"]
        logger.info("kb_sync_started", kb_id=kb_id, ingestion_job_id=job_id)
        return job_id

    def poll_sync(
        self,
        kb_id: str,
        ingestion_job_id: str,
        *,
        data_source_id: str,
        timeout_s: int = DEFAULT_SYNC_TIMEOUT_S,
        poll_interval_s: int = POLL_INTERVAL_S,
    ) -> str:
        # KI-014: get_ingestion_job은 dataSourceId도 필수. keyword-only로 전달 강제.
        if self._is_fake(kb_id):
            return MOCK_STATUS
        client = self._client or get_bedrock_agent_client()
        deadline = time.monotonic() + timeout_s
        while True:
            status = self._fetch_ingestion_status(client, kb_id, ingestion_job_id, data_source_id)
            if status == COMPLETE_STATUS or status in FAILED_STATUSES:
                return status
            if time.monotonic() >= deadline:
                return status
            time.sleep(poll_interval_s)

    def _fetch_ingestion_status(
        self, client: Any, kb_id: str, ingestion_job_id: str, data_source_id: str
    ) -> str:
        try:
            response = client.get_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error("kb_sync_poll_failed", error_type=type(exc).__name__)
            raise BedrockRetrievalError("KB sync 폴링 실패") from exc
        status: str = response["ingestionJob"]["status"]
        return status

    def get_status(self, kb_id: str) -> KbStatus:
        if self._is_fake(kb_id):
            return KbStatus(kb_id=kb_id or "none", status=MOCK_STATUS, is_mock=True)
        client = self._client or get_bedrock_agent_client()
        try:
            response = client.get_knowledge_base(knowledgeBaseId=kb_id)
        except (ClientError, BotoCoreError) as exc:
            logger.error("kb_status_failed", error_type=type(exc).__name__)
            raise BedrockNotAvailableError("KB 상태 조회 실패") from exc
        kb = response["knowledgeBase"]
        return KbStatus(
            kb_id=kb_id,
            status=kb.get("status", "UNKNOWN"),
            last_sync_at=str(kb["updatedAt"]) if kb.get("updatedAt") else None,
        )


def get_kb_admin_service() -> KbAdminService:
    return KbAdminService(settings=get_settings())
