"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ListChecks, Loader2, Plus, Sparkles, Trash2 } from "lucide-react";
import AiEvaluationDialog from "@/components/AiEvaluationDialog";
import { STATUS_SOLID } from "@/components/ui/Button";
import {
  PRINCIPLE_MAX_LENGTH,
  REASONING_MAX_LENGTH,
  STATUS_LABELS,
  STATUS_ORDER,
  addItem,
  createChecklist,
  deleteItem,
  listChecklists,
  scoreOf,
  supportsAiEvaluation,
  updateItem,
  type Checklist,
  type ChecklistItem,
  type ItemStatus,
} from "@/lib/checklist";


type Load =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; checklist: Checklist | null };

/** 워크북 탭 안의 체크리스트. 사용자가 원칙별 상태를 직접 고르고 근거를 적는다.
 *  상태는 누르는 즉시 PATCH, 근거는 입력칸을 벗어날 때 저장한다. */
export default function ChecklistSection({
  stockCode,
  stockName,
  onChecklistChange,
}: {
  stockCode: string;
  stockName: string;
  /** 현재 체크리스트 id를 부모(결정 기록 연결용)에 알린다. */
  onChecklistChange?: (checklistId: string | null) => void;
}) {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newPrinciple, setNewPrinciple] = useState("");
  const [evalTarget, setEvalTarget] = useState<ChecklistItem | null>(null);
  const aiEnabled = supportsAiEvaluation(stockCode);

  const refresh = useCallback(async () => {
    try {
      const [first] = await listChecklists(stockCode);
      setLoad({ kind: "ready", checklist: first ?? null });
    } catch (e) {
      setLoad({ kind: "error", message: e instanceof Error ? e.message : "불러오기 실패" });
    }
  }, [stockCode]);

  useEffect(() => {
    setLoad({ kind: "loading" });
    refresh();
  }, [refresh]);

  const checklist = load.kind === "ready" ? load.checklist : null;
  useEffect(() => {
    onChecklistChange?.(checklist?.id ?? null);
  }, [checklist?.id, onChecklistChange]);

  // 서버가 돌려준 항목으로 로컬 상태를 바꾼다 (전체 재조회 없이 점수 즉시 반영).
  const replaceItem = useCallback((updated: ChecklistItem) => {
    setLoad((prev) =>
      prev.kind === "ready" && prev.checklist
        ? {
            kind: "ready",
            checklist: {
              ...prev.checklist,
              items: prev.checklist.items.map((i) => (i.id === updated.id ? updated : i)),
            },
          }
        : prev
    );
  }, []);

  const run = useCallback(async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "요청 실패");
    } finally {
      setBusy(null);
    }
  }, []);

  const onCreate = () =>
    run("create", async () => {
      await createChecklist(stockCode, stockName);
      await refresh();
    });

  const onStatus = (cl: Checklist, item: ChecklistItem, status: ItemStatus) => {
    if (item.status === status) return;
    run(item.id, async () => replaceItem(await updateItem(cl.id, item.id, { status })));
  };

  const onReasoning = (cl: Checklist, item: ChecklistItem, reasoning: string) => {
    const next = reasoning.trim();
    if (next === item.reasoning) return;
    run(item.id, async () => replaceItem(await updateItem(cl.id, item.id, { reasoning: next })));
  };

  const onDelete = (cl: Checklist, item: ChecklistItem) => {
    if (!window.confirm(`"${item.principle}" 원칙을 삭제할까요?`)) return;
    run(item.id, async () => {
      await deleteItem(cl.id, item.id);
      await refresh();
    });
  };

  // AI 평가 "판정 적용": 상태와 근거를 함께 PATCH. 실패하면 다이얼로그가 에러를 보여준다.
  const applyEvaluation = useCallback(
    async (status: ItemStatus, reasoning: string) => {
      if (!checklist || !evalTarget) return;
      replaceItem(await updateItem(checklist.id, evalTarget.id, { status, reasoning }));
      setEvalTarget(null);
    },
    [checklist, evalTarget, replaceItem]
  );

  const onAdd = (e: FormEvent, cl: Checklist) => {
    e.preventDefault();
    const principle = newPrinciple.trim();
    if (!principle) return;
    run("add", async () => {
      await addItem(cl.id, principle);
      setNewPrinciple("");
      await refresh();
    });
  };

  const card =
    "rounded-[24px] border border-border bg-surface p-5";

  return (
    <section className={card} aria-label="체크리스트">
      <div className="flex items-center gap-2">
        <ListChecks className="h-4 w-4 text-fg-muted" />
        <p className="text-base font-black text-fg">체크리스트</p>
      </div>

      {load.kind === "loading" && (
        <div className="flex items-center justify-center gap-2 py-8">
          <Loader2 className="h-4 w-4 animate-spin text-fg-subtle" />
          <span className="text-sm font-semibold text-fg-subtle">
            불러오는 중이에요
          </span>
        </div>
      )}

      {load.kind === "error" && (
        <div className="mt-3">
          <p className="text-sm font-semibold text-danger">{load.message}</p>
          <button
            type="button"
            onClick={() => {
              setLoad({ kind: "loading" });
              refresh();
            }}
            className="mt-2 rounded-full bg-surface-muted px-4 py-2 text-xs font-bold text-fg-muted"
          >
            다시 시도
          </button>
        </div>
      )}

      {load.kind === "ready" && !checklist && (
        <div className="py-6 text-center">
          <p className="text-sm font-semibold text-fg-muted">
            체크리스트가 비어 있어요. 본인의 투자 원칙으로 이 종목을 점검해 보세요.
          </p>
          <button
            type="button"
            onClick={onCreate}
            disabled={busy === "create"}
            className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-fg px-4 py-2 text-sm font-bold text-surface disabled:opacity-50"
          >
            {busy === "create" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            체크리스트 만들기
          </button>
        </div>
      )}

      {checklist && (
        <>
          <ScoreLine items={checklist.items} />

          {checklist.items.length === 0 ? (
            <p className="mt-3 rounded-2xl bg-surface-muted px-4 py-5 text-center text-sm font-semibold text-fg-subtle">
              원칙이 없어요. 아래에서 첫 원칙을 추가해 보세요.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {checklist.items.map((item) => (
                <li key={item.id} className="rounded-2xl bg-surface-muted px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="break-words text-sm font-bold leading-snug text-fg">
                      {item.principle}
                    </p>
                    <button
                      type="button"
                      onClick={() => onDelete(checklist, item)}
                      disabled={busy === item.id}
                      aria-label="원칙 삭제"
                      className="shrink-0 rounded-full p-1 text-fg-subtle transition hover:bg-border hover:text-danger disabled:opacity-50"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div
                    className="mt-2 flex flex-wrap items-center gap-1.5"
                    role="radiogroup"
                    aria-label={`${item.principle} 판단`}
                  >
                    {STATUS_ORDER.map((s) => (
                      <button
                        key={s}
                        type="button"
                        role="radio"
                        aria-checked={item.status === s}
                        onClick={() => onStatus(checklist, item, s)}
                        disabled={busy === item.id}
                        className={`rounded-full px-3 py-1 text-xs font-bold transition disabled:opacity-60 ${
                          item.status === s
                            ? STATUS_SOLID[s]
                            : "bg-surface text-fg-muted hover:bg-border-subtle"
                        }`}
                      >
                        {STATUS_LABELS[s]}
                      </button>
                    ))}
                    {busy === item.id && <Loader2 className="h-3.5 w-3.5 animate-spin text-fg-subtle" />}
                    {aiEnabled && (
                      <button
                        type="button"
                        onClick={() => setEvalTarget(item)}
                        disabled={busy === item.id}
                        className="ml-auto inline-flex items-center gap-1 rounded-full bg-brand/10 px-2.5 py-1 text-xs font-bold text-brand transition hover:bg-brand/15 disabled:opacity-60"
                      >
                        <Sparkles className="h-3.5 w-3.5" />
                        AI 평가
                      </button>
                    )}
                  </div>
                  <input
                    // 서버 값이 바뀌면(삭제·재조회) 입력칸도 새로 그린다.
                    key={`${item.id}:${item.reasoning}`}
                    defaultValue={item.reasoning}
                    onBlur={(e) => onReasoning(checklist, item, e.target.value)}
                    maxLength={REASONING_MAX_LENGTH}
                    placeholder="판단 근거 (예: 사업보고서 2025 확인)"
                    className="mt-2 w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-2 focus:ring-brand"
                  />
                </li>
              ))}
            </ul>
          )}

          <form onSubmit={(e) => onAdd(e, checklist)} className="mt-3 flex gap-2">
            <input
              value={newPrinciple}
              onChange={(e) => setNewPrinciple(e.target.value)}
              maxLength={PRINCIPLE_MAX_LENGTH}
              disabled={busy === "add"}
              placeholder="원칙 추가 (예: 영업이익이 3년 연속 늘었는가?)"
              className="min-w-0 flex-1 rounded-full border border-border bg-surface px-4 py-2 text-sm text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-2 focus:ring-brand"
            />
            <button
              type="submit"
              disabled={busy === "add" || !newPrinciple.trim()}
              className="inline-flex shrink-0 items-center gap-1 rounded-full bg-fg px-3 py-2 text-xs font-bold text-surface disabled:opacity-40"
            >
              {busy === "add" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              원칙 추가
            </button>
          </form>
        </>
      )}

      {error && <p className="mt-3 text-xs font-semibold text-danger">{error}</p>}

      {checklist && evalTarget && (
        <AiEvaluationDialog
          open
          onClose={() => setEvalTarget(null)}
          onApply={applyEvaluation}
          checklistId={checklist.id}
          itemId={evalTarget.id}
          principle={evalTarget.principle}
        />
      )}
    </section>
  );
}

function ScoreLine({ items }: { items: ChecklistItem[] }) {
  const { satisfied, total, pct } = scoreOf(items);
  const uncertain = items.filter((i) => i.status === "uncertain").length;
  return (
    <div className="mt-3 rounded-2xl bg-surface-muted px-4 py-3">
      <p className="font-mono text-lg font-semibold tabular-nums text-fg">
        {total}개 중 {satisfied}개 충족 <span className="text-fg-subtle">({pct}%)</span>
      </p>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-border">
        <div className="h-full rounded-full bg-success" style={{ width: `${pct}%` }} />
      </div>
      {uncertain > 0 && (
        <p className="mt-1.5 text-xs font-semibold text-fg-subtle">
          판단 보류 {uncertain}개. 직접 확인한 뒤 상태를 골라 주세요.
        </p>
      )}
    </div>
  );
}
