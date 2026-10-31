"""KI-020 C: Guardrail INTERVENED 응답을 '면책 문구만' 대신 차단 안내로 돌려준다."""

from typing import Any

import pytest

from app.config import Settings
from app.core.guardrail import DISCLAIMER, GUARDRAIL_BLOCKED_ANSWER, enforce_disclaimer
from app.services.rag_service import RagService

KB_ID = "KB-TEST"
GUARDRAIL_ID = "gr-test"


class FakeAgent:
    def __init__(
        self, text: str, action: str, citations: list[dict[str, Any]] | None = None
    ) -> None:
        self._response = {
            "output": {"text": text},
            "citations": citations or [],
            "guardrailAction": action,
        }
        self.requests: list[dict[str, Any]] = []

    def retrieve_and_generate(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return self._response


def _cite(excerpt: str = "ROE는 자기자본이익률") -> dict[str, Any]:
    ref = {
        "content": {"text": excerpt},
        "location": {"s3Location": {"uri": "s3://kb/term_001.txt"}},
    }
    return {"retrievedReferences": [ref]}


def _ask(agent: FakeAgent, guardrail_id: str = GUARDRAIL_ID) -> Any:
    settings = Settings(_env_file=None, bedrock_kb_id=KB_ID, bedrock_guardrail_id=guardrail_id)
    return RagService(settings, agent_client=agent).ask("ROE 설명해줘", context_type="glossary")


def test_intervened_returns_blocked_answer_ki020() -> None:
    resp = _ask(FakeAgent(GUARDRAIL_BLOCKED_ANSWER, "INTERVENED", citations=[_cite()]))
    assert resp.answer == f"{GUARDRAIL_BLOCKED_ANSWER}\n\n{DISCLAIMER}"
    assert resp.source == "guardrail_blocked"
    assert resp.citations == []
    assert resp.disclaimer.strip()
    assert resp.guardrail_action == "intervened"


def test_intervened_with_legacy_disclaimer_message_not_empty_ki020() -> None:
    # 구 설정: 차단 메시지 == 면책 문구. 예전엔 본문이 사라져 면책 문구만 남았다.
    resp = _ask(FakeAgent(DISCLAIMER, "INTERVENED"))
    assert resp.answer.startswith(GUARDRAIL_BLOCKED_ANSWER)
    assert resp.answer != DISCLAIMER


def test_not_intervened_keeps_normal_path_and_reports_none() -> None:
    resp = _ask(FakeAgent("ROE는 자기자본이익률입니다.", "NONE", citations=[_cite()]))
    assert resp.source == "knowledge_base"
    assert resp.guardrail_action == "none"
    assert len(resp.citations) == 1


def test_guardrail_not_configured_reports_none_action() -> None:
    resp = _ask(
        FakeAgent("ROE는 자기자본이익률입니다.", "NONE", citations=[_cite()]), guardrail_id=""
    )
    assert resp.guardrail_action is None


@pytest.mark.parametrize(
    "text",
    [
        f"{GUARDRAIL_BLOCKED_ANSWER}\n\n{DISCLAIMER}",
        f"{DISCLAIMER}\n{GUARDRAIL_BLOCKED_ANSWER}",
        GUARDRAIL_BLOCKED_ANSWER,
    ],
)
def test_enforce_disclaimer_keeps_blocked_answer_and_single_disclaimer(text: str) -> None:
    out = enforce_disclaimer(text)
    assert GUARDRAIL_BLOCKED_ANSWER in out
    assert out.count(DISCLAIMER) == 1
    assert out.endswith(DISCLAIMER)
