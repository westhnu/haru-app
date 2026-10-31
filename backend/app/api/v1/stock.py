from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.models.stock import STOCK_CODE_PATTERN, StockSummaryResponse
from app.services.dart_tool import (
    DartError,
    DartNoFinancialsError,
    DartRateLimitError,
    DartStockNotFoundError,
)
from app.services.stock_summary_service import StockSummaryService, get_stock_summary_service

router = APIRouter(prefix="/api/v1/stock", tags=["stock"])

# 사용자에게는 원인 범주만 알리고, DART status·메시지 원문은 서버 로그에만 남긴다.
DART_ERROR_RESPONSES: dict[type[DartError], tuple[int, str]] = {
    DartStockNotFoundError: (
        status.HTTP_404_NOT_FOUND,
        "DART에 등록되지 않은 종목 코드예요.",
    ),
    DartNoFinancialsError: (
        status.HTTP_404_NOT_FOUND,
        "조회할 수 있는 정기보고서 재무제표가 없어요.",
    ),
    DartRateLimitError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "DART 조회 한도에 걸렸어요. 잠시 후 다시 시도해 보세요.",
    ),
}
DEFAULT_DART_ERROR = (status.HTTP_502_BAD_GATEWAY, "DART 조회에 실패했어요.")


@router.get("/{code}/summary")
def get_stock_summary(
    code: Annotated[str, Path(pattern=STOCK_CODE_PATTERN, description="6자리 종목코드")],
    service: Annotated[StockSummaryService, Depends(get_stock_summary_service)],
) -> StockSummaryResponse:
    try:
        return service.summarize(code)
    except DartError as exc:
        status_code, detail = DART_ERROR_RESPONSES.get(type(exc), DEFAULT_DART_ERROR)
        raise HTTPException(status_code, detail) from exc
