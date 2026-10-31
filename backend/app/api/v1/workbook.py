from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.engine import get_session
from app.db.repositories import workbook_repo
from app.models.workbook import (
    Workbook,
    WorkbookBlock,
    WorkbookBlockAddRequest,
    WorkbookCreateRequest,
    WorkbookListResponse,
)

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbook"])

SessionDep = Annotated[Session, Depends(get_session)]
WORKBOOK_NOT_FOUND = "워크북 없음."


@router.get("", response_model=WorkbookListResponse)
def list_workbooks(session: SessionDep, stock_code: str | None = None) -> WorkbookListResponse:
    items = workbook_repo.list_workbooks(session, stock_code)
    return WorkbookListResponse(workbooks=items, total=len(items))


@router.post("", response_model=Workbook)
def create_workbook(req: WorkbookCreateRequest, session: SessionDep) -> Workbook:
    return workbook_repo.create_workbook(session, req.stock_code, req.stock_name, req.title)


@router.get("/{workbook_id}", response_model=Workbook)
def get_workbook(workbook_id: str, session: SessionDep) -> Workbook:
    wb = workbook_repo.get_workbook(session, workbook_id)
    if wb is None:
        raise HTTPException(status_code=404, detail=WORKBOOK_NOT_FOUND)
    return wb


@router.post("/{workbook_id}/blocks", response_model=WorkbookBlock)
def add_block(workbook_id: str, req: WorkbookBlockAddRequest, session: SessionDep) -> WorkbookBlock:
    block = workbook_repo.add_block(session, workbook_id, req.block_type, req.content)
    if block is None:
        raise HTTPException(status_code=404, detail=WORKBOOK_NOT_FOUND)
    return block


@router.delete("/{workbook_id}/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_block(workbook_id: str, block_id: str, session: SessionDep) -> Response:
    if not workbook_repo.delete_block(session, workbook_id, block_id):
        raise HTTPException(status_code=404, detail="워크북 또는 블록 없음.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
