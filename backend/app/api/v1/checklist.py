import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status

from app.models.checklist import (
    Checklist,
    ChecklistCreateRequest,
    ChecklistItem,
    ChecklistItemAddRequest,
    ChecklistItemUpdateRequest,
    ChecklistScoreResponse,
)

router = APIRouter(prefix="/api/v1/checklists", tags=["checklist"])

PERCENT = 100
SCORE_DECIMALS = 1

# In-memory store. 세션 4-5에서 SQLite로 승격 예정 (재시작 시 초기화, 샘플은 모듈 로드 때 복원).
_CHECKLISTS: dict[str, Checklist] = {}

# 프론트 체감용 샘플. 원칙 2: 출처 없는 재무 수치를 넣지 않는다 — 원칙 문장만 두고
# 판단(status·reasoning)은 사용자가 채운다.
_CHECKLISTS["sample-value"] = Checklist(
    id="sample-value",
    stock_code="005930",
    stock_name="삼성전자",
    items=[
        ChecklistItem(id="1", principle="PER이 업종 평균 대비 저평가인가?"),
        ChecklistItem(id="2", principle="최근 3년 ROE 추이가 10% 이상 유지되는가?"),
        ChecklistItem(id="3", principle="부채비율이 업종 평균보다 낮은가?"),
    ],
)


def _get_or_404(checklist_id: str) -> Checklist:
    if checklist_id not in _CHECKLISTS:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return _CHECKLISTS[checklist_id]


def _item_or_404(cl: Checklist, item_id: str) -> ChecklistItem:
    for item in cl.items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Checklist item not found")


@router.get("")
def list_checklists(stock_code: str | None = None) -> dict[str, Any]:
    items = [c for c in _CHECKLISTS.values() if stock_code is None or c.stock_code == stock_code]
    return {"checklists": items, "total": len(items)}


@router.post("", response_model=Checklist)
def create_checklist(req: ChecklistCreateRequest) -> Checklist:
    new_id = str(uuid.uuid4())
    cl = Checklist(id=new_id, stock_code=req.stock_code, stock_name=req.stock_name)
    _CHECKLISTS[new_id] = cl
    return cl


@router.get("/{checklist_id}", response_model=Checklist)
def get_checklist(checklist_id: str) -> Checklist:
    return _get_or_404(checklist_id)


@router.post("/{checklist_id}/items", response_model=ChecklistItem)
def add_item(checklist_id: str, req: ChecklistItemAddRequest) -> ChecklistItem:
    cl = _get_or_404(checklist_id)
    item = ChecklistItem(principle=req.principle, reasoning=req.reasoning)
    cl.items.append(item)
    cl.touch()
    return item


@router.patch("/{checklist_id}/items/{item_id}", response_model=ChecklistItem)
def update_item(checklist_id: str, item_id: str, req: ChecklistItemUpdateRequest) -> ChecklistItem:
    cl = _get_or_404(checklist_id)
    item = _item_or_404(cl, item_id)
    if req.status is not None:
        item.status = req.status
    if req.reasoning is not None:
        item.reasoning = req.reasoning
    cl.touch()
    return item


@router.delete("/{checklist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(checklist_id: str, item_id: str) -> Response:
    cl = _get_or_404(checklist_id)
    _item_or_404(cl, item_id)
    cl.items = [i for i in cl.items if i.id != item_id]
    cl.touch()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
