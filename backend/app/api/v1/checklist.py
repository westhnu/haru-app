from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.v1.stock import DART_ERROR_RESPONSES, DEFAULT_DART_ERROR
from app.db.engine import get_session
from app.db.repositories import checklist_repo
from app.models.checklist import (
    AiEvaluation,
    Checklist,
    ChecklistCreateRequest,
    ChecklistItem,
    ChecklistItemAddRequest,
    ChecklistItemUpdateRequest,
    ChecklistScoreResponse,
)
from app.services.checklist_eval_service import (
    ChecklistEvalService,
    UnsupportedMarketError,
    get_checklist_eval_service,
)
from app.services.dart_tool import DartError

router = APIRouter(prefix="/api/v1/checklists", tags=["checklist"])

SessionDep = Annotated[Session, Depends(get_session)]
EvalServiceDep = Annotated[ChecklistEvalService, Depends(get_checklist_eval_service)]
NOT_FOUND = "Checklist not found"
ITEM_NOT_FOUND = "Checklist or item not found"


@router.get("")
def list_checklists(session: SessionDep, stock_code: str | None = None) -> dict[str, Any]:
    items = checklist_repo.list_checklists(session, stock_code)
    return {"checklists": items, "total": len(items)}


@router.post("", response_model=Checklist)
def create_checklist(req: ChecklistCreateRequest, session: SessionDep) -> Checklist:
    return checklist_repo.create_checklist(session, req.stock_code, req.stock_name)


@router.get("/{checklist_id}", response_model=Checklist)
def get_checklist(checklist_id: str, session: SessionDep) -> Checklist:
    cl = checklist_repo.get_checklist(session, checklist_id)
    if cl is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return cl


@router.post("/{checklist_id}/items", response_model=ChecklistItem)
def add_item(checklist_id: str, req: ChecklistItemAddRequest, session: SessionDep) -> ChecklistItem:
    item = checklist_repo.add_item(session, checklist_id, req.principle, req.reasoning)
    if item is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return item


@router.patch("/{checklist_id}/items/{item_id}", response_model=ChecklistItem)
def update_item(
    checklist_id: str, item_id: str, req: ChecklistItemUpdateRequest, session: SessionDep
) -> ChecklistItem:
    item = checklist_repo.update_item(session, checklist_id, item_id, req.status, req.reasoning)
    if item is None:
        raise HTTPException(status_code=404, detail=ITEM_NOT_FOUND)
    return item


@router.delete("/{checklist_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(checklist_id: str, item_id: str, session: SessionDep) -> Response:
    if not checklist_repo.delete_item(session, checklist_id, item_id):
        raise HTTPException(status_code=404, detail=ITEM_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{checklist_id}/score", response_model=ChecklistScoreResponse)
def score_checklist(checklist_id: str, session: SessionDep) -> ChecklistScoreResponse:
    result = checklist_repo.score(session, checklist_id)
    if result is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return result


@router.post("/{checklist_id}/items/{item_id}/evaluate", response_model=AiEvaluation)
def evaluate_item(
    checklist_id: str, item_id: str, session: SessionDep, eval_service: EvalServiceDep
) -> AiEvaluation:
    """원칙 하나를 DART 재무 데이터로 AI 평가한 제안을 돌려준다.

    저장하지 않는다(사용자가 확인 후 PATCH로 반영).

    종목은 체크리스트의 stock_code만 쓴다 (다른 종목 데이터로 평가하는 경로를 열지 않는다).
    """
    cl = checklist_repo.get_checklist(session, checklist_id)
    item = next((i for i in cl.items if i.id == item_id), None) if cl else None
    if cl is None or item is None:
        raise HTTPException(status_code=404, detail=ITEM_NOT_FOUND)
    try:
        return eval_service.evaluate_item(cl.stock_code, item.principle)
    except UnsupportedMarketError as exc:
        raise HTTPException(
            422,
            "DART 미지원 종목입니다. AI 평가는 국내 상장 종목(6자리 코드)만 지원합니다.",
        ) from exc
    except DartError as exc:
        status_code, detail = DART_ERROR_RESPONSES.get(type(exc), DEFAULT_DART_ERROR)
        raise HTTPException(status_code, detail) from exc
