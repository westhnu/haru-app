import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import admin, checklist, glossary, health, journal, poc, stock, workbook
from app.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    # APP_ENV=prod인데 필수 설정이 비어 있으면 여기서 ValidationError가 나서
    # uvicorn 자체가 뜨지 않는다 (결정 2, fail-fast).
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
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
