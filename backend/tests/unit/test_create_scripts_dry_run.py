"""Phase 4 생성 스크립트 dry-run/apply 검증 (T-453 확장).

실제 boto3 호출 없이 Spy로 호출 여부·순서·idempotent를 검증한다.
dry-run은 어떤 AWS API도 호출하지 않아야 한다(완전 무호출).
"""

from typing import Any

import pytest
from botocore.exceptions import ClientError

from app.config import Settings
from scripts.guardrail import create_guardrail as cg
from scripts.kb import (
    create_or_sync_kb as kb,
)
from scripts.kb import (
    create_s3_bucket as s3b,
)
from scripts.kb import (
    create_vector_bucket as vb,
)
from scripts.kb import (
    create_vector_index as vi,
)

ACCOUNT = "205474063205"


class SpySTS:
    def get_caller_identity(self) -> dict[str, Any]:
        return {"Account": ACCOUNT}


def _not_found(op: str, code: str = "NotFoundException") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "x"}}, op)


# --- T-401 create_s3_bucket ----------------------------------------------------


class SpyS3Bucket:
    def __init__(self, calls: list[str], exists: bool = False) -> None:
        self._calls = calls
        self._exists = exists

    def head_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("head_bucket")
        if not self._exists:
            raise _not_found("HeadBucket", "404")
        return {}

    def create_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("create_bucket")
        return {}

    def put_public_access_block(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("put_public_access_block")
        return {}

    def put_bucket_versioning(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("put_bucket_versioning")
        return {}

    def put_bucket_encryption(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("put_bucket_encryption")
        return {}


def test_s3_bucket_dry_run_no_calls() -> None:
    calls: list[str] = []
    assert s3b.run(dry_run=True, s3=SpyS3Bucket(calls), sts=SpySTS()) is True
    assert calls == []


def test_s3_bucket_defaults_to_dry_run() -> None:
    from scripts._cli import parse_dry_run

    assert parse_dry_run("x", []) is True
    assert parse_dry_run("x", ["--apply"]) is False


def test_s3_bucket_apply_creates_in_order() -> None:
    calls: list[str] = []
    s3b.run(dry_run=False, s3=SpyS3Bucket(calls, exists=False), sts=SpySTS())
    assert calls == [
        "head_bucket",
        "create_bucket",
        "put_public_access_block",
        "put_bucket_versioning",
        "put_bucket_encryption",
    ]


def test_s3_bucket_idempotent_skips_when_exists() -> None:
    calls: list[str] = []
    s3b.run(dry_run=False, s3=SpyS3Bucket(calls, exists=True), sts=SpySTS())
    assert "create_bucket" not in calls


# --- T-401.5-A create_vector_bucket --------------------------------------------


class SpyVectorBucket:
    def __init__(self, calls: list[str], exists: bool = False) -> None:
        self._calls = calls
        self._exists = exists

    def get_vector_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("get_vector_bucket")
        if not self._exists:
            raise _not_found("GetVectorBucket")
        return {"vectorBucket": {"vectorBucketArn": "arn:vec"}}

    def create_vector_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("create_vector_bucket")
        self._exists = True
        return {}


def test_vector_bucket_dry_run_no_calls() -> None:
    calls: list[str] = []
    assert vb.run(dry_run=True, s3v=SpyVectorBucket(calls), sts=SpySTS()) is True
    assert calls == []


def test_vector_bucket_apply_creates() -> None:
    calls: list[str] = []
    vb.run(dry_run=False, s3v=SpyVectorBucket(calls, exists=False), sts=SpySTS())
    assert "create_vector_bucket" in calls


def test_vector_bucket_idempotent() -> None:
    calls: list[str] = []
    vb.run(dry_run=False, s3v=SpyVectorBucket(calls, exists=True), sts=SpySTS())
    assert "create_vector_bucket" not in calls


# --- T-401.5-B create_vector_index ---------------------------------------------


class SpyVectorIndex:
    def __init__(self, calls: list[str], exists: bool = False) -> None:
        self._calls = calls
        self._exists = exists

    def get_index(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("get_index")
        if not self._exists:
            raise _not_found("GetIndex")
        return {"index": {"indexArn": "arn:idx"}}

    def create_index(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("create_index")
        self._exists = True
        return {}


def test_vector_index_dry_run_no_calls() -> None:
    calls: list[str] = []
    assert vi.run(dry_run=True, s3v=SpyVectorIndex(calls), sts=SpySTS()) is True
    assert calls == []


def test_vector_index_apply_creates_with_dimension() -> None:
    calls: list[str] = []
    captured: dict[str, Any] = {}

    class _Spy(SpyVectorIndex):
        def create_index(self, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return super().create_index(**kwargs)

    vi.run(dry_run=False, s3v=_Spy(calls, exists=False), sts=SpySTS())
    assert captured["dimension"] == 1024
    assert captured["distanceMetric"] == "cosine"


def test_vector_index_idempotent() -> None:
    calls: list[str] = []
    vi.run(dry_run=False, s3v=SpyVectorIndex(calls, exists=True), sts=SpySTS())
    assert "create_index" not in calls


def test_create_index_sets_non_filterable_metadata_ki016() -> None:
    captured: dict[str, Any] = {}

    class _Spy(SpyVectorIndex):
        def create_index(self, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return super().create_index(**kwargs)

    vi.run(dry_run=False, s3v=_Spy([], exists=False), sts=SpySTS())
    keys = captured["metadataConfiguration"]["nonFilterableMetadataKeys"]
    assert "AMAZON_BEDROCK_TEXT" in keys
    assert "AMAZON_BEDROCK_METADATA" in keys


def test_create_index_dry_run_no_create_ki016() -> None:
    calls: list[str] = []
    assert vi.run(dry_run=True, s3v=SpyVectorIndex(calls), sts=SpySTS()) is True
    assert "create_index" not in calls


# --- T-404/405 create_or_sync_kb -----------------------------------------------


class _KBPaginator:
    def __init__(self, calls: list[str], existing_kb: bool) -> None:
        self._calls = calls
        self._existing_kb = existing_kb

    def paginate(self, **kwargs: Any) -> Any:
        self._calls.append("list_knowledge_bases")
        if self._existing_kb:
            yield {
                "knowledgeBaseSummaries": [
                    {"name": "haru-glossary-kb", "knowledgeBaseId": "KB-existing"}
                ]
            }
        else:
            yield {"knowledgeBaseSummaries": []}


class _DSPaginator:
    def __init__(self, calls: list[str], existing_ds: bool) -> None:
        self._calls = calls
        self._existing_ds = existing_ds

    def paginate(self, **kwargs: Any) -> Any:
        self._calls.append("paginate_list_data_sources")  # 멱등성 체크용 (sync 직접 호출과 구분)
        if self._existing_ds:
            yield {
                "dataSourceSummaries": [{"name": "haru-glossary-s3", "dataSourceId": "DS-existing"}]
            }
        else:
            yield {"dataSourceSummaries": []}


class SpyAgentKB:
    def __init__(
        self,
        calls: list[str],
        existing_kb: bool = False,
        existing_ds: bool = False,
        kb_statuses: list[str] | None = None,
        failure_reasons: list[str] | None = None,
    ) -> None:
        self._calls = calls
        self._existing_kb = existing_kb
        self._existing_ds = existing_ds
        # get_knowledge_base가 순서대로 반환할 상태. 기본은 즉시 ACTIVE.
        self._kb_statuses = kb_statuses if kb_statuses is not None else ["ACTIVE"]
        self._failure_reasons = failure_reasons or []

    def get_knowledge_base(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("get_knowledge_base")
        status = self._kb_statuses[0] if len(self._kb_statuses) == 1 else self._kb_statuses.pop(0)
        kb: dict[str, Any] = {"knowledgeBaseId": "KB1", "status": status}
        if status in ("FAILED", "DELETING", "DELETE_UNSUCCESSFUL"):
            kb["failureReasons"] = self._failure_reasons
        return {"knowledgeBase": kb}

    def get_paginator(self, op: str) -> Any:
        if op == "list_knowledge_bases":
            return _KBPaginator(self._calls, self._existing_kb)
        return _DSPaginator(self._calls, self._existing_ds)

    def create_knowledge_base(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("create_knowledge_base")
        return {"knowledgeBase": {"knowledgeBaseId": "KB1"}}

    def create_data_source(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("create_data_source")
        return {"dataSource": {"dataSourceId": "DS1"}}

    def list_data_sources(self, **kwargs: Any) -> dict[str, Any]:
        # KI-011: fresh create->sync 경로는 이 API를 호출하면 안 된다.
        # 호출되면 2차 --apply에서 겪은 AccessDenied를 재현해 테스트를 실패시킨다.
        self._calls.append("list_data_sources")
        raise _not_found("ListDataSources", "AccessDeniedException")

    def start_ingestion_job(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("start_ingestion_job")
        return {"ingestionJob": {"ingestionJobId": "JOB1"}}

    def get_ingestion_job(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("get_ingestion_job")
        return {"ingestionJob": {"status": "COMPLETE"}}


def _settings_with_role(role: str = "arn:role") -> Settings:
    return Settings(
        _env_file=None,
        bedrock_kb_role_arn=role,
        haru_kb_s3_bucket="haru-kb-data-x",
        haru_kb_vector_bucket_arn="arn:vec",
        haru_kb_s3_vector_index_arn="arn:idx",
    )


def test_kb_dry_run_no_calls() -> None:
    calls: list[str] = []
    ok = kb.run(
        dry_run=True,
        do_create=True,
        agent=SpyAgentKB(calls),
        sts=SpySTS(),
        settings=_settings_with_role(),
    )
    assert ok is True
    assert calls == []


def test_kb_apply_without_role_shows_guide() -> None:
    calls: list[str] = []
    ok = kb.run(
        dry_run=False,
        do_create=True,
        agent=SpyAgentKB(calls),
        sts=SpySTS(),
        settings=_settings_with_role(role=""),
    )
    assert ok is False
    assert "create_knowledge_base" not in calls


def test_kb_apply_creates_kb_and_data_source() -> None:
    calls: list[str] = []
    ok = kb.run(
        dry_run=False,
        do_create=True,
        agent=SpyAgentKB(calls),
        sts=SpySTS(),
        settings=_settings_with_role(),
    )
    assert ok is True
    # 멱등성 체크(list) 후 둘 다 없으면 생성.
    assert calls == [
        "list_knowledge_bases",
        "create_knowledge_base",
        "get_knowledge_base",
        "paginate_list_data_sources",
        "create_data_source",
    ]


def test_create_kb_skips_when_name_exists() -> None:
    calls: list[str] = []
    ok = kb.run(
        dry_run=False,
        do_create=True,
        agent=SpyAgentKB(calls, existing_kb=True, existing_ds=True),
        sts=SpySTS(),
        settings=_settings_with_role(),
    )
    assert ok is True
    assert "create_knowledge_base" not in calls  # 동명 KB 재사용
    assert "create_data_source" not in calls  # 동명 DS 재사용
    assert "list_knowledge_bases" in calls


def test_create_data_source_skips_when_name_exists() -> None:
    calls: list[str] = []
    # KB는 새로, DS만 이미 존재
    ok = kb.run(
        dry_run=False,
        do_create=True,
        agent=SpyAgentKB(calls, existing_kb=False, existing_ds=True),
        sts=SpySTS(),
        settings=_settings_with_role(),
    )
    assert ok is True
    assert "create_knowledge_base" in calls  # KB는 생성
    assert "create_data_source" not in calls  # DS는 재사용


def test_storage_config_omits_index_name_ki010() -> None:
    # KI-010: indexArn과 indexName 동시 전달 시 ValidationException. indexName은 넣지 않는다.
    storage = kb._storage_config(_settings_with_role())
    s3v = storage["s3VectorsConfiguration"]
    assert "indexArn" in s3v
    assert "vectorBucketArn" in s3v
    assert "indexName" not in s3v


def test_sync_uses_create_result_ds_id_ki011() -> None:
    # fresh create->sync: create가 반환한 ds_id를 직접 써서 list_data_sources를 호출하지 않는다.
    calls: list[str] = []
    ok = kb.run(
        dry_run=False,
        do_create=True,
        do_sync=True,
        agent=SpyAgentKB(calls),
        sts=SpySTS(),
        settings=_settings_with_role(),
    )
    assert ok is True
    assert "list_data_sources" not in calls  # KI-011: 재조회 안 함
    assert "start_ingestion_job" in calls


def test_create_waits_for_kb_active_ki013(monkeypatch: Any) -> None:
    # KI-013: create 후 ACTIVE까지 폴링한 뒤에만 sync 시작.
    monkeypatch.setattr(kb.time, "sleep", lambda _s: None)
    calls: list[str] = []
    agent = SpyAgentKB(calls, kb_statuses=["CREATING", "CREATING", "ACTIVE"])
    ok = kb.run(
        dry_run=False,
        do_create=True,
        do_sync=True,
        agent=agent,
        sts=SpySTS(),
        settings=_settings_with_role(),
    )
    assert ok is True
    assert calls.count("get_knowledge_base") == 3  # CREATING, CREATING, ACTIVE
    # get_knowledge_base(마지막 ACTIVE)가 start_ingestion_job보다 앞선다.
    assert calls.index("get_knowledge_base") < calls.index("start_ingestion_job")
    assert calls.count("start_ingestion_job") == 1


def test_create_fails_fast_on_kb_failed_ki013(monkeypatch: Any) -> None:
    monkeypatch.setattr(kb.time, "sleep", lambda _s: None)
    calls: list[str] = []
    agent = SpyAgentKB(calls, kb_statuses=["FAILED"], failure_reasons=["dummy"])
    with pytest.raises(RuntimeError):
        kb.run(
            dry_run=False,
            do_create=True,
            do_sync=True,
            agent=agent,
            sts=SpySTS(),
            settings=_settings_with_role(),
        )
    assert "start_ingestion_job" not in calls  # sync 도달 전 fail-fast


def test_wait_kb_active_passes_through_when_already_active_ki013() -> None:
    calls: list[str] = []
    agent = SpyAgentKB(calls, kb_statuses=["ACTIVE"])
    kb._wait_kb_active(agent, "KB1", poll_interval_s=0)
    assert calls.count("get_knowledge_base") == 1  # 즉시 통과


def test_kb_no_mode_returns_false() -> None:
    assert kb.run(dry_run=True, settings=_settings_with_role()) is False


# --- T-407 create_guardrail ----------------------------------------------------


class SpyBedrockGuardrail:
    def __init__(self, calls: list[str], existing: bool = False) -> None:
        self._calls = calls
        self._existing = existing

    def list_guardrails(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("list_guardrails")
        if self._existing:
            return {"guardrails": [{"name": cg.GUARDRAIL_NAME, "id": "gr-existing"}]}
        return {"guardrails": []}

    def create_guardrail(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("create_guardrail")
        return {"guardrailId": "gr-new"}


def test_guardrail_dry_run_no_calls() -> None:
    calls: list[str] = []
    assert cg.run(dry_run=True, bedrock=SpyBedrockGuardrail(calls)) is True
    assert calls == []


def test_guardrail_apply_creates_six_policies() -> None:
    calls: list[str] = []
    cg.run(dry_run=False, bedrock=SpyBedrockGuardrail(calls, existing=False))
    assert calls == ["list_guardrails", "create_guardrail"]
    # 6개 정책 키 존재 확인
    kw = cg._build_kwargs()
    assert len(kw["topicPolicyConfig"]["topicsConfig"]) == 2
    assert len(kw["wordPolicyConfig"]["wordsConfig"]) == 4
    assert kw["sensitiveInformationPolicyConfig"]["piiEntitiesConfig"][0]["type"] == "KR_RRN"
    assert len(kw["contentPolicyConfig"]["filtersConfig"]) == 3
    assert kw["contextualGroundingPolicyConfig"]["filtersConfig"][0]["threshold"] == 0.75


def test_guardrail_idempotent_skips_when_exists() -> None:
    calls: list[str] = []
    cg.run(dry_run=False, bedrock=SpyBedrockGuardrail(calls, existing=True))
    assert "create_guardrail" not in calls
