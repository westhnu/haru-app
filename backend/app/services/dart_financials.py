"""DART 단일회사 전체 재무제표 응답 → StockFinancials (회계연도 누적 기준).

jutopia `_compute_metrics`는 참고만 한다. 반기·분기 손익에 3개월 금액(thstrm_amount)을 쓰고
반기순이익·분기순이익 계정을 놓치는 문제가 실측으로 확인됐다 (KI-008).

필드 기준 — 2026-09-13 삼성전자 2026 반기·2024 사업보고서 실측:
- 손익(IS·CIS): 반기·분기는 thstrm_add_amount가 누적, thstrm_amount는 3개월 단독
- 현금흐름(CF): 누적 필드가 없고 thstrm_amount 자체가 누적
- 재무상태(BS): thstrm_amount가 기말 시점 값
- 전년 비교: 반기·분기 손익은 frmtrm_add_amount, 사업보고서는 frmtrm_amount
"""

import calendar
from typing import Any, NamedTuple

from app.models.stock import ReportType, StockFinancials

Row = dict[str, Any]

REPORT_TYPES: dict[str, ReportType] = {
    "11011": "annual",
    "11012": "half_cumulative",
    "11013": "quarterly",
    "11014": "quarterly",
}
# 회계연도 시작부터 보고서 기준일까지의 개월 수
REPORT_MONTHS: dict[str, int] = {"11013": 3, "11012": 6, "11014": 9, "11011": 12}
DECEMBER = "12"
INCOME_STATEMENTS = ("IS", "CIS")


class AccountRule(NamedTuple):
    # 앞에 있는 재무제표 구분을 먼저 찾는다 (순이익은 CF에도 있으므로 손익계산서로 한정)
    statements: tuple[str, ...]
    account_ids: frozenset[str]
    # 공백을 제거한 계정명
    names: frozenset[str]


def _names(*names: str) -> frozenset[str]:
    return frozenset(name.replace(" ", "") for name in names)


ACCOUNT_RULES: dict[str, AccountRule] = {
    "revenue": AccountRule(
        INCOME_STATEMENTS,
        frozenset({"ifrs-full_Revenue"}),
        _names("매출액", "수익(매출액)", "영업수익", "매출"),
    ),
    "operating_income": AccountRule(
        INCOME_STATEMENTS,
        frozenset({"dart_OperatingIncomeLoss"}),
        _names("영업이익", "영업이익(손실)"),
    ),
    # 계정명은 보고서에 따라 당기·반기·분기순이익으로 바뀐다. account_id가 가장 안정적이다.
    "net_income": AccountRule(
        INCOME_STATEMENTS,
        frozenset({"ifrs-full_ProfitLoss"}),
        _names(
            *(f"{term}순이익{loss}" for term in ("당기", "반기", "분기") for loss in ("", "(손실)"))
        ),
    ),
    "total_liabilities": AccountRule(
        ("BS",), frozenset({"ifrs-full_Liabilities"}), _names("부채총계")
    ),
    "total_equity": AccountRule(("BS",), frozenset({"ifrs-full_Equity"}), _names("자본총계")),
    "operating_cf": AccountRule(
        ("CF",),
        frozenset({"ifrs-full_CashFlowsFromUsedInOperatingActivities"}),
        _names("영업활동현금흐름", "영업활동으로 인한 현금흐름"),
    ),
    "investing_cf": AccountRule(
        ("CF",),
        frozenset({"ifrs-full_CashFlowsFromUsedInInvestingActivities"}),
        _names("투자활동현금흐름", "투자활동으로 인한 현금흐름"),
    ),
    "financing_cf": AccountRule(
        ("CF",),
        frozenset({"ifrs-full_CashFlowsFromUsedInFinancingActivities"}),
        _names("재무활동현금흐름", "재무활동으로 인한 현금흐름"),
    ),
}
GROWTH_FIELDS: dict[str, str] = {
    "revenue_growth": "revenue",
    "operating_income_growth": "operating_income",
    "net_income_growth": "net_income",
}


