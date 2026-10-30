"""용어 사전 KB 질의 라우터 (T-302, US-1).

POST /api/v1/glossary/ask → rag_service.ask(context_type="glossary").
예외 매핑은 poc.py와 동일 패턴 — 내부 AWS 오류를 숨기고 502로 변환한다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.models.rag import MAX_QUERY_LENGTH, RagResponse
from app.services.rag_service import RagService, RagServiceError, get_rag_service

router = APIRouter(prefix="/api/v1/glossary", tags=["glossary"])


class GlossaryAskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)


@router.post("/ask")
def ask(
    request: GlossaryAskRequest,
    service: Annotated[RagService, Depends(get_rag_service)],
) -> RagResponse:
    try:
        return service.ask(request.query, context_type="glossary")
    except RagServiceError as exc:
        # AWS 에러 메시지·ARN 같은 내부 정보는 로그에만 남기고 클라이언트에는 노출하지 않는다.
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI 응답 생성에 실패했습니다.") from exc
