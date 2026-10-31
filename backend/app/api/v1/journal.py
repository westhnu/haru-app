import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status

from app.models.journal import JournalEntry, JournalEntryCreateRequest, VirtualPosition

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])

PRICE_DECIMALS = 2

# In-memory store. 세션 4-5에서 SQLite로 승격 예정 (재시작 시 초기화, 샘플은 모듈 로드 때 복원).
_ENTRIES: dict[str, JournalEntry] = {}

# 원칙 2: 샘플 근거에 출처 없는 수치를 넣지 않는다.
_ENTRIES["sample-1"] = JournalEntry(
    id="sample-1",
    stock_code="005930",
    stock_name="삼성전자",
    decision="watch",
    reasoning="체크리스트 원칙을 직접 채워 본 뒤 결정하기로 함. 다음 분기 실적 공시를 확인할 예정.",
    checklist_id="sample-value",
    virtual_quantity=0,
)


@router.get("/entries")
def list_entries(stock_code: str | None = None) -> dict[str, Any]:
    items = [e for e in _ENTRIES.values() if stock_code is None or e.stock_code == stock_code]
    return {"entries": items, "total": len(items)}


@router.post("/entries", response_model=JournalEntry)
def create_entry(req: JournalEntryCreateRequest) -> JournalEntry:
    new_id = str(uuid.uuid4())
    entry = JournalEntry(id=new_id, **req.model_dump())
    _ENTRIES[new_id] = entry
    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: str) -> Response:
    if _ENTRIES.pop(entry_id, None) is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
