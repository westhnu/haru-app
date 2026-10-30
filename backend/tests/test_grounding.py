import pytest

from app.core.grounding import find_ungrounded_figures

ALLOWED = {40.0, 10.0, -12.3}


@pytest.mark.parametrize(
    "text",
    [
        "DART 2026년 반기보고서 기준 부채비율은 40.0%, 영업이익률은 10.0%입니다.",
        "매출액은 전기 대비 12.3% 감소했습니다.",
        "부채비율은 약 40%입니다.",
        "3분기보고서는 아직 공시되지 않았습니다.",
    ],
)
def test_grounded_text_passes(text: str) -> None:
    assert find_ungrounded_figures(text, ALLOWED) == []


@pytest.mark.parametrize(
    "text",
    [
        "매출액은 302조 2,314억원입니다.",
        "현재 주가는 80,000원입니다.",
        "영업이익은 10조를 넘었습니다.",
    ],
)
def test_money_amounts_are_always_ungrounded(text: str) -> None:
    assert find_ungrounded_figures(text, ALLOWED)


def test_unknown_percentage_is_ungrounded() -> None:
    assert find_ungrounded_figures("영업이익률은 15.2%입니다.", ALLOWED) == ["15.2%"]
