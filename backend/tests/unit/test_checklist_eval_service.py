"""Phase B ChecklistEvalService — Fake DART + Fake Converse (외부 호출 없음)."""

import json
from typing import Any

import pytest
from botocore.exceptions import ClientError

from app.config import Settings
from app.models.stock import DartResult, StockFinancials, StockSource
from app.services.checklist_eval_service import (
    FALLBACK_PREFIX,
    ChecklistEvalService,
    UnsupportedMarketError,
    build_eval_prompt,
    principle_percentages,
)

DART_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260814000001"
PRINCIPLE = "부채비율이 200% 미만인가?"


def make_dart(is_mock: bool = False, **fin: Any) -> DartResult:
    base: dict[str, Any] = {
        "report_year": 2026,
        "report_code": "11012",
        "report_label": "2026년 반기보고서",
        "report_type": "half_cumulative",
        "period_covered": "2026-01-01 ~ 2026-06-30",
        "statement_type": "CFS",
        "debt_ratio": 40.0,
        "operating_margin": 10.0,
        "revenue_growth": -12.3,
    }
    base.update(fin)
    return DartResult(
        code="005930",
        name="삼성전자",
        corp_code="00126380",
        rcept_no="20260814000001",
        financials=StockFinancials(**base),
        source=StockSource(name="DART 2026년 반기보고서", url=DART_URL),
        is_mock=is_mock,
    )


class FakeDartTool:
    def __init__(self, result: DartResult) -> None:
        self.result = result
        self.calls: list[str] = []

    def fetch_dart_financial(self, stock_code: str) -> DartResult:
        self.calls.append(stock_code)
        return self.result


class FakeRuntime:
    def __init__(self, payload: dict[str, Any] | str, stop_reason: str = "end_turn") -> None:
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        self.requests: list[dict[str, Any]] = []
        self._response = {
            "output": {"message": {"role": "assistant", "content": [{"text": text}]}},
            "stopReason": stop_reason,
            "usage": {"inputTokens": 900, "outputTokens": 120},
        }

    def converse(self, **request: Any) -> dict[str, Any]:
        self.requests.append(request)
        return self._response


class ExplodingRuntime:
    def converse(self, **request: Any) -> dict[str, Any]:
        raise AssertionError("mock DART에서는 모델을 호출하면 안 된다")


class FailingRuntime:
    def converse(self, **request: Any) -> dict[str, Any]:
        raise ClientError({"Error": {"Code": "ThrottlingException", "Message": "x"}}, "Converse")


def service(
    runtime: Any, dart: DartResult | None = None, guardrail: str = "gr-1"
) -> ChecklistEvalService:
    settings = Settings(_env_file=None, bedrock_guardrail_id=guardrail)
    return ChecklistEvalService(settings, FakeDartTool(dart or make_dart()), runtime_client=runtime)


def test_evaluate_satisfied() -> None:
    rt = FakeRuntime(
        {
            "suggested_status": "satisfied",
            "reasoning": "DART 2026년 반기보고서 기준 부채비율 40.0%로 기준 200%보다 낮습니다.",
            "used_facts": ["부채비율(%)"],
        }
    )
    ev = service(rt).evaluate_item("005930", PRINCIPLE)
    assert ev.suggested_status == "satisfied"
    assert ev.evaluation_source == "bedrock"
    assert ev.used_facts == ["부채비율(%)"]
    assert [s.url for s in ev.sources] == [DART_URL]
    assert ev.disclaimer and ev.report_label.startswith("DART 2026년 반기보고서")
    req = rt.requests[0]
    assert req["guardrailConfig"] == {"guardrailIdentifier": "gr-1", "guardrailVersion": "DRAFT"}
    prompt = req["messages"][0]["content"][0]["text"]
    assert "부채비율(%)" in prompt and PRINCIPLE in prompt


def test_evaluate_uncertain_due_to_missing_data() -> None:
    rt = FakeRuntime(
        {
            "suggested_status": "uncertain",
            "reasoning": "최근 3년치 ROE를 계산할 다년 데이터가 제공되지 않아 판단할 수 없습니다.",
            "used_facts": [],
        }
    )
    ev = service(rt).evaluate_item("005930", "최근 3년 ROE 추이가 10% 이상 유지되는가?")
    assert ev.suggested_status == "uncertain"
    assert ev.evaluation_source == "bedrock"  # 모델 스스로의 refuse는 검증 통과


