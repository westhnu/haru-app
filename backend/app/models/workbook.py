import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _now() -> datetime:
    # datetime.utcnow()는 Python 3.12에서 deprecated라 timezone-aware 시각을 쓴다.
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


BlockType = Literal["memo", "financial", "news", "chart", "checklist_ref"]
# MVP(Sprint 3b)에서 추가할 수 있는 블록. 나머지 타입은 외부 데이터 연결 설계 후 연다.
SUPPORTED_BLOCK_TYPES: frozenset[str] = frozenset({"memo"})
MEMO_MAX_LENGTH = 1000


class MemoContent(BaseModel):
    """memo 블록 본문. 공백만 있는 메모는 거부한다."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    text: str = Field(..., min_length=1, max_length=MEMO_MAX_LENGTH)


class WorkbookBlock(BaseModel):
    """워크북의 한 블록 (financial, news, chart, memo 등)."""

    id: str = Field(default_factory=_new_id)
    block_type: BlockType
    content: dict[str, Any]
    created_at: datetime = Field(default_factory=_now)


class Workbook(BaseModel):
    """종목별 워크북."""

    id: str
    stock_code: str
    stock_name: str
    title: str
    blocks: list[WorkbookBlock] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    def touch(self) -> None:
        """블록이 바뀔 때 호출해 updated_at을 갱신한다."""
        self.updated_at = _now()


class WorkbookCreateRequest(BaseModel):
    stock_code: str
    stock_name: str
    title: str


class WorkbookBlockAddRequest(BaseModel):
    """블록 추가 요청. block_type별로 content를 검증해 정규화된 dict로 바꾼다."""

    block_type: BlockType
    content: dict[str, Any]

    @model_validator(mode="after")
    def _validate_content(self) -> "WorkbookBlockAddRequest":
        if self.block_type not in SUPPORTED_BLOCK_TYPES:
            raise ValueError(f"block_type '{self.block_type}'은 아직 지원하지 않습니다 (MVP: memo)")
        if self.block_type == "memo":
            self.content = MemoContent.model_validate(self.content).model_dump()
        return self


class WorkbookListResponse(BaseModel):
    workbooks: list[Workbook]
    total: int
