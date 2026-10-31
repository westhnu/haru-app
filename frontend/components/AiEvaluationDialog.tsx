"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ExternalLink, Loader2, Sparkles, X } from "lucide-react";
import {
  EVALUATION_SOURCE_LABELS,
  STATUS_LABELS,
  evaluateItem,
  type AiEvaluation,
  type ItemStatus,
} from "@/lib/checklist";

const STATUS_CHIP: Record<ItemStatus, string> = {
  satisfied: "bg-emerald-600 text-white dark:bg-emerald-500",
  unsatisfied: "bg-rose-600 text-white dark:bg-rose-500",
  uncertain: "bg-slate-700 text-white dark:bg-slate-300 dark:text-slate-900",
};

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; evaluation: AiEvaluation };

/** 원칙 하나의 AI 평가 바텀시트. 열릴 때 1회 평가를 요청하고(저장 안 함), 사용자가 "적용"을 눌러야 반영된다.
 *  TermDetailDialog 패턴: portal, ESC·배경 닫기, scroll lock, Strict Mode 중복 호출 방지(다음 tick 시작). */
export default function AiEvaluationDialog({
  open,
  onClose,
  onApply,
  checklistId,
  itemId,
  principle,
}: {
  open: boolean;
  onClose: () => void;
  /** 적용 성공 시 부모가 닫는다. 실패하면 에러를 던져 다이얼로그에 표시한다. */
  onApply: (status: ItemStatus, reasoning: string) => Promise<void>;
  checklistId: string;
  itemId: string;
  principle: string;
}) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleClose = useCallback(() => {
    if (applying) return;
    abortRef.current?.abort();
    onClose();
  }, [applying, onClose]);

  useEffect(() => {
    if (!open) {
      setState({ kind: "idle" });
      setApplyError(null);
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ kind: "loading" });
    // Strict Mode(dev)의 mount→cleanup→mount에서 첫 실행은 타이머 단계에서 취소된다.
    // abort만으로는 이미 프록시를 탄 요청의 서버 측 Bedrock 호출(과금)을 멈출 수 없다.
    const timer = window.setTimeout(async () => {
      try {
        const evaluation = await evaluateItem(checklistId, itemId, controller.signal);
        setState({ kind: "done", evaluation });
      } catch (e) {
        if (controller.signal.aborted) return;
        setState({ kind: "error", message: e instanceof Error ? e.message : "평가 실패" });
      }
    }, 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, checklistId, itemId]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, handleClose]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  async function apply(evaluation: AiEvaluation) {
    setApplying(true);
    setApplyError(null);
    try {
      await onApply(evaluation.suggested_status, evaluation.reasoning);
    } catch (e) {
      setApplyError(e instanceof Error ? e.message : "적용 실패");
    } finally {
      setApplying(false);
    }
  }

  if (!open || typeof document === "undefined") return null;

  const loading = state.kind === "loading";
  const evaluation = state.kind === "done" ? state.evaluation : null;

  return createPortal(
    <div
      role="dialog"
      aria-modal
      aria-label="AI 평가"
      className="fixed inset-0 z-50 flex items-end sm:items-start sm:justify-center sm:pt-24"
    >
      <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm" onClick={handleClose} />

      <div className="relative z-10 mx-auto flex max-h-[85svh] w-full max-w-[480px] flex-col overflow-hidden rounded-t-[28px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-card sm:rounded-[28px]">
        <div className="flex items-start justify-between gap-3 border-b border-slate-100 dark:border-slate-800 px-5 py-4">
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 text-[15px] font-black text-slate-900 dark:text-slate-100">
              <Sparkles className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              AI 평가
            </p>
            <p className="mt-0.5 break-words text-[12px] font-semibold text-slate-500 dark:text-slate-400">
              {principle}
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="닫기"
            className="rounded-full p-1.5 text-slate-400 transition hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-400"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4" aria-live="polite">
          {loading && (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600 dark:text-blue-400" />
              <p className="text-[13px] font-semibold text-slate-500 dark:text-slate-400">
                AI가 DART 재무 데이터를 분석 중... (최대 10초)
              </p>
            </div>
          )}

          {state.kind === "error" && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-[13px] text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
              {state.message}
            </div>
          )}

          {evaluation && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-3 py-1 text-[13px] font-black ${STATUS_CHIP[evaluation.suggested_status]}`}>
                  {STATUS_LABELS[evaluation.suggested_status]}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                    evaluation.evaluation_source === "bedrock"
                      ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                      : "bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                  }`}
                >
                  {EVALUATION_SOURCE_LABELS[evaluation.evaluation_source]}
                </span>
              </div>

              <p className="whitespace-pre-wrap break-words text-[14px] leading-relaxed text-slate-800 dark:text-slate-200">
                {evaluation.reasoning}
              </p>

              {evaluation.used_facts.length > 0 && (
                <div>
                  <p className="mb-1 text-[11px] font-bold text-slate-400 dark:text-slate-500">사용된 지표</p>
                  <div className="flex flex-wrap gap-1.5">
                    {evaluation.used_facts.map((f) => (
                      <span
                        key={f}
                        className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                      >
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <p className="mb-1 text-[11px] font-bold text-slate-400 dark:text-slate-500">
                  출처{evaluation.report_label ? ` · ${evaluation.report_label}` : ""}
                </p>
                <ul className="space-y-1">
                  {evaluation.sources.map((s) => (
                    <li key={s.url}>
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 break-all text-[12px] font-semibold text-blue-700 underline-offset-2 hover:underline dark:text-blue-300"
                      >
                        {s.name}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    </li>
                  ))}
                </ul>
              </div>

              {applyError && (
                <p className="text-[12px] font-semibold text-red-600 dark:text-red-400">{applyError}</p>
              )}
            </>
          )}

          <p className="rounded-xl bg-slate-50 px-3 py-2 text-[11px] font-semibold leading-relaxed text-slate-500 dark:bg-slate-800/50 dark:text-slate-400">
            AI 평가는 참고용입니다. 최종 판단은 본인에게 있습니다.
            {evaluation?.disclaimer ? ` ${evaluation.disclaimer}` : ""}
          </p>
        </div>

        <div className="flex gap-2 border-t border-slate-100 dark:border-slate-800 px-5 py-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={applying}
            className="flex-1 rounded-full bg-slate-100 dark:bg-slate-800 py-2.5 text-[13px] font-bold text-slate-600 dark:text-slate-300 transition hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-50"
          >
            {loading ? "취소" : "닫기"}
          </button>
          {evaluation && (
            <button
              type="button"
              onClick={() => apply(evaluation)}
              disabled={applying}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-full bg-slate-900 dark:bg-slate-100 py-2.5 text-[13px] font-bold text-white dark:text-slate-900 transition hover:bg-slate-800 disabled:opacity-40"
            >
              {applying && <Loader2 className="h-4 w-4 animate-spin" />}
              이 판정 적용
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
