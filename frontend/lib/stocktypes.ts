// ── 종목 상세 페이지 타입 ──────────────────────────────

export interface PricePoint {
  date: string; // YYYY-MM-DD
  close: number;
  volume: number; // 거래량(주)
}

export interface FinancialRow {
  label: string; // 계정명 (매출액 등)
  value: number | null; // 금액 (원)
}

export type IndicatorTone = "good" | "neutral" | "caution";

export interface Indicator {
  label: string;
  value: string; // 표시용 포맷 문자열
  hint?: string; // 용어 짧은 설명
  tone?: IndicatorTone; // 양호/보통/주의
  context?: string; // 업종(섹터) 평균 대비 등 판단 근거
}

export interface StockProfile {
  code: string;
  name: string;
  price: number | null;
  changePct: number | null; // 직전 대비 등락률 %
  market?: string; // KOSPI/KOSDAQ
}

/** 가격 시계열에서 계산한 시세 요약 */
export interface PriceBasics {
  high: number; // 기간 최고가
  low: number; // 기간 최저가
  returnPct: number; // 기간 등락률 %
  latestVolume: number; // 최근 거래량
  avgVolume: number; // 기간 평균 거래량
  periodDays: number; // 기간(영업일 수)
}

/** 수급 동향 (외국인·기관·개인 순매수 수량) */
export interface SupplyInfo {
  date: string;
  rows: { label: string; netQty: number }[]; // +순매수 / -순매도 (주)
}

export interface StockResponse {
  profile: StockProfile;
  prices: PricePoint[];
  basics: PriceBasics;
  indicators: Indicator[];
  supply: SupplyInfo;
  financials: {
    year: string | null;
    rows: FinancialRow[];
  };
  meta: {
    priceMode: "live" | "mock";
    dartMode: "live" | "mock";
    indicatorsMode: "live" | "mock";
    supplyMode: "live" | "mock";
    warnings: string[];
  };
}
