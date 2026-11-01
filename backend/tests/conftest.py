"""pytest 공용 fixture.

실제 AWS 호출은 절대 하지 않는다. Fake 클라이언트를 monkeypatch로 주입하거나
생성자 주입으로 격리한다.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db import engine as db_engine
from app.db.init import init_db, seed_if_empty


class FakeAgentRuntimeClient:
    """bedrock-agent-runtime.retrieve_and_generate 응답 형태만 흉내 내고 요청을 기록한다."""

    def __init__(self, output_text: str, citations: list[dict[str, Any]] | None = None) -> None:
        self.requests: list[dict[str, Any]] = []
        self._response: dict[str, Any] = {
            "output": {"text": output_text},
            "citations": citations or [],
            "sessionId": "test-session",
        }

    def retrieve_and_generate(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return self._response


def make_s3_citation(excerpt: str, uri: str) -> dict[str, Any]:
    """RetrieveAndGenerate citations[] 한 항목 (S3 location)."""
    return {
        "generatedResponsePart": {"textResponsePart": {"text": "생성된 문장", "span": {}}},
        "retrievedReferences": [
            {"content": {"text": excerpt}, "location": {"type": "S3", "s3Location": {"uri": uri}}}
        ],
    }


@pytest.fixture
def fake_agent_runtime(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeAgentRuntimeClient]:
    """get_agent_runtime_client를 Fake로 패치한다 — 실제 boto3 호출이 일어나지 않는다."""
    fake = FakeAgentRuntimeClient("기본 응답")

    def _factory() -> FakeAgentRuntimeClient:
        return fake

    monkeypatch.setattr("app.services.rag_service.get_agent_runtime_client", _factory)
    yield fake


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """테스트마다 빈 in-memory SQLite를 새로 만든다 (Phase A).

    테스트가 create_app()을 매번 새로 만들기 때문에 앱 인스턴스별 dependency_overrides 대신
    세션 공급원(get_engine·get_sessionmaker) 자체를 바꿔 끼운다.
    실제 backend/data/haru.db는 열지 않는다.
    """
    engine = db_engine.build_engine("sqlite:///:memory:")
    init_db(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    for target in ("app.db.engine", "app.main"):
        monkeypatch.setattr(f"{target}.get_engine", lambda: engine)
        monkeypatch.setattr(f"{target}.get_sessionmaker", lambda: factory)
    yield engine
    engine.dispose()


@pytest.fixture
def seeded_db(isolated_db: Engine) -> Engine:
    """앱 기동 때와 같은 샘플 seed가 필요한 테스트용."""
    with Session(isolated_db) as session:
        seed_if_empty(session)
    return isolated_db
