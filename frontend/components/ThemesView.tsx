"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, RefreshCw, Network, ChevronRight } from "lucide-react";
import type { Confidence, ThemeResponse, ThemeStock } from "@/lib/thememap";
import { nameToCode } from "@/lib/corpcodes";
import GlossaryText from "@/components/GlossaryText";
import { usePullToRefresh } from "@/lib/usePullToRefresh";

type Resp = ThemeResponse & { empty?: boolean };

const CONF: Record<Confidence, { cls: string; label: string }> = {
  high: { cls: "bg-emerald-50 text-emerald-700", label: "신뢰도 높음" },
  medium: { cls: "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400", label: "신뢰도 보통" },
  low: { cls: "bg-amber-50 text-amber-700", label: "신뢰도 낮음" },
};

// 테마명 → 일관된 색 (해시) — 같은 테마는 항상 같은 색.
const PALETTE = [
  "bg-sky-500",
  "bg-emerald-500",
  "bg-violet-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-indigo-500",
] as const;
function paletteOf(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  return PALETTE[Math.abs(h) % PALETTE.length];
}

function StockChip({ s }: { s: ThemeStock }) {
  // 진짜 종목으로 매핑되는 경우만 링크. 메타 항목 (예: '대형주', '美 CPI')은 정보 카드.
  const krCode = s.code || nameToCode(s.name);
  const usTicker =
    s.symbol && /^[A-Z]{1,5}$/.test(s.symbol) ? s.symbol : null;
  const target = krCode || usTicker;
  const baseCls =
    "flex items-center justify-between gap-3 rounded-2xl px-4 py-3";
  const inner = (
    <>
      <div className="flex min-w-0 flex-1 items-baseline gap-1.5">
        <span
          title={s.name}
          className="truncate text-[14px] font-black text-slate-900 dark:text-slate-100"
        >
          {s.name}
        </span>
        {s.symbol && (
          <span className="shrink-0 text-[11px] font-bold text-slate-400 dark:text-slate-500">
            {s.symbol}
          </span>
        )}
      </div>
      <div className="flex max-w-[52%] shrink-0 items-center gap-1.5">
        {s.reason && (
          <span
            title={s.reason}
            className="truncate text-right text-[12px] font-semibold text-slate-500 dark:text-slate-400"
          >
            {s.reason}
          </span>
        )}
        {target && (
          <ChevronRight className="h-4 w-4 shrink-0 text-slate-300 dark:text-slate-600" />
        )}
      </div>
    </>
  );
  return target ? (
    <Link
      href={`/stock/${encodeURIComponent(target)}?name=${encodeURIComponent(s.name)}`}
      className={`${baseCls} bg-slate-50 dark:bg-slate-900 transition hover:bg-slate-100 dark:hover:bg-slate-800`}
    >
      {inner}
    </Link>
  ) : (
    <div className={`${baseCls} bg-slate-50 dark:bg-slate-900/60 cursor-default`}>{inner}</div>
  );
}

