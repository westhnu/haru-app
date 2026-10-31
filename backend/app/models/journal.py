from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# 사용자가 직접 기록하는 본인의 결정. AI가 권유하는 값이 아니다 (원칙 1).
# 가상 기록이며 실제 주문·거래를 만들지 않는다 (원칙 4).
Decision = Literal["buy", "sell", "hold", "watch"]
REASONING_MAX_LENGTH = 1000


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
    virtual_price: float | None = None  # 가상 단가 (실매매 없음)
    virtual_quantity: int | None = None
    created_at: datetime = Field(default_factory=_now)


class JournalEntryCreateRequest(BaseModel):
    """결정 기록 요청. id·created_at은 서버가 만든다."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    stock_code: str = Field(..., min_length=1)
    stock_name: str = Field(..., min_length=1)
    decision: Decision
    reasoning: str = Field(..., min_length=1, max_length=REASONING_MAX_LENGTH)
    checklist_id: str | None = None
    workbook_id: str | None = None
    virtual_price: float | None = Field(default=None, ge=0)
    virtual_quantity: int | None = Field(default=None, ge=0)


class VirtualPosition(BaseModel):
    """buy 기록 합산 가상 포지션. 시세 연동 전이라 현재가·손익 필드는 두지 않는다."""

    stock_code: str
    stock_name: str
    quantity: int
    avg_price: float
