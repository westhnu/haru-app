"""disclaimer 빈 문자열 금지 회귀 방지 (T-104, 원칙 5).

이 테스트는 지금 바로 통과해야 한다 — RagResponse의 field_validator가 빈 disclaimer를 막는다.
"""

import pytest
from pydantic import ValidationError

from app.core.guardrail import DISCLAIMER
from app.models.rag import RagResponse


@pytest.mark.parametrize("empty", ["", "   ", "\n\t"])
def test_rag_response_rejects_empty_disclaimer(empty: str) -> None:
    with pytest.raises(ValidationError):
        RagResponse(answer="a", source="mock", model_id="mock", disclaimer=empty)


def test_rag_response_default_disclaimer_is_non_empty() -> None:
    response = RagResponse(answer="a", source="mock", model_id="mock")

    assert response.disclaimer == DISCLAIMER
    assert response.disclaimer.strip()
