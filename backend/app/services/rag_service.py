"""Bedrock Knowledge Base RetrieveAndGenerate 래퍼 (기획안 §13.4 패턴 A).

KB ID가 없으면 Bedrock을 호출하지 않고 mock 응답을 돌려준다. 어느 경로든 응답은 반드시
`apply_output_guard`를 거치고, 질의는 반드시 `mask_pii`를 거친 뒤에만 외부로 나간다.
근거가 없을 때의 처리는 질의 종류에 따라 다르다 (`resolve_answer`, 결정 1).
"""

import time
from typing import Any, Literal

import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings
from app.core.guardrail import NO_EVIDENCE_STOCK_ANSWER, apply_output_guard, mask_pii
from app.core.prompts import RAG_PROMPT_TEMPLATES
from app.models.rag import AnswerSource, ContextType, RagCitation, RagResponse
from app.services.bedrock_client import get_agent_runtime_client
from app.services.exceptions import BedrockError, BedrockRetrievalError

MAX_TOKENS = 2048
MOCK_MODEL_ID = "mock"
# KB 데이터 소스는 S3(§13.3)가 기본이고, 웹 크롤러 소스를 붙일 경우를 대비해 WEB도 받는다.
REFERENCE_SOURCE_FIELDS: tuple[tuple[str, str], ...] = (
    ("s3Location", "uri"),
    ("webLocation", "url"),
)

logger = structlog.get_logger(__name__)


# 하위 호환: 기존 호출처(api/v1/poc.py의 except)가 그대로 신규 Bedrock 예외를 잡도록
# BedrockError를 베이스로 재노출한다. 신규 코드는 services.exceptions를 직접 import 한다.
RagServiceError = BedrockError


class RagService:
    def __init__(self, settings: Settings, agent_client: Any | None = None) -> None:
        self._settings = settings
        self._client = agent_client

    def ask(self, query: str, context_type: ContextType = "general") -> RagResponse:
        safe_query = mask_pii(query)
        if not self._settings.bedrock_kb_id:
            return self._mock_response(safe_query)

        raw = self._retrieve_and_generate(
            safe_query,
            guardrail_id=self._settings.bedrock_guardrail_id or None,
            guardrail_version=self._settings.bedrock_guardrail_version,
            context_type=context_type,
        )
        citations = parse_citations(raw.get("citations", []))
        answer, source = resolve_answer(raw["output"]["text"], citations, context_type)
        return RagResponse(
            answer=apply_output_guard(answer),
            citations=citations,
            source=source,
            model_id=self._settings.bedrock_model_id,
        )

    def _mock_response(self, query: str) -> RagResponse:
        logger.info("rag_mock_response", query_length=len(query))
        answer = f"[MOCK] Knowledge Base가 설정되지 않아 개발용 응답을 반환합니다. 질문: {query}"
        # mock에는 실제 근거 문서가 없으므로 출처를 지어내지 않고 빈 배열로 둔다 (원칙 2).
        return RagResponse(
            answer=apply_output_guard(answer),
            source="mock",
            model_id=MOCK_MODEL_ID,
            is_mock=True,
        )

    def _retrieve_and_generate(
        self,
        query: str,
        guardrail_id: str | None = None,
        guardrail_version: str = "DRAFT",
        context_type: Literal["glossary", "stock", "general"] = "general",
    ) -> dict[str, Any]:
        client = self._client or get_agent_runtime_client()
        started = time.perf_counter()
        request = self._build_request(query, context_type, guardrail_id, guardrail_version)
        try:
            response: dict[str, Any] = client.retrieve_and_generate(**request)
        except (ClientError, BotoCoreError) as exc:
            logger.error("rag_bedrock_failed", error_type=type(exc).__name__, error=str(exc))
            # Phase 5 실호출 시 ResourceNotFound→NotAvailable 등 세분 변환을 활성화한다.
            raise BedrockRetrievalError("RetrieveAndGenerate 호출 실패") from exc

        logger.info(
            "rag_bedrock_succeeded",
            context_type=context_type,
            latency_ms=round((time.perf_counter() - started) * 1000),
            citation_count=len(response.get("citations", [])),
            guardrail_action=response.get("guardrailAction", "NONE"),
        )
        return response

    def _build_request(
        self,
        query: str,
        context_type: ContextType,
        guardrail_id: str | None = None,
        guardrail_version: str = "DRAFT",
    ) -> dict[str, Any]:
        generation: dict[str, Any] = {
            "promptTemplate": {"textPromptTemplate": RAG_PROMPT_TEMPLATES[context_type]},
            "inferenceConfig": {"textInferenceConfig": {"maxTokens": MAX_TOKENS}},
        }
        # REQ-GR-02: guardrail_id가 있으면 호출 kwargs에 Guardrail 설정을 반드시 포함한다.
        if guardrail_id:
            generation["guardrailConfiguration"] = {
                "guardrailId": guardrail_id,
                "guardrailVersion": guardrail_version,
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


def resolve_answer(
    text: str, citations: list[RagCitation], context_type: ContextType
) -> tuple[str, AnswerSource]:
    """근거 유무와 질의 종류로 최종 답변과 그 출처 유형을 정한다 (결정 1)."""
    if citations:
        return text, "knowledge_base"
    if context_type == "stock":
        # 원칙 2: 종목·재무 질의는 근거 없이 모델 지식으로 답하지 않는다.
        return NO_EVIDENCE_STOCK_ANSWER, "no_evidence"
    return text, "general_knowledge"


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
