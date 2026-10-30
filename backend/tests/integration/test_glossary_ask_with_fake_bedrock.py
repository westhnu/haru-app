"""Fake Bedrock 응답 주입 시 RagResponse 매핑이 정확한지 (T-203).

conftest의 fake_agent_runtime fixture로 get_agent_runtime_client를 패치해 실호출을 막는다.
"""

from app.config import Settings
from app.core.guardrail import DISCLAIMER
from app.services.rag_service import RagService
from tests.conftest import FakeAgentRuntimeClient, make_s3_citation

KB_ID = "TESTKB0001"
MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
S3_SOURCE = "s3://haru-kb/glossary/per.jsonl"
PER_EXCERPT = "PER(주가수익비율) = 주가 / 주당순이익(EPS)"


def _service_with_fake(fake: FakeAgentRuntimeClient) -> RagService:
    settings = Settings(_env_file=None, bedrock_kb_id=KB_ID, bedrock_model_id=MODEL_ID)
    return RagService(settings, agent_client=fake)


def test_fake_bedrock_answer_and_citations_mapped() -> None:
    fake = FakeAgentRuntimeClient(
        "PER은 주가를 주당순이익으로 나눈 값입니다.",
        citations=[make_s3_citation(PER_EXCERPT, S3_SOURCE)],
    )

    response = _service_with_fake(fake).ask("PER이 뭐야?", context_type="glossary")

    assert response.answer == f"PER은 주가를 주당순이익으로 나눈 값입니다.\n\n{DISCLAIMER}"
    assert response.source == "knowledge_base"
    assert response.model_id == MODEL_ID
    assert len(response.citations) == 1
    assert response.citations[0].excerpt == PER_EXCERPT
    assert response.citations[0].source == S3_SOURCE
    assert response.is_mock is False


def test_fake_bedrock_deduplicates_identical_citations() -> None:
    fake = FakeAgentRuntimeClient(
        "설명",
        citations=[
            make_s3_citation(PER_EXCERPT, S3_SOURCE),
            make_s3_citation(PER_EXCERPT, S3_SOURCE),
        ],
    )

    response = _service_with_fake(fake).ask("PER이 뭐야?", context_type="glossary")

    assert len(response.citations) == 1


def test_fake_bedrock_factory_patched_not_called_for_injected_client(
    fake_agent_runtime: FakeAgentRuntimeClient,
) -> None:
    # 생성자 주입이 우선하므로 fixture의 패치 대상은 호출되지 않는다 (실호출 0 확인용 스모크).
    fake = FakeAgentRuntimeClient("설명", citations=[make_s3_citation(PER_EXCERPT, S3_SOURCE)])

    response = _service_with_fake(fake).ask("PER이 뭐야?", context_type="glossary")

    assert response.citations[0].source == S3_SOURCE
    assert fake_agent_runtime.requests == []
