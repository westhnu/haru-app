"""rag_service context_type 분기 + similarity 파싱 + summary_source 매트릭스 (T-301).

Fake Bedrock 응답을 주입해 실호출 없이 분기 로직만 검증한다.
"""

from typing import Any

from app.config import Settings
from app.core.guardrail import NO_EVIDENCE_STOCK_ANSWER
from app.models.rag import ContextType
from app.services.rag_service import _extract_similarity, parse_citations

KB_ID = "TESTKB0001"


class FakeAgent:
    def __init__(self, text: str, citations: list[dict[str, Any]]) -> None:
        self._response = {"output": {"text": text}, "citations": citations}

    def retrieve_and_generate(self, **request: Any) -> dict[str, Any]:
        return self._response


def _citation(excerpt: str, uri: str, score: float | None) -> dict[str, Any]:
    reference: dict[str, Any] = {
        "content": {"text": excerpt},
        "location": {"type": "S3", "s3Location": {"uri": uri}},
    }
    if score is not None:
        reference["metadata"] = {"score": score}
    return {"retrievedReferences": [reference]}


def _ask(context_type: ContextType, citations: list[dict[str, Any]]) -> Any:
    from app.services.rag_service import RagService

    settings = Settings(_env_file=None, bedrock_kb_id=KB_ID)
    agent = FakeAgent("원본 답변 텍스트", citations)
    return RagService(settings, agent_client=agent).ask("질문", context_type=context_type)


# --- similarity 파싱 (결정 A) ---------------------------------------------------


def test_extract_similarity_metadata_score() -> None:
    assert _extract_similarity({"metadata": {"score": 0.87}}) == 0.87


def test_extract_similarity_relevance_score_fallback() -> None:
    assert _extract_similarity({"relevanceScore": 0.62}) == 0.62


def test_extract_similarity_missing_returns_none() -> None:
    assert _extract_similarity({"content": {"text": "x"}}) is None


def test_parse_citations_maps_similarity() -> None:
    parsed = parse_citations([_citation("PER=...", "s3://kb/per.jsonl", 0.87)])

    assert parsed[0].similarity == 0.87


# --- context 분기 + summary_source 매트릭스 (결정 B) ----------------------------


def test_general_high_similarity_is_bedrock() -> None:
    response = _ask("general", [_citation("근거", "s3://kb/a", 0.87)])

    assert response.source == "knowledge_base"
    assert response.summary_source == "bedrock"


def test_stock_low_similarity_refuses() -> None:
    response = _ask("stock", [_citation("근거", "s3://kb/a", 0.41)])

    assert NO_EVIDENCE_STOCK_ANSWER in response.answer
    assert response.source == "no_evidence"
    assert response.summary_source == "template"


def test_glossary_low_similarity_uses_general_knowledge() -> None:
    response = _ask("glossary", [_citation("근거", "s3://kb/a", 0.41)])

    assert response.source == "general_knowledge"
    assert response.summary_source == "general_knowledge"


def test_general_unchanged_when_grounded() -> None:
    # 기존 동작 유지: general + 충분한 근거 → knowledge_base/bedrock.
    response = _ask("general", [_citation("근거", "s3://kb/a", 0.62)])

    assert response.source == "knowledge_base"
    assert response.summary_source == "bedrock"


def test_no_citations_glossary_general_knowledge() -> None:
    # citation이 아예 없을 때도 glossary는 일반지식 허용.
    response = _ask("glossary", [])

    assert response.source == "general_knowledge"
    assert response.summary_source == "general_knowledge"
