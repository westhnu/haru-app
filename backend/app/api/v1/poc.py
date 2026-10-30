from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.rag import RagRequest, RagResponse
from app.services.rag_service import RagService, RagServiceError, get_rag_service

router = APIRouter(prefix="/api/v1/poc", tags=["poc"])


@router.post("/ask")
def ask(
    request: RagRequest,
    service: Annotated[RagService, Depends(get_rag_service)],
) -> RagResponse:
    try:
        return service.ask(request.query, request.context_type)
    except RagServiceError as exc:
        # AWS 에러 메시지·ARN 같은 내부 정보는 로그에만 남기고 클라이언트에는 노출하지 않는다.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI 응답 생성에 실패했습니다.") from exc
