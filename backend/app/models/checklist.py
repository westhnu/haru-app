from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

ItemStatus = Literal["satisfied", "unsatisfied", "uncertain"]


def _now() -> datetime:
    return datetime.now(UTC)


class ChecklistItem(BaseModel):
    id: str
    principle: str  # 사용자 원칙 (예: "PER < 15")
    status: ItemStatus
    reasoning: str = ""  # AI 또는 사용자 근거


class Checklist(BaseModel):
    id: str
    stock_code: str
    stock_name: str
    items: list[ChecklistItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)


class ChecklistScoreResponse(BaseModel):
    checklist_id: str
    total: int
    satisfied: int
    unsatisfied: int
    uncertain: int
    score_pct: float  # satisfied / total * 100
