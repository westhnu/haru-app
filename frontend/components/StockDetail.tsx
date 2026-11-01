"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Info, BarChart3, BookOpen } from "lucide-react";
import type { IndicatorTone, StockResponse } from "@/lib/stocktypes";
import PriceChart from "@/components/PriceChart";
import GlossaryText from "@/components/GlossaryText";
import { PageHeader } from "@/components/layout/PageHeader";
import { PageShell } from "@/components/layout/PageShell";
import { HARU_BACKEND_ENABLED } from "@/lib/featureFlags";
import WorkbookPanel from "@/components/WorkbookPanel";

const TONE: Record<IndicatorTone, { cls: string; label: string }> = {
  good: { cls: "bg-emerald-50 text-emerald-700", label: "양호" },
  neutral: { cls: "bg-surface-muted text-fg-muted", label: "보통" },
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
  const [data, setData] = useState<StockResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState<(typeof RANGES)[number]["key"]>("3m");

  const [tab, setTab] = useState<StockTab>(initialTab);

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
    <PageShell className="pt-0">
        {/* 상단 — sticky PageHeader (Phase F2). 뒤로는 종목 목록(플래그 off면 홈) */}
        <div className="sticky top-0 z-30 -mx-4 bg-surface/85 px-4 pt-md backdrop-blur-md md:-mx-6 md:px-6">
          <PageHeader
            title={data?.profile.name ?? name ?? code}
            subtitle={
              <span className="tabular-nums">
                {data?.profile.code ?? code}
                {data?.profile.market ? ` · ${data.profile.market}` : ""}
              </span>
            }
            back={HARU_BACKEND_ENABLED ? { href: "/workbook", label: "종목" } : { href: "/", label: "홈" }}
          />
        </div>
        {/* 본문: page-space 간격이 내부 mt-* 를 덮지 않도록 한 덩어리로 둔다 */}
        <div>
        {loading || !data ? (
          <div className="mt-4 space-y-5 animate-pulse-soft">
            {/* 헤더 — 종목명 + 가격 */}
            <div className="space-y-2">
              <div className="h-7 w-40 rounded bg-surface-muted" />
              <div className="h-3 w-20 rounded bg-surface-muted" />
              <div className="mt-3 h-9 w-48 rounded bg-surface-muted" />
            </div>
            {/* 차트 카드 */}
            <div className="rounded-[24px] border border-border bg-surface p-4">
              <div className="h-[180px] rounded-2xl bg-surface-muted" />
              <div className="mt-3 h-9 rounded-full bg-surface-muted" />
            </div>
            {/* 탭 */}
            <div className="h-10 rounded-full bg-surface-muted" />
            {/* 시세 요약 (2-col grid) */}
            <div className="rounded-[24px] border border-border bg-surface p-5">
              <div className="h-3 w-24 rounded bg-surface-muted" />
              <div className="mt-3 grid grid-cols-2 gap-2">
                {[0, 1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-14 rounded-2xl bg-surface-muted"
                  />
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {/* 헤더 */}
            <div>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-[2rem] font-black tabular-nums text-fg">
                  {data.profile.price !== null
                    ? formatPrice(data.profile.price, data.profile.currency)
                    : "—"}
                </span>
                {data.profile.changePct !== null && (
                  <span className={`text-base font-black tabular-nums ${priceColor}`}>
                    {up ? "+" : ""}
                    {data.profile.changePct.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>

            {/* 해외 종목 안내 배너 */}
            {data.meta.priceMode === "unsupported" && (
              <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
                <p className="font-black">해외 종목은 라이브 시세 미지원</p>
                <p className="mt-1 leading-6">
                  한국투자증권(KIS) Open API 조회 대상이 아니에요. 시세·재무 차트는 표시하지 않아요. 브리핑 본문의 텍스트 정보를 참고해 주세요.
                </p>
              </div>
            )}

            {/* 해외/비지원 종목은 차트·시세요약·수급·지표·재무 섹션을 모두 숨김 */}
            {data.meta.priceMode !== "unsupported" && (
            <>
            {/* 차트 */}
            <div className="mt-5 rounded-[24px] border border-border bg-surface p-4 shadow-soft">
              <PriceChart
                prices={sliced}
                up={up}
                currency={data.profile.currency}
              />
              <div className="mt-3 flex items-center gap-1.5 rounded-full bg-surface-muted p-1">
                {RANGES.map((r) => (
                  <button
                    key={r.key}
                    onClick={() => setRange(r.key)}
                    className={`flex-1 rounded-full px-3 py-1.5 text-xs font-bold transition ${
                      range === r.key
                        ? "bg-surface text-fg shadow-sm"
                        : "text-fg-muted"
                    }`}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
              {data.meta.priceMode === "mock" && (
                <p className="mt-2.5 text-center text-xs font-medium text-fg-subtle">
                  데모 시세 · 실시간 시세 연동 예정
                </p>
              )}
            </div>

            {/* 탭 — 재무는 DART 라이브가 있을 때만 노출 (해외 종목엔 unsupported). 워크북은 항상 노출 */}
            <div className="mt-4 flex items-center gap-1.5 rounded-full bg-surface-muted p-1">
                <button
                  onClick={() => setTab("info")}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-4 py-2 text-sm font-bold transition ${
                    tab === "info"
                      ? "bg-surface text-fg shadow-sm"
                      : "text-fg-muted"
                  }`}
                >
                  <Info className="h-4 w-4" />
                  종목정보
                </button>
                {data.meta.dartMode !== "unsupported" && (
                  <button
                    onClick={() => setTab("financial")}
                    className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-4 py-2 text-sm font-bold transition ${
                      tab === "financial"
                        ? "bg-surface text-fg shadow-sm"
                        : "text-fg-muted"
                    }`}
                  >
                    <BarChart3 className="h-4 w-4" />
                    재무제표
                  </button>
                )}
                <button
                  onClick={() => setTab("workbook")}
                  className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-4 py-2 text-sm font-bold transition ${
                    tab === "workbook"
                      ? "bg-surface text-fg shadow-sm"
                      : "text-fg-muted"
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
                <div className="rounded-[24px] border border-border bg-surface p-5">
                  <p className="text-sm font-black text-fg">
                    시세 요약
                    <span className="ml-1.5 text-xs font-bold text-fg-subtle">
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
                <div className="rounded-[24px] border border-border bg-surface p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-black text-fg">
                      수급 동향
                      <span className="ml-1.5 text-xs font-bold text-fg-subtle">
                        순매수 / 순매도
                      </span>
                    </p>
                    {data.meta.supplyMode === "mock" && (
                      <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs font-bold text-fg-subtle">
                        데모
                      </span>
                    )}
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {data.supply.rows.map((r, i) => {
                      const buy = r.netQty >= 0;
                      return (
                        <div key={i} className="rounded-2xl bg-surface-muted px-3 py-3 text-center">
                          <p className="text-xs font-semibold text-fg-muted">
                            {r.label}
                          </p>
                          <p
                            className={`mt-1 text-sm font-black tabular-nums ${
                              buy ? "text-rose-600" : "text-blue-600"
                            }`}
                          >
                            {formatNet(r.netQty)}
                          </p>
                          <p className="mt-0.5 text-xs font-bold text-fg-subtle">
                            {buy ? "순매수" : "순매도"}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                  {data.supply.date && (
                    <p className="mt-2 text-xs font-semibold text-fg-subtle">
                      {data.supply.date} 기준
                    </p>
                  )}
                </div>
                )}

                {/* 투자 참고 지표 */}
                <div className="rounded-[24px] border border-border bg-surface p-5">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-black text-fg">
                      투자 참고 지표
                    </p>
                    {data.meta.indicatorsMode === "mock" && (
                      <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs font-bold text-fg-subtle">
                        데모
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs font-semibold text-fg-subtle">
                    양호·보통·주의는 업종(섹터) 평균 대비 참고 평가예요.
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-2">
                    {data.indicators.map((ind, i) => (
                      <div key={i} className="rounded-2xl bg-surface-muted px-4 py-3">
                        <div className="flex items-center justify-between gap-2">
                          <GlossaryText
                            text={ind.label}
                            className="text-xs font-semibold text-fg-muted"
                            showAiDetail
                          />
                          {ind.tone && (
                            <span
                              className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-bold ${TONE[ind.tone].cls}`}
                            >
                              {TONE[ind.tone].label}
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-base font-black tabular-nums text-fg">
                          {ind.value}
                        </p>
                        {ind.context && (
                          <p className="mt-0.5 text-xs font-bold leading-snug text-fg-muted">
                            {ind.context}
                          </p>
                        )}
                        {ind.hint && (
                          <p className="mt-0.5 text-xs font-medium leading-snug text-fg-subtle">
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
              <div className="mt-4 overflow-hidden rounded-[24px] border border-border bg-surface">
                <div className="flex items-center justify-between border-b border-border-subtle px-5 py-3">
                  <span className="text-sm font-black text-fg">
                    핵심 재무
                  </span>
                  <span className="text-xs font-bold text-fg-subtle">
                    {data.financials.year ? `${data.financials.year} 연간` : "—"}
                    {data.meta.dartMode === "live" ? " · DART" : " · 데모"}
                  </span>
                </div>
                {data.financials.rows.map((r, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between gap-3 px-5 py-3.5 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-border-subtle"
                  >
                    <GlossaryText
                      text={r.label}
                      className="text-sm font-semibold text-fg-muted"
                      showAiDetail
                    />
                    <span className="text-right text-sm font-black text-fg">
                      {formatKRW(r.value)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            </>
            )}

            {data.meta.warnings.length > 0 && (
              <details className="mt-4 rounded-2xl border border-border bg-surface p-4 text-xs font-semibold text-fg-subtle">
                <summary className="cursor-pointer list-none">
                  데이터 안내 {data.meta.warnings.length}건
                </summary>
                <ul className="mt-2.5 space-y-1.5">
                  {data.meta.warnings.map((w, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="mt-[8px] h-1.5 w-1.5 shrink-0 rounded-full bg-border" />
                      <span className="leading-6">{w}</span>
                    </li>
                  ))}
                </ul>
              </details>
            )}

            <p className="px-1 pt-5 text-xs font-medium leading-relaxed text-fg-subtle">
              재무 데이터 출처: DART(전자공시시스템). 투자 참고용이며 특정 종목의 매수·매도 권유가 아니에요.
            </p>
          </>
        )}
        </div>
    </PageShell>
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
    <div className="rounded-2xl bg-surface-muted px-4 py-3">
      <p className="text-xs font-semibold text-fg-muted">{label}</p>
      <p className={`mt-0.5 text-base font-black tabular-nums text-fg ${valueClass ?? ""}`}>
        {value}
      </p>
    </div>
  );
}
