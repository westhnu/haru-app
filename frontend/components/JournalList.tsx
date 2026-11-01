"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronRight, Loader2, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
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


type Load =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; entries: JournalEntry[]; positions: VirtualPosition[] };

type Group = { code: string; name: string; entries: JournalEntry[] };

const card =
  "rounded-[24px] border border-border bg-surface";

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
        <Loader2 className="h-5 w-5 animate-spin text-fg-subtle" />
        <span className="text-sm font-semibold text-fg-subtle">
          저널을 불러오는 중이에요
        </span>
      </div>
    );
  }

  if (load.kind === "error") {
    return (
      <div className={`${card} p-5`}>
        <p className="text-sm font-semibold text-danger">{load.message}</p>
        <button
          type="button"
          onClick={() => {
            setLoad({ kind: "loading" });
            refresh();
          }}
          className="mt-3 rounded-full bg-surface-muted px-4 py-2 text-xs font-bold text-fg-muted"
        >
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 px-1">
        <span className="rounded-full bg-warning/10 px-2 py-0.5 text-xs font-bold text-warning">
          가상 기록
        </span>
        <span className="text-xs font-semibold text-fg-subtle">
          실제 주문·거래가 아니에요.
        </span>
      </div>

      <section className={card} aria-label="가상 포지션">
        <p className="border-b border-border-subtle px-5 py-3 text-sm font-black text-fg">
          가상 포지션
          <span className="ml-1.5 text-xs font-semibold text-fg-subtle">
            &quot;매수 결정&quot; 기록의 가상 수량·단가 합산
          </span>
        </p>
        {load.positions.length === 0 ? (
          <p className="px-5 py-5 text-sm font-semibold text-fg-subtle">
            가상 포지션이 없어요. &quot;매수 결정&quot;을 기록할 때 가상 수량·단가를 적으면 여기에 모여요.
          </p>
        ) : (
          <ul>
            {load.positions.map((p) => (
              <li
                key={p.stock_code}
                className="flex items-center justify-between gap-3 px-5 py-3 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-border-subtle"
              >
                <span className="text-sm font-bold text-fg">
                  {p.stock_name}
                  <span className="ml-1.5 text-xs font-bold tabular-nums text-fg-subtle">
                    {p.stock_code}
                  </span>
                </span>
                <span className="text-right font-mono text-lg font-semibold tabular-nums text-fg">
                  {p.quantity.toLocaleString()}주 · 평균 {p.avg_price.toLocaleString()}원
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="border-t border-border-subtle px-5 py-2.5 text-xs font-medium text-fg-subtle">
          시세 연동 전이라 현재가·손익은 표시하지 않아요.
        </p>
      </section>

      {groups.length === 0 ? (
        <p className={`${card} px-5 py-10 text-center text-sm font-semibold text-fg-subtle`}>
          저널에 기록이 없어요. 종목에서 결정을 남기면 여기에 쌓여요.
        </p>
      ) : (
        groups.map((g) => (
          <section key={g.code} className={card}>
            <Link
              href={`/stock/${encodeURIComponent(g.code)}?name=${encodeURIComponent(g.name)}&tab=workbook`}
              className="flex items-center justify-between border-b border-border-subtle px-5 py-3 transition hover:bg-surface-muted"
            >
              <span className="text-sm font-black text-fg">
                {g.name}
                <span className="ml-1.5 text-xs font-bold tabular-nums text-fg-subtle">
                  {g.code}
                </span>
              </span>
              <ChevronRight className="h-4 w-4 text-fg-subtle" />
            </Link>
            <ul>
              {g.entries.map((e) => (
                <li
                  key={e.id}
                  className="px-5 py-3.5 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-border-subtle"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {/* 결정은 본인 기록 — 색으로 좋고 나쁨을 암시하지 않게 중립 outline (원칙 1) */}
                      <Badge variant="outline">{DECISION_LABELS[e.decision]} (본인 기록)</Badge>
                      <span className="text-xs font-semibold text-fg-subtle">
                        {formatDateTime(e.created_at)}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => onDelete(e)}
                      disabled={busy === e.id}
                      aria-label="기록 삭제"
                      className="rounded-full p-1 text-fg-subtle transition hover:bg-border-subtle hover:text-danger disabled:opacity-50"
                    >
                      {busy === e.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                  <p className="mt-1.5 whitespace-pre-wrap break-words text-sm leading-relaxed text-fg">
                    {e.reasoning}
                  </p>
                  {(e.virtual_quantity || e.virtual_price) ? (
                    <p className="mt-1 text-xs font-semibold tabular-nums text-fg-subtle">
                      가상 {e.virtual_quantity ? `${e.virtual_quantity.toLocaleString()}주` : ""}
                      {e.virtual_quantity && e.virtual_price ? " · " : ""}
                      {e.virtual_price ? `${e.virtual_price.toLocaleString()}원` : ""}
                    </p>
                  ) : null}
                  {(e.checklist_id || e.workbook_id) && (
                    <p className="mt-1 text-xs font-medium text-fg-subtle">
                      연결: {[e.workbook_id && "워크북", e.checklist_id && "체크리스트"].filter(Boolean).join(" · ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))
      )}

      {error && <p className="px-1 text-xs font-semibold text-danger">{error}</p>}
    </div>
  );
}
