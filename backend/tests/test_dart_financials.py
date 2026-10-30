"""DART 응답 → StockFinancials 매핑 (KI-008 회귀 방지).

픽스처 수치는 2026-09-13 실측한 삼성전자 2026 반기보고서(연결) 원본 행에서 가져왔다.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.models.stock import StockFinancials
from app.services.dart_financials import (
    ACCOUNT_RULES,
    REPORT_TYPES,
    build_financials,
    find_account,
    period_covered,
)

HALF_YEAR = (2026, "11012", "2026년 반기보고서")
NON_STANDARD_ID = "-표준계정코드 미사용-"
SAMSUNG_2024_ANNUAL = Path(
    "/Users/westhnu/Agent/Claude/jutopia_data/data/dart_cache/fin_00126380_2024_11011_CFS.json"
)


def row(sj_div: str, account_id: str, account_nm: str, **amounts: str) -> dict[str, Any]:
    return {
        "rcept_no": "20260814003699",
        "currency": "KRW",
        "sj_div": sj_div,
        "account_id": account_id,
        "account_nm": account_nm,
        **amounts,
    }


SAMSUNG_2026_HALF = [
    row(
        "BS",
        "ifrs-full_Equity",
        "자본총계",
        thstrm_amount="579309676000000",
        frmtrm_amount="436320337000000",
    ),
    row(
        "BS",
        "ifrs-full_Liabilities",
        "부채총계",
        thstrm_amount="180170840000000",
        frmtrm_amount="130621773000000",
    ),
    row(
        "IS",
        "dart_OperatingIncomeLoss",
        "영업이익",
        thstrm_amount="89492412000000",
        thstrm_add_amount="146725209000000",
        frmtrm_q_amount="4676057000000",
        frmtrm_add_amount="11361329000000",
    ),
    row(
        "IS",
        "ifrs-full_ProfitLossAttributableToOwnersOfParent",
        "지배회사지분 반기순이익",
        thstrm_amount="71269468000000",
        thstrm_add_amount="118370658000000",
        frmtrm_q_amount="4934034000000",
        frmtrm_add_amount="12962441000000",
    ),
    row(
        "IS",
        "ifrs-full_ProfitLoss",
        "반기순이익",
        thstrm_amount="71624461000000",
        thstrm_add_amount="118849733000000",
        frmtrm_q_amount="5116435000000",
        frmtrm_add_amount="13339313000000",
    ),
    row(
        "IS",
        "ifrs-full_Revenue",
        "매출액",
        thstrm_amount="171499470000000",
        thstrm_add_amount="305372914000000",
        frmtrm_q_amount="74566317000000",
        frmtrm_add_amount="153706820000000",
    ),
    row(
        "CF",
        "ifrs-full_CashFlowsFromUsedInOperatingActivities",
        "영업활동현금흐름",
        thstrm_amount="145355192000000",
        frmtrm_q_amount="33941002000000",
    ),
    row("CF", "ifrs-full_ProfitLoss", "반기순이익", thstrm_amount="71624461000000"),
]


@pytest.fixture
def half_year() -> StockFinancials:
    return build_financials(SAMSUNG_2026_HALF, HALF_YEAR, "CFS", "12")


def test_half_year_income_uses_cumulative_not_three_month_amount(
    half_year: StockFinancials,
) -> None:
    """KI-008 회귀: 반기 손익이 3개월 금액(thstrm_amount)으로 나오면 실패해야 한다."""
    three_month_revenue = 171_499_470_000_000.0

    assert half_year.revenue != three_month_revenue
    assert half_year.revenue == 305_372_914_000_000.0
    assert half_year.operating_income == 146_725_209_000_000.0
    assert half_year.net_income == 118_849_733_000_000.0


def test_half_year_growth_uses_prior_year_cumulative(half_year: StockFinancials) -> None:
    growth = (
        half_year.revenue_growth,
        half_year.operating_income_growth,
        half_year.net_income_growth,
    )

    assert growth == (98.7, 1191.4, 791.0)


def test_ratios_use_cumulative_income_and_period_end_balance(half_year: StockFinancials) -> None:
    assert half_year.operating_margin == 48.0
    assert half_year.debt_ratio == 31.1


def test_cash_flow_without_cumulative_field_uses_thstrm_amount(half_year: StockFinancials) -> None:
    assert half_year.operating_cf == 145_355_192_000_000.0


def test_half_year_report_metadata(half_year: StockFinancials) -> None:
    assert half_year.report_type == "half_cumulative"
    assert half_year.period_covered == "2026-01-01 ~ 2026-06-30"


@pytest.mark.parametrize(
    ("reprt_code", "report_type", "period"),
    [
        ("11013", "quarterly", "2026-01-01 ~ 2026-03-31"),
        ("11012", "half_cumulative", "2026-01-01 ~ 2026-06-30"),
        ("11014", "quarterly", "2026-01-01 ~ 2026-09-30"),
        ("11011", "annual", "2026-01-01 ~ 2026-12-31"),
    ],
)
def test_report_type_and_period_by_report_code(
    reprt_code: str, report_type: str, period: str
) -> None:
    assert REPORT_TYPES[reprt_code] == report_type
    assert period_covered(2026, reprt_code, "12") == period


def test_period_is_not_guessed_for_non_december_fiscal_year() -> None:
    assert period_covered(2026, "11012", "03") is None
    assert period_covered(2026, "11012", None) is None


@pytest.mark.parametrize("name", ["당기순이익", "반기순이익", "분기순이익(손실)"])
def test_net_income_name_match_skips_controlling_interest_row(name: str) -> None:
    rows = [
        row("IS", NON_STANDARD_ID, "지배회사지분 반기순이익", thstrm_amount="1"),
        row("IS", NON_STANDARD_ID, name, thstrm_amount="2"),
    ]

    matched = find_account(rows, ACCOUNT_RULES["net_income"])

    assert matched is not None
    assert matched["account_nm"] == name


def test_interim_growth_never_compares_with_non_cumulative_prior_amount() -> None:
    rows = [row("IS", "ifrs-full_Revenue", "매출액", thstrm_add_amount="120", frmtrm_amount="100")]

    financials = build_financials(rows, HALF_YEAR, "CFS", "12")

    assert financials.revenue == 120.0
    assert financials.revenue_growth is None


@pytest.mark.skipif(not SAMSUNG_2024_ANNUAL.is_file(), reason="jutopia DART 캐시 파일 없음")
def test_annual_report_from_real_dart_response() -> None:
    items = json.loads(SAMSUNG_2024_ANNUAL.read_text(encoding="utf-8"))

    financials = build_financials(items, (2024, "11011", "2024년 사업보고서"), "CFS", "12")

    assert financials.report_type == "annual"
    assert financials.period_covered == "2024-01-01 ~ 2024-12-31"
    assert financials.revenue == 300_870_903_000_000.0
    assert financials.net_income == 34_451_351_000_000.0
    assert financials.revenue_growth == 16.2
