"""DART 재무 데이터 + Bedrock 요약 오케스트레이션.

금액·비율의 원천은 DART(→ `financials`)뿐이다. 모델에는 코드가 계산한 비율만 넘기고,
요약에 근거 없는 수치가 섞이면 AI 요약을 버리고 코드가 만든 템플릿 요약으로 바꾼다 (원칙 2).
Bedrock이 실패해도 DART 수치는 템플릿 요약과 함께 돌려준다.
"""

import json
from typing import Any

import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings
from app.core.grounding import find_ungrounded_figures
from app.core.guardrail import apply_output_guard
from app.core.prompts import SYSTEM_PROMPT_STOCK_SUMMARY
from app.models.stock import (
    STATEMENT_LABELS,
    DartResult,
    SeriesPoint,
    StockFinancials,
    StockSummaryResponse,
    SummarySource,
)
from app.services.bedrock_client import get_runtime_client
from app.services.dart_tool import DartTool, get_dart_tool

SUMMARY_MAX_TOKENS = 1024

logger = structlog.get_logger(__name__)


class StockSummaryService:
    def __init__(
        self, settings: Settings, dart_tool: DartTool, runtime_client: Any | None = None
    ) -> None:
        self._settings = settings
        self._dart_tool = dart_tool
        self._client = runtime_client

    def summarize(self, stock_code: str) -> StockSummaryResponse:
        dart = self._dart_tool.fetch_dart_financial(stock_code)
        summary, summary_source = self._summarize(dart)
        return StockSummaryResponse(
            code=dart.code,
            name=dart.name,
            financials=dart.financials,
            summary=apply_output_guard(summary),
            summary_source=summary_source,
            sources=[dart.source],
            is_mock=dart.is_mock,
        )

    def _summarize(self, dart: DartResult) -> tuple[str, SummarySource]:
        if dart.is_mock:
            # 가짜 수치를 모델이 요약하면 그럴듯한 문장이 나와 오해 소지가 크다 → 호출하지 않는다.
            return f"[MOCK] {template_summary(dart)}", "mock"
        text = self._converse(build_stock_prompt(dart))
        if text is None:
            return template_summary(dart), "template"
        ungrounded = find_ungrounded_figures(text, set(ratio_facts(dart.financials).values()))
        if ungrounded:
            logger.warning("stock_summary_ungrounded", code=dart.code, figures=ungrounded)
            return template_summary(dart), "template"
        return text, "bedrock"

    def _converse(self, user_prompt: str) -> str | None:
        client = self._client or get_runtime_client()
        try:
            response = client.converse(**self._build_converse_request(user_prompt))
        except (ClientError, BotoCoreError) as exc:
            logger.error(
                "stock_summary_bedrock_failed", error_type=type(exc).__name__, error=str(exc)
            )
            return None
        stop_reason = response.get("stopReason")
        if stop_reason != "end_turn":
            # max_tokens(잘린 문장)·guardrail_intervened 등은 요약으로 쓰지 않는다.
            logger.warning("stock_summary_unusable_stop_reason", stop_reason=stop_reason)
            return None
        content = response["output"]["message"]["content"]
        return "".join(block.get("text", "") for block in content).strip() or None

    def _build_converse_request(self, user_prompt: str) -> dict[str, Any]:
        request: dict[str, Any] = {
            "modelId": self._settings.bedrock_model_id,
            "system": [{"text": SYSTEM_PROMPT_STOCK_SUMMARY}],
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {"maxTokens": SUMMARY_MAX_TOKENS},
        }
        if self._settings.bedrock_guardrail_id:
            request["guardrailConfig"] = {
                "guardrailIdentifier": self._settings.bedrock_guardrail_id,
                "guardrailVersion": self._settings.bedrock_guardrail_version,
            }
        return request


def ratio_facts(financials: StockFinancials) -> dict[str, float]:
    """모델에 넘기고 요약 검증에도 쓰는 비율. 모두 DART 원본 금액에서 코드로 계산한 값이다."""
    candidates = {
        "부채비율(%)": financials.debt_ratio,
        "영업이익률(%)": financials.operating_margin,
        "매출액 증감률(%)": growth_rate(financials.revenue_series),
        "영업이익 증감률(%)": growth_rate(financials.operating_income_series),
        "당기순이익 증감률(%)": growth_rate(financials.net_income_series),
    }
    return {label: value for label, value in candidates.items() if value is not None}


def growth_rate(series: list[SeriesPoint]) -> float | None:
    """직전 기간 대비 증감률(%). 시계열은 전전기 → 전기 → 당기 순서다."""
    if len(series) < 2 or series[-2].amount == 0:
        return None
    previous, current = series[-2].amount, series[-1].amount
    return round((current - previous) / abs(previous) * 100, 1)


def build_stock_prompt(dart: DartResult) -> str:
    statement = STATEMENT_LABELS[dart.financials.statement_type]
    facts: dict[str, Any] = {
        "회사명": dart.name,
        "종목코드": dart.code,
        "보고서": f"DART {dart.financials.report_label}",
        "재무제표 구분": f"{statement}재무제표",
        **ratio_facts(dart.financials),
    }
    data = json.dumps(facts, ensure_ascii=False, indent=2)
    instruction = "위 DART 데이터만으로 이 회사의 재무 상태를 3~4문장으로 요약하세요."
    return f"<dart_data>\n{data}\n</dart_data>\n\n{instruction}"


def template_summary(dart: DartResult) -> str:
    """모델 없이 코드가 만드는 요약. DART 원본에서 계산한 비율만 쓴다."""
    financials = dart.financials
    statement = STATEMENT_LABELS[financials.statement_type]
    basis = f"DART {financials.report_label}({statement}재무제표) 기준"
    facts = ratio_facts(financials)
    if not facts:
        return f"{basis} 핵심 비율을 계산할 수 있는 계정과목을 찾지 못했습니다."
    listed = ", ".join(
        f"{label.removesuffix('(%)')} {value:.1f}%" for label, value in facts.items()
    )
    return f"{basis} {listed}입니다. 세부 금액은 DART 원문을 확인하세요."


def get_stock_summary_service() -> StockSummaryService:
    return StockSummaryService(get_settings(), get_dart_tool())
