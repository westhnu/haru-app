"""POST /api/v1/poc/ask 통합 테스트.

실제 AWS 호출은 절대 하지 않는다 — 요금·flakiness 방지. Bedrock 클라이언트는 Fake로 주입한다.
"""

from collections.abc import Iterator
from typing import Any

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.guardrail import DISCLAIMER, SAFE_REPLACEMENT
from app.main import app
from app.services.rag_service import RagService, get_rag_service

ASK_URL = "/api/v1/poc/ask"
KB_ID = "TESTKB0001"
MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
S3_SOURCE = "s3://haru-kb/glossary/per.md"
PER_EXCERPT = "PER(주가수익비율) = 주가 / 주당순이익(EPS)"


class FakeAgentRuntimeClient:
    """RetrieveAndGenerate 응답 형태만 흉내 내고, 받은 요청을 기록한다."""

    def __init__(self, output_text: str, citations: list[dict[str, Any]] | None = None) -> None:
        self.requests: list[dict[str, Any]] = []
        self._response = {
            "output": {"text": output_text},
            "citations": citations or [],
            "sessionId": "test-session",
        }

    def retrieve_and_generate(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return self._response


class ExplodingClient:
    def retrieve_and_generate(self, **request: Any) -> dict[str, Any]:
        raise AssertionError("KB 미설정 상태에서는 Bedrock을 호출하면 안 된다")


class FailingClient:
    def retrieve_and_generate(self, **request: Any) -> dict[str, Any]:
        error = {"Error": {"Code": "AccessDeniedException", "Message": "arn:aws:bedrock:secret"}}
        raise ClientError(error, "RetrieveAndGenerate")


def s3_citation(excerpt: str, uri: str) -> dict[str, Any]:
    return {
        "generatedResponsePart": {"textResponsePart": {"text": "생성된 문장", "span": {}}},
        "retrievedReferences": [
            {"content": {"text": excerpt}, "location": {"type": "S3", "s3Location": {"uri": uri}}}
        ],
    }


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.clear()


def use_service(agent_client: Any, kb_id: str = KB_ID) -> None:
    # 로컬 backend/.env 에 실제 KB ID가 있어도 테스트가 실호출하지 않도록
    # .env를 읽지 않고 값을 명시한다.
    settings = Settings(_env_file=None, bedrock_kb_id=kb_id, bedrock_model_id=MODEL_ID)
    service = RagService(settings, agent_client=agent_client)
    app.dependency_overrides[get_rag_service] = lambda: service


def test_ask_without_kb_returns_mock_with_disclaimer(client: TestClient) -> None:
    use_service(ExplodingClient(), kb_id="")

    response = client.post(ASK_URL, json={"query": "PER이 뭐야?"})

    assert response.status_code == 200
    body = response.json()
    assert body["model_id"] == "mock"
    assert body["answer"].endswith(DISCLAIMER)
    assert body["disclaimer"] == DISCLAIMER
    assert body["citations"] == []


def test_ask_with_kb_returns_answer_citations_and_disclaimer(client: TestClient) -> None:
    fake = FakeAgentRuntimeClient(
        "PER은 주가를 주당순이익으로 나눈 값입니다.",
        citations=[s3_citation(PER_EXCERPT, S3_SOURCE), s3_citation(PER_EXCERPT, S3_SOURCE)],
    )
    use_service(fake)

    response = client.post(ASK_URL, json={"query": "PER이 뭐야?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == f"PER은 주가를 주당순이익으로 나눈 값입니다.\n\n{DISCLAIMER}"
    assert body["citations"] == [{"excerpt": PER_EXCERPT, "source": S3_SOURCE}]
    assert body["model_id"] == MODEL_ID
    kb_config = fake.requests[0]["retrieveAndGenerateConfiguration"]["knowledgeBaseConfiguration"]
    assert kb_config["knowledgeBaseId"] == KB_ID
    assert (
        "$search_results$"
        in kb_config["generationConfiguration"]["promptTemplate"]["textPromptTemplate"]
    )


def test_forbidden_phrase_from_model_is_replaced(client: TestClient) -> None:
    use_service(
        FakeAgentRuntimeClient("실적이 좋아 보입니다. 이 종목을 매수하세요. 내일 오릅니다.")
    )

    response = client.post(ASK_URL, json={"query": "삼성전자 어때?"})

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert answer == f"{SAFE_REPLACEMENT}\n\n{DISCLAIMER}"
    assert "매수하세요" not in answer


def test_pii_is_masked_before_reaching_bedrock(client: TestClient) -> None:
    fake = FakeAgentRuntimeClient("계좌 정보는 다루지 않습니다.")
    use_service(fake)

    client.post(ASK_URL, json={"query": "계좌 110-123-456789 수익률 알려줘"})

    assert fake.requests[0]["input"]["text"] == "계좌 [계좌번호] 수익률 알려줘"


def test_bedrock_failure_returns_502_without_internal_details(client: TestClient) -> None:
    use_service(FailingClient())

    response = client.post(ASK_URL, json={"query": "PER이 뭐야?"})

    assert response.status_code == 502
    assert "arn:aws" not in response.text
