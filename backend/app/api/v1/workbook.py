import uuid

from fastapi import APIRouter, HTTPException

from app.models.workbook import (
    Workbook,
    WorkbookBlock,
    WorkbookCreateRequest,
    WorkbookListResponse,
)

router = APIRouter(prefix="/api/v1/workbooks", tags=["workbook"])

# In-memory store. 세션 4-5에서 SQLite로 승격 예정 (재시작 시 초기화됨).
_WORKBOOKS: dict[str, Workbook] = {}

# 프론트 체감용 샘플
_WORKBOOKS["sample-samsung"] = Workbook(
    id="sample-samsung",
    stock_code="005930",
    stock_name="삼성전자",
    title="삼성전자 2025 Q3 분석",
    blocks=[
        WorkbookBlock(
            block_type="memo",
            content={"text": "매출 성장 둔화, 메모리 사이클 확인 필요"},
        ),
    ],
)


@router.get("", response_model=WorkbookListResponse)
def list_workbooks() -> WorkbookListResponse:
    items = list(_WORKBOOKS.values())
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
    if workbook_id not in _WORKBOOKS:
        raise HTTPException(status_code=404, detail="Workbook not found")
    return _WORKBOOKS[workbook_id]
