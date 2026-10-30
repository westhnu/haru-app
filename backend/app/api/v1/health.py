from fastapi import APIRouter

from app import __version__
from app.models.health import HealthResponse

# 로드밸런서·Lambda 헬스체크가 버전 prefix 없이 찌를 수 있도록 루트 경로에 둔다.
router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)
