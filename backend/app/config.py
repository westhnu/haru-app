from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
AppEnv = Literal["local", "dev", "staging", "prod"]

BACKEND_DIR = Path(__file__).resolve().parent.parent

# prod에서 비어 있으면 mock 응답·Guardrail 미적용 상태로
# "조용히" 떠 버리는 설정들. 기동 자체를 막는다 (결정 2).
PROD_REQUIRED_SETTINGS: tuple[str, ...] = (
    "bedrock_kb_id",
    "bedrock_guardrail_id",
    "haru_kb_s3_bucket",
    "haru_kb_vector_bucket_arn",
    "dart_api_key",
    "jutopia_data_dir",
)


class Settings(BaseSettings):
    """환경변수 단일 진입점. 코드 어디에서도 os.getenv를 직접 부르지 않는다."""

    model_config = SettingsConfigDict(
        # CWD와 무관하게 backend/.env 를 읽는다.
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # 검증 실패 메시지에 입력값(API 키 등)이 찍혀 기동 로그로 새지 않게 한다.
        hide_input_in_errors=True,
    )

    app_env: AppEnv = "local"
    app_name: str = "Haru API"
    log_level: LogLevel = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    aws_region: str = "ap-northeast-2"
    # 서울 리전의 Claude 4.5+ 는 추론 프로파일 ID가 필요하다 (sprint-0-log).
    bedrock_model_id: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    # 비어 있으면 RAG 서비스가 mock 응답으로 동작한다.
    bedrock_kb_id: str = ""
    bedrock_guardrail_id: str = ""
    bedrock_guardrail_version: str = "DRAFT"
    # KB 벡터스토어 백킹. prod 필수(PROD_REQUIRED_SETTINGS). 인덱스 ARN은 KB 생성 스크립트가 채운다.
    # haru_kb_s3_bucket: 데이터소스용 일반 S3 버킷.
    # haru_kb_vector_bucket_arn: 임베딩용 S3 vector bucket — 일반 버킷과 별개 리소스.
    haru_kb_s3_bucket: str = ""
    haru_kb_vector_bucket_arn: str = ""
    haru_kb_s3_vector_index_arn: str = ""
    # KB가 임베딩·S3 접근에 사용하는 IAM Role. Phase 4에서 수동 생성 후 설정(스펙 범위 밖).
    bedrock_kb_role_arn: str = ""

    # 비어 있으면 DART 도구가 개발용 mock 데이터로 동작한다.
    dart_api_key: str = ""
    dart_cache_ttl_seconds: int = 1800
    dart_cache_dir: Path = BACKEND_DIR / ".cache" / "dart"
    # jutopia_data 저장소 경로. dart_client.py를 파일 단위로 읽는다.
    jutopia_data_dir: str = ""

    @model_validator(mode="after")
    def require_prod_settings(self) -> Self:
        if self.app_env != "prod":
            return self
        missing = [name.upper() for name in PROD_REQUIRED_SETTINGS if not getattr(self, name)]
        if missing:
            # 이름만 알린다. 값은 절대 메시지에 넣지 않는다.
            raise ValueError(f"APP_ENV=prod 필수 설정 누락: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