def build_financials(
    items: list[Row],
    report: tuple[int, str, str],
    statement_type: str,
    fiscal_month: str | None,
) -> StockFinancials:
    year, reprt_code, label = report
    report_type = REPORT_TYPES[reprt_code]
    rows = {metric: find_account(items, rule) for metric, rule in ACCOUNT_RULES.items()}
    amounts = {metric: current_amount(row) for metric, row in rows.items()}
    return StockFinancials(
        report_year=year,
        report_code=reprt_code,
        report_label=label,
        report_type=report_type,
        period_covered=period_covered(year, reprt_code, fiscal_month),
        statement_type=statement_type,  # type: ignore[arg-type]
        currency=items[0].get("currency") or "KRW",
        debt_ratio=percentage(amounts["total_liabilities"], amounts["total_equity"]),
        operating_margin=percentage(amounts["operating_income"], amounts["revenue"]),
        **amounts,
        **growth_rates(rows, amounts, report_type),
    )


def find_account(items: list[Row], rule: AccountRule) -> Row | None:
    """재무제표 구분 우선순위 → account_id 일치 → 공백 제거 계정명 정확 일치.

    부분 문자열 매칭은 하지 않는다. "지배회사지분 반기순이익"이 순이익으로 잡히면 안 된다.
    """
    for statement in rule.statements:
        rows = [item for item in items if item.get("sj_div") == statement]
        by_id = next((row for row in rows if row.get("account_id") in rule.account_ids), None)
        by_name = next(
            (row for row in rows if _normalize(row.get("account_nm")) in rule.names), None
        )
        if by_id or by_name:
            return by_id or by_name
    return None


def current_amount(row: Row | None) -> float | None:
    """누적 금액 우선. 사업보고서·현금흐름·재무상태표에는 누적 필드가 없어 thstrm_amount로 폴백."""
    if row is None:
        return None
    cumulative = parse_amount(row.get("thstrm_add_amount"))
    return cumulative if cumulative is not None else parse_amount(row.get("thstrm_amount"))


def previous_amount(row: Row | None, report_type: ReportType) -> float | None:
    """전년 동기 누적 금액.

    사업보고서만 frmtrm_amount(전기)로 폴백한다. 반기·분기 손익의 frmtrm_amount는
    비어 있거나 기간이 다른 값일 수 있어 폴백하면 기간이 어긋난 비교가 된다.
    """
    if row is None:
        return None
    cumulative = parse_amount(row.get("frmtrm_add_amount"))
    if cumulative is not None or report_type != "annual":
        return cumulative
    return parse_amount(row.get("frmtrm_amount"))


def growth_rates(
    rows: dict[str, Row | None], amounts: dict[str, float | None], report_type: ReportType
) -> dict[str, float | None]:
    return {
        field: growth_rate(amounts[metric], previous_amount(rows[metric], report_type))
        for field, metric in GROWTH_FIELDS.items()
    }


def period_covered(year: int, reprt_code: str, fiscal_month: str | None) -> str | None:
    """손익·현금흐름이 포괄하는 기간 'YYYY-MM-DD ~ YYYY-MM-DD'.

    12월 결산만 계산한다. 다른 결산월은 DART bsns_year가 가리키는 달력 연도를
    실측으로 확인하지 못했으므로 날짜를 추정하지 않고 None을 돌려준다.
    """
    if fiscal_month != DECEMBER:
        return None
    end_month = REPORT_MONTHS[reprt_code]
    last_day = calendar.monthrange(year, end_month)[1]
    return f"{year}-01-01 ~ {year}-{end_month:02d}-{last_day:02d}"


def percentage(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or not denominator:
        return None
    return round(numerator / denominator * 100, 1)


def growth_rate(current: float | None, previous: float | None) -> float | None:
    if current is None or not previous:
        return None
    return round((current - previous) / abs(previous) * 100, 1)


def parse_amount(value: Any) -> float | None:
    """DART 금액 문자열("1,234" / "-" / "") → float."""
    text = "" if value is None else str(value).replace(",", "").strip()
    if text in ("", "-"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _normalize(account_name: Any) -> str:
    return str(account_name or "").replace(" ", "")
