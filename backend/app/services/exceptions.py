"""Bedrock 연동 예외.

Phase 2에서는 정의만 한다 — KB_ID가 비어 Fake 모드로 동작하므로 실제 raise는 없다.
Phase 5에서 rag_service가 실호출을 붙일 때 boto3 예외(ClientError 등)를 아래 3종으로
변환해 올린다. 호출처는 서비스 계층 예외만 알면 되고 botocore 세부는 캡슐화된다.
"""


class BedrockError(Exception):
    """Bedrock 연동 공통 베이스. 원인 예외는 __cause__로 보존한다."""


class BedrockRetrievalError(BedrockError):
    """RetrieveAndGenerate 일반 호출 실패 (스로틀링·검증 오류 등)."""


class BedrockGuardrailBlockedError(BedrockError):
    """Guardrail이 응답에 개입(intervened)해 차단한 경우. Phase 5에서 활용."""


class BedrockNotAvailableError(BedrockError):
    """KB·Guardrail 리소스가 없거나(ResourceNotFoundException) 접근 불가한 경우."""
