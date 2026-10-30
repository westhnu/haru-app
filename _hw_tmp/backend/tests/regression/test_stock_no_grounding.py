"""stock 컨텍스트 근거 부재 회귀 방지 (T-104 뼈대, REQ-RAG-04).

Phase 3/5에서 rag_service가 context_type="stock"이고 유사도 임계 미달일 때
대체 문구를 반환하도록 구현한 뒤 Green으로 전환한다.
"""

import pytest


@pytest.mark.skip(reason="Phase 3/5에서 구현")
def test_stock_context_no_grounding_returns_alt_message() -> None:
    """stock 질의에 KB 근거가 없으면 LLM 일반지식 대신 대체 문구를 반환한다. (REQ-RAG-04)"""
