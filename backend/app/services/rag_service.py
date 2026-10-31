"""Bedrock Knowledge Base RetrieveAndGenerate 래퍼 (기획안 §13.4 패턴 A).

KB ID가 없으면 Bedrock을 호출하지 않고 mock 응답을 돌려준다. 어느 경로든 응답은 반드시
`apply_output_guard`를 거치고, 질의는 반드시 `mask_pii`를 거친 뒤에만 외부로 나간다.
근거가 없을 때의 처리는 질의 종류에 따라 다르다 (`resolve_answer`, 결정 1).
"""

import time
from dataclasses import dataclass
from typing import Any, Literal

import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings
from app.core.guardrail import (
    DISCLAIMER,
    GUARDRAIL_BLOCKED_ANSWER,
    NO_EVIDENCE_STOCK_ANSWER,
    apply_output_guard,
    mask_pii,
)
from app.core.prompts import RAG_PROMPT_TEMPLATES
from app.models.rag import (
    AnswerSource,
    ContextType,
    GuardrailAction,
    RagCitation,
    RagResponse,
    SummarySource,
)
from app.services.bedrock_client import get_agent_runtime_client
from app.services.exceptions import BedrockError, BedrockRetrievalError

MAX_TOKENS = 2048
MOCK_MODEL_ID = "mock"
# REQ-RAG-03/04: 이 미만이면 KB 근거가 불충분하다고 본다.
SIMILARITY_THRESHOLD = 0.5
# KB 데이터 소스는 S3(§13.3)가 기본이고, 웹 크롤러 소스를 붙일 경우를 대비해 WEB도 받는다.
REFERENCE_SOURCE_FIELDS: tuple[tuple[str, str], ...] = (
    ("s3Location", "uri"),
    ("webLocation", "url"),
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AnswerResolution:
    """resolve_answer 단일 반환 타입. (text, source) tuple을 대체한다 (결정 B).

    source는 근거 출처, summary_source는 생성 방식 — 서로 다른 레이어의 메타데이터다.
    """

    text: str
    source: AnswerSource
    summary_source: SummarySource
    similarity_max: float | None = None


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
            return self._mock_response(safe_query, context_type)

        raw = self._retrieve_and_generate(
            safe_query,
            guardrail_id=self._settings.bedrock_guardrail_id or None,
            guardrail_version=self._settings.bedrock_guardrail_version,
            context_type=context_type,
        )
        action = _guardrail_action(raw, self._settings.bedrock_guardrail_id)
        if action == "intervened":
            return self._blocked_response(raw["output"]["text"], context_type)
        citations = parse_citations(raw.get("citations", []))
        resolution = resolve_answer(raw["output"]["text"], citations, context_type)
        logger.info(
            "rag_ask",
            context_type=context_type,
            similarity_max=resolution.similarity_max,
            summary_source=resolution.summary_source,
        )
        return RagResponse(
            answer=apply_output_guard(resolution.text),
            citations=citations,
            source=resolution.source,
            summary_source=resolution.summary_source,
            context_type=context_type,
            model_id=self._settings.bedrock_model_id,
            guardrail_action=action,
        )

    def _blocked_response(self, text: str, context_type: ContextType) -> RagResponse:
        """Guardrail 차단 응답 (KI-020).

        Bedrock이 준 차단 메시지를 쓰되, 면책 문구뿐이면(구 설정) 안내 문구로 대체한다.
        """
        body = text.replace(DISCLAIMER, "").strip() or GUARDRAIL_BLOCKED_ANSWER
        logger.info("guardrail_blocked", context_type=context_type, guardrail_action="intervened")
        return RagResponse(
            answer=apply_output_guard(body),
            citations=[],
            source="guardrail_blocked",
            summary_source="template",
            context_type=context_type,
            model_id=self._settings.bedrock_model_id,
            guardrail_action="intervened",
        )

    def _mock_response(self, query: str, context_type: ContextType = "general") -> RagResponse:
        logger.info("rag_mock_response", query_length=len(query), context_type=context_type)
        answer = f"[MOCK] Knowledge Base가 설정되지 않아 개발용 응답을 반환합니다. 질문: {query}"
        # mock에는 실제 근거 문서가 없으므로 출처를 지어내지 않고 빈 배열로 둔다 (원칙 2).
        return RagResponse(
            answer=apply_output_guard(answer),
            source="mock",
            summary_source="template",
            context_type=context_type,
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


def _max_similarity(citations: list[RagCitation]) -> float | None:
    """citation similarity 중 최댓값. similarity가 하나도 없으면 None."""
    scores = [c.similarity for c in citations if c.similarity is not None]
    return max(scores) if scores else None


def _guardrail_action(raw: dict[str, Any], guardrail_id: str) -> GuardrailAction | None:
    """Guardrail 미연결이면 None, 연결됐으면 Bedrock guardrailAction을 소문자 계약값으로 바꾼다."""
    if not guardrail_id:
        return None
    return "intervened" if raw.get("guardrailAction") == "INTERVENED" else "none"


def resolve_answer(
    text: str, citations: list[RagCitation], context_type: ContextType
) -> AnswerResolution:
    """근거 유무·유사도·질의 종류로 최종 답변과 메타데이터를 정한다 (결정 1 + REQ-RAG-03/04)."""
    similarity_max = _max_similarity(citations)
    grounded = bool(citations) and (
        similarity_max is None or similarity_max >= SIMILARITY_THRESHOLD
    )
    if grounded:
        return AnswerResolution(
            text=text,
            source="knowledge_base",
            summary_source="bedrock",
            similarity_max=similarity_max,
        )
    if context_type == "stock":
        # REQ-RAG-04: 종목·재무 질의는 근거 불충분 시 일반지식 대신 거절 문구(= template).
        return AnswerResolution(
            text=NO_EVIDENCE_STOCK_ANSWER,
            source="no_evidence",
            summary_source="template",
            similarity_max=similarity_max,
        )
    # glossary·general: 근거 불충분 시 LLM 일반지식 허용 (REQ-RAG-03).
    return AnswerResolution(
        text=text,
        source="general_knowledge",
        summary_source="general_knowledge",
        similarity_max=similarity_max,
    )


# Bedrock KB가 유사도 점수를 어느 필드로 내려주는지는 Phase 5 실측에서 확정한다.
# 지금은 알려진 후보 2경로를 순서대로 시도한다 (실측 후 1줄 조정 예정).
SIMILARITY_FIELD_PATHS: tuple[tuple[str, ...], ...] = (("metadata", "score"), ("relevanceScore",))


def _extract_similarity(reference: dict[str, Any]) -> float | None:
    for path in SIMILARITY_FIELD_PATHS:
        node: Any = reference
        try:
            for key in path:
                node = node[key]
            return float(node)
        except (KeyError, TypeError):
            continue
    return None


def parse_citations(raw_citations: list[dict[str, Any]]) -> list[RagCitation]:
    """RetrieveAndGenerate citations → RagCitation 목록.

    같은 청크가 여러 문장에서 인용되면 한 번만 남긴다. 중복 시 similarity는 먼저 본 값을 유지한다.
    """
    unique: dict[tuple[str, str], RagCitation] = {}
    for citation in raw_citations:
        for reference in citation.get("retrievedReferences", []):
            source = _reference_source(reference.get("location", {}))
            excerpt = reference.get("content", {}).get("text", "")
            # 출처를 특정할 수 없는 근거는 인용으로 내보내지 않는다 (원칙 2).
            if source and excerpt:
                unique.setdefault(
                    (source, excerpt),
                    RagCitation(
                        excerpt=excerpt, source=source, similarity=_extract_similarity(reference)
                    ),
                )
    return list(unique.values())


def _reference_source(location: dict[str, Any]) -> str | None:
    for location_key, field in REFERENCE_SOURCE_FIELDS:
        if value := location.get(location_key, {}).get(field):
            return str(value)
    return None


def get_rag_service() -> RagService:
    return RagService(settings=get_settings())
