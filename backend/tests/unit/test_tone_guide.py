"""Phase F1 말투 가이드 — has_tone_violation (planning/tone_guide.md)."""

import pytest

from app.core.guardrail import (
    AI_EVAL_NOTICE,
    DISCLAIMER,
    NO_EVIDENCE_STOCK_ANSWER,
    SAFE_REPLACEMENT,
    find_tone_violations,
    has_tone_violation,
)


@pytest.mark.parametrize(
    "text",
    [
        "DART 기준 부채비율 31.1%, 200% 미만 충족.",
        "AI 평가는 참고용. 최종 판단은 본인 책임.",
        "회고 필요. 저널에서 결정 재검토.",
        "체크리스트·결정 기록 필요.",  # '필요'는 '요'로 끝나지만 명사
        "종목 개요",
        f"PER: 주가 ÷ 주당순이익.\n\n{DISCLAIMER}",  # 원칙 5 면책 문구는 whitelist
    ],
)
def test_passes(text: str) -> None:
    assert find_tone_violations(text) == []


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("부채비율이 낮아 보여요.", "ending"),
        ("아직 데이터가 부족합니다.", "vague"),
        ("현재 PER 11.2 수준입니다.", "ending"),
        ("판단되지 않았어요", "passive"),
        ("다시 확인해 주세요", "over_polite"),
        ("당신의 투자 리듬", "address"),
        ("곧 갱신", "vague"),
    ],
)
def test_violations(text: str, kind: str) -> None:
    found = find_tone_violations(text)
    assert has_tone_violation(text)
    assert any(f.startswith(f"{kind}:") for f in found), found


def test_fixed_user_facing_constants_pass() -> None:
    for text in (AI_EVAL_NOTICE, SAFE_REPLACEMENT, NO_EVIDENCE_STOCK_ANSWER):
        assert not has_tone_violation(text), text


def test_disclaimer_text_unchanged_principle5() -> None:
    # 원칙 5 고정 문구 — 말투 교정 대상이 아니다
    assert DISCLAIMER == "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."
