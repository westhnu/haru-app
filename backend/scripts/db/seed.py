"""SQLite 스키마 생성 + 샘플 seed (Phase A). 앱 기동(lifespan)과 같은 동작을 CLI로 실행한다.

    PYTHONPATH=. uv run python scripts/db/seed.py

테이블별로 비어 있을 때만 샘플을 넣는다(idempotent). 외부 호출 없음.
"""

import sys

from sqlalchemy import func, select

from app.config import get_settings
from app.db.engine import get_engine, get_sessionmaker
from app.db.init import init_db, seed_if_empty
from app.db.models import ChecklistORM, JournalEntryORM, WorkbookORM


def main() -> int:
    url = get_settings().database_url
    init_db(get_engine())
    with get_sessionmaker()() as session:
        seeded = seed_if_empty(session)
        counts = {
            orm.__tablename__: session.scalar(select(func.count()).select_from(orm))
            for orm in (WorkbookORM, ChecklistORM, JournalEntryORM)
        }
    print(f"DB: {url}")
    print(f"seed: {', '.join(seeded) if seeded else '건너뜀 (모든 테이블에 데이터 있음)'}")
    print(f"rows: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
