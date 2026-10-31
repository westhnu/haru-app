"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, NotebookPen, Plus, Trash2 } from "lucide-react";
import ChecklistSection from "@/components/ChecklistSection";
import JournalEntryDialog from "@/components/JournalEntryDialog";
import WorkbookEditDialog from "@/components/WorkbookEditDialog";
import {
  BLOCK_TYPE_LABELS,
  createWorkbook,
  deleteBlock,
  formatDateTime,
  listWorkbooks,
  memoText,
  type Workbook,
} from "@/lib/workbook";

type Load =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; workbooks: Workbook[] };

/** StockDetail "워크북" 탭. 종목별 워크북의 memo 블록, 체크리스트, 결정 기록 진입점을 모은다.
 *  흐름: 메모로 정리 → 체크리스트로 점검 → 본인 결정 기록(저널).
 *  한 종목에 워크북이 여러 개면 첫 번째를 기본 선택한다. */
export default function WorkbookPanel({
  stockCode,
  stockName,
}: {
  stockCode: string;
  stockName: string;
}) {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null); // "create" | 삭제 중인 block id
  const [actionError, setActionError] = useState<string | null>(null);
  const [checklistId, setChecklistId] = useState<string | null>(null);
  const [journalOpen, setJournalOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const workbooks = await listWorkbooks(stockCode);
      setLoad({ kind: "ready", workbooks });
      setSelectedId((prev) =>
        prev && workbooks.some((w) => w.id === prev) ? prev : (workbooks[0]?.id ?? null)
      );
    } catch (e) {
      setLoad({ kind: "error", message: e instanceof Error ? e.message : "불러오기 실패" });
    }
  }, [stockCode]);

  useEffect(() => {
    setLoad({ kind: "loading" });
    refresh();
  }, [refresh]);

  const onCreate = useCallback(async () => {
    setBusy("create");
    setActionError(null);
    try {
      const wb = await createWorkbook(stockCode, stockName);
      setSelectedId(wb.id);
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "워크북 생성 실패");
    } finally {
      setBusy(null);
    }
  }, [stockCode, stockName, refresh]);

  const onDelete = useCallback(
    async (workbookId: string, blockId: string) => {
      if (!window.confirm("이 블록을 삭제할까요? 되돌릴 수 없어요.")) return;
      setBusy(blockId);
      setActionError(null);
      try {
        await deleteBlock(workbookId, blockId);
        await refresh();
      } catch (e) {
        setActionError(e instanceof Error ? e.message : "삭제 실패");
      } finally {
        setBusy(null);
      }
    },
    [refresh]
  );

  const card =
    "rounded-[24px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5";

  let workbookArea: JSX.Element | null = null;
  if (load.kind === "loading") {
    workbookArea = (
      <div className={`${card} flex items-center justify-center gap-2 py-10`}>
        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
        <span className="text-[13px] font-semibold text-slate-400 dark:text-slate-500">
          워크북을 불러오는 중...
        </span>
      </div>
    );
  } else if (load.kind === "error") {
    workbookArea = (
      <div className={card}>
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

  const workbooks = load.kind === "ready" ? load.workbooks : [];
  const wb = workbooks.find((w) => w.id === selectedId) ?? null;

  return (
    <div className="mt-4 space-y-3">
      {workbookArea}
      {load.kind === "ready" && workbooks.length > 1 && (
        <div className="flex gap-1.5 overflow-x-auto">
          {workbooks.map((w) => (
            <button
              key={w.id}
              type="button"
              onClick={() => setSelectedId(w.id)}
              className={`shrink-0 rounded-full px-3 py-1.5 text-[12px] font-bold ${
                w.id === selectedId
                  ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                  : "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
              }`}
            >
              {w.title}
            </button>
          ))}
        </div>
      )}

      {load.kind === "ready" && (
      <div className={card}>
        {!wb ? (
          <div className="py-6 text-center">
            <p className="text-[14px] font-bold text-slate-700 dark:text-slate-200">
              아직 분석이 없습니다.
            </p>
            <p className="mt-1 text-[12px] font-semibold text-slate-400 dark:text-slate-500">
              워크북을 만들고 블록을 추가해 시작하세요.
            </p>
            <button
              type="button"
              onClick={onCreate}
              disabled={busy === "create"}
              className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-slate-900 dark:bg-slate-100 px-4 py-2 text-[13px] font-bold text-white dark:text-slate-900 disabled:opacity-50"
            >
              {busy === "create" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              워크북 만들기
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-[15px] font-black text-slate-900 dark:text-slate-100">
                  {wb.title}
                </p>
                <p className="mt-0.5 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                  블록 {wb.blocks.length}개 · 수정 {formatDateTime(wb.updated_at)}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setDialogOpen(true)}
                className="inline-flex shrink-0 items-center gap-1 rounded-full bg-slate-900 dark:bg-slate-100 px-3 py-1.5 text-[12px] font-bold text-white dark:text-slate-900"
              >
                <Plus className="h-3.5 w-3.5" />
                블록 추가
              </button>
            </div>

            {wb.blocks.length === 0 ? (
              <p className="mt-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 px-4 py-6 text-center text-[13px] font-semibold text-slate-400 dark:text-slate-500">
                아직 블록이 없어요. &quot;블록 추가&quot;로 메모를 남겨 보세요.
              </p>
            ) : (
              <ul className="mt-4 space-y-2">
                {wb.blocks.map((b) => {
                  const text = memoText(b);
                  return (
                    <li
                      key={b.id}
                      className="rounded-2xl bg-slate-50 dark:bg-slate-800/50 px-4 py-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500">
                          {BLOCK_TYPE_LABELS[b.block_type] ?? b.block_type} ·{" "}
                          {formatDateTime(b.created_at)}
                        </span>
                        <button
                          type="button"
                          onClick={() => onDelete(wb.id, b.id)}
                          disabled={busy === b.id}
                          aria-label="블록 삭제"
                          className="rounded-full p-1 text-slate-400 transition hover:bg-slate-200 hover:text-red-600 dark:hover:bg-slate-700 disabled:opacity-50"
                        >
                          {busy === b.id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="h-3.5 w-3.5" />
                          )}
                        </button>
                      </div>
                      <p className="mt-1 whitespace-pre-wrap break-words text-[14px] leading-relaxed text-slate-800 dark:text-slate-200">
                        {text ?? "이 블록 종류는 아직 화면에서 지원하지 않아요."}
                      </p>
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}

        {actionError && (
          <p className="mt-3 text-[12px] font-semibold text-red-600 dark:text-red-400">{actionError}</p>
        )}
      </div>
      )}

      <ChecklistSection
        stockCode={stockCode}
        stockName={stockName}
        onChecklistChange={setChecklistId}
      />

      <button
        type="button"
        onClick={() => setJournalOpen(true)}
        className="flex w-full items-center justify-center gap-2 rounded-[20px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 py-3.5 text-[14px] font-black text-slate-900 dark:text-slate-100 transition hover:bg-slate-50 dark:hover:bg-slate-800/60"
      >
        <NotebookPen className="h-4 w-4" />
        결정 기록하기
      </button>

      <p className="px-1 text-[11px] font-medium leading-relaxed text-slate-400 dark:text-slate-500">
        워크북은 본인의 생각을 정리하는 공간이에요. Haru는 종목을 추천하지 않으며, 최종 결정은
        사용자에게 있습니다.
      </p>

      <JournalEntryDialog
        open={journalOpen}
        onClose={() => setJournalOpen(false)}
        stockCode={stockCode}
        stockName={stockName}
        defaultChecklistId={checklistId}
        defaultWorkbookId={wb?.id ?? null}
      />

      {wb && (
        <WorkbookEditDialog
          workbookId={wb.id}
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          onSaved={refresh}
        />
      )}
    </div>
  );
}
