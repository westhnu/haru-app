"""ORM 테이블 (Phase A). API 계약은 app/models/*의 Pydantic 모델이고, 변환은 repository가 한다."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.engine import Base


def utcnow() -> datetime:
    # func.now()는 SQLite에서 초 단위라 같은 초에 추가한 블록 순서가 뒤섞인다.
    # 그래서 Python에서 µs 단위 UTC 시각을 넣는다.
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class UTCDateTime(TypeDecorator[datetime]):
    """SQLite는 timezone을 저장하지 않는다. UTC naive로 저장하고 읽을 때 UTC aware로 돌려준다.

    그대로 두면 API가 "2026-10-31T06:00:00"(Z 없음)을 내보내고,
    브라우저가 로컬 시각으로 읽어 9시간 어긋난다.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None else None


class WorkbookORM(Base):
    __tablename__ = "workbooks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    stock_code: Mapped[str] = mapped_column(String(32), index=True)
    stock_name: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    blocks: Mapped[list["WorkbookBlockORM"]] = relationship(
        back_populates="workbook",
        cascade="all, delete-orphan",
        order_by="(WorkbookBlockORM.created_at, WorkbookBlockORM.id)",
    )


class WorkbookBlockORM(Base):
    __tablename__ = "workbook_blocks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    workbook_id: Mapped[str] = mapped_column(
        ForeignKey("workbooks.id", ondelete="CASCADE"), index=True
    )
    block_type: Mapped[str] = mapped_column(String(32))
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    workbook: Mapped[WorkbookORM] = relationship(back_populates="blocks")


class ChecklistORM(Base):
    __tablename__ = "checklists"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    stock_code: Mapped[str] = mapped_column(String(32), index=True)
    stock_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    items: Mapped[list["ChecklistItemORM"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="(ChecklistItemORM.created_at, ChecklistItemORM.id)",
    )


class ChecklistItemORM(Base):
    __tablename__ = "checklist_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    checklist_id: Mapped[str] = mapped_column(
        ForeignKey("checklists.id", ondelete="CASCADE"), index=True
    )
    principle: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="uncertain")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    # API에는 노출하지 않고 정렬에만 쓴다.
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    checklist: Mapped[ChecklistORM] = relationship(back_populates="items")


class JournalEntryORM(Base):
    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    stock_code: Mapped[str] = mapped_column(String(32), index=True)
    stock_name: Mapped[str] = mapped_column(String(100))
    decision: Mapped[str] = mapped_column(String(16))
    reasoning: Mapped[str] = mapped_column(Text)
    # 연결된 워크북·체크리스트가 사라져도 기록은 남긴다 (회고 자료).
    checklist_id: Mapped[str | None] = mapped_column(
        ForeignKey("checklists.id", ondelete="SET NULL"), nullable=True, index=True
    )
    workbook_id: Mapped[str | None] = mapped_column(
        ForeignKey("workbooks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    virtual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    virtual_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
