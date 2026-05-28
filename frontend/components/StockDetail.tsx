"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Info, BarChart3 } from "lucide-react";
import type { IndicatorTone, StockResponse } from "@/lib/stocktypes";
import PriceChart from "@/components/PriceChart";
import GlossaryText from "@/components/GlossaryText";

const TONE: Record<IndicatorTone, { cls: string; label: string }> = {
  good: { cls: "bg-emerald-50 text-emerald-700", label: "양호" },
  neutral: { cls: "bg-slate-100 text-slate-500", label: "보통" },
  caution: { cls: "bg-rose-50 text-rose-700", label: "주의" },
};

const RANGES = [
  { key: "1m", label: "1개월", n: 20 },
  { key: "3m", label: "3개월", n: 60 },
  { key: "all", label: "전체", n: 999 },
] as const;

function formatKRW(v: number | null): string {
  if (v === null) return "—";
  const neg = v < 0;
  let n = Math.abs(v);
  const jo = Math.floor(n / 1_0000_0000_0000);
  n -= jo * 1_0000_0000_0000;
  const eok = Math.floor(n / 1_0000_0000);
  const parts: string[] = [];
  if (jo > 0) parts.push(`${jo.toLocaleString()}조`);
  if (eok > 0 || jo > 0) parts.push(`${eok.toLocaleString()}억`);
  if (parts.length === 0) parts.push(`${Math.round(v).toLocaleString()}원`);
  return (neg ? "-" : "") + parts.join(" ");
}

function formatVol(v: number): string {
  if (v >= 10000) return `${Math.round(v / 10000).toLocaleString()}만주`;
  return `${v.toLocaleString()}주`;
}

function formatNet(v: number): string {
  const sign = v > 0 ? "+" : v < 0 ? "-" : "";
  const abs = Math.abs(v);
  const body =
    abs >= 10000 ? `${Math.round(abs / 10000).toLocaleString()}만주` : `${abs.toLocaleString()}주`;
  return `${sign}${body}`;
}

