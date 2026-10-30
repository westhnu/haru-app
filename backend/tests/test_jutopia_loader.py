"""jutopia_data 파일 단위 로더 — allowlist, .env 유출 차단, jutopia 계약 테스트."""

import importlib.util
import os
from pathlib import Path

import pytest

from app.services.jutopia_loader import JutopiaModuleError, load_jutopia_module

CANARY = "HARU_TEST_DOTENV_CANARY"
JUTOPIA_DIR = Path("/Users/westhnu/Agent/Claude/jutopia_data")

requires_jutopia = pytest.mark.skipif(
    not (JUTOPIA_DIR / "dart_client.py").is_file(), reason="로컬 jutopia_data 저장소 없음"
)


def write_fake_dart_client(directory: Path) -> None:
    (directory / ".env").write_text(f"{CANARY}=leaked\n", encoding="utf-8")
    source = "from dotenv import load_dotenv\n\nload_dotenv()\nLOADED = True\n"
    (directory / "dart_client.py").write_text(source, encoding="utf-8")


def isolate_canary(monkeypatch: pytest.MonkeyPatch) -> None:
    # setenv → delenv 순서로 등록해 두면, 테스트 중 무엇이 설정되든 종료 시 원래(없음)로 복구된다.
    monkeypatch.setenv(CANARY, "placeholder")
    monkeypatch.delenv(CANARY)


@pytest.mark.parametrize("name", ["web_order", "HantuStock", "app", "run_mock_trades"])
def test_rejects_modules_outside_allowlist(tmp_path: Path, name: str) -> None:
    with pytest.raises(JutopiaModuleError):
        load_jutopia_module(name, tmp_path)


def test_rejects_empty_directory_setting() -> None:
    with pytest.raises(JutopiaModuleError):
        load_jutopia_module("dart_client", "")


def test_control_plain_import_leaks_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """대조군: 차단 없이 import하면 .env가 실제로 올라온다 → 아래 차단 테스트가 의미 있음을 보장."""
    write_fake_dart_client(tmp_path)
    monkeypatch.chdir(tmp_path)
    isolate_canary(monkeypatch)

    spec = importlib.util.spec_from_file_location("plain_dart_client", tmp_path / "dart_client.py")
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(importlib.util.module_from_spec(spec))

    assert os.environ.get(CANARY) == "leaked"


def test_loader_blocks_import_time_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_fake_dart_client(tmp_path)
    monkeypatch.chdir(tmp_path)
    isolate_canary(monkeypatch)

    module = load_jutopia_module("dart_client", tmp_path)

    assert module.LOADED is True
    assert CANARY not in os.environ


@requires_jutopia
def test_real_jutopia_import_adds_no_env_vars() -> None:
    before = set(os.environ)

    load_jutopia_module("dart_client", JUTOPIA_DIR)

    assert set(os.environ) == before


@requires_jutopia
def test_jutopia_dart_client_contract() -> None:
    """Haru가 기대는 jutopia 비공개 메서드가 그대로 있는지 (KI-006).

    재무 매핑은 KI-008 이후 Haru(dart_financials)로 옮겼고, 보고서 시도 순서만 빌려 쓴다.
    """
    dart_client = load_jutopia_module("dart_client", JUTOPIA_DIR)
    calculator = object.__new__(dart_client.DartClient)

    attempts = calculator._determine_report_attempts()

    assert attempts and all(len(attempt) == 3 for attempt in attempts)
    assert all(reprt_code in {"11011", "11012", "11013", "11014"} for _, reprt_code, _ in attempts)
