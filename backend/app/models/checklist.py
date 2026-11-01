import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.guardrail import DISCLAIMER
from app.models.stock import StockSource

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


EvaluationSource = Literal["bedrock", "template", "mock"]


class AiEvaluation(BaseModel):
    """원칙 하나에 대한 AI 판정 제안 (저장하지 않음, 사용자가 확인 후 PATCH로 반영).

    원칙 2: 근거 출처(DART)가 없는 판정은 스키마 차원에서 만들 수 없다.
    """

    suggested_status: ItemStatus
    reasoning: str = Field(..., min_length=1, max_length=REASONING_MAX_LENGTH)
    sources: list[StockSource] = Field(..., min_length=1)
    used_facts: list[str] = Field(default_factory=list)
    # bedrock: 검증 통과한 AI 판정 / template: 코드 fallback(판단 보류) / mock: 개발용 DART
    evaluation_source: EvaluationSource
    report_label: str = ""
    disclaimer: str = DISCLAIMER
