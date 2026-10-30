"""GET /api/v1/stock/{code}/summary 통합 테스트 — DART·Bedrock 모두 Fake, 실제 호출 없음."""

from collections.abc import Iterator
from typing import Any

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.guardrail import DISCLAIMER, SAFE_REPLACEMENT
from app.main import app
from app.models.stock import DartResult, StockFinancials, StockSource
from app.services.dart_tool import (
    DartError,
    DartNoFinancialsError,
    DartRateLimitError,
    DartStockNotFoundError,
    DartUnavailableError,
    MockDartTool,
)
from app.services.stock_summary_service import StockSummaryService, get_stock_summary_service

SUMMARY_URL = "/api/v1/stock/005930/summary"
RCEPT_NO = "20260814000123"
DART_URL = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={RCEPT_NO}"
SOURCE_NAME = "DART 2026년 반기보고서 (연결재무제표)"

LIVE_RESULT = DartResult(
    code="005930",
    name="삼성전자",
    corp_code="00126380",
    rcept_no=RCEPT_NO,
    financials=StockFinancials(
        report_year=2026,
        report_code="11012",
        report_label="2026년 반기보고서",
        report_type="half_cumulative",
        period_covered="2026-01-01 ~ 2026-06-30",
        statement_type="CFS",
        revenue=877.0,
        debt_ratio=40.0,
        operating_margin=10.0,
        revenue_growth=-12.3,
    ),
    source=StockSource(name=SOURCE_NAME, url=DART_URL),
)
GROUNDED_SUMMARY = (
    "DART 2026년 반기보고서 기준 부채비율은 40.0%, 영업이익률은 10.0%입니다. "
    "매출액은 전년 동기 대비 12.3% 감소했습니다."
)


class FakeDartTool:
    def __init__(self, result: DartResult | None = None, error: DartError | None = None) -> None:
        self._result = result
        self._error = error

    def fetch_dart_financial(self, stock_code: str) -> DartResult:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeRuntimeClient:
    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.requests: list[dict[str, Any]] = []
        message = {"role": "assistant", "content": [{"text": text}]}
        self._response = {"output": {"message": message}, "stopReason": stop_reason}

    def converse(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return self._response


class ExplodingRuntimeClient:
    def converse(self, **request: Any) -> dict[str, Any]:
        raise AssertionError("mock 데이터는 Bedrock으로 요약하면 안 된다")


class FailingRuntimeClient:
    def converse(self, **request: Any) -> dict[str, Any]:
        error = {"Error": {"Code": "ThrottlingException", "Message": "slow down"}}
        raise ClientError(error, "Converse")


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.clear()


def use_service(dart_tool: Any, runtime_client: Any) -> None:
    settings = Settings(_env_file=None, bedrock_guardrail_id="")
    service = StockSummaryService(settings, dart_tool, runtime_client=runtime_client)
    app.dependency_overrides[get_stock_summary_service] = lambda: service


def test_mock_mode_is_labeled_and_never_calls_bedrock(client: TestClient) -> None:
    use_service(MockDartTool(), ExplodingRuntimeClient())

    response = client.get(SUMMARY_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["is_mock"] is True
    assert body["summary_source"] == "mock"
    assert body["summary"].startswith("[MOCK]")
    assert body["summary"].endswith(DISCLAIMER)
    assert body["sources"][0]["name"].startswith("[MOCK]")
    assert body["disclaimer"] == DISCLAIMER


def test_grounded_ai_summary_is_returned_with_dart_source(client: TestClient) -> None:
    runtime = FakeRuntimeClient(GROUNDED_SUMMARY)
    use_service(FakeDartTool(LIVE_RESULT), runtime)

    body = client.get(SUMMARY_URL).json()

    assert body["summary_source"] == "bedrock"
    assert body["summary"] == f"{GROUNDED_SUMMARY}\n\n{DISCLAIMER}"
    assert body["sources"] == [{"name": SOURCE_NAME, "url": DART_URL}]
    assert (body["code"], body["name"], body["is_mock"]) == ("005930", "삼성전자", False)
    assert body["financials"]["report_type"] == "half_cumulative"
    assert body["financials"]["period_covered"] == "2026-01-01 ~ 2026-06-30"
    prompt = runtime.requests[0]["messages"][0]["content"][0]["text"]
    assert '"매출액 전년 대비 증감률(%)": -12.3' in prompt
    assert '"기간(누적)": "2026-01-01 ~ 2026-06-30"' in prompt


def test_ungrounded_ai_figures_fall_back_to_template(client: TestClient) -> None:
    runtime = FakeRuntimeClient("매출액은 302조원이고 부채비율은 40.0%입니다.")
    use_service(FakeDartTool(LIVE_RESULT), runtime)

    body = client.get(SUMMARY_URL).json()

    assert body["summary_source"] == "template"
    assert "302조" not in body["summary"]
    assert "부채비율 40.0%" in body["summary"]
    assert "2026-01-01 ~ 2026-06-30 누적" in body["summary"]


def test_forbidden_phrase_in_ai_summary_is_replaced(client: TestClient) -> None:
    runtime = FakeRuntimeClient("부채비율이 40.0%로 낮으니 이 종목을 매수하세요.")
    use_service(FakeDartTool(LIVE_RESULT), runtime)

    summary = client.get(SUMMARY_URL).json()["summary"]

    assert summary == f"{SAFE_REPLACEMENT}\n\n{DISCLAIMER}"


@pytest.mark.parametrize(
    "runtime",
    [FailingRuntimeClient(), FakeRuntimeClient("잘린 요약", stop_reason="max_tokens")],
    ids=["bedrock_error", "truncated"],
)
def test_unusable_bedrock_result_falls_back_to_template(client: TestClient, runtime: Any) -> None:
    use_service(FakeDartTool(LIVE_RESULT), runtime)

    response = client.get(SUMMARY_URL)

    assert response.status_code == 200
    assert response.json()["summary_source"] == "template"


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (DartStockNotFoundError("x"), 404),
        (DartNoFinancialsError("x"), 404),
        (DartRateLimitError("x"), 503),
        (DartUnavailableError("x"), 502),
    ],
)
def test_dart_errors_map_to_http_status(
    client: TestClient, error: DartError, status_code: int
) -> None:
    use_service(FakeDartTool(error=error), ExplodingRuntimeClient())

    assert client.get(SUMMARY_URL).status_code == status_code


@pytest.mark.parametrize("code", ["abc123", "12345", "1234567"])
def test_invalid_stock_code_is_rejected(client: TestClient, code: str) -> None:
    use_service(FakeDartTool(LIVE_RESULT), ExplodingRuntimeClient())

    assert client.get(f"/api/v1/stock/{code}/summary").status_code == 422
