"""models/rag.py 하위 호환·신규 필드 검증 (T-103)."""

import pytest
from pydantic import ValidationError

from app.core.guardrail import DISCLAIMER
from app.models.rag import RagCitation, RagResponse


def test_citation_backward_compatible_without_similarity() -> None:
    citation = RagCitation(excerpt="PER = Price / EPS", source="s3://haru-kb/glossary/per.jsonl")

    assert citation.similarity is None


def test_citation_accepts_similarity_in_range() -> None:
    citation = RagCitation(excerpt="x", source="s3://x", similarity=0.87)

    assert citation.similarity == 0.87


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_citation_rejects_similarity_out_of_range(bad: float) -> None:
    with pytest.raises(ValidationError):
        RagCitation(excerpt="x", source="s3://x", similarity=bad)


def test_response_new_fields_have_defaults() -> None:
    # 기존 생성 지점과 동일한 최소 인자로 만들어도 신규 필드가 default로 채워진다.
    response = RagResponse(answer="PER은 ...", source="knowledge_base", model_id="mock")

    assert response.context_type == "general"
    assert response.guardrail_action is None
    assert response.is_mock is False
    assert response.disclaimer == DISCLAIMER


@pytest.mark.parametrize("empty", ["", "   "])
def test_response_disclaimer_must_not_be_empty(empty: str) -> None:
    with pytest.raises(ValidationError):
        RagResponse(answer="a", source="mock", model_id="mock", disclaimer=empty)
