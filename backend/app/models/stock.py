from typing import Literal

from pydantic import BaseModel, Field

from app.core.guardrail import DISCLAIMER

STOCK_CODE_PATTERN = r"^\d{6}$"
STATEMENT_LABELS: dict[str, str] = {"CFS": "연결", "OFS": "개별"}

StatementType = Literal["CFS", "OFS"]
# half_cumulative: 반기보고서(6개월 누적)
# quarterly: 1분기(3개월)·3분기(9개월 누적) — 실제 기간은 period_covered로 확인
# annual: 사업보고서(12개월)
ReportType = Literal["half_cumulative", "quarterly", "annual"]
# bedrock: AI 요약(수치 검증 통과) / template: 코드가 만든 요약 / mock: 개발용
SummarySource = Literal["bedrock", "template", "mock"]

GROWTH_DESCRIPTION = "전년 동기 누적 대비 증감률(%). 사업보고서는 전기 대비"


class StockFinancials(BaseModel):
    """DART 원본 금액과 그 금액에서 코드로 계산한 비율만 담는다.

    AI가 만든 수치는 이 모델에 절대 들어오지 않는다 (원칙 2).
    손익·현금흐름은 회계연도 누적 금액, 재무상태표 항목은 period_covered 종료일 시점 값이다.
    """

    report_year: int
    report_code: str = Field(description="11011 사업 / 11012 반기 / 11013 1분기 / 11014 3분기")
    report_label: str
    report_type: ReportType
    period_covered: str | None = Field(
        default=None,
        description="손익·현금흐름 누적 기간 'YYYY-MM-DD ~ YYYY-MM-DD'. 12월 결산이 아니면 null",
    )
    statement_type: StatementType
    currency: str = "KRW"
    revenue: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None
    operating_cf: float | None = None
    investing_cf: float | None = None
    financing_cf: float | None = None
    debt_ratio: float | None = Field(default=None, description="부채총계 / 자본총계 x 100")
    operating_margin: float | None = Field(default=None, description="영업이익 / 매출액 x 100")
    revenue_growth: float | None = Field(default=None, description=GROWTH_DESCRIPTION)
    operating_income_growth: float | None = Field(default=None, description=GROWTH_DESCRIPTION)
    net_income_growth: float | None = Field(default=None, description=GROWTH_DESCRIPTION)


class StockSource(BaseModel):
    name: str
    url: str


class DartResult(BaseModel):
    code: str
    name: str
    corp_code: str
    rcept_no: str
    financials: StockFinancials
    source: StockSource
    is_mock: bool = False


class StockSummaryResponse(BaseModel):
    code: str
    name: str
    financials: StockFinancials
    summary: str
    summary_source: SummarySource
    # 원칙 2: 출처 없는 재무 응답은 스키마 차원에서 만들 수 없게 한다.
    sources: list[StockSource] = Field(min_length=1)
    disclaimer: str = DISCLAIMER
    is_mock: bool = False
