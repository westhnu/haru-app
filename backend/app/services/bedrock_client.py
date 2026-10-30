"""Bedrock boto3 클라이언트 팩토리.

boto3 클라이언트는 생성 비용(자격증명 해석·엔드포인트 모델 로딩)이 크고 스레드 간 공유가 가능하므로
프로세스당 한 번만 만들어 재사용한다.
"""

from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

from app.config import get_settings

# LLM 생성은 수십 초가 걸릴 수 있어 read_timeout을 넉넉히 두고,
# 스로틀링은 adaptive 재시도로 흡수한다.
BOTO_CONFIG = Config(
    connect_timeout=5,
    read_timeout=120,
    retries={"max_attempts": 3, "mode": "adaptive"},
)


@lru_cache
def get_runtime_client() -> Any:
    return _make_client("bedrock-runtime")


@lru_cache
def get_agent_runtime_client() -> Any:
    return _make_client("bedrock-agent-runtime")


@lru_cache
def get_bedrock_agent_client() -> Any:
    """KB 관리용(생성·sync·describe) bedrock-agent 제어 평면 클라이언트."""
    return _make_client("bedrock-agent")


def _make_client(service_name: str) -> Any:
    return boto3.client(service_name, region_name=get_settings().aws_region, config=BOTO_CONFIG)
