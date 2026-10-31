"""Journal 저장소. 가상 기록이며 실제 주문·거래를 만들지 않는다 (원칙 4)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import JournalEntryORM
from app.models.journal import JournalEntry, JournalEntryCreateRequest, VirtualPosition

PRICE_DECIMALS = 2


def _to_model(orm: JournalEntryORM) -> JournalEntry:
    return JournalEntry.model_validate(orm, from_attributes=True)


def list_entries(session: Session, stock_code: str | None = None) -> list[JournalEntry]:
    stmt = select(JournalEntryORM).order_by(JournalEntryORM.created_at, JournalEntryORM.id)
    if stock_code is not None:
        stmt = stmt.where(JournalEntryORM.stock_code == stock_code)
    return [_to_model(e) for e in session.scalars(stmt)]


def create_entry(session: Session, req: JournalEntryCreateRequest) -> JournalEntry:
    orm = JournalEntryORM(**req.model_dump())
    session.add(orm)
    session.commit()
    return _to_model(orm)


def delete_entry(session: Session, entry_id: str) -> bool:
    orm = session.get(JournalEntryORM, entry_id)
    if orm is None:
        return False
    session.delete(orm)
    session.commit()
    return True


def get_virtual_positions(session: Session) -> list[VirtualPosition]:
    """buy 기록 중 가상 수량·단가가 모두 양수인 것만 종목별로 합산한다."""
    e = JournalEntryORM
    stmt = (
        select(
            e.stock_code,
            func.min(e.stock_name),
            func.sum(e.virtual_quantity),
            func.sum(e.virtual_price * e.virtual_quantity),
        )
        .where(e.decision == "buy", e.virtual_price > 0, e.virtual_quantity > 0)
        .group_by(e.stock_code)
        .order_by(e.stock_code)
    )
    return [
        VirtualPosition(
            stock_code=code,
            stock_name=name,
            quantity=int(qty),
            avg_price=round(float(cost) / int(qty), PRICE_DECIMALS),
        )
        for code, name, qty, cost in session.execute(stmt)
    ]
