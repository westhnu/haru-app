"""스키마 생성 + 샘플 seed (Phase A).

seed_if_empty는 테이블별로 비어 있을 때만 샘플을 넣는다(idempotent). 사용자 데이터가 하나라도
있으면 그 테이블은 건드리지 않는다. 원칙 2: 샘플에는 출처 없는 재무 수치를 넣지 않는다.
"""

import structlog
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401  (테이블 등록)
from app.db.engine import Base, get_engine
from app.db.models import (
    ChecklistItemORM,
    ChecklistORM,
    JournalEntryORM,
    WorkbookBlockORM,
    WorkbookORM,
)

logger = structlog.get_logger(__name__)

SAMPLE_WORKBOOK_ID = "sample-samsung"
SAMPLE_CHECKLIST_ID = "sample-value"
SAMPLE_JOURNAL_ID = "sample-1"


def init_db(engine: Engine | None = None) -> None:
    Base.metadata.create_all(engine or get_engine())


def _is_empty(session: Session, orm: type) -> bool:
    return (session.scalar(select(func.count()).select_from(orm)) or 0) == 0


def seed_if_empty(session: Session) -> list[str]:
    """비어 있는 테이블에만 샘플을 넣고, 넣은 테이블 이름을 돌려준다."""
    seeded: list[str] = []
    if _is_empty(session, WorkbookORM):
        session.add(
            WorkbookORM(
                id=SAMPLE_WORKBOOK_ID,
                stock_code="005930",
                stock_name="삼성전자",
                title="삼성전자 2025 Q3 분석",
                blocks=[
                    WorkbookBlockORM(
                        id="sample-memo-001",
                        block_type="memo",
                        content={"text": "매출 성장 둔화, 메모리 사이클 확인 필요"},
                    )
                ],
            )
        )
        seeded.append("workbooks")
    if _is_empty(session, ChecklistORM):
        # 1·2는 DART 비율로 판정 가능, 3은 다년 데이터가 없어 AI가 '판단 어려움'으로 답해야 한다
        # (원칙 2 refuse 체감). 판정·근거는 비워 둔다.
        principles = (
            "부채비율이 200% 미만인가?",
            "영업이익률이 전년 대비 개선되었는가?",
            "최근 3년 ROE 추이가 10% 이상 유지되는가?",
        )
        session.add(
            ChecklistORM(
                id=SAMPLE_CHECKLIST_ID,
                stock_code="005930",
                stock_name="삼성전자",
                items=[
                    ChecklistItemORM(id=f"{SAMPLE_CHECKLIST_ID}-{i}", principle=p)
                    for i, p in enumerate(principles, 1)
                ],
            )
        )
        seeded.append("checklists")
    session.flush()  # 저널 샘플이 체크리스트를 FK로 참조하므로 먼저 반영
    if _is_empty(session, JournalEntryORM):
        has_checklist = session.get(ChecklistORM, SAMPLE_CHECKLIST_ID) is not None
        session.add(
            JournalEntryORM(
                id=SAMPLE_JOURNAL_ID,
                stock_code="005930",
                stock_name="삼성전자",
                decision="watch",
                reasoning=(
                    "체크리스트 원칙을 직접 채워 본 뒤 결정하기로 함. "
                    "다음 분기 실적 공시를 확인할 예정."
                ),
                checklist_id=SAMPLE_CHECKLIST_ID if has_checklist else None,
                virtual_quantity=0,
            )
        )
        seeded.append("journal_entries")
    session.commit()
    if seeded:
        logger.info("db_seeded", tables=seeded)
    return seeded
