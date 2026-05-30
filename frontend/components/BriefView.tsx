"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  RefreshCw,
  Sparkles,
  Sunrise,
  Sunset,
  ExternalLink,
  Globe,
  Landmark,
  CalendarDays,
} from "lucide-react";
import type { ReactNode } from "react";
import type { BriefResponse, BriefType, Region } from "@/lib/types";
import { BRIEF_META, DISCLAIMER } from "@/lib/types";
import SectionCard from "@/components/SectionCard";
import VerifyBadge from "@/components/VerifyBadge";

function RegionHeader({ region }: { region: Region }) {
  const Icon = region === "해외" ? Globe : Landmark;
  return (
    <div className="flex items-center gap-2 pt-3 first:pt-1">
      <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-slate-900 text-white">
        <Icon className="h-4 w-4" />
      </div>
      <span className="text-[14px] font-black text-slate-900">
        {region} 시장
      </span>
      <span className="h-px flex-1 bg-slate-200" />
    </div>
  );
}

// 종류별 시그니처 액센트 (아침=warm, 저녁=cool)
const ACCENT: Record<
  BriefType,
  { tile: string; label: string; glow: string }
> = {
  morning: {
    tile: "bg-gradient-to-br from-amber-400 to-orange-500",
    label: "text-amber-300",
    glow: "radial-gradient(120% 70% at 50% -10%, rgba(251,146,60,0.16), transparent 70%)",
  },
  evening: {
    tile: "bg-gradient-to-br from-indigo-400 to-violet-500",
    label: "text-indigo-300",
    glow: "radial-gradient(120% 70% at 50% -10%, rgba(129,140,248,0.18), transparent 70%)",
  },
};

