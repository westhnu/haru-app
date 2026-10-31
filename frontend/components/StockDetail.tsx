"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, Info, BarChart3, BookOpen } from "lucide-react";
import type { IndicatorTone, StockResponse } from "@/lib/stocktypes";
import PriceChart from "@/components/PriceChart";
import GlossaryText from "@/components/GlossaryText";
import WorkbookPanel from "@/components/WorkbookPanel";

const TONE: Record<IndicatorTone, { cls: string; label: string }> = {
  good: { cls: "bg-emerald-50 text-emerald-700", label: "양호" },
  neutral: { cls: "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400", label: "보통" },
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
  const n = Math.abs(v);
  const JO = 1_0000_0000_0000;
  const EOK = 1_0000_0000;
  const sign = neg ? "-" : "";
  // 조 단위면 소숫점 1자리로 압축 ('1,748조 373억' → '1,748.0조')
  // 100조 이상은 정수 — 더 간결.
  if (n >= JO) {
    const joVal = n / JO;
    const precision = joVal >= 100 ? 0 : 1;
    return `${sign}${joVal.toLocaleString(undefined, { maximumFractionDigits: precision })}조`;
  }
  // 억 단위 — 1억 이상이면 억 표기 (소숫점 1자리)
  if (n >= EOK) {
    const eokVal = n / EOK;
    const precision = eokVal >= 100 ? 0 : 1;
    return `${sign}${eokVal.toLocaleString(undefined, { maximumFractionDigits: precision })}억`;
  }
  // 그 외 원 단위
  return `${sign}${Math.round(n).toLocaleString()}원`;
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

export type StockTab = "info" | "financial" | "workbook";

export default function StockDetail({
  code,
  name,
  initialTab = "info",
}: {
  code: string;
  name?: string;
  initialTab?: StockTab;
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
  const [tab, setTab] = useState<StockTab>(initialTab);
  // 스크롤 시 종목명이 화면에서 사라지면 mini 종목명을 sticky bar 에 표시
  const titleRef = useRef<HTMLHeadingElement | null>(null);
  const [showMini, setShowMini] = useState(false);
  useEffect(() => {
    const el = titleRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => setShowMini(!entry.isIntersecting),
      { threshold: 0, rootMargin: "-56px 0px 0px 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [data]);

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
    <div className="min-h-svh bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto min-h-svh w-full max-w-[480px] bg-white dark:bg-slate-900 px-5 pb-24">
        {/* 상단 바 — sticky. 스크롤 시 mini 종목명 fade-in */}
        <div className="sticky top-0 z-30 -mx-5 px-5 backdrop-blur-md bg-white/85 dark:bg-slate-900/85">
        <div className="flex items-center justify-between gap-3 py-4">
          <button
            type="button"
            onClick={goBack}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 px-3.5 py-2 text-[13px] font-bold text-slate-600 dark:text-slate-400 transition hover:bg-slate-200"
          >
            <ArrowLeft className="h-4 w-4" />
            뒤로
          </button>
          {/* mini 종목명 */}
          <p
            aria-hidden={!showMini}
            className={`pointer-events-none flex-1 truncate text-center text-[14px] font-black text-slate-950 dark:text-white transition-opacity duration-200 ${
              showMini ? "opacity-100" : "opacity-0"
            }`}
          >
            {data?.profile.name ?? ""}
          </p>
          {/* placeholder 우측 spacer (좌우 균형) */}
          <span className="w-[64px] shrink-0" aria-hidden />
        </div>
        </div>

        {loading || !data ? (
          <div className="mt-4 space-y-5 animate-pulse-soft">
            {/* 헤더 — 종목명 + 가격 */}
            <div className="space-y-2">
              <div className="h-7 w-40 rounded bg-slate-100 dark:bg-slate-800" />
              <div className="h-3 w-20 rounded bg-slate-100 dark:bg-slate-800" />
              <div className="mt-3 h-9 w-48 rounded bg-slate-100 dark:bg-slate-800" />
            </div>
            {/* 차트 카드 */}
            <div className="rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
              <div className="h-[180px] rounded-2xl bg-slate-50 dark:bg-slate-900" />
              <div className="mt-3 h-9 rounded-full bg-slate-100 dark:bg-slate-800" />
            </div>
            {/* 탭 */}
            <div className="h-10 rounded-full bg-slate-100 dark:bg-slate-800" />
            {/* 시세 요약 (2-col grid) */}
            <div className="rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
              <div className="h-3 w-24 rounded bg-slate-100 dark:bg-slate-800" />
              <div className="mt-3 grid grid-cols-2 gap-2">
                {[0, 1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-14 rounded-2xl bg-slate-50 dark:bg-slate-900"
                  />
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* 헤더 */}
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1
                  ref={titleRef}
                  className="text-[1.7rem] font-black tracking-tight text-slate-950 dark:text-white"
                >
                  {data.profile.name}
                </h1>
                {data.profile.market && (
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-bold text-slate-500 dark:text-slate-400">
                    {data.profile.market}
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-[13px] font-semibold text-slate-400 dark:text-slate-500">
                {data.profile.code}
              </p>
              <div className="mt-3 flex flex-wrap items-baseline gap-2">
                <span className="text-[2rem] font-black tabular-nums text-slate-950 dark:text-white">
                  {data.profile.price !== null
                    ? formatPrice(data.profile.price, data.profile.currency)
                    : "—"}
                </span>
                {data.profile.changePct !== null && (
                  <span className={`text-[15px] font-black tabular-nums ${priceColor}`}>
                    {up ? "+" : ""}
                    {data.profile.changePct.toFixed(2)}%
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
            <div className="mt-5 rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-soft">
              <PriceChart
                prices={sliced}
                up={up}
                currency={data.profile.currency}
              />
              <div className="mt-3 flex items-center gap-1.5 rounded-full bg-slate-100 dark:bg-slate-800 p-1">
                {RANGES.map((r) => (
                  <button
                    key={r.key}
                    onClick={() => setRange(r.key)}
                    className={`flex-1 rounded-full px-3 py-1.5 text-[12px] font-bold transition ${
                      range === r.key
                        ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                        : "text-slate-500 dark:text-slate-400"
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
              {data.meta.priceMode === "mock" && (
                <p className="mt-2.5 text-center text-[11px] font-medium text-slate-400 dark:text-slate-500">
                  데모 시세 · 실시간 시세 연동 예정
                </p>
              )}
            </div>

            {/* 탭 — 재무는 DART 라이브가 있을 때만 노출 (해외 종목엔 unsupported). 워크북은 항상 노출 */}
            <div className="mt-4 flex items-center gap-1.5 rounded-full bg-slate-100 dark:bg-slate-800 p-1">
                <button
                  onClick={() => setTab("info")}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-bold transition ${
                    tab === "info"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                      : "text-slate-500 dark:text-slate-400"
                  }`}
                >
                  <Info className="h-4 w-4" />
                  종목정보
                </button>
                {data.meta.dartMode !== "unsupported" && (
                  <button
                    onClick={() => setTab("financial")}
                    className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-bold transition ${
                      tab === "financial"
                        ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                        : "text-slate-500 dark:text-slate-400"
                    }`}
                  >
                    <BarChart3 className="h-4 w-4" />
                    재무제표
                  </button>
                )}
                <button
                  onClick={() => setTab("workbook")}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-bold transition ${
                    tab === "workbook"
                      ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                      : "text-slate-500 dark:text-slate-400"
                  }`}
                >
                  <BookOpen className="h-4 w-4" />
                  워크북
                </button>
              </div>

            {/* 종목정보 */}
            {tab === "info" && (
              <div className="mt-4 space-y-3">
                {/* 시세 요약 */}
                <div className="rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                  <p className="text-[13px] font-black text-slate-900 dark:text-slate-100">
                    시세 요약
                    <span className="ml-1.5 text-[11px] font-bold text-slate-400 dark:text-slate-500">
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
                <div className="rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-[13px] font-black text-slate-900 dark:text-slate-100">
                      수급 동향
                      <span className="ml-1.5 text-[11px] font-bold text-slate-400 dark:text-slate-500">
                        순매수 / 순매도
                      </span>
                    </p>
                    {data.meta.supplyMode === "mock" && (
                      <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-400 dark:text-slate-500">
                        데모
                      </span>
                    )}
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {data.supply.rows.map((r, i) => {
                      const buy = r.netQty >= 0;
                      return (
                        <div key={i} className="rounded-2xl bg-slate-50 dark:bg-slate-900 px-3 py-3 text-center">
                          <p className="text-[12px] font-semibold text-slate-500 dark:text-slate-400">
                            {r.label}
                          </p>
                          <p
                            className={`mt-1 text-[14px] font-black tabular-nums ${
                              buy ? "text-rose-600" : "text-blue-600"
                            }`}
                          >
                            {formatNet(r.netQty)}
                          </p>
                          <p className="mt-0.5 text-[10px] font-bold text-slate-400 dark:text-slate-500">
                            {buy ? "순매수" : "순매도"}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                  {data.supply.date && (
                    <p className="mt-2 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                      {data.supply.date} 기준
                    </p>
                  )}
                </div>
                )}

                {/* 투자 참고 지표 */}
                <div className="rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-[13px] font-black text-slate-900 dark:text-slate-100">
                      투자 참고 지표
                    </p>
                    {data.meta.indicatorsMode === "mock" && (
                      <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-400 dark:text-slate-500">
                        데모
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                    양호·보통·주의는 업종(섹터) 평균 대비 참고 평가예요.
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    {data.indicators.map((ind, i) => (
                      <div key={i} className="rounded-2xl bg-slate-50 dark:bg-slate-900 px-4 py-3">
                        <div className="flex items-center justify-between gap-2">
                          <GlossaryText
                            text={ind.label}
                            className="text-[12px] font-semibold text-slate-500 dark:text-slate-400"
                            showAiDetail
                          />
                          {ind.tone && (
                            <span
                              className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${TONE[ind.tone].cls}`}
                            >
                              {TONE[ind.tone].label}
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-[15px] font-black tabular-nums text-slate-900 dark:text-slate-100">
                          {ind.value}
                        </p>
                        {ind.context && (
                          <p className="mt-0.5 text-[11px] font-bold leading-snug text-slate-500 dark:text-slate-400">
                            {ind.context}
                          </p>
                        )}
                        {ind.hint && (
                          <p className="mt-0.5 text-[11px] font-medium leading-snug text-slate-400 dark:text-slate-500">
                            {ind.hint}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 워크북 */}
            {tab === "workbook" && (
              <WorkbookPanel stockCode={code} stockName={data.profile.name || name || code} />
            )}

            {/* 재무 */}
            {tab === "financial" && data.meta.dartMode !== "unsupported" && (
              <div className="mt-4 overflow-hidden rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-5 py-3">
                  <span className="text-[13px] font-black text-slate-900 dark:text-slate-100">
                    핵심 재무
                  </span>
                  <span className="text-[12px] font-bold text-slate-400 dark:text-slate-500">
                    {data.financials.year ? `${data.financials.year} 연간` : "—"}
                    {data.meta.dartMode === "live" ? " · DART" : " · 데모"}
                  </span>
                </div>
                {data.financials.rows.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-3 px-5 py-3.5 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-slate-100 dark:border-slate-800"
                  >
                    <GlossaryText
                      text={r.label}
                      className="text-[14px] font-semibold text-slate-500 dark:text-slate-400"
                      showAiDetail
                    />
                    <span className="text-right text-[14px] font-black text-slate-900 dark:text-slate-100">
                      {formatKRW(r.value)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            </>
            )}

            {data.meta.warnings.length > 0 && (
              <details className="mt-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 text-[12px] font-semibold text-slate-400 dark:text-slate-500">
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

            <p className="px-1 pt-5 text-[11px] font-medium leading-relaxed text-slate-400 dark:text-slate-500">
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
    <div className="rounded-2xl bg-slate-50 dark:bg-slate-900 px-4 py-3">
      <p className="text-[12px] font-semibold text-slate-500 dark:text-slate-400">{label}</p>
      <p className={`mt-0.5 text-[15px] font-black tabular-nums text-slate-900 dark:text-slate-100 ${valueClass ?? ""}`}>
        {value}
      </p>
    </div>
  );
}
