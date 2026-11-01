"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { Loader2, X } from "lucide-react";
import {
  DECISIONS_WITH_POSITION,
  DECISION_LABELS,
  DECISION_ORDER,
  REASONING_MAX_LENGTH,
  recordDecision,
  type Decision,
} from "@/lib/journal";

/** 숫자 입력 검증: 빈 값은 null, 음수·숫자 아님은 에러 메시지. */
function parseNonNegative(raw: string, integer: boolean): { value: number | null; error?: string } {
  const s = raw.trim();
  if (!s) return { value: null };
  const n = Number(s);
  if (!Number.isFinite(n) || n < 0) return { value: null, error: "0 이상의 숫자를 입력해 주세요" };
  if (integer && !Number.isInteger(n)) return { value: null, error: "수량은 정수로 입력해 주세요" };
  return { value: n };
}

/** 본인 결정 기록 바텀시트 (TermDetailDialog 패턴: portal, ESC·배경 닫기, scroll lock).
 *  원칙 1: 사용자 본인의 기록. 원칙 4: 가상 기록이며 실제 주문·거래를 만들지 않는다. */
export default function JournalEntryDialog({
  open,
  onClose,
  onSaved,
  stockCode,
  stockName,
  defaultChecklistId,
  defaultWorkbookId,
}: {
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
  stockCode: string;
  stockName: string;
  defaultChecklistId?: string | null;
  defaultWorkbookId?: string | null;
}) {
  const [decision, setDecision] = useState<Decision>("watch");
  const [reasoning, setReasoning] = useState("");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleClose = useCallback(() => {
    if (saving) return;
    onClose();
  }, [saving, onClose]);

  useEffect(() => {
    if (!open) return;
    setDecision("watch");
    setReasoning("");
    setQty("");
    setPrice("");
    setError(null);
    setSaved(false);
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

  const withPosition = DECISIONS_WITH_POSITION.includes(decision);
  const qtyParsed = parseNonNegative(qty, true);
  const priceParsed = parseNonNegative(price, false);
  const fieldError = withPosition ? (qtyParsed.error ?? priceParsed.error) : undefined;
  const trimmed = reasoning.trim();
  const canSave = !saving && !saved && trimmed.length > 0 && !fieldError;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      await recordDecision({
        stock_code: stockCode,
        stock_name: stockName,
        decision,
        reasoning: trimmed,
        checklist_id: defaultChecklistId ?? null,
        workbook_id: defaultWorkbookId ?? null,
        virtual_quantity: withPosition ? qtyParsed.value : null,
        virtual_price: withPosition ? priceParsed.value : null,
      });
      setSaved(true);
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장하지 못했어요");
    } finally {
      setSaving(false);
    }
  }

  if (!open || typeof document === "undefined") return null;

  const inputCls =
    "w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm tabular-nums text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-2 focus:ring-brand";

  return createPortal(
    <div
      role="dialog"
      aria-modal
      aria-label={`${stockName} 결정 기록`}
      className="fixed inset-0 z-50 flex items-end sm:items-start sm:justify-center sm:pt-24"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={handleClose} />

      <form
        onSubmit={onSubmit}
        className="relative z-10 mx-auto flex max-h-[85svh] w-full max-w-container-sm md:max-w-container-md flex-col overflow-hidden rounded-t-[28px] border border-border bg-surface shadow-card sm:rounded-[28px]"
      >
        <div className="flex items-center justify-between gap-3 border-b border-border-subtle px-5 py-4">
          <div className="min-w-0">
            <p className="truncate text-base font-black text-fg">
              {stockName} · 결정 기록
            </p>
            <p className="text-xs font-semibold text-fg-subtle">
              본인 기록 · 가상
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="닫기"
            className="rounded-full p-1.5 text-fg-subtle transition hover:bg-border-subtle hover:text-fg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          {saved ? (
            <div className="py-6 text-center">
              <p className="text-sm font-bold text-fg">기록했어요.</p>
              <p className="mt-1 text-xs font-semibold text-fg-subtle">
                &quot;투자 저널&quot;에서 전체 기록을 볼 수 있어요.
              </p>
            </div>
          ) : (
            <>
              <fieldset>
                <legend className="mb-1.5 text-xs font-bold text-fg-muted">
                  나의 결정 (본인 기록)
                </legend>
                <div className="grid grid-cols-4 gap-1.5" role="radiogroup">
                  {DECISION_ORDER.map((d) => (
                    <button
                      key={d}
                      type="button"
                      role="radio"
                      aria-checked={decision === d}
                      onClick={() => setDecision(d)}
                      className={`rounded-full px-2 py-2 text-xs font-bold transition ${
                        decision === d
                          ? "bg-fg text-surface"
                          : "bg-surface-muted text-fg-muted"
                      }`}
                    >
                      {DECISION_LABELS[d]}
                    </button>
                  ))}
                </div>
              </fieldset>

              <div>
                <label className="mb-1.5 block text-xs font-bold text-fg-muted">
                  결정 근거
                </label>
                <textarea
                  ref={textareaRef}
                  value={reasoning}
                  onChange={(e) => setReasoning(e.target.value)}
                  maxLength={REASONING_MAX_LENGTH}
                  rows={5}
                  disabled={saving}
                  placeholder="왜 이렇게 결정했는지 적어 두세요. 회고할 때 다시 봐요."
                  className="w-full resize-none rounded-2xl border border-border bg-surface px-4 py-3 text-sm leading-relaxed text-fg placeholder:text-fg-subtle focus:outline-none focus:ring-2 focus:ring-brand"
                />
                <p className="mt-1 text-right text-xs font-semibold tabular-nums text-fg-subtle">
                  {reasoning.length} / {REASONING_MAX_LENGTH}
                </p>
              </div>

              {withPosition && (
                <div className="grid grid-cols-2 gap-2">
                  <label className="block">
                    <span className="mb-1 block text-xs font-bold text-fg-muted">
                      가상 수량 (선택)
                    </span>
                    <input
                      inputMode="numeric"
                      value={qty}
                      onChange={(e) => setQty(e.target.value)}
                      placeholder="예: 10"
                      className={inputCls}
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-xs font-bold text-fg-muted">
                      가상 단가 (선택)
                    </span>
                    <input
                      inputMode="decimal"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      placeholder="원"
                      className={inputCls}
                    />
                  </label>
                </div>
              )}
              {fieldError && (
                <p className="text-xs font-semibold text-danger">{fieldError}</p>
              )}

              {(defaultChecklistId || defaultWorkbookId) && (
                <p className="text-xs font-semibold text-fg-subtle">
                  연결:{" "}
                  {[defaultWorkbookId && "현재 워크북", defaultChecklistId && "체크리스트"]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              )}

              {error && (
                <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
                  {error}
                </div>
              )}
            </>
          )}

          <p className="rounded-xl bg-warning/10 px-3 py-2 text-xs font-semibold leading-relaxed text-warning">
            가상 기록이에요. 실제 주문·거래가 아니며, 종목 추천 없이 최종 결정은 본인이 해요.
          </p>
        </div>

        <div className="flex gap-2 border-t border-border-subtle px-5 py-3">
          <button
            type="button"
            onClick={handleClose}
            disabled={saving}
            className="flex-1 rounded-full bg-surface-muted py-2.5 text-sm font-bold text-fg-muted transition hover:bg-border disabled:opacity-50"
          >
            {saved ? "닫기" : "취소"}
          </button>
          {!saved && (
            <button
              type="submit"
              disabled={!canSave}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-full bg-fg py-2.5 text-sm font-bold text-surface transition hover:bg-fg/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              기록하기
            </button>
          )}
        </div>
      </form>
    </div>,
    document.body
  );
}
