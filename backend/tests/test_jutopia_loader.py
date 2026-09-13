"""jutopia_data 파일 단위 로더 — allowlist, .env 유출 차단, jutopia 계약 테스트."""

import importlib.util
import json
import os
from pathlib import Path

import pytest

from app.models.stock import StockFinancials
from app.services.dart_tool import METRIC_FIELDS
from app.services.jutopia_loader import JutopiaModuleError, load_jutopia_module

CANARY = "HARU_TEST_DOTENV_CANARY"
JUTOPIA_DIR = Path("/Users/westhnu/Agent/Claude/jutopia_data")
SAMSUNG_2024_ANNUAL = JUTOPIA_DIR / "data" / "dart_cache" / "fin_00126380_2024_11011_CFS.json"

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
    """Haru가 기대는 jutopia 비공개 메서드가 그대로 있는지 (KI-006)."""
    dart_client = load_jutopia_module("dart_client", JUTOPIA_DIR)
    calculator = object.__new__(dart_client.DartClient)

    attempts = calculator._determine_report_attempts()

    assert attempts and all(len(attempt) == 3 for attempt in attempts)
    assert callable(calculator._compute_metrics)


@pytest.mark.skipif(not SAMSUNG_2024_ANNUAL.is_file(), reason="jutopia DART 캐시 파일 없음")
def test_jutopia_metrics_on_real_dart_response_fit_haru_schema() -> None:
    """실제 DART 응답(삼성전자 2024 사업보고서)으로 계산·스키마 호환을 확인한다."""
    items = json.loads(SAMSUNG_2024_ANNUAL.read_text(encoding="utf-8"))
    dart_client = load_jutopia_module("dart_client", JUTOPIA_DIR)
    calculator = object.__new__(dart_client.DartClient)

    metrics = calculator._compute_metrics(items, 2024, "11011", "2024년 사업보고서")
    financials = StockFinancials(
        report_year=2024,
        report_code="11011",
        report_label="2024년 사업보고서",
        statement_type="CFS",
        **{field: metrics[field] for field in METRIC_FIELDS if metrics.get(field) is not None},
    )

    assert items[0]["rcept_no"] == "20250311001085"
    assert financials.revenue == 300_870_903_000_000.0
    assert financials.debt_ratio is not None
    assert financials.operating_margin is not None
    assert len(financials.revenue_series) >= 2
