"""teardown 스크립트 dry-run/confirm 동작 검증 (T-453).

실제 boto3 호출 없이 Spy 클라이언트로 호출 여부·순서를 검증한다.
"""

from typing import Any

from botocore.exceptions import ClientError

from app.config import Settings
from scripts.guardrail import teardown as gt
from scripts.kb import teardown as kt

KB_ID = "KB0001"
VECTOR_BUCKET_ARN = "arn:aws:s3vectors:ap-northeast-2:0:bucket/vec"
INDEX_ARN = "arn:aws:s3vectors:ap-northeast-2:0:bucket/vec/index/haru-glossary"
DATA_BUCKET = "haru-kb-data-0-ap-northeast-2"
GUARDRAIL_ID = "gr0001"


def _not_found(op: str) -> ClientError:
    return ClientError({"Error": {"Code": "ResourceNotFoundException", "Message": "x"}}, op)


def _full_settings() -> Settings:
    return Settings(
        _env_file=None,
        bedrock_kb_id=KB_ID,
        bedrock_guardrail_id=GUARDRAIL_ID,
        haru_kb_s3_bucket=DATA_BUCKET,
        haru_kb_vector_bucket_arn=VECTOR_BUCKET_ARN,
        haru_kb_s3_vector_index_arn=INDEX_ARN,
    )


def _empty_settings() -> Settings:
    return Settings(_env_file=None)


class SpyAgent:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def delete_knowledge_base(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("delete_knowledge_base")
        return {}


class SpyS3Vectors:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def delete_index(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("delete_index")
        return {}

    def delete_vector_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("delete_vector_bucket")
        return {}


class SpyS3:
    def __init__(self, calls: list[str], keys: list[str] | None = None) -> None:
        self._calls = calls
        self._keys = keys or ["glossary/glossary.jsonl"]

    def get_paginator(self, op: str) -> Any:
        keys = self._keys
        calls = self._calls

        class _Paginator:
            def paginate(self, **kwargs: Any) -> Any:
                calls.append("list_objects_v2")
                yield {"Contents": [{"Key": k} for k in keys]}

        return _Paginator()

    def delete_objects(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("delete_objects")
        return {}

    def delete_bucket(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("delete_bucket")
        return {}


class SpyBedrock:
    def __init__(self, calls: list[str], exists: bool = True) -> None:
        self._calls = calls
        self._exists = exists

    def get_guardrail(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("get_guardrail")
        if not self._exists:
            raise _not_found("GetGuardrail")
        return {"name": "haru"}

    def delete_guardrail(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append("delete_guardrail")
        return {}


# --- KB teardown ---------------------------------------------------------------


def test_kb_teardown_dry_run_calls_no_delete_apis() -> None:
    calls: list[str] = []
    ok = kt.run_teardown(
        _full_settings(),
        dry_run=True,
        agent=SpyAgent(calls),
        s3v=SpyS3Vectors(calls),
        s3=SpyS3(calls),
    )

    assert ok is True
    assert calls == []  # dry-run은 어떤 AWS API도 호출하지 않는다


def test_kb_teardown_without_flag_defaults_to_dry_run() -> None:
    # 플래그 생략 → dry_run True
    assert kt._parse_args([]) is True
    assert kt._parse_args(["--dry-run"]) is True
    assert kt._parse_args(["--confirm"]) is False


def test_kb_teardown_confirm_calls_delete_apis_in_reverse_order() -> None:
    calls: list[str] = []
    ok = kt.run_teardown(
        _full_settings(),
        dry_run=False,
        agent=SpyAgent(calls),
        s3v=SpyS3Vectors(calls),
        s3=SpyS3(calls),
    )

    assert ok is True
    # KB → index → vector bucket → S3 객체(list+delete) → bucket 역순
    assert calls == [
        "delete_knowledge_base",
        "delete_index",
        "delete_vector_bucket",
        "list_objects_v2",
        "delete_objects",
        "delete_bucket",
    ]


def test_kb_teardown_skips_empty_settings() -> None:
    calls: list[str] = []
    ok = kt.run_teardown(
        _empty_settings(),
        dry_run=False,
        agent=SpyAgent(calls),
        s3v=SpyS3Vectors(calls),
        s3=SpyS3(calls),
    )

    assert ok is True
    assert calls == []  # 설정이 비면 지울 것이 없어 성공 종료


# --- Guardrail teardown --------------------------------------------------------


def test_guardrail_teardown_dry_run_no_delete() -> None:
    calls: list[str] = []
    ok = gt.run_teardown(_full_settings(), dry_run=True, bedrock=SpyBedrock(calls))

    assert ok is True
    assert "delete_guardrail" not in calls  # dry-run은 삭제 안 함


def test_guardrail_teardown_confirm_deletes() -> None:
    calls: list[str] = []
    ok = gt.run_teardown(_full_settings(), dry_run=False, bedrock=SpyBedrock(calls))

    assert ok is True
    assert calls == ["get_guardrail", "delete_guardrail"]


def test_guardrail_teardown_skips_missing_resource() -> None:
    calls: list[str] = []
    ok = gt.run_teardown(_full_settings(), dry_run=False, bedrock=SpyBedrock(calls, exists=False))

    assert ok is True
    assert "delete_guardrail" not in calls  # 없으면 skip + 성공


def test_guardrail_teardown_skips_empty_settings() -> None:
    calls: list[str] = []
    ok = gt.run_teardown(_empty_settings(), dry_run=False, bedrock=SpyBedrock(calls))

    assert ok is True
    assert calls == []
