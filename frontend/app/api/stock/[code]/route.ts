import { NextResponse } from "next/server";
import type { PriceBasics, PricePoint, StockResponse } from "@/lib/stocktypes";
import { corpInfo } from "@/lib/corpcodes";
import { fetchFinancials } from "@/lib/dart";
import {
  mockFinancials,
  mockIndicators,
  mockPrices,
  mockSupply,
} from "@/lib/stockmock";
import {
  kisConfigured,
  kisDaily,
  kisQuote,
  kisInvestor,
  indicatorsFromQuote,
  type KisQuote,
} from "@/lib/kis";

export const dynamic = "force-dynamic";
export const maxDuration = 30;

export async function GET(
  req: Request,
  { params }: { params: { code: string } }
) {
  const code = decodeURIComponent(params.code);
  const nameParam = new URL(req.url).searchParams.get("name") || undefined;
  const info = corpInfo(code);
  const isKrCode = /^\d{6}$/.test(code);
  const warnings: string[] = [];

  let priceMode: "live" | "mock" = "mock";
  let indicatorsMode: "live" | "mock" = "mock";
  let supplyMode: "live" | "mock" = "mock";
  let prices: PricePoint[] = mockPrices(code, info ? 80000 : 50000);
  let indicators = mockIndicators();
  let supply = mockSupply();
  let quote: KisQuote | null = null;

  // ── KIS 실시간 시세 (국내 6자리 코드 + 키 있을 때) ──
  if (isKrCode && kisConfigured()) {
    try {
      const daily = await kisDaily(code, 90);
      if (daily.length > 1) {
        prices = daily;
        priceMode = "live";
      } else {
        warnings.push("KIS 일봉 데이터 없음 → 데모 시세");
      }
    } catch (e) {
      warnings.push(`KIS 일봉 실패: ${(e as Error).message} → 데모 시세`);
    }
    try {
      quote = await kisQuote(code);
      if (quote) {
        indicators = indicatorsFromQuote(quote);
        indicatorsMode = "live";
      } else {
        warnings.push("KIS 현재가 없음 → 데모 지표");
      }
    } catch (e) {
      warnings.push(`KIS 현재가 실패: ${(e as Error).message} → 데모 지표`);
    }
    try {
      const inv = await kisInvestor(code);
      if (inv) {
        supply = {
          date: inv.date,
          rows: [
            { label: "외국인", netQty: inv.foreign },
            { label: "기관", netQty: inv.institution },
            { label: "개인", netQty: inv.individual },
          ],
        };
        supplyMode = "live";
      } else {
        warnings.push("KIS 수급 없음 → 데모 수급");
      }
    } catch (e) {
      warnings.push(`KIS 수급 실패: ${(e as Error).message} → 데모 수급`);
    }
  } else if (!isKrCode) {
    warnings.push("해외·비표준 코드 → 시세·지표 데모 데이터");
  } else {
    warnings.push("KIS 키 없음 → 시세·지표 데모 데이터");
  }

  if (priceMode === "mock") warnings.push("시세·거래량은 데모 데이터입니다");
  if (indicatorsMode === "mock") warnings.push("투자 참고지표는 데모 값입니다");

  // ── 시세 요약 계산 ──
  const closes = prices.map((p) => p.close);
  const vols = prices.map((p) => p.volume);
  const last = quote?.price ?? closes[closes.length - 1] ?? null;
  const prev = closes[closes.length - 2] ?? null;
  const first = closes[0] ?? null;
  const changePct =
    quote != null
      ? quote.changePct
      : last !== null && prev
        ? Math.round(((last - prev) / prev) * 1000) / 10
        : null;

  const basics: PriceBasics = {
    high: Math.max(...closes),
    low: Math.min(...closes),
    returnPct:
      last !== null && first ? Math.round(((last - first) / first) * 1000) / 10 : 0,
    latestVolume: quote?.volume ?? vols[vols.length - 1] ?? 0,
    avgVolume: Math.round(vols.reduce((a, b) => a + b, 0) / vols.length),
    periodDays: prices.length,
  };

  // ── 재무: DART 라이브 (corp_code 매핑 + 키), 아니면 데모 ──
  let dartMode: "live" | "mock" = "mock";
  let financials = mockFinancials() as StockResponse["financials"];
  if (info) {
    const fin = await fetchFinancials(info.corp);
    if (fin.warning) warnings.push(fin.warning);
    if (fin.rows.some((r) => r.value !== null)) {
      financials = { year: fin.year, rows: fin.rows };
      dartMode = "live";
    }
  } else {
    warnings.push("DART corp_code 미등록 종목 → 재무 데모 데이터");
  }

  const body: StockResponse = {
    profile: {
      code,
      name: info?.name || quote?.name || nameParam || code,
      price: last,
      changePct,
      market: info?.market,
    },
    prices,
    basics,
    indicators,
    supply,
    financials,
    meta: { priceMode, dartMode, indicatorsMode, supplyMode, warnings },
  };
  return NextResponse.json(body);
}
