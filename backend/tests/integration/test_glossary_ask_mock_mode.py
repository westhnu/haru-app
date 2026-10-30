"""KB_ID 미설정 시 RagService가 mock 응답을 반환하는지 (T-203).

실제 Bedrock 호출이 일어나면 안 된다 — ExplodingClient로 호출 시 즉시 실패시킨다.
"""

from typing import Any

from app.config import Settings
from app.core.guardrail import DISCLAIMER
from app.services.rag_service import RagService


class ExplodingClient:
    def retrieve_and_generate(self, **request: Any) -> dict[str, Any]:
        raise AssertionError("KB 미설정 상태에서는 Bedrock을 호출하면 안 된다")


def _service_without_kb() -> RagService:
    settings = Settings(_env_file=None, bedrock_kb_id="")
    return RagService(settings, agent_client=ExplodingClient())


def test_ask_mock_mode_sets_mock_source() -> None:
    response = _service_without_kb().ask("PER이 뭐야?", context_type="glossary")

    assert response.source == "mock"
    assert response.model_id == "mock"
    assert response.is_mock is True


def test_ask_mock_mode_has_valid_disclaimer_and_no_citations() -> None:
    response = _service_without_kb().ask("PER이 뭐야?", context_type="glossary")

    assert response.disclaimer == DISCLAIMER
    assert response.disclaimer.strip()
    assert response.citations == []
