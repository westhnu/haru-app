from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.engine import get_session
from app.db.repositories import checklist_repo, journal_repo, workbook_repo
from app.models.journal import JournalEntry, JournalEntryCreateRequest

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/entries")
def list_entries(session: SessionDep, stock_code: str | None = None) -> dict[str, Any]:
    items = journal_repo.list_entries(session, stock_code)
    return {"entries": items, "total": len(items)}


@router.post("/entries", response_model=JournalEntry)
def create_entry(req: JournalEntryCreateRequest, session: SessionDep) -> JournalEntry:
    # 연결 대상은 FK라 없는 id를 그대로 넣으면 IntegrityError(500)가 난다 → 422로 먼저 거른다.
    if req.checklist_id and not checklist_repo.exists(session, req.checklist_id):
        raise HTTPException(status_code=422, detail="연결할 체크리스트가 없습니다")
    if req.workbook_id and not workbook_repo.exists(session, req.workbook_id):
        raise HTTPException(status_code=422, detail="연결할 워크북이 없습니다")
    return journal_repo.create_entry(session, req)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: str, session: SessionDep) -> Response:
    if not journal_repo.delete_entry(session, entry_id):
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/portfolio")
def get_virtual_portfolio(session: SessionDep) -> dict[str, Any]:
    positions = journal_repo.get_virtual_positions(session)
    return {"positions": positions, "total": len(positions)}
