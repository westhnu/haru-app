"""SQLAlchemy 2.0 sync 엔진·세션 (Phase A).

엔진·세션 팩토리는 첫 사용 때 만든다(import만으로 DB 파일이 생기지 않게).
테스트는 conftest가 get_engine·get_sessionmaker를 in-memory 엔진으로 바꿔 끼운다.
"""

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine(url: str) -> Engine:
    """SQLite 전용 설정을 붙여 엔진을 만든다.

    - FastAPI sync 엔드포인트는 스레드풀에서 돌므로 check_same_thread=False
    - :memory:는 연결마다 DB가 따로 생기므로 StaticPool로 연결 하나를 공유
    - 파일 DB는 상위 디렉터리를 만든다 (backend/data/)
    - FK 제약(ON DELETE CASCADE·SET NULL)은 SQLite에서 연결마다 켜야 동작한다
    """
    parsed = make_url(url)
    kwargs: dict[str, Any] = {}
    if parsed.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}
        database = parsed.database or ""
        if database in ("", ":memory:"):
            kwargs["poolclass"] = StaticPool
        else:
            Path(database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **kwargs)
    if parsed.get_backend_name() == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn: Any, _record: Any) -> None:
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings().database_url)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI Depends용 요청 단위 세션. 커밋은 repository가 한다."""
    with get_sessionmaker()() as session:
        yield session