export default function ThemesView() {
  const router = useRouter();
  const [data, setData] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const goBack = useCallback(() => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push("/");
    }
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/themes", { cache: "no-store" });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setData((await res.json()) as Resp);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  // 운영에선 EventBridge Scheduler → Lambda 가 매일 테마 매핑을 갱신한다.
  // UI 의 버튼은 저장된 최신본을 다시 가져오는 역할만 한다.
  const generate = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      await load();
    } finally {
      setGenerating(false);
    }
  }, [load]);

  useEffect(() => {
    load();
  }, [load]);

  // 모바일 풀-투-리프레시
  const { progress: pullProgress, refreshing: pulling } = usePullToRefresh(load);

  const isEmpty = data?.empty || (data?.items?.length ?? 0) === 0;

  return (
    <div className="min-h-svh bg-slate-50 dark:bg-slate-950">
      {(pullProgress > 0 || pulling) && (
        <div
          aria-hidden
          className="pointer-events-none fixed inset-x-0 top-0 z-50 flex justify-center"
          style={{
            transform: `translateY(${Math.min(50, pullProgress * 60)}px)`,
            opacity: Math.min(1, pullProgress),
          }}
        >
          <div className="mt-2 flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-lg dark:bg-slate-800">
            <RefreshCw
              className={`h-4 w-4 text-slate-700 dark:text-slate-300 ${pulling ? "animate-spin" : ""}`}
              style={!pulling ? { transform: `rotate(${pullProgress * 360}deg)` } : undefined}
            />
          </div>
        </div>
      )}
      <div className="mx-auto min-h-svh w-full max-w-[480px] bg-white dark:bg-slate-900 px-5 pb-24">
        {/* 상단 바 */}
        <div className="flex items-center justify-between py-5">
          <button
            type="button"
            onClick={goBack}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 dark:bg-slate-800 px-3.5 py-2 text-[13px] font-bold text-slate-600 dark:text-slate-400 transition hover:bg-slate-200"
          >
            <ArrowLeft className="h-4 w-4" />
            뒤로
          </button>
          <button
            onClick={generate}
            disabled={generating}
            className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 dark:bg-slate-800 px-3.5 py-2 text-[13px] font-bold text-slate-600 dark:text-slate-400 transition hover:bg-slate-200 disabled:opacity-40"
          >
            <RefreshCw className={`h-4 w-4 ${generating ? "animate-spin" : ""}`} />
            {generating ? "분석 중" : "다시 분석"}
          </button>
        </div>

        {/* 타이틀 */}
        <div className="pt-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-500 text-white shadow-soft">
            <Network className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-[2rem] font-black leading-tight tracking-tight text-slate-950 dark:text-white">
            이슈·테마 매핑
          </h1>
          <p className="mt-2 text-[15px] font-semibold leading-7 text-slate-500 dark:text-slate-400">
            오늘의 이슈가 어떤 테마·종목으로 번지는지 연결해 드려요.
          </p>
          {data && !isEmpty && data.meta.forDate && (
            <p className="mt-3 text-[13px] font-bold text-slate-400 dark:text-slate-500">
              {data.meta.forDate} 기준
            </p>
          )}
        </div>

        {/* 로딩 */}
        {loading && (
          <div className="mt-8 space-y-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="animate-pulse-soft rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                {/* 테마명 + 신뢰도 뱃지 */}
                <div className="flex items-center gap-2">
                  <div className="h-5 w-40 rounded bg-slate-100 dark:bg-slate-800" />
                  <div className="h-4 w-16 rounded-full bg-slate-100 dark:bg-slate-800" />
                </div>
                {/* 요약 */}
                <div className="mt-3 space-y-2">
                  <div className="h-3 rounded bg-slate-100 dark:bg-slate-800" />
                  <div className="h-3 w-4/5 rounded bg-slate-100 dark:bg-slate-800" />
                </div>
                {/* 종목 칩 2개 */}
                <div className="mt-4 space-y-2">
                  <div className="h-11 rounded-2xl bg-slate-50 dark:bg-slate-900" />
                  <div className="h-11 rounded-2xl bg-slate-50 dark:bg-slate-900" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 빈 상태 */}
        {!loading && isEmpty && (
          <div className="mt-8 rounded-[28px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-7 text-center shadow-card">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-500 text-white">
              <Network className="h-7 w-7" />
            </div>
            <p className="mt-5 text-[17px] font-black text-slate-950 dark:text-white">
              아직 분석된 테마가 없어요
            </p>
            <p className="mt-2 text-[14px] font-semibold leading-6 text-slate-500 dark:text-slate-400">
              매일 08:00·17:00 KST에 자동 분석됩니다.
              <br />
              잠시 후 새로고침 해주세요.
            </p>
            <button
              onClick={generate}
              disabled={generating}
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 py-4 text-base font-bold text-white transition hover:bg-slate-800 disabled:opacity-50"
            >
              {generating ? "갱신 중…" : "새로고침"}
            </button>
          </div>
        )}

        {error && !loading && (
          <div className="mt-6 rounded-2xl bg-slate-100 dark:bg-slate-800 p-4 text-[13px] font-semibold text-slate-700 dark:text-slate-300">
            {error}
          </div>
        )}

        {/* 테마 카드 */}
        {data && !loading && !isEmpty && (
          <div className="mt-8 space-y-3">
            {data.items.map((item, i) => {
              const conf = CONF[item.confidence] ?? CONF.medium;
              const palette = paletteOf(item.theme);
              return (
                <section
                  key={i}
                  className="animate-fade-up relative overflow-hidden rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-soft"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  {/* 좌측 컬러 strip — 같은 테마는 항상 같은 색 */}
                  <span
                    aria-hidden
                    className={`absolute inset-y-0 left-0 w-[3px] ${palette}`}
                  />
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        aria-hidden
                        className={`h-2 w-2 shrink-0 rounded-full ${palette}`}
                      />
                      <h2 className="text-[17px] font-black tracking-tight text-slate-950 dark:text-white">
                        {item.theme}
                      </h2>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold ${conf.cls}`}
                    >
                      {conf.label}
                    </span>
                  </div>

                  <GlossaryText
                    text={item.summary}
                    className="mt-2 block text-[15px] font-medium leading-[1.8] text-slate-700 dark:text-slate-300"
                  />

                  {item.drivers && item.drivers.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {item.drivers.map((d, k) => (
                        <span
                          key={k}
                          className="rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-1 text-[11px] font-bold text-slate-600 dark:text-slate-400"
                        >
                          {d}
                        </span>
                      ))}
                    </div>
                  )}

                  {item.stocks && item.stocks.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {item.stocks.map((s, k) => (
                        <StockChip key={k} s={s} />
                      ))}
                    </div>
                  )}
                </section>
              );
            })}

            {data.sources.length > 0 && (
              <details className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 text-[13px]">
                <summary className="cursor-pointer list-none font-black text-slate-900 dark:text-slate-100">
                  근거 이슈 {data.sources.length}건
                </summary>
                <div className="mt-3 space-y-2">
                  {data.sources.map((s, i) => (
                    <a
                      key={i}
                      href={s.url}
                      target="_blank"
                      rel="noreferrer"
                      className="block truncate rounded-2xl bg-slate-50 dark:bg-slate-900 px-4 py-3 font-semibold text-slate-700 dark:text-slate-300 transition hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      {s.title}
                    </a>
                  ))}
                </div>
              </details>
            )}

            <p className="px-1 pt-3 text-[11px] font-medium leading-relaxed text-slate-400 dark:text-slate-500">
              이슈→테마 매핑은 AI(zero-shot)가 공개 이슈를 정리한 참고 자료이며, 특정
              종목 매수·매도 권유가 아닙니다.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
