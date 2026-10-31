"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronRight, Loader2, Trash2 } from "lucide-react";
import WorkbookTempBadge from "@/components/WorkbookTempBadge";
import { formatDateTime } from "@/lib/backendFetch";
import {
  DECISION_LABELS,
  deleteEntry,
  getVirtualPositions,
  listEntries,
  type Decision,
  type JournalEntry,
  type VirtualPosition,
} from "@/lib/journal";

const DECISION_BADGE: Record<Decision, string> = {
  buy: "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300",
  sell: "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  hold: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  watch: "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
};

type Load =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; entries: JournalEntry[]; positions: VirtualPosition[] };

type Group = { code: string; name: string; entries: JournalEntry[] };

const card =
  "rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900";

/** 투자 저널: 본인 결정 기록(종목별, 최신순)과 buy 기록 합산 가상 포지션. */
export default function JournalList() {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [entries, positions] = await Promise.all([listEntries(), getVirtualPositions()]);
      setLoad({ kind: "ready", entries, positions });
    } catch (e) {
      setLoad({ kind: "error", message: e instanceof Error ? e.message : "불러오기 실패" });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const groups = useMemo<Group[]>(() => {
    if (load.kind !== "ready") return [];
    const sorted = [...load.entries].sort(
      (a, b) => (Date.parse(b.created_at) || 0) - (Date.parse(a.created_at) || 0)
    );
    const byCode = new Map<string, Group>();
    for (const e of sorted) {
      const g = byCode.get(e.stock_code) ?? { code: e.stock_code, name: e.stock_name, entries: [] };
      g.entries.push(e);
      byCode.set(e.stock_code, g);
    }
    return [...byCode.values()]; // 최신 기록이 있는 종목이 위로 (정렬된 순서로 삽입)
  }, [load]);

  const onDelete = async (entry: JournalEntry) => {
    if (!window.confirm("이 기록을 삭제할까요? 되돌릴 수 없어요.")) return;
    setBusy(entry.id);
    setError(null);
    try {
      await deleteEntry(entry.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "삭제 실패");
    } finally {
      setBusy(null);
    }
  };

  if (load.kind === "loading") {
    return (
      <div className="flex items-center justify-center gap-2 py-16">
        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
        <span className="text-[13px] font-semibold text-slate-400 dark:text-slate-500">
          저널을 불러오는 중...
        </span>
      </div>
    );
  }

  if (load.kind === "error") {
    return (
      <div className={`${card} p-5`}>
        <p className="text-[13px] font-semibold text-red-600 dark:text-red-400">{load.message}</p>
        <button
          type="button"
          onClick={() => {
            setLoad({ kind: "loading" });
            refresh();
          }}
          className="mt-3 rounded-full bg-slate-100 dark:bg-slate-800 px-4 py-2 text-[12px] font-bold text-slate-600 dark:text-slate-300"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 px-1">
        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
          가상 기록
        </span>
        <WorkbookTempBadge />
        <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500">
          실제 주문·거래가 아니며, 서버를 재시작하면 샘플만 남아요.
        </span>
      </div>

      <section className={card} aria-label="가상 포지션">
        <p className="border-b border-slate-100 dark:border-slate-800 px-5 py-3 text-[13px] font-black text-slate-900 dark:text-slate-100">
          가상 포지션
          <span className="ml-1.5 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
            &quot;매수 결정&quot; 기록의 가상 수량·단가 합산
          </span>
        </p>
        {load.positions.length === 0 ? (
          <p className="px-5 py-5 text-[13px] font-semibold text-slate-400 dark:text-slate-500">
            아직 가상 포지션이 없어요. &quot;매수 결정&quot;을 기록할 때 가상 수량·단가를 적으면 여기에
            모입니다.
          </p>
        ) : (
          <ul>
            {load.positions.map((p) => (
              <li
                key={p.stock_code}
                className="flex items-center justify-between gap-3 px-5 py-3 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-slate-100 dark:border-slate-800"
              >
                <span className="text-[14px] font-bold text-slate-900 dark:text-slate-100">
                  {p.stock_name}
                  <span className="ml-1.5 text-[11px] font-bold tabular-nums text-slate-400 dark:text-slate-500">
                    {p.stock_code}
                  </span>
                </span>
                <span className="text-right text-[13px] font-bold tabular-nums text-slate-700 dark:text-slate-300">
                  {p.quantity.toLocaleString()}주 · 평균 {p.avg_price.toLocaleString()}원
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="border-t border-slate-100 dark:border-slate-800 px-5 py-2.5 text-[11px] font-medium text-slate-400 dark:text-slate-500">
          시세 연동 전이라 현재가·손익은 표시하지 않아요.
        </p>
      </section>

      {groups.length === 0 ? (
        <p className={`${card} px-5 py-10 text-center text-[13px] font-semibold text-slate-400 dark:text-slate-500`}>
          아직 기록이 없어요. 종목 상세의 &quot;워크북&quot; 탭에서 &quot;결정 기록하기&quot;를 눌러 보세요.
        </p>
      ) : (
        groups.map((g) => (
          <section key={g.code} className={card}>
            <Link
              href={`/stock/${encodeURIComponent(g.code)}?name=${encodeURIComponent(g.name)}&tab=workbook`}
              className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-5 py-3 transition hover:bg-slate-50 dark:hover:bg-slate-800/50"
            >
              <span className="text-[13px] font-black text-slate-900 dark:text-slate-100">
                {g.name}
                <span className="ml-1.5 text-[11px] font-bold tabular-nums text-slate-400 dark:text-slate-500">
                  {g.code}
                </span>
              </span>
              <ChevronRight className="h-4 w-4 text-slate-300 dark:text-slate-600" />
            </Link>
            <ul>
              {g.entries.map((e) => (
                <li
                  key={e.id}
                  className="px-5 py-3.5 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-slate-100 dark:border-slate-800"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${DECISION_BADGE[e.decision]}`}>
                        {DECISION_LABELS[e.decision]}
                      </span>
                      <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                        {formatDateTime(e.created_at)}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => onDelete(e)}
                      disabled={busy === e.id}
                      aria-label="기록 삭제"
                      className="rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-red-600 dark:hover:bg-slate-800 disabled:opacity-50"
                    >
                      {busy === e.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                  <p className="mt-1.5 whitespace-pre-wrap break-words text-[14px] leading-relaxed text-slate-800 dark:text-slate-200">
                    {e.reasoning}
                  </p>
                  {(e.virtual_quantity || e.virtual_price) ? (
                    <p className="mt-1 text-[11px] font-semibold tabular-nums text-slate-400 dark:text-slate-500">
                      가상 {e.virtual_quantity ? `${e.virtual_quantity.toLocaleString()}주` : ""}
                      {e.virtual_quantity && e.virtual_price ? " · " : ""}
                      {e.virtual_price ? `${e.virtual_price.toLocaleString()}원` : ""}
                    </p>
                  ) : null}
                  {(e.checklist_id || e.workbook_id) && (
                    <p className="mt-1 text-[11px] font-medium text-slate-400 dark:text-slate-500">
                      연결: {[e.workbook_id && "워크북", e.checklist_id && "체크리스트"].filter(Boolean).join(" · ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))
      )}

      {error && <p className="px-1 text-[12px] font-semibold text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