/** 가격 표시 — 한국은 "원", 외화는 통화 기호/코드 사용 */
function formatPrice(value: number, currency?: string): string {
  if (!currency || currency === "KRW") {
    return `${Math.round(value).toLocaleString()}원`;
  }
  if (currency === "USD") {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${currency}`;
}

export default function StockDetail({
  code,
  name,
}: {
  code: string;
  name?: string;
}) {
  const router = useRouter();
  const [data, setData] = useState<StockResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState<(typeof RANGES)[number]["key"]>("3m");

  // 브라우저 히스토리가 있으면 뒤로가기, 없으면 홈으로 (직접 URL 접속 케이스)
  const goBack = useCallback(() => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push("/");
    }
  }, [router]);
  const [tab, setTab] = useState<"info" | "financial">("info");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const q = name ? `?name=${encodeURIComponent(name)}` : "";
      const res = await fetch(`/api/stock/${encodeURIComponent(code)}${q}`, {
        cache: "no-store",
      });
      setData((await res.json()) as StockResponse);
    } finally {
      setLoading(false);
    }
  }, [code, name]);

  useEffect(() => {
    load();
  }, [load]);

  const sliced = useMemo(() => {
    if (!data) return [];
    const n = RANGES.find((r) => r.key === range)?.n ?? 60;
    return data.prices.slice(-n);
  }, [data, range]);

  const up = (data?.profile.changePct ?? 0) >= 0;
  const priceColor = up ? "text-rose-600" : "text-blue-600";

  return (
    <div className="min-h-svh bg-slate-50">
      <div className="mx-auto min-h-svh w-full max-w-[480px] bg-white px-5 pb-12">
        <div className="flex items-center justify-between py-5">
          <button
            type="button"
            onClick={goBack}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3.5 py-2 text-[13px] font-bold text-slate-600 transition hover:bg-slate-200"
          >
            <ArrowLeft className="h-4 w-4" />
            뒤로
          </button>
        </div>

        {loading || !data ? (
          <div className="mt-4 space-y-3">
            <div className="h-8 w-40 animate-pulse-soft rounded bg-slate-100" />
            <div className="h-[180px] animate-pulse-soft rounded-2xl bg-slate-50" />
          </div>
        ) : (
          <>
            {/* 헤더 */}
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-[1.7rem] font-black tracking-tight text-slate-950">
                  {data.profile.name}
                </h1>
                {data.profile.market && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-500">
                    {data.profile.market}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-[13px] font-semibold text-slate-400">
                {data.profile.code}
              </p>
              <div className="mt-3 flex flex-wrap items-baseline gap-2">
                <span className="text-[2rem] font-black text-slate-950">
                  {data.profile.price !== null
                    ? formatPrice(data.profile.price, data.profile.currency)
                    : "—"}
                </span>
                {data.profile.changePct !== null && (
                  <span className={`text-[15px] font-black ${priceColor}`}>
                    {up ? "+" : ""}
                    {data.profile.changePct}%
                  </span>
                )}
              </div>
            </div>

            {/* 해외 종목 안내 배너 */}
            {data.meta.priceMode === "unsupported" && (
              <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-[13px] font-semibold text-amber-900">
                <p className="font-black">해외 종목은 라이브 시세 미지원</p>
                <p className="mt-1 leading-6">
                  이 종목은 한국투자증권(KIS) Open API 의 조회 대상이 아니에요. 시세·재무 차트는 표시되지 않습니다. 브리핑 본문의 텍스트 정보만 참고해 주세요.
                </p>
              </div>
            )}

            {/* 해외/비지원 종목은 차트·시세요약·수급·지표·재무 섹션을 모두 숨김 */}
            {data.meta.priceMode !== "unsupported" && (
            <>
            {/* 차트 */}
            <div className="mt-5 rounded-[24px] border border-slate-200 bg-white p-4 shadow-soft">
              <PriceChart prices={sliced} up={up} />
              <div className="mt-3 flex items-center gap-1.5 rounded-full bg-slate-100 p-1">
                {RANGES.map((r) => (
                  <button
                    key={r.key}
                    onClick={() => setRange(r.key)}
                    className={`flex-1 rounded-full px-3 py-1.5 text-[12px] font-bold transition ${
                      range === r.key
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-500"
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
              {data.meta.priceMode === "mock" && (
                <p className="mt-2.5 text-center text-[11px] font-medium text-slate-400">
                  데모 시세 · 실시간 시세 연동 예정
                </p>
              )}
            </div>

            {/* 탭 — 재무는 DART 라이브가 있을 때만 노출 (해외 종목엔 unsupported) */}
            {data.meta.dartMode !== "unsupported" && (
              <div className="mt-4 flex items-center gap-1.5 rounded-full bg-slate-100 p-1">
                <button
                  onClick={() => setTab("info")}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-bold transition ${
                    tab === "info"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500"
                  }`}
                >
                  <Info className="h-4 w-4" />
                  종목정보
                </button>
                <button
                  onClick={() => setTab("financial")}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-bold transition ${
                    tab === "financial"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500"
                  }`}
                >
                  <BarChart3 className="h-4 w-4" />
                  재무제표
                </button>
              </div>
            )}

            {/* 종목정보 */}
            {tab === "info" && (
              <div className="mt-4 space-y-3">
                {/* 시세 요약 */}
                <div className="rounded-[24px] border border-slate-200 bg-white p-5">
                  <p className="text-[13px] font-black text-slate-900">
                    시세 요약
                    <span className="ml-1.5 text-[11px] font-bold text-slate-400">
                      최근 {data.basics.periodDays}거래일
                    </span>
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <Stat label="기간 최고가" value={formatPrice(data.basics.high, data.profile.currency)} />
                    <Stat label="기간 최저가" value={formatPrice(data.basics.low, data.profile.currency)} />
                    <Stat
                      label="기간 등락률"
                      value={`${data.basics.returnPct >= 0 ? "+" : ""}${data.basics.returnPct}%`}
                      valueClass={
                        data.basics.returnPct >= 0
                          ? "text-rose-600"
                          : "text-blue-600"
                      }
                    />
                    <Stat label="최근 거래량" value={formatVol(data.basics.latestVolume)} />
                    <Stat label="평균 거래량" value={formatVol(data.basics.avgVolume)} />
                  </div>
                </div>

                {/* 수급 동향 — 해외 종목엔 표시하지 않음 */}
                {data.meta.supplyMode !== "unsupported" && (
                <div className="rounded-[24px] border border-slate-200 bg-white p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-[13px] font-black text-slate-900">
                      수급 동향
                      <span className="ml-1.5 text-[11px] font-bold text-slate-400">
                        순매수 / 순매도
                      </span>
                    </p>
                    {data.meta.supplyMode === "mock" && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-400">
                        데모
                      </span>
                    )}
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {data.supply.rows.map((r, i) => {
                      const buy = r.netQty >= 0;
                      return (
                        <div key={i} className="rounded-2xl bg-slate-50 px-3 py-3 text-center">
                          <p className="text-[12px] font-semibold text-slate-500">
                            {r.label}
                          </p>
                          <p
                            className={`mt-1 text-[14px] font-black ${
                              buy ? "text-rose-600" : "text-blue-600"
                            }`}
                          >
                            {formatNet(r.netQty)}
                          </p>
                          <p className="mt-0.5 text-[10px] font-bold text-slate-400">
                            {buy ? "순매수" : "순매도"}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                  {data.supply.date && (
                    <p className="mt-2 text-[11px] font-semibold text-slate-400">
                      {data.supply.date} 기준
                    </p>
                  )}
                </div>
                )}

                {/* 투자 참고 지표 */}
                <div className="rounded-[24px] border border-slate-200 bg-white p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-[13px] font-black text-slate-900">
                      투자 참고 지표
                    </p>
                    {data.meta.indicatorsMode === "mock" && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-400">
                        데모
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-[11px] font-semibold text-slate-400">
                    양호·보통·주의는 업종(섹터) 평균 대비 참고 평가예요.
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    {data.indicators.map((ind, i) => (
                      <div key={i} className="rounded-2xl bg-slate-50 px-4 py-3">
                        <div className="flex items-center justify-between gap-2">
                          <GlossaryText
                            text={ind.label}
                            className="text-[12px] font-semibold text-slate-500"
                          />
                          {ind.tone && (
                            <span
                              className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${TONE[ind.tone].cls}`}
                            >
                              {TONE[ind.tone].label}
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-[15px] font-black text-slate-900">
                          {ind.value}
                        </p>
                        {ind.context && (
                          <p className="mt-0.5 text-[11px] font-bold leading-snug text-slate-500">
                            {ind.context}
                          </p>
                        )}
                        {ind.hint && (
                          <p className="mt-0.5 text-[11px] font-medium leading-snug text-slate-400">
                            {ind.hint}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 재무 */}
            {tab === "financial" && (
              <div className="mt-4 overflow-hidden rounded-[24px] border border-slate-200 bg-white">
                <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
                  <span className="text-[13px] font-black text-slate-900">
                    핵심 재무
                  </span>
                  <span className="text-[12px] font-bold text-slate-400">
                    {data.financials.year ? `${data.financials.year} 연간` : "—"}
                    {data.meta.dartMode === "live" ? " · DART" : " · 데모"}
                  </span>
                </div>
                {data.financials.rows.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-3 px-5 py-3.5 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-slate-100"
                  >
                    <GlossaryText
                      text={r.label}
                      className="text-[14px] font-semibold text-slate-500"
                    />
                    <span className="text-right text-[14px] font-black text-slate-900">
                      {formatKRW(r.value)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            </>
            )}

            {data.meta.warnings.length > 0 && (
              <details className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 text-[12px] font-semibold text-slate-400">
                <summary className="cursor-pointer list-none">
                  데이터 안내 {data.meta.warnings.length}건
                </summary>
                <ul className="mt-2.5 space-y-1.5">
                  {data.meta.warnings.map((w, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="mt-[8px] h-1.5 w-1.5 shrink-0 rounded-full bg-slate-200" />
                      <span className="leading-6">{w}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}

            <p className="px-1 pt-5 text-[11px] font-medium leading-relaxed text-slate-400">
              재무 데이터 출처: DART(전자공시시스템). 본 정보는 투자 참고용이며 특정
              종목 매수·매도 권유가 아닙니다.
            </p>
          </>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="rounded-2xl bg-slate-50 px-4 py-3">
      <p className="text-[12px] font-semibold text-slate-500">{label}</p>
      <p className={`mt-0.5 text-[15px] font-black text-slate-900 ${valueClass ?? ""}`}>
        {value}
      </p>
    </div>
  );
}
