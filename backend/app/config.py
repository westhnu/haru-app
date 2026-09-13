from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """환경변수 단일 진입점. 코드 어디에서도 os.getenv를 직접 부르지 않는다."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Haru API"
    log_level: LogLevel = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    aws_region: str = "ap-northeast-2"
    # 서울 리전의 Claude 4.5+ 는 ON_DEMAND 호출이 불가해 추론 프로파일 ID가 필요하다 (sprint-0-log).
    bedrock_model_id: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    # 비어 있으면 Sprint 1 RAG 서비스가 mock 응답으로 동작한다.
    bedrock_kb_id: str = ""
    bedrock_guardrail_id: str = ""
    bedrock_guardrail_version: str = "DRAFT"


@lru_cache
def get_settings() -> Settings:
    return Settings()
