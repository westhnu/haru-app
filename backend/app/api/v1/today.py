from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.engine import get_session
from app.models.today import TodayCard
from app.services.today_service import TodayService, get_today_service

router = APIRouter(prefix="/api/v1/today", tags=["today"])


@router.get("", response_model=TodayCard)
def get_today(
    session: Annotated[Session, Depends(get_session)],
    today_service: Annotated[TodayService, Depends(get_today_service)],
) -> TodayCard:
    """홈 '오늘의 흐름' 카드. 사용자 본인 기록(저널·워크북·체크리스트)만 요약한다."""
    return today_service.build_today_card(session)
