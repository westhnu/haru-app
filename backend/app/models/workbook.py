from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    # datetime.utcnow()는 Python 3.12에서 deprecated라 timezone-aware 시각을 쓴다.
    return datetime.now(UTC)


class WorkbookBlock(BaseModel):
    """워크북의 한 블록 (financial, news, chart, memo 등)."""

    block_type: str  # financial | news | chart | memo | checklist_ref
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


class WorkbookCreateRequest(BaseModel):
    stock_code: str
    stock_name: str
    title: str


class WorkbookListResponse(BaseModel):
    workbooks: list[Workbook]
    total: int
