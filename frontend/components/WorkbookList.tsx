"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronRight, Loader2 } from "lucide-react";
import WorkbookTempBadge from "@/components/WorkbookTempBadge";
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
        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
        <span className="text-[13px] font-semibold text-slate-400 dark:text-slate-500">
          워크북을 불러오는 중...
        </span>
      </div>
    );
  }

  if (load.kind === "error") {
    return (
      <div className="rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
        <p className="text-[13px] font-semibold text-red-600 dark:text-red-400">{load.message}</p>
        <button
          type="button"
          onClick={refresh}
          className="mt-3 rounded-full bg-slate-100 dark:bg-slate-800 px-4 py-2 text-[12px] font-bold text-slate-600 dark:text-slate-300"
        >
          다시 시도
        </button>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <p className="rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-5 py-10 text-center text-[13px] font-semibold text-slate-400 dark:text-slate-500">
        아직 워크북이 없어요. 종목 상세의 &quot;워크북&quot; 탭에서 만들어 보세요.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 px-1">
        <WorkbookTempBadge />
        <span className="text-[11px] font-semibold text-slate-400 dark:text-slate-500">
          서버를 재시작하면 추가한 내용이 사라지고 샘플만 남아요.
        </span>
      </div>
      {groups.map((g) => (
        <section
          key={g.code}
          className="rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
        >
          <p className="border-b border-slate-100 dark:border-slate-800 px-5 py-3 text-[13px] font-black text-slate-900 dark:text-slate-100">
            {g.name}
            <span className="ml-1.5 text-[11px] font-bold tabular-nums text-slate-400 dark:text-slate-500">
              {g.code}
            </span>
          </p>
          {g.workbooks.map((wb) => {
            const firstMemo = wb.blocks.map(memoText).find((t): t is string => t !== null);
            return (
              <Link
                key={wb.id}
                href={`/stock/${encodeURIComponent(wb.stock_code)}?name=${encodeURIComponent(wb.stock_name)}&tab=workbook`}
                className="flex items-center gap-3 px-5 py-3.5 transition hover:bg-slate-50 dark:hover:bg-slate-800/50 [&:not(:last-child)]:border-b [&:not(:last-child)]:border-slate-100 dark:border-slate-800"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-bold text-slate-900 dark:text-slate-100">
                    {wb.title}
                  </p>
                  {firstMemo && (
                    <p className="mt-0.5 truncate text-[12px] font-medium text-slate-500 dark:text-slate-400">
                      {firstMemo}
                    </p>
                  )}
                  <p className="mt-0.5 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                    블록 {wb.blocks.length}개 · 수정 {formatDateTime(wb.updated_at)}
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-slate-300 dark:text-slate-600" />
              </Link>
            );
          })}
        </section>
      ))}
    </div>
  );
}
