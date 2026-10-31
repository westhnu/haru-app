from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

# 사용자가 직접 기록하는 본인의 결정. AI가 권유하는 값이 아니다 (원칙 1).
Decision = Literal["buy", "sell", "hold", "watch"]


def _now() -> datetime:
    return datetime.now(UTC)


class JournalEntry(BaseModel):
    id: str
    stock_code: str
    stock_name: str
    decision: Decision
    reasoning: str  # 결정 근거
    checklist_id: str | None = None
    workbook_id: str | None = None
    virtual_price: float | None = None  # 가상 매수가 (실매매 없음)
    virtual_quantity: int | None = None
    created_at: datetime = Field(default_factory=_now)


class VirtualPosition(BaseModel):
    stock_code: str
    stock_name: str
    quantity: int
    avg_price: float
    current_price: float = 0.0  # 외부 시세 조회로 갱신 예정
    pnl: float = 0.0
    pnl_pct: float = 0.0
