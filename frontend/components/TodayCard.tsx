"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, BookOpen, ListChecks, NotebookPen, Search, type LucideIcon } from "lucide-react";
import SearchDialog from "@/components/SearchDialog";
import { HARU_BACKEND_ENABLED } from "@/lib/featureFlags";
import { fetchTodayCard, type NextAction, type TodayCard as TodayCardData } from "@/lib/today";

const ICONS: Record<NextAction, LucideIcon> = {
  empty: Search,
  checklist_incomplete: ListChecks,
  review_decision: NotebookPen,
  start_new: BookOpen,
};

type State = { kind: "loading" } | { kind: "hidden" } | { kind: "ready"; card: TodayCardData };

/** 홈 '오늘의 흐름'. 본인 기록(저널·워크북·체크리스트)에서 다음 행동 하나를 제안한다.
 *  플래그 off(운영)이거나 백엔드에 닿지 않으면 아무것도 그리지 않는다 — 홈이 깨지지 않게. */
export default function TodayCard() {
  const [state, setState] = useState<State>(
    HARU_BACKEND_ENABLED ? { kind: "loading" } : { kind: "hidden" }
  );
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    if (!HARU_BACKEND_ENABLED) return;
    const controller = new AbortController();
    fetchTodayCard(controller.signal)
      .then((card) => setState({ kind: "ready", card }))
      .catch(() => {
        if (!controller.signal.aborted) setState({ kind: "hidden" });
      });
    return () => controller.abort();
  }, []);

  if (state.kind === "hidden") return null;

  if (state.kind === "loading") {
    return (
      <section aria-label="오늘의 흐름" className="mt-6 animate-pulse-soft rounded-[28px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
        <div className="h-3 w-20 rounded-full bg-slate-200 dark:bg-slate-700" />
        <div className="mt-4 h-4 w-full rounded-full bg-slate-100 dark:bg-slate-800" />
        <div className="mt-2 h-4 w-3/4 rounded-full bg-slate-100 dark:bg-slate-800" />
        <div className="mt-5 h-9 w-36 rounded-full bg-slate-100 dark:bg-slate-800" />
      </section>
    );
  }

  const { card } = state;
  const Icon = ICONS[card.next_action];
  const satisfied = card.context.score_satisfied;
  const total = card.context.score_total;
  const ctaCls =
    "inline-flex items-center gap-1.5 rounded-full bg-slate-900 dark:bg-slate-100 px-4 py-2.5 text-[13px] font-bold text-white dark:text-slate-900 transition hover:bg-slate-800";

  return (
    <section
      aria-label="오늘의 흐름"
      className="mt-6 rounded-[28px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-soft"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-[12px] font-black tracking-wide text-slate-500 dark:text-slate-400">
          <Icon className="h-4 w-4" />
          오늘의 흐름
        </p>
        {typeof satisfied === "number" && typeof total === "number" && (
          <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold tabular-nums text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            체크리스트 {satisfied}/{total} 충족
          </span>
        )}
      </div>
      <p className="mt-3 text-[15px] font-bold leading-relaxed text-slate-900 dark:text-slate-100">
        {card.message}
      </p>
      <div className="mt-4">
        {card.next_action === "empty" || !card.cta_href ? (
          <button type="button" onClick={() => setSearchOpen(true)} className={ctaCls}>
            {card.cta_label}
            <ArrowRight className="h-4 w-4" />
          </button>
        ) : (
          <Link href={card.cta_href} className={ctaCls}>
            {card.cta_label}
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>
      <p className="mt-3 text-[11px] font-medium text-slate-400 dark:text-slate-500">
        {card.disclaimer}
      </p>
      {card.next_action === "empty" && (
        <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
      )}
    </section>
  );
}