function timeAgo(iso: string): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "방금 전";
  if (m < 60) return `${m}분 전`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}시간 전`;
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Seoul",
  }).format(new Date(iso));
}

export default function BriefView({ type }: { type: BriefType }) {
  const meta = BRIEF_META[type];
  const accent = ACCENT[type];
  const HeroIcon = type === "morning" ? Sunrise : Sunset;
  const router = useRouter();
  const [data, setData] = useState<BriefResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 브라우저 히스토리가 있으면 뒤로가기, 없으면 홈
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
      const res = await fetch(`/api/brief?type=${type}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setData((await res.json()) as BriefResponse);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [type]);

  // 운영에선 EventBridge Scheduler 가 매일 08:00·17:00 KST 에 Lambda 를 호출해
  // 브리핑을 갱신한다. UI 의 버튼은 저장된 최신본을 다시 가져오는 역할만 한다.
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

  const isEmpty = data?.empty || !data?.brief;

  return (
    <div className="min-h-svh bg-slate-50">
      <div className="relative mx-auto min-h-svh w-full max-w-[480px] overflow-hidden bg-white px-5 pb-12">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 z-0 h-72"
          style={{ background: accent.glow }}
        />

        <div className="relative z-10">
          {/* 상단 바 */}
          <div className="flex items-center justify-between py-5">
            <button
              type="button"
              onClick={goBack}
              className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3.5 py-2 text-[13px] font-bold text-slate-600 transition hover:bg-slate-200"
            >
              <ArrowLeft className="h-4 w-4" />
              뒤로
            </button>
            <button
              onClick={generate}
              disabled={generating}
              className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3.5 py-2 text-[13px] font-bold text-slate-600 transition hover:bg-slate-200 disabled:opacity-40"
            >
              <RefreshCw
                className={`h-4 w-4 ${generating ? "animate-spin" : ""}`}
              />
              {generating ? "갱신 중" : "새로고침"}
            </button>
          </div>

          {/* 타이틀 */}
          <div className="pt-3">
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-soft ${accent.tile}`}
            >
              <HeroIcon className="h-6 w-6" />
            </div>
            <h1 className="mt-4 text-[2rem] font-black leading-tight tracking-tight text-slate-950">
              {meta.label}
            </h1>
            <p className="mt-2 text-[15px] font-medium leading-[1.75] text-slate-600">
              {meta.subtitle}
            </p>

            {data && data.meta.forDate && (
              <div className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-bold tabular-nums text-slate-600">
                <CalendarDays className="h-4 w-4 text-slate-400" />
                {data.meta.forDate}
              </div>
            )}

            {data && !isEmpty && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1.5 text-[12px] font-bold ${
                    data.meta.mode === "live"
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {data.meta.mode === "live"
                    ? data.meta.mainModel
                    : "데모 데이터"}
                </span>
                <VerifyBadge
                  verify={data.verify}
                  verifyModel={data.meta.verifyModel}
                />
                {data.meta.generatedAt && (
                  <span className="text-[12px] font-semibold text-slate-400">
                    업데이트 {timeAgo(data.meta.generatedAt)}
                  </span>
                )}
              </div>
            )}

            {/* 휴장 안내 배너 */}
            {data && data.meta.marketNote && (
              <div className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-[13px] font-bold text-amber-700">
                {data.meta.marketNote} 직전 거래일·해외 동향 위주로 참고하세요.
              </div>
            )}
          </div>

          {/* 로딩 */}
          {loading && (
            <div className="mt-8 space-y-3">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="animate-pulse-soft rounded-[24px] border border-slate-200 bg-white p-5"
                >
                  <div className="mb-3 h-10 w-10 rounded-2xl bg-slate-100" />
                  <div className="h-14 rounded-xl bg-slate-50" />
                </div>
              ))}
            </div>
          )}

          {/* 빈 상태 */}
          {!loading && isEmpty && (
            <div className="mt-8 rounded-[28px] border border-slate-200 bg-white p-7 text-center shadow-card">
              <div
                className={`mx-auto flex h-14 w-14 items-center justify-center rounded-2xl text-white ${accent.tile}`}
              >
                <Sparkles className="h-7 w-7" />
              </div>
              <p className="mt-5 text-[17px] font-black text-slate-950">
                아직 생성된 브리핑이 없어요
              </p>
              <p className="mt-2 text-[14px] font-medium leading-[1.75] text-slate-600">
                매일 {meta.time}에 자동 생성됩니다.
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

          {/* 에러 */}
          {error && !loading && (
            <div className="mt-6 rounded-2xl bg-slate-100 p-4 text-[13px] font-semibold text-slate-700">
              {error}
            </div>
          )}

          {/* 본문 */}
          {data && !loading && !isEmpty && data.brief && (
            <div className="mt-8 space-y-3">
              {/* 오늘 한 줄 */}
              <section className="animate-fade-up rounded-[28px] bg-gradient-to-br from-slate-950 to-slate-900 p-6 shadow-card">
                <p className="inline-flex items-center gap-1.5 text-[12px] font-bold tracking-wide text-white/60">
                  <Sparkles className={`h-3.5 w-3.5 ${accent.label}`} />
                  오늘 한 줄
                </p>
                <p className="mt-3 text-[17.5px] font-bold leading-[1.7] text-white">
                  {data.brief.oneLine}
                </p>
              </section>

              {(() => {
                const regions = meta.regions;
                const items: ReactNode[] = [];
                let last: Region | null = null;
                data.brief.sections.forEach((s, i) => {
                  const region = regions[i] ?? "국내";
                  if (region !== last) {
                    items.push(
                      <RegionHeader key={`h${i}`} region={region} />
                    );
                    last = region;
                  }
                  items.push(<SectionCard key={i} index={i} section={s} />);
                });
                return items;
              })()}

              {data.brief.dataGaps && data.brief.dataGaps.length > 0 && (
                <section className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 p-5 text-[13px] font-semibold text-slate-500">
                  <p className="mb-2 text-slate-600">
                    정보가 없어 채우지 못한 항목
                  </p>
                  <ul className="space-y-1.5">
                    {data.brief.dataGaps.map((g, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="mt-[8px] h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300" />
                        <span className="leading-6">{g}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {data.sources.length > 0 && (
                <details className="rounded-2xl border border-slate-200 bg-white p-5 text-[13px]">
                  <summary className="cursor-pointer list-none font-black text-slate-900">
                    근거 뉴스 {data.sources.length}건
                  </summary>
                  <div className="mt-3 space-y-2">
                    {data.sources.map((s, i) => (
                      <a
                        key={i}
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3 transition hover:bg-slate-100"
                      >
                        <span className="min-w-0 flex-1 truncate font-semibold text-slate-700">
                          {s.title}
                        </span>
                        <ExternalLink className="h-4 w-4 shrink-0 text-slate-400" />
                      </a>
                    ))}
                  </div>
                </details>
              )}

              {data.meta.warnings.length > 0 && (
                <details className="rounded-2xl border border-slate-200 bg-white p-5 text-[12px] font-semibold text-slate-400">
                  <summary className="cursor-pointer list-none">
                    동작 진단 {data.meta.warnings.length}건
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

              <p className="px-1 pt-3 text-[11px] font-medium leading-relaxed text-slate-400">
                {DISCLAIMER}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
