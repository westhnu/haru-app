"""말투 가이드 — L1(엄격) / L2(서비스) 검사 (Phase F1·F1.5, planning/tone_guide.md)."""

import pytest

from app.core.guardrail import (
    AI_EVAL_NOTICE,
    DISCLAIMER,
    NO_EVIDENCE_STOCK_ANSWER,
    SAFE_REPLACEMENT,
    find_tone_violations_l1,
    find_tone_violations_l2,
    has_tone_violation_l1,
    has_tone_violation_l2,
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
def test_l1_passes(text: str) -> None:
    assert find_tone_violations_l1(text) == []


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
def test_l1_violations(text: str, kind: str) -> None:
    found = find_tone_violations_l1(text)
    assert has_tone_violation_l1(text)
    assert any(f.startswith(f"{kind}:") for f in found), found


def test_fixed_user_facing_constants_pass() -> None:
    for text in (AI_EVAL_NOTICE, SAFE_REPLACEMENT, NO_EVIDENCE_STOCK_ANSWER):
        assert not has_tone_violation_l1(text), text


def test_disclaimer_text_unchanged_principle5() -> None:
    # 원칙 5 고정 문구 — 말투 교정 대상이 아니다
    assert DISCLAIMER == "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."


# --- L2 (서비스 톤, Phase F1.5) ---------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "메모가 없어요. '블록 추가'로 첫 메모를 작성해 보세요.",
        "체크리스트를 찾을 수 없어요.",
        "국내 상장 종목만 평가할 수 있어요.",
        "요청에 실패했어요. 다시 시도해 보세요.",
        "국내 상장 종목만 AI 평가를 지원해요. 6자리 종목 코드를 사용해 주세요.",  # '주세요'는 허용
        "DART 조회 한도에 걸렸어요. 잠시 후 다시 시도해 보세요.",  # '잠시 후'는 행동 안내
        "흩어진 뉴스와 시세를 Haru가 정리해 드려요.",  # 'Haru가' 1회는 허용
        "투자! 기록",  # 단어 안의 '자!'는 감탄사 아님
    ],
)
def test_l2_passes(text: str) -> None:
    assert find_tone_violations_l2(text) == []


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("확인해 주시면 감사하겠습니다.", "over_polite"),
        ("검토 바랍니다.", "over_polite"),
        ("처리되지 않았습니다.", "passive"),
        ("아직 데이터가 없습니다.", "vague"),
        ("당신의 결정을 기록해 보세요.", "address"),
        ("저희 Haru는 추천하지 않아요.", "self_reference"),
        ("Haru는 추천하지 않아요.", "self_reference"),
        ("오! 좋아요!", "exclamation"),
    ],
)
def test_l2_violations(text: str, kind: str) -> None:
    found = find_tone_violations_l2(text)
    assert has_tone_violation_l2(text)
    assert any(f.startswith(f"{kind}:") for f in found), found


@pytest.mark.parametrize(
    "text",
    ["DART 기준 부채비율 31.1%, 200% 미만 충족.", "회고 필요. 저널에서 결정 재검토.", "판단 보류"],
)
def test_l1_passing_text_also_passes_l2(text: str) -> None:
    assert not has_tone_violation_l1(text)
    assert not has_tone_violation_l2(text)


def test_l2_allows_polite_endings_that_l1_rejects() -> None:
    text = "체크리스트를 찾을 수 없어요."
    assert has_tone_violation_l1(text) and not has_tone_violation_l2(text)
