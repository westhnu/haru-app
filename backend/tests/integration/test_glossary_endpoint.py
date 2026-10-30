"""POST /api/v1/glossary/ask 통합 테스트 (T-302).

실제 AWS 호출은 하지 않는다 — mock 모드와 Fake 클라이언트 주입만 사용한다.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.guardrail import DISCLAIMER
from app.main import app
from app.services.rag_service import RagService, get_rag_service

ASK_URL = "/api/v1/glossary/ask"
KB_ID = "TESTKB0001"


class FailingClient:
    def retrieve_and_generate(self, **request: Any) -> dict[str, Any]:
        error = {"Error": {"Code": "AccessDeniedException", "Message": "arn:aws:bedrock:secret"}}
        raise ClientError(error, "RetrieveAndGenerate")


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override(service: RagService) -> None:
    app.dependency_overrides[get_rag_service] = lambda: service


def test_glossary_ask_mock_mode_returns_200(client: TestClient) -> None:
    _override(RagService(Settings(_env_file=None, bedrock_kb_id="")))

    response = client.post(ASK_URL, json={"query": "PER이 뭐야?"})

    assert response.status_code == 200
    body = response.json()
    assert body["is_mock"] is True
    assert body["disclaimer"] == DISCLAIMER
    assert body["citations"] == []
    assert body["context_type"] == "glossary"
    assert body["summary_source"] == "template"


def test_glossary_ask_blank_query_returns_422(client: TestClient) -> None:
    _override(RagService(Settings(_env_file=None, bedrock_kb_id="")))

    response = client.post(ASK_URL, json={"query": "   "})

    assert response.status_code == 422


def test_glossary_ask_bedrock_failure_returns_502(client: TestClient) -> None:
    _override(
        RagService(Settings(_env_file=None, bedrock_kb_id=KB_ID), agent_client=FailingClient())
    )

    response = client.post(ASK_URL, json={"query": "PER이 뭐야?"})

    assert response.status_code == 502
    assert "arn:aws" not in response.text
