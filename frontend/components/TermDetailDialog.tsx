"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Loader2, X } from "lucide-react";
import GlossaryResult, { type GlossaryAnswer } from "@/components/GlossaryResult";

// next.config rewrites: /backend/* → FastAPI /api/v1/* (Bedrock KB + Guardrail 경유, KI-018)
const ASK_ENDPOINT = "/backend/glossary/ask";
const CACHE_PREFIX = "haru:term:";

/** 받침 유무로 주격 조사를 고른다. 한글이 아니면(영문 약어 등) "이"로 둔다 ("PER이 뭐야?"). */
function subjectParticle(word: string): "이" | "가" {
  const code = word.charCodeAt(word.length - 1) - 0xac00;
  if (code < 0 || code > 11171) return "이";
  return code % 28 === 0 ? "가" : "이";
}

export function termQuery(term: string): string {
  return `${term}${subjectParticle(term)} 뭐야?`;
}

// sessionStorage는 사파리 사생활 보호 모드 등에서 예외를 던질 수 있어 실패해도 무시한다.
function readCache(term: string): GlossaryAnswer | null {
  try {
    const raw = window.sessionStorage.getItem(CACHE_PREFIX + term);
    return raw ? (JSON.parse(raw) as GlossaryAnswer) : null;
  } catch {
    return null;
  }
}

function writeCache(term: string, answer: GlossaryAnswer): void {
  // mock 응답은 백엔드 설정이 바뀌면 의미가 없어지므로 캐시하지 않는다.
  if (answer.is_mock) return;
  try {
    window.sessionStorage.setItem(CACHE_PREFIX + term, JSON.stringify(answer));
  } catch {
    /* 용량 초과·비활성: 캐시 없이 동작 */
  }
}

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; answer: GlossaryAnswer; cached: boolean };

/** 용어 자세히 보기 바텀시트. 열릴 때 Bedrock KB RAG(/glossary/ask)에 질의하고 세션 동안 캐시한다.
 *  응답 p95가 약 13초(Phase 5a 3차)라 로딩 안내와 취소를 둔다. */
export default function TermDetailDialog({
  term,
  open,
  onClose,
}: {
  term: string;
  open: boolean;
  onClose: () => void;
}) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const abortRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const handleClose = useCallback(() => {
    cancel();
    onClose();
  }, [cancel, onClose]);

  // 열릴 때 캐시 확인 → 없으면 질의. 닫히거나 unmount되면 진행 중 요청을 취소한다.
  useEffect(() => {
    if (!open) {
      setState({ kind: "idle" });
      return;
    }
    const cached = readCache(term);
    if (cached) {
      setState({ kind: "done", answer: cached, cached: true });
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ kind: "loading" });
    // fetch는 다음 tick에 시작한다. Strict Mode(dev)의 mount→cleanup→mount에서 첫 실행은
    // 타이머 단계에서 취소되어 요청이 나가지 않는다. abort만으로는 이미 프록시를 탄 요청의
    // 서버 측 Bedrock 호출(과금)을 멈출 수 없기 때문이다.
    const timer = window.setTimeout(async () => {
      try {
        const r = await fetch(ASK_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: termQuery(term) }),
          signal: controller.signal,
        });
        if (!r.ok) throw new Error(`요청 실패 (${r.status})`);
        const answer = (await r.json()) as GlossaryAnswer;
        writeCache(term, answer);
        setState({ kind: "done", answer, cached: false });
      } catch (e) {
        if (controller.signal.aborted) return; // 사용자 취소·닫힘은 에러로 보지 않는다
        setState({
          kind: "error",
          message: e instanceof Error ? e.message : "알 수 없는 에러",
        });
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
      }
    }, 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, term]);

  // ESC 로 닫기
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, handleClose]);

  // body scroll lock
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open || typeof document === "undefined") return null;

  const loading = state.kind === "loading";

  // 툴팁(inline span) 안에서 열리므로 document.body로 portal해 DOM 중첩·z-index 간섭을 피한다.
  return createPortal(
    <div
      role="dialog"
      aria-modal
      aria-label={`${term} 자세히`}
      className="fixed inset-0 z-50 flex items-end sm:items-start sm:justify-center sm:pt-24"
      onClick={(e) => e.stopPropagation()}
    >
      <div
        className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm"
        onClick={handleClose}
      />

      <div className="relative z-10 mx-auto flex max-h-[85svh] w-full max-w-[480px] flex-col overflow-hidden rounded-t-[28px] border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-card sm:rounded-[28px]">
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 dark:border-slate-800 px-5 py-4">
          <p className="truncate text-[15px] font-black text-slate-900 dark:text-slate-100">
            {term} · 자세히
          </p>
          <button
            type="button"
            onClick={handleClose}
            aria-label="닫기"
            className="rounded-full p-1.5 text-slate-400 transition hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-400"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4" aria-live="polite">
          {loading && (
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600 dark:text-blue-400" />
              <p className="text-[13px] font-semibold text-slate-500 dark:text-slate-400">
                AWS Bedrock KB에서 근거를 찾는 중... (최대 15초)
              </p>
            </div>
          )}
          {state.kind === "error" && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-[13px] text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
              {state.message}
            </div>
          )}
          {state.kind === "done" && (
            <>
              {state.cached && (
                <p className="mb-2 text-[11px] font-semibold text-slate-400 dark:text-slate-500">
                  이번 세션에서 받은 답변을 다시 보여드려요.
                </p>
              )}
              <GlossaryResult answer={state.answer} />
            </>
          )}
        </div>

        <div className="border-t border-slate-100 dark:border-slate-800 px-5 py-3">
          <button
            type="button"
            onClick={handleClose}
            className="w-full rounded-full bg-slate-100 dark:bg-slate-800 py-2.5 text-[13px] font-bold text-slate-600 dark:text-slate-300 transition hover:bg-slate-200 dark:hover:bg-slate-700"
          >
            {loading ? "취소" : "닫기"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
