"""AI 요약 속 수치가 DART 원본에서 계산된 값인지 대조한다.

원칙 2(AI가 만든 수치는 그대로 반환하지 않는다)의 코드 레벨 검증이다.
요약 프롬프트는 금액을 쓰지 말고 제공된 비율만 인용하라고 지시하므로
- 금액 단위(원·조·억)가 붙은 수치는 존재 자체가 위반이고
- 비율(%)은 제공된 값과 일치해야 한다.
"""

import re

_PERCENT = re.compile(r"-?(\d+(?:\.\d+)?)\s*(?:%|퍼센트)")
_MONEY = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:조|억|만)?\s*원|\d[\d,]*(?:\.\d+)?\s*(?:조|억)")


def find_ungrounded_figures(text: str, allowed_percentages: set[float]) -> list[str]:
    """허용되지 않은 수치 표현 목록. 빈 목록이면 통과."""
    allowed = {round(abs(value), 1) for value in allowed_percentages}
    violations = [match.group(0).strip() for match in _MONEY.finditer(text)]
    for match in _PERCENT.finditer(text):
        if not _is_allowed_percentage(match.group(1), allowed):
            violations.append(match.group(0).strip())
    return violations


def _is_allowed_percentage(raw: str, allowed: set[float]) -> bool:
    # 증감률은 "12.3% 감소"처럼 부호 없이 쓰이므로 절댓값으로 비교한다.
    value = float(raw)
    if "." in raw:
        return round(value, 1) in allowed
    # "약 40%"처럼 정수로 반올림해 쓴 경우는 허용한다.
    return any(round(candidate) == value for candidate in allowed)
