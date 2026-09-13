"""LiveDartTool 단위 테스트 — DART HTTP는 Fake로 대체하며 실제 호출은 하지 않는다."""

import io
import zipfile
from pathlib import Path
from typing import Any

import pytest
import requests

from app.core.cache import TTLCache
from app.services.dart_tool import (
    DartNoFinancialsError,
    DartRateLimitError,
    DartStockNotFoundError,
    DartUnavailableError,
    LiveDartTool,
    StatementLookup,
)

API_KEY = "test-dart-key-0123456789abcdef"
RCEPT_NO = "20260814000123"
STATEMENTS_ENDPOINT = "fnlttSinglAcntAll.json"
NO_DATA = {"status": "013", "message": "조회된 데이타가 없습니다."}


def corp_code_zip() -> bytes:
    xml = (
        "<result>"
        "<list><corp_code>00126380</corp_code><corp_name>삼성전자</corp_name>"
        "<stock_code>005930</stock_code></list>"
        "<list><corp_code>99999999</corp_code><corp_name>비상장회사</corp_name>"
        "<stock_code> </stock_code></list>"
        "</result>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CORPCODE.xml", xml)
    return buffer.getvalue()


def statements() -> dict[str, Any]:
    item = {
        "rcept_no": RCEPT_NO,
        "currency": "KRW",
        "account_nm": "매출액",
        "thstrm_amount": "1000",
    }
    return {"status": "000", "message": "정상", "list": [item]}


class FakeResponse:
    def __init__(self, payload: dict[str, Any] | None = None, content: bytes = b"") -> None:
        self._payload = payload
        self.content = content

    def json(self) -> dict[str, Any]:
        if self._payload is None:
            raise ValueError("not json")
        return self._payload

    def raise_for_status(self) -> None:
        return None


class FakeDartHttp:
    """DART 엔드포인트를 흉내 내고 호출을 기록한다. 등록하지 않은 보고서는 '데이터 없음(013)'."""

    def __init__(self, reports: dict[tuple[str, str, str], dict[str, Any]] | None = None) -> None:
        self.reports = reports or {}
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, params: dict[str, str], timeout: float) -> FakeResponse:
        endpoint = url.rsplit("/", 1)[-1]
        self.calls.append((endpoint, params))
        if endpoint == "corpCode.xml":
            return FakeResponse(content=corp_code_zip())
        key = (params["bsns_year"], params["reprt_code"], params["fs_div"])
        return FakeResponse(payload=self.reports.get(key, NO_DATA))

    def count(self, endpoint: str) -> int:
        return sum(1 for called, _ in self.calls if called == endpoint)


class FakeCalculator:
    """jutopia DartClient의 순수 계산 메서드 두 개만 흉내 낸다."""

    def _determine_report_attempts(self) -> list[tuple[int, str, str]]:
        return [(2026, "11012", "2026년 반기보고서"), (2025, "11011", "2025년 사업보고서")]

    def _compute_metrics(
        self, items: list[dict[str, Any]], year: int, reprt_code: str, label: str
    ) -> dict[str, Any]:
        return {
            "revenue": float(items[0]["thstrm_amount"]),
            "debt_ratio": 40.0,
            "revenue_series": [],
        }


def make_tool(tmp_path: Path, http: Any) -> LiveDartTool:
    cache: TTLCache[StatementLookup] = TTLCache("test_dart_statements", ttl_seconds=1800)
    return LiveDartTool(API_KEY, FakeCalculator(), cache, tmp_path, http_get=http)


def test_fetch_returns_dart_numbers_with_viewer_source(tmp_path: Path) -> None:
    http = FakeDartHttp({("2026", "11012", "CFS"): statements()})

    result = make_tool(tmp_path, http).fetch_dart_financial("005930")

    assert (result.name, result.corp_code, result.rcept_no) == ("삼성전자", "00126380", RCEPT_NO)
    assert result.financials.revenue == 1000.0
    assert result.financials.report_label == "2026년 반기보고서"
    assert result.source.url == f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={RCEPT_NO}"
    assert result.source.name == "DART 2026년 반기보고서 (연결재무제표)"
    assert all(params["crtfc_key"] == API_KEY for _, params in http.calls)


def test_falls_back_to_separate_statements(tmp_path: Path) -> None:
    http = FakeDartHttp({("2026", "11012", "OFS"): statements()})

    result = make_tool(tmp_path, http).fetch_dart_financial("005930")

    assert result.financials.statement_type == "OFS"
    assert "개별재무제표" in result.source.name


def test_uses_older_report_when_latest_is_not_filed(tmp_path: Path) -> None:
    http = FakeDartHttp({("2025", "11011", "CFS"): statements()})

    result = make_tool(tmp_path, http).fetch_dart_financial("005930")

    assert result.financials.report_year == 2025


def test_repeated_fetch_hits_statement_cache(tmp_path: Path) -> None:
    http = FakeDartHttp({("2025", "11011", "CFS"): statements()})
    tool = make_tool(tmp_path, http)

    tool.fetch_dart_financial("005930")
    calls_after_first = http.count(STATEMENTS_ENDPOINT)
    tool.fetch_dart_financial("005930")

    # 2026 반기 CFS·OFS(데이터 없음) + 2025 사업 CFS. 빈 결과까지 캐시되어 두 번째는 0회.
    assert calls_after_first == 3
    assert http.count(STATEMENTS_ENDPOINT) == calls_after_first


def test_corp_index_is_reused_from_disk_after_restart(tmp_path: Path) -> None:
    first_http = FakeDartHttp({("2026", "11012", "CFS"): statements()})
    second_http = FakeDartHttp({("2026", "11012", "CFS"): statements()})

    make_tool(tmp_path, first_http).fetch_dart_financial("005930")
    make_tool(tmp_path, second_http).fetch_dart_financial("005930")

    assert first_http.count("corpCode.xml") == 1
    assert second_http.count("corpCode.xml") == 0


def test_unknown_stock_code_raises_not_found(tmp_path: Path) -> None:
    with pytest.raises(DartStockNotFoundError):
        make_tool(tmp_path, FakeDartHttp()).fetch_dart_financial("123456")


def test_no_filed_reports_raises_no_financials(tmp_path: Path) -> None:
    with pytest.raises(DartNoFinancialsError):
        make_tool(tmp_path, FakeDartHttp()).fetch_dart_financial("005930")


def test_rate_limit_status_is_not_treated_as_missing_data(tmp_path: Path) -> None:
    rate_limited = {"status": "020", "message": "요청 제한을 초과하였습니다."}
    http = FakeDartHttp({("2026", "11012", "CFS"): rate_limited})

    with pytest.raises(DartRateLimitError):
        make_tool(tmp_path, http).fetch_dart_financial("005930")

    # jutopia 구현과 달리 개별재무제표로 재요청해 한도를 더 쓰지 않는다.
    assert http.count(STATEMENTS_ENDPOINT) == 1


def test_network_error_does_not_leak_api_key(tmp_path: Path) -> None:
    def broken_http(url: str, params: dict[str, str], timeout: float) -> FakeResponse:
        raise requests.ConnectionError(f"Max retries exceeded with url: {url}?crtfc_key={API_KEY}")

    with pytest.raises(DartUnavailableError) as exc_info:
        make_tool(tmp_path, broken_http).fetch_dart_financial("005930")

    assert API_KEY not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__ is True
