"""Hantu(한국투자증권) 조회 전용 래퍼.

원칙 4: 매매·주문 코드 전면 금지.
KI-002: 주문 메서드 이름을 코드에 쓰지 않는다. 화이트리스트로만 노출한다.
KI-004: jutopia_loader 경유로 로드해 import 시점 load_dotenv 실행을 차단한다.
"""

from typing import Any

from app.services.jutopia_loader import load_hantu_stock_class

# KI-002에서 승인된 조회 메서드 6개. 이 목록 밖은 어떤 메서드도 노출하지 않는다.
_READONLY_METHODS = frozenset(
    {
        "get_holding_stock",
        "get_holding_stock_detail",
        "get_holding_cash",
        "get_transaction_history",
        "get_transaction_summary",
        "get_minute_chart",
    }
)


class HantuReadOnly:
    """조회 함수 6개만 명시적으로 위임한다.

    상속하지 않는 이유: 상속하면 부모의 주문 메서드까지 노출된다.
    """

    def __init__(self, raw_client: Any = None) -> None:
        # raw_client는 테스트 주입용. None이면 실제 클래스를 로드해 생성한다.
        if raw_client is None:
            raw_client = load_hantu_stock_class()()
        self._raw = raw_client

    def __getattr__(self, name: str) -> Any:
        if name not in _READONLY_METHODS:
            raise AttributeError(
                f"'{name}'는 화이트리스트에 없음. 허용: {sorted(_READONLY_METHODS)}"
            )
        return getattr(self._raw, name)


def is_available() -> bool:
    """실 Hantu 클래스 로드 가능 여부 (의존성·경로 누락이면 False)."""
    try:
        load_hantu_stock_class()
    except Exception:
        return False
    return True
