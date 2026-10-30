import pytest

from app.core.guardrail import (
    DISCLAIMER,
    SAFE_REPLACEMENT,
    apply_output_guard,
    enforce_disclaimer,
    has_forbidden_phrase,
    mask_pii,
)

GUARDED_REPLACEMENT = f"{SAFE_REPLACEMENT}\n\n{DISCLAIMER}"


# --- 회귀 방지 필수 3종 (Sprint 1 브리핑) ---------------------------------------------


@pytest.mark.parametrize("text", ["이 종목을 매수하세요", "내일 오릅니다"])
def test_forbidden_phrase_is_replaced_with_safe_response(text: str) -> None:
    assert apply_output_guard(text) == GUARDED_REPLACEMENT


def test_resident_registration_number_is_masked() -> None:
    masked = mask_pii("주민번호는 900101-1234567입니다")

    assert "900101-1234567" not in masked
    assert masked == "주민번호는 [주민등록번호]입니다"


# --- 금지 표현 변형 · 오탐 방지 ---------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "삼성전자는 지금 사세요.",
        "이제는 팔아야 합니다.",
        "10만원까지 갑니다.",
        "무조건 수익 나는 종목입니다.",
        "이 종목 매수를 추천합니다.",
        "내일 급등 종목 3선",
    ],
)
def test_forbidden_variants_are_detected(text: str) -> None:
    assert has_forbidden_phrase(text)


@pytest.mark.parametrize(
    "text",
    [
        "당신의 체크리스트 7개 중 5개를 충족합니다.",
        "DART 2025-1Q 기준 매출은 1,000억원입니다.",
        "과거 52주 최고가는 80,000원까지 상승했습니다.",
        "본 서비스는 수익을 보장하지 않습니다.",
        "특정 종목의 매수를 권유하지 않습니다.",
    ],
)
def test_allowed_expressions_are_not_flagged(text: str) -> None:
    assert not has_forbidden_phrase(text)


def test_disclaimer_appears_exactly_once_at_the_end() -> None:
    text = f"PER은 주가를 주당순이익으로 나눈 값입니다. {DISCLAIMER} 참고하세요."

    guarded = enforce_disclaimer(enforce_disclaimer(text))

    assert guarded.count(DISCLAIMER) == 1
    assert guarded.endswith(DISCLAIMER)


# --- PII 마스킹 --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("연락처 010-1234-5678", "연락처 [전화번호]"),
        ("신한 110-123-456789 입금", "신한 [계좌번호] 입금"),
        ("한투 계좌 12345678-01", "한투 계좌 [계좌번호]"),
        ("카드 1234-5678-9012-3456", "카드 [카드번호]"),
    ],
)
def test_pii_is_masked(text: str, expected: str) -> None:
    assert mask_pii(text) == expected


@pytest.mark.parametrize("text", ["2025-09-13 공시", "종목코드 005930", "2024-2025 실적"])
def test_non_pii_numbers_are_kept(text: str) -> None:
    assert mask_pii(text) == text
