/**
 * TwelveData API — 해외 종목 (NASDAQ, NYSE 등) 일봉·현재가 라이브 조회.
 * Free tier: 800 calls/day, 8 calls/min. S3 캐싱으로 호출 절감.
 *
 * env: TWELEVE_KEY  (변수명은 .env 표기 그대로 유지)
 */

import type { PricePoint } from "./stocktypes";
import { readCache, writeCache } from "./cache";

const BASE = "https://api.twelvedata.com";

const key = () => process.env.TWELEVE_KEY || "";

export const tdConfigured = (): boolean => !!key();

export interface TdQuote {
  symbol: string;
  name: string;
  currency: string; // "USD" 등
  exchange: string; // "NASDAQ" 등
  price: number;
  changePct: number;
  volume: number;
  avgVolume: number;
  high52w: number;
  low52w: number;
}

const TTL_QUOTE_MS = 5 * 60 * 1000; // 5분
const TTL_DAILY_MS = 30 * 60 * 1000; // 30분 (일봉은 자주 갱신될 필요 없음)

function num(v: unknown): number {
  const n = Number(String(v ?? "").replace(/,/g, ""));
  return Number.isFinite(n) ? n : 0;
}

/** 현재가 + 52주 + 거래량 등. */
export async function tdQuote(symbol: string): Promise<TdQuote | null> {
  if (!key()) return null;
  const cacheKey = `td-quote-${symbol}`;
  const cached = await readCache<TdQuote>(cacheKey);
  if (cached) return cached;

  const url = `${BASE}/quote?symbol=${encodeURIComponent(symbol)}&apikey=${key()}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`TwelveData quote ${res.status}`);
  const data = (await res.json()) as Record<string, unknown> & {
    status?: string;
    message?: string;
    fifty_two_week?: { high?: string; low?: string };
  };
  if (data.status === "error") {
    throw new Error(`TwelveData: ${data.message ?? "unknown error"}`);
  }
  const out: TdQuote = {
    symbol: String(data.symbol ?? symbol),
    name: String(data.name ?? symbol),
    currency: String(data.currency ?? ""),
    exchange: String(data.exchange ?? ""),
    price: num(data.close),
    changePct: num(data.percent_change),
    volume: num(data.volume),
    avgVolume: num(data.average_volume),
    high52w: num(data.fifty_two_week?.high),
    low52w: num(data.fifty_two_week?.low),
  };
  if (!out.price) return null;
  await writeCache(cacheKey, out, TTL_QUOTE_MS);
  return out;
}

/** 일봉 시계열 — 최근 N일. */
export async function tdDaily(
  symbol: string,
  days: number = 90
): Promise<PricePoint[]> {
  if (!key()) return [];
  const cacheKey = `td-daily-${symbol}-${days}`;
  const cached = await readCache<PricePoint[]>(cacheKey);
  if (cached) return cached;

  const url =
    `${BASE}/time_series?symbol=${encodeURIComponent(symbol)}` +
    `&interval=1day&outputsize=${days}&order=ASC&apikey=${key()}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`TwelveData time_series ${res.status}`);
  const data = (await res.json()) as {
    status?: string;
    message?: string;
    values?: { datetime: string; close: string; volume: string }[];
  };
  if (data.status === "error") {
    throw new Error(`TwelveData: ${data.message ?? "unknown error"}`);
  }
  const points: PricePoint[] = (data.values ?? []).map((v) => ({
    date: v.datetime,
    close: num(v.close),
    volume: num(v.volume),
  }));
  if (points.length < 2) return [];
  await writeCache(cacheKey, points, TTL_DAILY_MS);
  return points;
}
