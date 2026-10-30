"""GET /api/v1/admin/kb-status 통합 테스트 (T-303).

KB_ID 미설정(mock)과 Fake bedrock-agent 주입(is_mock=False) 두 경로를 검증한다.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.kb_admin_service import KbAdminService, get_kb_admin_service

STATUS_URL = "/api/v1/admin/kb-status"
KB_ID = "TESTKB0001"


class FakeBedrockAgent:
    def get_knowledge_base(self, **kwargs: Any) -> dict[str, Any]:
        return {"knowledgeBase": {"status": "ACTIVE", "updatedAt": "2026-10-30T00:00:00Z"}}


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_kb_status_mock_mode(client: TestClient) -> None:
    settings = Settings(_env_file=None, bedrock_kb_id="")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_kb_admin_service] = lambda: KbAdminService(settings)

    response = client.get(STATUS_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["is_mock"] is True
    assert body["status"] == "COMPLETE"


def test_kb_status_with_fake_agent(client: TestClient) -> None:
    settings = Settings(_env_file=None, bedrock_kb_id=KB_ID)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_kb_admin_service] = lambda: KbAdminService(
        settings, agent_client=FakeBedrockAgent()
    )

    response = client.get(STATUS_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["is_mock"] is False
    assert body["kb_id"] == KB_ID
    assert body["status"] == "ACTIVE"
    assert body["last_synced_at"] == "2026-10-30T00:00:00Z"
