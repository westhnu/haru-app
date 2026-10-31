import uuid
from typing import Any

from fastapi import APIRouter

from app.models.journal import JournalEntry, VirtualPosition

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])

PRICE_DECIMALS = 2

# In-memory store. 세션 4-5에서 SQLite로 승격 예정.
_ENTRIES: dict[str, JournalEntry] = {}

_ENTRIES["sample-1"] = JournalEntry(
    id="sample-1",
    stock_code="005930",
    stock_name="삼성전자",
    decision="watch",
    reasoning="체크리스트 2/3 충족, PER 양호하나 부채비율 초과. 추가 분기 실적 확인 후 결정.",
    checklist_id="sample-value",
    virtual_quantity=0,
)


@router.get("/entries")
def list_entries() -> dict[str, Any]:
    return {"entries": list(_ENTRIES.values()), "total": len(_ENTRIES)}


@router.post("/entries", response_model=JournalEntry)
def create_entry(req: JournalEntry) -> JournalEntry:
    new_id = str(uuid.uuid4())
    entry = req.model_copy(update={"id": new_id})
    _ENTRIES[new_id] = entry
    return entry


def _aggregate_buys() -> dict[str, dict[str, Any]]:
    """buy 기록만 종목별 수량·원가로 합산한다 (가상 포지션, 실매매 없음)."""
    agg: dict[str, dict[str, Any]] = {}
    for e in _ENTRIES.values():
        if e.decision != "buy" or not e.virtual_price or not e.virtual_quantity:
            continue
        slot = agg.setdefault(e.stock_code, {"qty": 0, "cost": 0.0, "name": e.stock_name})
        slot["qty"] += e.virtual_quantity
        slot["cost"] += e.virtual_price * e.virtual_quantity
    return agg


@router.get("/portfolio")
def get_virtual_portfolio() -> dict[str, Any]:
    positions = [
        VirtualPosition(
            stock_code=code,
            stock_name=data["name"],
            quantity=data["qty"],
            avg_price=round(data["cost"] / data["qty"], PRICE_DECIMALS),
        )
        for code, data in _aggregate_buys().items()
        if data["qty"] > 0
    ]
    return {"positions": positions, "total": len(positions)}
