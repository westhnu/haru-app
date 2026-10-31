"""홈 '오늘의 흐름' 카드 (Phase E).

사용자 본인 기록만 요약하며, 날짜·공시 일정을 추측하지 않는다.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.core.guardrail import DISCLAIMER


class NextAction(StrEnum):
    EMPTY = "empty"  # 저널·워크북 없음
    CHECKLIST_INCOMPLETE = "checklist_incomplete"  # 최근 결정의 체크리스트에 미판단 항목
    REVIEW_DECISION = "review_decision"  # 최근 결정 회고
    START_NEW = "start_new"  # 워크북만 있음 → 체크리스트·결정 기록 시작


class TodayCard(BaseModel):
    next_action: NextAction
    message: str
    cta_label: str
    # EMPTY는 종목 검색 다이얼로그를 여는 행동이라 링크가 없다(빈 문자열).
    # 프론트가 next_action으로 분기한다.
    cta_href: str = ""
    context: dict[str, str | int] = Field(default_factory=dict)
    disclaimer: str = DISCLAIMER
