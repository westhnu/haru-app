import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.models.workbook import (
    Workbook,
    WorkbookBlock,
    WorkbookBlockAddRequest,
    WorkbookCreateRequest,
    WorkbookListResponse,
)

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbook"])

# In-memory store. 세션 4-5에서 SQLite로 승격 예정 (재시작 시 초기화됨, 샘플은 모듈 로드 때 복원).
_WORKBOOKS: dict[str, Workbook] = {}

# 프론트 체감용 샘플
_WORKBOOKS["sample-samsung"] = Workbook(
    id="sample-samsung",
    stock_code="005930",
    stock_name="삼성전자",
    title="삼성전자 2025 Q3 분석",
    blocks=[
        WorkbookBlock(
            id="sample-memo-001",
            block_type="memo",
            content={"text": "매출 성장 둔화, 메모리 사이클 확인 필요"},
        ),
    ],
)


def _get_or_404(workbook_id: str) -> Workbook:
    wb = _WORKBOOKS.get(workbook_id)
    if wb is None:
        raise HTTPException(status_code=404, detail="Workbook not found")
    return wb


@router.get("", response_model=WorkbookListResponse)
def list_workbooks(stock_code: str | None = None) -> WorkbookListResponse:
    items = [wb for wb in _WORKBOOKS.values() if stock_code is None or wb.stock_code == stock_code]
    return WorkbookListResponse(workbooks=items, total=len(items))


@router.post("", response_model=Workbook)
def create_workbook(req: WorkbookCreateRequest) -> Workbook:
    new_id = str(uuid.uuid4())
    wb = Workbook(
        id=new_id,
        stock_code=req.stock_code,
        stock_name=req.stock_name,
        title=req.title,
    )
    _WORKBOOKS[new_id] = wb
    return wb


@router.get("/{workbook_id}", response_model=Workbook)
def get_workbook(workbook_id: str) -> Workbook:
    return _get_or_404(workbook_id)


@router.post("/{workbook_id}/blocks", response_model=WorkbookBlock)
def add_block(workbook_id: str, req: WorkbookBlockAddRequest) -> WorkbookBlock:
    wb = _get_or_404(workbook_id)
    block = WorkbookBlock(block_type=req.block_type, content=req.content)
    wb.blocks.append(block)
    wb.touch()
    return block


@router.delete("/{workbook_id}/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_block(workbook_id: str, block_id: str) -> Response:
    wb = _get_or_404(workbook_id)
    remaining = [b for b in wb.blocks if b.id != block_id]
    if len(remaining) == len(wb.blocks):
        raise HTTPException(status_code=404, detail="Block not found")
    wb.blocks = remaining
    wb.touch()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
