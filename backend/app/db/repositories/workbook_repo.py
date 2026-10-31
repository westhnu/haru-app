"""Workbook 저장소. ORM ↔ Pydantic(app.models.workbook) 변환을 여기서만 한다."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import WorkbookBlockORM, WorkbookORM, utcnow
from app.models.workbook import Workbook, WorkbookBlock


def _to_model(orm: WorkbookORM) -> Workbook:
    return Workbook.model_validate(orm, from_attributes=True)


def list_workbooks(session: Session, stock_code: str | None = None) -> list[Workbook]:
    stmt = (
        select(WorkbookORM)
        .options(selectinload(WorkbookORM.blocks))
        .order_by(WorkbookORM.created_at, WorkbookORM.id)
    )
    if stock_code is not None:
        stmt = stmt.where(WorkbookORM.stock_code == stock_code)
    return [_to_model(w) for w in session.scalars(stmt)]


def get_workbook(session: Session, workbook_id: str) -> Workbook | None:
    orm = session.get(WorkbookORM, workbook_id)
    return _to_model(orm) if orm else None


def exists(session: Session, workbook_id: str) -> bool:
    return session.get(WorkbookORM, workbook_id) is not None


def create_workbook(session: Session, stock_code: str, stock_name: str, title: str) -> Workbook:
    orm = WorkbookORM(stock_code=stock_code, stock_name=stock_name, title=title)
    session.add(orm)
    session.commit()
    return _to_model(orm)


def add_block(
    session: Session, workbook_id: str, block_type: str, content: dict[str, Any]
) -> WorkbookBlock | None:
    wb = session.get(WorkbookORM, workbook_id)
    if wb is None:
        return None
    block = WorkbookBlockORM(block_type=block_type, content=content)
    wb.blocks.append(block)
    wb.updated_at = utcnow()
    session.commit()
    return WorkbookBlock.model_validate(block, from_attributes=True)


def delete_block(session: Session, workbook_id: str, block_id: str) -> bool:
    """삭제했으면 True. 워크북이나 블록이 없으면 False."""
    wb = session.get(WorkbookORM, workbook_id)
    if wb is None:
        return False
    block = next((b for b in wb.blocks if b.id == block_id), None)
    if block is None:
        return False
    wb.blocks.remove(block)  # delete-orphan
    wb.updated_at = utcnow()
    session.commit()
    return True
