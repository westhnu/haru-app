"""Bedrock Guardrail 회귀 방지 (T-104 뼈대).

Phase 2에서 Fake Bedrock/Guardrail 응답을 주입하고, Phase 5에서 실호출 경로를 붙인 뒤
아래 케이스를 Green으로 전환한다. 지금은 구현 전이라 skip으로 둔다.
"""

import pytest

PENDING = "Phase 2/5에서 구현"


@pytest.mark.skip(reason=PENDING)
def test_investment_advice_blocked_by_bedrock_guardrail() -> None:
    """Guardrail이 intervened를 반환하면 코드가 표준 대체 문구로 응답한다. (REQ-GR-04)"""


@pytest.mark.skip(reason=PENDING)
def test_bedrock_guardrail_blocked_still_has_disclaimer() -> None:
    """Guardrail 차단 응답에도 disclaimer가 포함된다. (원칙 5)"""


@pytest.mark.skip(reason=PENDING)
def test_guardrail_and_code_double_defense() -> None:
    """Guardrail을 통과했더라도 code 후처리가 금지 표현을 잡는다. (원칙 1 이중 방어)"""


@pytest.mark.skip(reason=PENDING)
def test_guardrail_blocked_event_logged() -> None:
    """Guardrail 차단 시 event=guardrail_blocked 로그가 기록된다. (REQ-GR-03)"""
