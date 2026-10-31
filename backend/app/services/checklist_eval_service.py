"""체크리스트 원칙 AI 평가 (Phase B). Converse + DART 재무 + 원칙 2 코드 검증.

흐름: DART 조회 → ratio_facts(코드 계산 비율)만 모델에 전달 → JSON 판정 →
코드 검증(status·길이·used_facts·근거 없는 수치·금지 표현) → 실패 시 '판단 보류' 템플릿.

- KB(RetrieveAndGenerate)를 쓰지 않는다. contextual grounding이 KB 청크 기준이라
  DART 인용이 차단되고, 구조화(JSON) 출력을 받을 수 없다.
  Guardrail(topic·content·word)은 guardrailConfig로 그대로 적용된다.
- mock DART면 모델을 호출하지 않는다 (가짜 수치로 그럴듯한 판정이 나오면 오해 소지가 크다).
- 결과는 저장하지 않는다. 사용자가 확인 후 PATCH로 반영한다.
"""

import json
import re
import time
from typing import Any

import structlog
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings
from app.core.grounding import find_ungrounded_figures
from app.core.guardrail import DISCLAIMER, has_forbidden_phrase, mask_pii
from app.core.prompts import SYSTEM_PROMPT_CHECKLIST_EVAL
from app.models.checklist import REASONING_MAX_LENGTH, AiEvaluation, EvaluationSource
from app.models.stock import STATEMENT_LABELS, STOCK_CODE_PATTERN, DartResult
from app.services.bedrock_client import get_runtime_client
from app.services.dart_tool import DartTool, get_dart_tool
from app.services.stock_summary_service import AMOUNT_BASIS, ratio_facts

EVAL_MAX_TOKENS = 600
VALID_STATUSES = frozenset({"satisfied", "unsatisfied", "uncertain"})
_PERCENT_IN_TEXT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|퍼센트)")
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

FALLBACK_PREFIX = "제공된 DART 데이터로 판단할 수 없습니다."
REASON_MOCK = "개발용 DART 데이터라 AI 평가를 하지 않았습니다. 실제 DART 연동 후 다시 시도하세요."
REASON_BEDROCK_FAILED = "AI 평가 호출에 실패했습니다. 잠시 후 다시 시도하세요."
REASON_STOPPED = "Guardrail 개입 또는 응답 잘림으로 AI 판정을 쓰지 않았습니다."
REASON_INVALID = (
    "AI 응답이 검증을 통과하지 못해 판정을 보류합니다. 원칙과 DART 원문을 직접 확인하세요."
)
REASON_NO_FACTS = "평가에 쓸 수 있는 재무 비율이 이 보고서에 없습니다. DART 원문을 확인하세요."

logger = structlog.get_logger(__name__)


class UnsupportedMarketError(ValueError):
    """DART가 지원하지 않는 종목(해외 등)."""


def report_label(dart: DartResult) -> str:
    f = dart.financials
    scope = f"{STATEMENT_LABELS[f.statement_type]}재무제표"
    period = f", {f.period_covered} 누적" if f.period_covered else ""
    return f"DART {f.report_label}({scope}{period})"


def principle_percentages(principle: str) -> set[float]:
    """원칙 문장에 사용자가 적은 기준값(예: "200%")은 reasoning에 다시 나와도
    근거 없는 수치가 아니다."""
    return {float(m.group(1)) for m in _PERCENT_IN_TEXT.finditer(principle)}


def build_eval_prompt(principle: str, dart: DartResult, facts: dict[str, float]) -> str:
    data = {
        "회사명": dart.name,
        "종목코드": dart.code,
        "보고서": report_label(dart),
        "금액 기준": AMOUNT_BASIS,
        **facts,
    }
    return (
        f"<principle>\n{principle}\n</principle>\n\n"
        f"<dart_data>\n{json.dumps(data, ensure_ascii=False, indent=2)}\n</dart_data>\n\n"
        "위 원칙을 <dart_data>만으로 평가해 JSON 객체 하나로 답하세요."
    )


