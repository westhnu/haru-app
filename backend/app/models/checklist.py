import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ItemStatus = Literal["satisfied", "unsatisfied", "uncertain"]
PRINCIPLE_MAX_LENGTH = 200
REASONING_MAX_LENGTH = 1000


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


class ChecklistItem(BaseModel):
    id: str = Field(default_factory=_new_id)
    principle: str  # 사용자 원칙 (예: "PER이 업종 평균 대비 저평가인가?")
    status: ItemStatus = "uncertain"
    reasoning: str = ""  # 사용자 근거 (MVP는 사용자가 직접 판단, AI 채점은 다음 단계)


class Checklist(BaseModel):
    id: str
    stock_code: str
    stock_name: str
    items: list[ChecklistItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()


class ChecklistCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    stock_code: str = Field(..., min_length=1)
    stock_name: str = Field(..., min_length=1)


class ChecklistItemAddRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    principle: str = Field(..., min_length=1, max_length=PRINCIPLE_MAX_LENGTH)
    reasoning: str = Field(default="", max_length=REASONING_MAX_LENGTH)


class ChecklistItemUpdateRequest(BaseModel):
    """상태·근거 부분 변경. 둘 중 하나 이상은 있어야 한다."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: ItemStatus | None = None
    reasoning: str | None = Field(default=None, max_length=REASONING_MAX_LENGTH)

    @model_validator(mode="after")
    def _at_least_one(self) -> "ChecklistItemUpdateRequest":
        if self.status is None and self.reasoning is None:
            raise ValueError("status 또는 reasoning 중 하나는 필요합니다")
        return self


class ChecklistScoreResponse(BaseModel):
    checklist_id: str
    total: int
    satisfied: int
    unsatisfied: int
    uncertain: int
    score_pct: float  # satisfied / total * 100
