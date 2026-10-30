"""KbAdminService start_sync / poll_sync / get_status 검증 (T-202 DoD).

KB_ID 빈 문자열(Fake 분기)과 Fake bedrock-agent 클라이언트 주입 두 경로를 모두 검증한다.
실제 boto3 호출은 하지 않는다.
"""

from typing import Any

from app.config import Settings
from app.services.kb_admin_service import (
    MOCK_INGESTION_JOB_ID,
    POLL_INTERVAL_S,
    KbAdminService,
)

KB_ID = "TESTKB0001"
DS_ID = "DS0001"
JOB_ID = "job-123"


class FakeBedrockAgent:
    """bedrock-agent 제어 평면 응답 형태만 흉내 낸다."""

    def __init__(self, statuses: list[str], kb_status: str = "ACTIVE") -> None:
        self._statuses = statuses
        self._kb_status = kb_status
        self.calls: list[str] = []

    def start_ingestion_job(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("start")
        return {"ingestionJob": {"ingestionJobId": JOB_ID}}

    def get_ingestion_job(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append("get")
        status = self._statuses.pop(0) if len(self._statuses) > 1 else self._statuses[0]
        return {"ingestionJob": {"status": status}}

    def get_knowledge_base(self, **kwargs: Any) -> dict[str, Any]:
        return {"knowledgeBase": {"status": self._kb_status, "updatedAt": "2026-10-30T00:00:00Z"}}


def _settings(kb_id: str) -> Settings:
    return Settings(_env_file=None, bedrock_kb_id=kb_id)


# --- Fake 분기 (KB_ID 빈 문자열) ---------------------------------------------------


def test_start_sync_fake_mode_returns_mock_job() -> None:
    svc = KbAdminService(_settings(""))

    assert svc.start_sync("", DS_ID) == MOCK_INGESTION_JOB_ID


def test_poll_sync_fake_mode_returns_complete() -> None:
    svc = KbAdminService(_settings(""))

    assert svc.poll_sync("", MOCK_INGESTION_JOB_ID) == "COMPLETE"


def test_get_status_fake_mode_is_mock() -> None:
    status = KbAdminService(_settings("")).get_status("")

    assert status.is_mock is True
    assert status.status == "COMPLETE"


def test_poll_interval_default_is_15s() -> None:
    assert POLL_INTERVAL_S == 15


# --- Fake 클라이언트 주입 (실호출 경로 로직 검증, boto3 없음) ------------------------


def test_start_sync_injected_returns_job_id() -> None:
    agent = FakeBedrockAgent(statuses=["IN_PROGRESS"])
    svc = KbAdminService(_settings(KB_ID), agent_client=agent)

    assert svc.start_sync(KB_ID, DS_ID) == JOB_ID
    assert "start" in agent.calls


def test_poll_sync_injected_stops_on_complete() -> None:
    agent = FakeBedrockAgent(statuses=["COMPLETE"])
    svc = KbAdminService(_settings(KB_ID), agent_client=agent)

    # poll_interval_s=0으로 sleep 없이 즉시 판정.
    assert svc.poll_sync(KB_ID, JOB_ID, poll_interval_s=0) == "COMPLETE"


def test_poll_sync_injected_stops_on_failed() -> None:
    agent = FakeBedrockAgent(statuses=["FAILED"])
    svc = KbAdminService(_settings(KB_ID), agent_client=agent)

    assert svc.poll_sync(KB_ID, JOB_ID, poll_interval_s=0) == "FAILED"


def test_get_status_injected_maps_fields() -> None:
    agent = FakeBedrockAgent(statuses=["COMPLETE"], kb_status="ACTIVE")
    svc = KbAdminService(_settings(KB_ID), agent_client=agent)

    status = svc.get_status(KB_ID)

    assert status.kb_id == KB_ID
    assert status.status == "ACTIVE"
    assert status.last_sync_at == "2026-10-30T00:00:00Z"
    assert status.is_mock is False
