"""pytest 공용 fixture.

실제 AWS 호출은 절대 하지 않는다. Fake 클라이언트를 monkeypatch로 주입하거나
생성자 주입으로 격리한다.
"""

from collections.abc import Iterator
from typing import Any

import pytest


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
