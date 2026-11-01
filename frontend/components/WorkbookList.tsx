"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronRight, Loader2 } from "lucide-react";
import { formatDateTime, listWorkbooks, memoText, type Workbook } from "@/lib/workbook";

type Load =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; workbooks: Workbook[] };

type Group = { code: string; name: string; workbooks: Workbook[] };

/** 전체 워크북을 종목별로 묶어 보여준다. 최근 수정된 종목이 위로 온다. */
export default function WorkbookList() {
  const [load, setLoad] = useState<Load>({ kind: "loading" });

  const refresh = useCallback(async () => {
    setLoad({ kind: "loading" });
    try {
      setLoad({ kind: "ready", workbooks: await listWorkbooks() });
    } catch (e) {
      setLoad({ kind: "error", message: e instanceof Error ? e.message : "불러오기 실패" });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const groups = useMemo<Group[]>(() => {
    if (load.kind !== "ready") return [];
    const byCode = new Map<string, Group>();
    for (const wb of load.workbooks) {
      const g = byCode.get(wb.stock_code) ?? { code: wb.stock_code, name: wb.stock_name, workbooks: [] };
      g.workbooks.push(wb);
      byCode.set(wb.stock_code, g);
    }
    const latest = (g: Group) => Math.max(...g.workbooks.map((w) => Date.parse(w.updated_at) || 0));
    return [...byCode.values()].sort((a, b) => latest(b) - latest(a));
  }, [load]);

  if (load.kind === "loading") {
    return (
      <div className="flex items-center justify-center gap-2 py-16">
        <Loader2 className="h-5 w-5 animate-spin text-fg-subtle" />
        <span className="text-sm font-semibold text-fg-subtle">
          워크북을 불러오는 중이에요
        </span>
      </div>
    );
  }

  if (load.kind === "error") {
    return (
      <div className="rounded-[24px] border border-border bg-surface p-5">
        <p className="text-sm font-semibold text-danger">{load.message}</p>
        <button
          type="button"
          onClick={refresh}
          className="mt-3 rounded-full bg-surface-muted px-4 py-2 text-xs font-bold text-fg-muted"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <p className="rounded-[24px] border border-border bg-surface px-5 py-10 text-center text-sm font-semibold text-fg-subtle">
        만든 워크북이 없어요. 종목 상세의 &quot;워크북&quot; 탭에서 만들어 보세요.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {groups.map((g) => (
        <section
          key={g.code}
          className="rounded-[24px] border border-border bg-surface"
        >
          <p className="border-b border-border-subtle px-5 py-3 text-sm font-black text-fg">
            {g.name}
            <span className="ml-1.5 text-xs font-bold tabular-nums text-fg-subtle">
              {g.code}
            </span>
          </p>
          {g.workbooks.map((wb) => {
            const firstMemo = wb.blocks.map(memoText).find((t): t is string => t !== null);
            return (
              <Link
                key={wb.id}
                href={`/stock/${encodeURIComponent(wb.stock_code)}?name=${encodeURIComponent(wb.stock_name)}&tab=workbook`}
                className="flex items-center gap-3 px-5 py-3.5 transition hover:bg-surface-muted [&:not(:last-child)]:border-b [&:not(:last-child)]:border-border-subtle"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-bold text-fg">
                    {wb.title}
                  </p>
                  {firstMemo && (
                    <p className="mt-0.5 truncate text-xs font-medium text-fg-muted">
                      {firstMemo}
                    </p>
                  )}
                  <p className="mt-0.5 text-xs font-semibold text-fg-subtle">
                    블록 {wb.blocks.length}개 · 수정 {formatDateTime(wb.updated_at)}
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-fg-subtle" />
              </Link>
            );
          })}
        </section>
      ))}
    </div>
  );
}
