"""원칙 4 + KI-002 + KI-004 회귀 방지.

Fake 원본 클라이언트를 주입하므로 KIS 키·네트워크·pandas 없이 항상 실행된다.
"""

import os
from pathlib import Path
from typing import Any

import pytest

from app.services.hantu_readonly import _READONLY_METHODS, HantuReadOnly
from app.services.jutopia_loader import load_hantu_stock_class

WRAPPER_SRC = Path(__file__).resolve().parents[2] / "app" / "services" / "hantu_readonly.py"
CANARY = "HARU_TEST_HANTU_DOTENV_CANARY"


class _FakeRaw:
    """원본 HantuStock 흉내. 주문 메서드도 갖고 있어 래퍼가 막는지 확인한다."""

    def get_holding_stock(self) -> list[Any]:
        return []

    def get_holding_stock_detail(self) -> dict[str, Any]:
        return {}

    def get_holding_cash(self) -> float:
        return 0.0

    def get_transaction_history(self) -> list[Any]:
        return []

    def get_transaction_summary(self) -> dict[str, Any]:
        return {}

    def get_minute_chart(self, ticker: str) -> dict[str, Any]:
        return {}

    # 테스트 로컬 전용. 서비스 코드에는 이 이름을 쓰지 않는다 (KI-002).
    def bid(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("래퍼가 차단해야 하므로 호출되면 안 된다")


def test_whitelist_methods_delegate() -> None:
    client = HantuReadOnly(raw_client=_FakeRaw())
    for method in _READONLY_METHODS:
        assert callable(getattr(client, method))


def test_non_whitelist_blocked() -> None:
    client = HantuReadOnly(raw_client=_FakeRaw())
    for name in ["bid", "ask", "send_order", "cancel_order", "arbitrary_xyz"]:
        with pytest.raises(AttributeError, match="화이트리스트"):
            getattr(client, name)
    assert hasattr(client, "bid") is False  # 원칙 4 필수 검증


def test_wrapper_source_has_no_order_method_names() -> None:
    src = WRAPPER_SRC.read_text(encoding="utf-8")
    for lit in ['"bid"', '"ask"', '"send_order"', '"cancel_order"']:
        assert lit not in src and lit.replace('"', "'") not in src, f"KI-002 위반: {lit}"


def test_no_sys_path_hack_in_wrapper() -> None:
    src = WRAPPER_SRC.read_text(encoding="utf-8")
    assert "sys.path" not in src, "KI-004 위반: sys.path 조작 금지"
    assert "from jutopia_data" not in src, "KI-004 위반: 직접 import 금지"


def test_hantu_loader_blocks_dotenv_leak(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """KI-004: 래퍼 전용 로더도 import 시점 load_dotenv를 막는다 (행동 검증)."""
    monkeypatch.setenv(CANARY, "placeholder")
    monkeypatch.delenv(CANARY)
    (tmp_path / ".env").write_text(f"{CANARY}=leaked\n", encoding="utf-8")
    (tmp_path / "HantuStock.py").write_text(
        "from dotenv import load_dotenv\n\nload_dotenv()\n\nclass HantuStock:\n    pass\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    cls = load_hantu_stock_class(tmp_path)

    assert cls.__name__ == "HantuStock"
    assert CANARY not in os.environ