@pytest.mark.parametrize(
    "payload",
    [
        # 업종 평균은 제공되지 않은 수치 → 환각
        {
            "suggested_status": "satisfied",
            "reasoning": "업종 평균 70.0%보다 낮은 40.0%입니다.",
            "used_facts": ["부채비율(%)"],
        },
        # 금액 생성
        {
            "suggested_status": "satisfied",
            "reasoning": "부채총계 4,000억원으로 낮습니다.",
            "used_facts": ["부채비율(%)"],
        },
        # 제공되지 않은 항목 이름
        {
            "suggested_status": "satisfied",
            "reasoning": "부채비율 40.0%입니다.",
            "used_facts": ["업종 평균 부채비율"],
        },
        # 근거 지표 없는 판정
        {"suggested_status": "unsatisfied", "reasoning": "기준에 미달합니다.", "used_facts": []},
        # 잘못된 status / 빈 reasoning / 너무 긴 reasoning
        {"suggested_status": "maybe", "reasoning": "x", "used_facts": []},
        {"suggested_status": "uncertain", "reasoning": "  ", "used_facts": []},
        {"suggested_status": "uncertain", "reasoning": "가" * 1001, "used_facts": []},
        # 매수 권유 (코드 금지 표현)
        {
            "suggested_status": "satisfied",
            "reasoning": "부채비율 40.0%로 지금 사세요.",
            "used_facts": ["부채비율(%)"],
        },
        # JSON 아님
        "부채비율이 낮아 충족합니다.",
    ],
)
def test_fallback_on_invalid_or_ungrounded_response(payload: Any) -> None:
    ev = service(FakeRuntime(payload)).evaluate_item("005930", PRINCIPLE)
    assert ev.evaluation_source == "template"
    assert ev.suggested_status == "uncertain"
    assert ev.reasoning.startswith(FALLBACK_PREFIX)
    assert ev.used_facts == [] and ev.sources[0].url == DART_URL


def test_principle_threshold_is_not_flagged_as_ungrounded() -> None:
    assert principle_percentages(PRINCIPLE) == {200.0}
    rt = FakeRuntime(
        {
            "suggested_status": "satisfied",
            "reasoning": "부채비율 40.0%로 200%보다 낮습니다.",
            "used_facts": ["부채비율(%)"],
        }
    )
    assert service(rt).evaluate_item("005930", PRINCIPLE).evaluation_source == "bedrock"


def test_json_in_code_fence_is_parsed() -> None:
    body = json.dumps(
        {"suggested_status": "uncertain", "reasoning": "판단 보류", "used_facts": []},
        ensure_ascii=False,
    )
    ev = service(FakeRuntime(f"```json\n{body}\n```")).evaluate_item("005930", PRINCIPLE)
    assert ev.evaluation_source == "bedrock"


@pytest.mark.parametrize("stop_reason", ["guardrail_intervened", "max_tokens"])
def test_fallback_on_guardrail_intervened(stop_reason: str) -> None:
    rt = FakeRuntime(
        {"suggested_status": "satisfied", "reasoning": "x", "used_facts": []}, stop_reason
    )
    ev = service(rt).evaluate_item("005930", PRINCIPLE)
    assert ev.evaluation_source == "template" and ev.suggested_status == "uncertain"
    assert "Guardrail" in ev.reasoning


def test_fallback_on_bedrock_error() -> None:
    ev = service(FailingRuntime()).evaluate_item("005930", PRINCIPLE)
    assert ev.evaluation_source == "template" and ev.suggested_status == "uncertain"


def test_fallback_on_mock_dart() -> None:
    ev = service(ExplodingRuntime(), make_dart(is_mock=True)).evaluate_item("005930", PRINCIPLE)
    assert ev.evaluation_source == "mock" and ev.suggested_status == "uncertain"


def test_fallback_when_no_ratio_facts_without_model_call() -> None:
    dart = make_dart(debt_ratio=None, operating_margin=None, revenue_growth=None)
    ev = service(ExplodingRuntime(), dart).evaluate_item("005930", PRINCIPLE)
    assert ev.evaluation_source == "template"


@pytest.mark.parametrize("code", ["NVDA", "AAPL", "12345", "0059300", ""])
def test_rejects_unsupported_market(code: str) -> None:
    dart_tool = FakeDartTool(make_dart())
    svc = ChecklistEvalService(
        Settings(_env_file=None), dart_tool, runtime_client=ExplodingRuntime()
    )
    with pytest.raises(UnsupportedMarketError):
        svc.evaluate_item(code, PRINCIPLE)
    assert dart_tool.calls == []  # DART도 호출하지 않는다


def test_no_guardrail_config_when_unset() -> None:
    rt = FakeRuntime({"suggested_status": "uncertain", "reasoning": "보류", "used_facts": []})
    service(rt, guardrail="").evaluate_item("005930", PRINCIPLE)
    assert "guardrailConfig" not in rt.requests[0]


def test_prompt_contains_only_code_computed_ratios() -> None:
    dart = make_dart(revenue=1_000_000_000_000.0)
    prompt = build_eval_prompt(PRINCIPLE, dart, {"부채비율(%)": 40.0})
    assert "1000000000000" not in prompt and "부채비율(%)" in prompt
