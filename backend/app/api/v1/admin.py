"""KB 운영 상태 조회 라우터 (T-303, US-3·REQ-OBS-03).

GET /api/v1/admin/kb-status → kb_admin_service.get_status(kb_id).
인증은 이 스펙 범위 밖(향후 스프린트). read-only 라서 HITL·부작용 없음.
KB_ID가 비면 kb_admin_service가 is_mock=True 응답을 돌려준다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.services.kb_admin_service import KbAdminService, get_kb_admin_service


class KbStatusResponse(BaseModel):
    kb_id: str
    status: str
    last_synced_at: str | None = None
    chunk_count: int | None = None
    is_mock: bool = False


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/kb-status")
def kb_status(
    service: Annotated[KbAdminService, Depends(get_kb_admin_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> KbStatusResponse:
    status = service.get_status(settings.bedrock_kb_id)
    # KbStatus(서비스 레이어) → KbStatusResponse(API 레이어) 필드명 매핑.
    return KbStatusResponse(
        kb_id=status.kb_id,
        status=status.status,
        last_synced_at=status.last_sync_at,
        chunk_count=status.indexed_chunks,
        is_mock=status.is_mock,
    )
