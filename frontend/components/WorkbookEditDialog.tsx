"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { Loader2, X } from "lucide-react";
import {
  BLOCK_TYPE_LABELS,
  MEMO_MAX_LENGTH,
  SUPPORTED_BLOCK_TYPES,
  addMemoBlock,
  type BlockType,
} from "@/lib/workbook";

const BLOCK_TYPES = Object.keys(BLOCK_TYPE_LABELS) as BlockType[];

/** 워크북 블록 추가 바텀시트 (TermDetailDialog 패턴: portal, ESC·배경 닫기, scroll lock).
 *  MVP는 memo만 추가할 수 있고 나머지 타입은 "준비 중"으로 비활성화한다. */
export default function WorkbookEditDialog({
  workbookId,
  open,
  onClose,
  onSaved,
}: {
  workbookId: string;
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleClose = useCallback(() => {
    if (saving) return; // 저장 중에는 닫지 않는다 (중복·유실 방지)
    onClose();
  }, [saving, onClose]);

  // 열릴 때 초기화 + 포커스
  useEffect(() => {
    if (!open) return;
    setText("");
    setError(null);
    const t = window.setTimeout(() => textareaRef.current?.focus(), 10);
    return () => window.clearTimeout(t);
  }, [open]);

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

  const trimmed = text.trim();
  const canSave = !saving && trimmed.length > 0 && trimmed.length <= MEMO_MAX_LENGTH;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      await addMemoBlock(workbookId, trimmed);
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다");
    } finally {
      setSaving(false);
    }
  }

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div
      role="dialog"
      aria-modal
      aria-label="워크북 블록 추가"
      className="fixed inset-0 z-50 flex items-end sm:items-start sm:justify-center sm:pt-24"
    >
      <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm" onClick={handleClose} />

      <form
        onSubmit={onSubmit}
        className="relative z-10 mx-auto flex max-h-[85svh] w-full max-w-[480px] flex-col overflow-hidden rounded-t-[28px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-card sm:rounded-[28px]"
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 px-5 py-4">
          <p className="text-[15px] font-black text-slate-900 dark:text-slate-100">블록 추가</p>
          <button
            type="button"
            onClick={handleClose}
            aria-label="닫기"
            className="rounded-full p-1.5 text-slate-400 transition hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-400"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="블록 종류">
            {BLOCK_TYPES.map((t) => {
              const enabled = SUPPORTED_BLOCK_TYPES.includes(t);
              return (
                <button
                  key={t}
                  type="button"
                  role="radio"
                  aria-checked={t === "memo"}
                  disabled={!enabled}
                  className={`rounded-full px-3 py-1.5 text-[12px] font-bold ${
                    t === "memo"
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "cursor-not-allowed bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500"
                  }`}
                >
                  {BLOCK_TYPE_LABELS[t]}
                  {!enabled && <span className="ml-1 text-[10px] font-semibold">준비 중</span>}
                </button>
              );
            })}
          </div>

          <div>
            <textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={MEMO_MAX_LENGTH}
              rows={6}
              disabled={saving}
              placeholder="이 종목을 보며 정리하고 싶은 생각을 적어 두세요. (예: 매수 근거, 확인할 지표)"
              className="w-full resize-none rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-950 px-4 py-3 text-[14px] leading-relaxed text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-right text-[11px] font-semibold tabular-nums text-slate-400 dark:text-slate-500">
              {text.length} / {MEMO_MAX_LENGTH}
            </p>
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-[13px] text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
              {error}
            </div>
          )}
        </div>

        <div className="flex gap-2 border-t border-slate-100 dark:border-slate-800 px-5 py-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={saving}
            className="flex-1 rounded-full bg-slate-100 dark:bg-slate-800 py-2.5 text-[13px] font-bold text-slate-600 dark:text-slate-300 transition hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-50"
          >
            취소
          </button>
          <button
            type="submit"
            disabled={!canSave}
            className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-full bg-slate-900 dark:bg-slate-100 py-2.5 text-[13px] font-bold text-white dark:text-slate-900 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            저장
          </button>
        </div>
      </form>
    </div>,
    document.body
  );
}
