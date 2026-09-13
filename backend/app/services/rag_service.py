"""Bedrock Knowledge Base RetrieveAndGenerate 래퍼 (기획안 §13.4 패턴 A).

KB ID가 없으면 Bedrock을 호출하지 않고 mock 응답을 돌려준다. 어느 경로든 응답은 반드시
`apply_output_guard`를 거치고, 질의는 반드시 `mask_pii`를 거친 뒤에만 외부로 나간다.
"""

import time
from typing import Any

import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings
from app.core.guardrail import apply_output_guard, mask_pii
from app.core.prompts import RAG_PROMPT_TEMPLATE
from app.models.rag import RagCitation, RagResponse
from app.services.bedrock_client import get_agent_runtime_client

MAX_TOKENS = 2048
MOCK_MODEL_ID = "mock"
# KB 데이터 소스는 S3(§13.3)가 기본이고, 웹 크롤러 소스를 붙일 경우를 대비해 WEB도 받는다.
REFERENCE_SOURCE_FIELDS: tuple[tuple[str, str], ...] = (
    ("s3Location", "uri"),
    ("webLocation", "url"),
)

logger = structlog.get_logger(__name__)


class RagServiceError(Exception):
    """Bedrock 호출 실패. 원인 예외는 __cause__로 보존한다."""


class RagService:
    def __init__(self, settings: Settings, agent_client: Any | None = None) -> None:
        self._settings = settings
        self._client = agent_client

    def ask(self, query: str) -> RagResponse:
        safe_query = mask_pii(query)
        if not self._settings.bedrock_kb_id:
            return self._mock_response(safe_query)

        raw = self._retrieve_and_generate(safe_query)
        return RagResponse(
            answer=apply_output_guard(raw["output"]["text"]),
            citations=parse_citations(raw.get("citations", [])),
            model_id=self._settings.bedrock_model_id,
        )

    def _mock_response(self, query: str) -> RagResponse:
        logger.info("rag_mock_response", query_length=len(query))
        answer = f"[MOCK] Knowledge Base가 설정되지 않아 개발용 응답을 반환합니다. 질문: {query}"
        # mock에는 실제 근거 문서가 없으므로 출처를 지어내지 않고 빈 배열로 둔다 (원칙 2).
        return RagResponse(answer=apply_output_guard(answer), model_id=MOCK_MODEL_ID)

    def _retrieve_and_generate(self, query: str) -> dict[str, Any]:
        client = self._client or get_agent_runtime_client()
        started = time.perf_counter()
        try:
            response: dict[str, Any] = client.retrieve_and_generate(**self._build_request(query))
        except (ClientError, BotoCoreError) as exc:
            logger.error("rag_bedrock_failed", error_type=type(exc).__name__, error=str(exc))
            raise RagServiceError("RetrieveAndGenerate 호출 실패") from exc

        logger.info(
            "rag_bedrock_succeeded",
            latency_ms=round((time.perf_counter() - started) * 1000),
            citation_count=len(response.get("citations", [])),
            guardrail_action=response.get("guardrailAction", "NONE"),
        )
        return response

    def _build_request(self, query: str) -> dict[str, Any]:
        generation: dict[str, Any] = {
            "promptTemplate": {"textPromptTemplate": RAG_PROMPT_TEMPLATE},
            "inferenceConfig": {"textInferenceConfig": {"maxTokens": MAX_TOKENS}},
        }
        if self._settings.bedrock_guardrail_id:
            generation["guardrailConfiguration"] = {
                "guardrailId": self._settings.bedrock_guardrail_id,
                "guardrailVersion": self._settings.bedrock_guardrail_version,
            }
        knowledge_base = {
            "knowledgeBaseId": self._settings.bedrock_kb_id,
            "modelArn": self._settings.bedrock_model_id,
            "generationConfiguration": generation,
        }
        return {
            "input": {"text": query},
            "retrieveAndGenerateConfiguration": {
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": knowledge_base,
            },
        }


def parse_citations(raw_citations: list[dict[str, Any]]) -> list[RagCitation]:
    """RetrieveAndGenerate citations → RagCitation 목록.

    같은 청크가 여러 문장에서 인용되면 한 번만 남긴다.
    """
    unique: dict[tuple[str, str], RagCitation] = {}
    for citation in raw_citations:
        for reference in citation.get("retrievedReferences", []):
            source = _reference_source(reference.get("location", {}))
            excerpt = reference.get("content", {}).get("text", "")
            # 출처를 특정할 수 없는 근거는 인용으로 내보내지 않는다 (원칙 2).
            if source and excerpt:
                unique.setdefault((source, excerpt), RagCitation(excerpt=excerpt, source=source))
    return list(unique.values())


def _reference_source(location: dict[str, Any]) -> str | None:
    for location_key, field in REFERENCE_SOURCE_FIELDS:
        if value := location.get(location_key, {}).get(field):
            return str(value)
    return None


def get_rag_service() -> RagService:
    return RagService(settings=get_settings())
