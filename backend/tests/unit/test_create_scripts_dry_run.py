"""Phase 4 생성 스크립트 dry-run/apply 검증 (T-453 확장).

실제 boto3 호출 없이 Spy로 호출 여부·순서·idempotent를 검증한다.
dry-run은 어떤 AWS API도 호출하지 않아야 한다(완전 무호출).
"""

import json
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

from app.config import Settings
from scripts.guardrail import create_guardrail as cg
from scripts.kb import (
    convert_glossary as cv,
)
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
from scripts.kb import (
    upload_glossary as up,
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


# --- T-402 convert_glossary (local, no AWS) ------------------------------------


def test_convert_line_count_matches_input(tmp_path: Path) -> None:
    src = tmp_path / "g.json"
    src.write_text(
        json.dumps({"PER": {"description": "d", "formula": "", "related_terms": []}}),
        encoding="utf-8",
    )
    out = tmp_path / "g.jsonl"
    count = cv.convert(src, out)
    assert count == 1
    assert len(out.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_convert_omits_empty_fields(tmp_path: Path) -> None:
    src = tmp_path / "g.json"
    src.write_text(
        json.dumps({"PER": {"description": "d", "formula": "", "related_terms": []}}),
        encoding="utf-8",
    )
    out = tmp_path / "g.jsonl"
    cv.convert(src, out)
    record = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert "formula" not in record  # 빈 문자열은 생략
    assert "related_terms" not in record  # 빈 배열은 생략
    assert record["id"] == "glossary_001"
    assert record["source"] == cv.SOURCE_FALLBACK


def test_convert_keeps_source_when_present(tmp_path: Path) -> None:
    src = tmp_path / "g.json"
    src.write_text(json.dumps({"X": {"description": "d", "source": "원본"}}), encoding="utf-8")
    out = tmp_path / "g.jsonl"
    cv.convert(src, out)
    record = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert record["source"] == "원본"


# --- T-403 upload_glossary -----------------------------------------------------


class SpyS3Upload:
    def __init__(self, calls: list[str], etag: str | None = None) -> None:
        self._calls = calls
        self._etag = etag

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("head_object")
        if self._etag is None:
            raise _not_found("HeadObject", "404")
        return {"ETag": f'"{self._etag}"'}

    def upload_file(self, *args: Any, **kwargs: Any) -> None:
        self._calls.append("upload_file")


def test_upload_dry_run_no_calls() -> None:
    calls: list[str] = []
    assert up.run(dry_run=True, s3=SpyS3Upload(calls), bucket="b") is True
    assert calls == []


def test_upload_empty_bucket_is_success_noop() -> None:
    calls: list[str] = []
    assert up.run(dry_run=False, s3=SpyS3Upload(calls), bucket="") is True
    assert calls == []


def test_upload_apply_uploads_when_absent() -> None:
    calls: list[str] = []
    # 로컬 파일이 존재해야 한다 (convert로 생성됨). 없으면 생성.
    if not up.LOCAL_PATH.exists():
        up.LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        up.LOCAL_PATH.write_text("{}\n", encoding="utf-8")
    up.run(dry_run=False, s3=SpyS3Upload(calls, etag=None), bucket="b")
    assert "upload_file" in calls


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
        self, calls: list[str], existing_kb: bool = False, existing_ds: bool = False
    ) -> None:
        self._calls = calls
        self._existing_kb = existing_kb
        self._existing_ds = existing_ds

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
