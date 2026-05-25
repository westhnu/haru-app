import type { Indicator, FinancialRow, PricePoint, SupplyInfo } from "./stocktypes";

/** 코드 기반 deterministic 가격·거래량 시계열(데모용) — 약 90 영업일. */
export function mockPrices(code: string, base = 70000): PricePoint[] {
  let seed = Array.from(code).reduce((a, c) => a + c.charCodeAt(0), 0) || 7;
  const rand = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  const points: PricePoint[] = [];
  let price = base;
  const today = new Date();
  for (let i = 89; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    if (d.getDay() === 0 || d.getDay() === 6) continue; // 주말 제외
    price = Math.max(1000, price * (1 + (rand() - 0.48) * 0.035));
    const volume = Math.round(5_000_000 + rand() * 18_000_000);
    points.push({
      date: d.toISOString().slice(0, 10),
      close: Math.round(price),
      volume,
    });
  }
  return points;
}

export function mockIndicators(): Indicator[] {
  return [
    { label: "시가총액", value: "485조 6,000억", tone: "neutral", context: "대형주" },
    {
      label: "PER",
      value: "13.2배",
      hint: "주가가 이익의 몇 배인지",
      tone: "good",
      context: "코스피 평균(10~15배) 수준",
    },
    {
      label: "PBR",
      value: "1.4배",
      hint: "주가가 순자산의 몇 배인지",
      tone: "good",
      context: "1배 이상·과열 아님",
    },
    {
      label: "EPS",
      value: "6,120원",
      hint: "주당 순이익",
      tone: "good",
      context: "전년 대비 증가",
    },
    {
      label: "배당수익률",
      value: "1.9%",
      hint: "주가 대비 연 배당",
      tone: "neutral",
      context: "시장 평균 수준",
    },
    {
      label: "외국인 보유율",
      value: "54.3%",
      tone: "good",
      context: "업종 내 높은 편",
    },
  ];
}

export function mockSupply(): SupplyInfo {
  return {
    date: new Date().toISOString().slice(0, 10),
    rows: [
      { label: "외국인", netQty: 1240000 },
      { label: "기관", netQty: -450000 },
      { label: "개인", netQty: -790000 },
    ],
  };
}

export function mockFinancials(): { year: string; rows: FinancialRow[] } {
  return {
    year: "2025",
    rows: [
      { label: "매출액", value: 2589000000000 },
      { label: "영업이익", value: 326000000000 },
      { label: "당기순이익", value: 254000000000 },
      { label: "자산총계", value: 4559000000000 },
      { label: "부채총계", value: 921000000000 },
      { label: "자본총계", value: 3638000000000 },
    ],
  };
}
