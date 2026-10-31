from typing import Any

from fastapi import APIRouter, HTTPException

from app.models.checklist import Checklist, ChecklistItem, ChecklistScoreResponse

router = APIRouter(prefix="/api/v1/checklists", tags=["checklist"])

PERCENT = 100
SCORE_DECIMALS = 1

# In-memory store. 세션 4-5에서 SQLite로 승격 예정.
_CHECKLISTS: dict[str, Checklist] = {}

_CHECKLISTS["sample-value"] = Checklist(
    id="sample-value",
    stock_code="005930",
    stock_name="삼성전자",
    items=[
        ChecklistItem(id="1", principle="PER < 15", status="satisfied", reasoning="현재 PER 11.2"),
        ChecklistItem(id="2", principle="ROE > 10%", status="satisfied", reasoning="ROE 12.3%"),
        ChecklistItem(
            id="3", principle="부채비율 < 50%", status="unsatisfied", reasoning="부채비율 58%"
        ),
    ],
)


def _get_or_404(checklist_id: str) -> Checklist:
    if checklist_id not in _CHECKLISTS:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return _CHECKLISTS[checklist_id]


@router.get("")
def list_checklists() -> dict[str, Any]:
    return {"checklists": list(_CHECKLISTS.values()), "total": len(_CHECKLISTS)}


@router.get("/{checklist_id}", response_model=Checklist)
def get_checklist(checklist_id: str) -> Checklist:
    return _get_or_404(checklist_id)


@router.get("/{checklist_id}/score", response_model=ChecklistScoreResponse)
def score_checklist(checklist_id: str) -> ChecklistScoreResponse:
    cl = _get_or_404(checklist_id)
    total = len(cl.items)
    counts = {
        s: sum(1 for i in cl.items if i.status == s)
        for s in ("satisfied", "unsatisfied", "uncertain")
    }
    pct = (counts["satisfied"] / total * PERCENT) if total > 0 else 0.0
    return ChecklistScoreResponse(
        checklist_id=checklist_id,
        total=total,
        satisfied=counts["satisfied"],
        unsatisfied=counts["unsatisfied"],
        uncertain=counts["uncertain"],
        score_pct=round(pct, SCORE_DECIMALS),
    )
