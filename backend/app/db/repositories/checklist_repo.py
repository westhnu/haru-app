"""Checklist 저장소. ORM ↔ Pydantic(app.models.checklist) 변환을 여기서만 한다."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ChecklistItemORM, ChecklistORM, utcnow
from app.models.checklist import Checklist, ChecklistItem, ChecklistScoreResponse, ItemStatus

PERCENT = 100
SCORE_DECIMALS = 1
STATUSES: tuple[ItemStatus, ...] = ("satisfied", "unsatisfied", "uncertain")


def _to_model(orm: ChecklistORM) -> Checklist:
    return Checklist.model_validate(orm, from_attributes=True)


def _item_model(orm: ChecklistItemORM) -> ChecklistItem:
    return ChecklistItem.model_validate(orm, from_attributes=True)


def list_checklists(session: Session, stock_code: str | None = None) -> list[Checklist]:
    stmt = (
        select(ChecklistORM)
        .options(selectinload(ChecklistORM.items))
        .order_by(ChecklistORM.created_at, ChecklistORM.id)
    )
    if stock_code is not None:
        stmt = stmt.where(ChecklistORM.stock_code == stock_code)
    return [_to_model(c) for c in session.scalars(stmt)]


def get_checklist(session: Session, checklist_id: str) -> Checklist | None:
    orm = session.get(ChecklistORM, checklist_id)
    return _to_model(orm) if orm else None


def exists(session: Session, checklist_id: str) -> bool:
    return session.get(ChecklistORM, checklist_id) is not None


def create_checklist(session: Session, stock_code: str, stock_name: str) -> Checklist:
    orm = ChecklistORM(stock_code=stock_code, stock_name=stock_name)
    session.add(orm)
    session.commit()
    return _to_model(orm)


def add_item(
    session: Session, checklist_id: str, principle: str, reasoning: str = ""
) -> ChecklistItem | None:
    cl = session.get(ChecklistORM, checklist_id)
    if cl is None:
        return None
    item = ChecklistItemORM(principle=principle, reasoning=reasoning, status="uncertain")
    cl.items.append(item)
    cl.updated_at = utcnow()
    session.commit()
    return _item_model(item)


def _find_item(cl: ChecklistORM, item_id: str) -> ChecklistItemORM | None:
    return next((i for i in cl.items if i.id == item_id), None)


def update_item(
    session: Session,
    checklist_id: str,
    item_id: str,
    status: ItemStatus | None = None,
    reasoning: str | None = None,
) -> ChecklistItem | None:
    """None인 필드는 그대로 둔다(부분 변경). 체크리스트나 항목이 없으면 None."""
    cl = session.get(ChecklistORM, checklist_id)
    item = _find_item(cl, item_id) if cl else None
    if cl is None or item is None:
        return None
    if status is not None:
        item.status = status
    if reasoning is not None:
        item.reasoning = reasoning
    cl.updated_at = utcnow()
    session.commit()
    return _item_model(item)


def delete_item(session: Session, checklist_id: str, item_id: str) -> bool:
    cl = session.get(ChecklistORM, checklist_id)
    item = _find_item(cl, item_id) if cl else None
    if cl is None or item is None:
        return False
    cl.items.remove(item)  # delete-orphan
    cl.updated_at = utcnow()
    session.commit()
    return True


def score(session: Session, checklist_id: str) -> ChecklistScoreResponse | None:
    cl = session.get(ChecklistORM, checklist_id)
    if cl is None:
        return None
    total = len(cl.items)
    counts = {s: sum(1 for i in cl.items if i.status == s) for s in STATUSES}
    pct = (counts["satisfied"] / total * PERCENT) if total > 0 else 0.0
    return ChecklistScoreResponse(
        checklist_id=checklist_id,
        total=total,
        satisfied=counts["satisfied"],
        unsatisfied=counts["unsatisfied"],
        uncertain=counts["uncertain"],
        score_pct=round(pct, SCORE_DECIMALS),
    )