def parse_eval_json(text: str) -> dict[str, Any] | None:
    """모델이 가끔 코드블록으로 감싸므로 첫 JSON 객체를 꺼낸다."""
    match = _JSON_OBJECT.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def validate_eval(
    data: dict[str, Any], facts: dict[str, float], principle: str
) -> tuple[str, str, list[str]] | str:
    """통과하면 (status, reasoning, used_facts), 실패하면 실패 사유 문자열(로그용)."""
    status = data.get("suggested_status")
    reasoning = data.get("reasoning")
    used = data.get("used_facts", [])
    if status not in VALID_STATUSES:
        return f"invalid_status:{status!r}"
    if not isinstance(reasoning, str) or not reasoning.strip():
        return "empty_reasoning"
    reasoning = reasoning.strip()
    if len(reasoning) > REASONING_MAX_LENGTH:
        return "reasoning_too_long"
    if not isinstance(used, list) or not all(isinstance(u, str) for u in used):
        return "invalid_used_facts"
    unknown = [u for u in used if u not in facts]
    if unknown:
        return f"unknown_used_facts:{unknown}"
    if status != "uncertain" and not used:
        return "decision_without_facts"  # 근거 지표 없이 충족/미충족 판정 금지
    allowed = set(facts.values()) | principle_percentages(principle)
    ungrounded = find_ungrounded_figures(reasoning, allowed)
    if ungrounded:
        return f"ungrounded_figures:{ungrounded}"
    if has_forbidden_phrase(reasoning):
        return "forbidden_phrase"
    return status, reasoning, used


class ChecklistEvalService:
    def __init__(
        self, settings: Settings, dart_tool: DartTool, runtime_client: Any | None = None
    ) -> None:
        self._settings = settings
        self._dart_tool = dart_tool
        self._client = runtime_client

    def evaluate_item(self, stock_code: str, principle: str) -> AiEvaluation:
        if not re.fullmatch(STOCK_CODE_PATTERN, stock_code):
            raise UnsupportedMarketError(stock_code)
        dart = self._dart_tool.fetch_dart_financial(stock_code)  # DartError는 라우터가 매핑
        if dart.is_mock:
            return self._fallback(dart, REASON_MOCK, "mock")
        facts = ratio_facts(dart.financials)
        if not facts:
            return self._fallback(dart, REASON_NO_FACTS)
        text = self._converse(build_eval_prompt(mask_pii(principle), dart, facts))
        if isinstance(text, Exception):
            return self._fallback(dart, REASON_BEDROCK_FAILED)
        if text is None:
            return self._fallback(dart, REASON_STOPPED)
        data = parse_eval_json(text)
        result = validate_eval(data, facts, principle) if data is not None else "invalid_json"
        if isinstance(result, str):
            logger.warning("checklist_eval_rejected", code=dart.code, reason=result)
            return self._fallback(dart, REASON_INVALID)
        status, reasoning, used = result
        return AiEvaluation(
            suggested_status=status,  # type: ignore[arg-type]
            reasoning=reasoning,
            sources=[dart.source],
            used_facts=used,
            evaluation_source="bedrock",
            report_label=report_label(dart),
            disclaimer=DISCLAIMER,
        )

    def _fallback(
        self, dart: DartResult, reason: str, source: EvaluationSource = "template"
    ) -> AiEvaluation:
        return AiEvaluation(
            suggested_status="uncertain",
            reasoning=f"{FALLBACK_PREFIX} {reason}",
            sources=[dart.source],
            used_facts=[],
            evaluation_source=source,
            report_label=report_label(dart),
            disclaimer=DISCLAIMER,
        )

    def _converse(self, user_prompt: str) -> str | None | Exception:
        """본문 텍스트, 사용 불가(stopReason≠end_turn)면 None, 호출 실패면 예외 객체."""
        client = self._client or get_runtime_client()
        request: dict[str, Any] = {
            "modelId": self._settings.bedrock_model_id,
            "system": [{"text": SYSTEM_PROMPT_CHECKLIST_EVAL}],
            "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
            "inferenceConfig": {"maxTokens": EVAL_MAX_TOKENS},
        }
        if self._settings.bedrock_guardrail_id:
            request["guardrailConfig"] = {
                "guardrailIdentifier": self._settings.bedrock_guardrail_id,
                "guardrailVersion": self._settings.bedrock_guardrail_version,
            }
        started = time.perf_counter()
        try:
            response = client.converse(**request)
        except (ClientError, BotoCoreError) as exc:
            logger.error("checklist_eval_bedrock_failed", error_type=type(exc).__name__)
            return exc
        stop_reason = response.get("stopReason")
        usage = response.get("usage", {})
        logger.info(
            "checklist_eval_bedrock",
            model_id=self._settings.bedrock_model_id,
            latency_ms=round((time.perf_counter() - started) * 1000),
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
            stop_reason=stop_reason,
            guardrail_action="intervened" if stop_reason == "guardrail_intervened" else "none",
        )
        if stop_reason != "end_turn":
            return None
        content = response["output"]["message"]["content"]
        return "".join(block.get("text", "") for block in content).strip() or None


def get_checklist_eval_service() -> ChecklistEvalService:
    return ChecklistEvalService(get_settings(), get_dart_tool())
