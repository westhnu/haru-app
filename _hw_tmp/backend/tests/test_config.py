import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.main import create_app

REQUIRED_IN_PROD = {
    "bedrock_kb_id": "KB0000TEST",
    "bedrock_guardrail_id": "gr0000test",
    "haru_kb_s3_bucket": "haru-kb-data-000000000000-ap-northeast-2",
    "haru_kb_vector_bucket_arn": "arn:aws:s3vectors:ap-northeast-2:0:bucket/vec",
    "dart_api_key": "dart-secret-value-do-not-log",
    "jutopia_data_dir": "/opt/jutopia_data",
}


def make_settings(**overrides: str) -> Settings:
    # 개발자 로컬 .env 영향을 받지 않도록 파일을 읽지 않고 모든 값을 명시한다.
    return Settings(_env_file=None, **{**REQUIRED_IN_PROD, **overrides})  # type: ignore[arg-type]


def test_local_env_allows_empty_keys() -> None:
    empty = {name: "" for name in REQUIRED_IN_PROD}

    settings = make_settings(app_env="local", **empty)

    assert settings.app_env == "local"


@pytest.mark.parametrize("missing", list(REQUIRED_IN_PROD))
def test_config_prod_fails_without_required_keys(missing: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_settings(app_env="prod", **{missing: ""})

    assert missing.upper() in str(exc_info.value)


def test_prod_passes_with_all_required_keys() -> None:
    assert make_settings(app_env="prod").app_env == "prod"


def test_prod_failure_message_hides_secret_values() -> None:
    with pytest.raises(ValidationError) as exc_info:
        make_settings(app_env="prod", bedrock_kb_id="")

    assert REQUIRED_IN_PROD["dart_api_key"] not in str(exc_info.value)


def test_unknown_app_env_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(app_env="production")


def test_create_app_fails_fast_in_prod_without_required_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    for name in REQUIRED_IN_PROD:
        monkeypatch.setenv(name.upper(), "")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValidationError):
            create_app()
    finally:
        get_settings.cache_clear()
