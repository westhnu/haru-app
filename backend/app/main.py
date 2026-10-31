from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import admin, checklist, glossary, health, journal, poc, stock, workbook
from app.config import get_settings
from app.core.logging import configure_logging
from app.db.engine import get_engine, get_sessionmaker
from app.db.init import init_db, seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """기동 시 스키마 생성 + 비어 있는 테이블에만 샘플 seed (Phase A, idempotent)."""
    init_db(get_engine())
    with get_sessionmaker()() as session:
        seed_if_empty(session)
    yield


def create_app() -> FastAPI:
    # APP_ENV=prod인데 필수 설정이 비어 있으면 여기서 ValidationError가 나서
    # uvicorn 자체가 뜨지 않는다 (결정 2, fail-fast).
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(poc.router)
    app.include_router(stock.router)
    app.include_router(glossary.router)
    app.include_router(admin.router)
    app.include_router(workbook.router)
    app.include_router(checklist.router)
    app.include_router(journal.router)

    structlog.get_logger().info("app_created", version=__version__, app_env=settings.app_env)
    return app


app = create_app()
