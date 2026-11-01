"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Bot, MessageSquarePlus, Send, Wrench, X } from "lucide-react";
import { EmptyState } from "@/components/layout/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/chat";

/** Phase G 챗 UI shell. 전송·세션 저장은 비활성(Phase G.1에서 연결) — 진입점도 아직 없다.
 *  모바일 풀스크린, md 이상은 가운데 다이얼로그(max-w-container-md). */
export default function ChatDialog({
  open,
  onClose,
  title = "새 대화",
  stockCode,
  messages = [],
}: {
  open: boolean;
  onClose: () => void;
  title?: string;
  stockCode?: string | null;
  messages?: ChatMessage[];
}) {
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div role="dialog" aria-modal aria-label={title} className="fixed inset-0 z-50 flex md:items-center md:justify-center">
      <div className="absolute inset-0 hidden bg-black/40 backdrop-blur-sm md:block" onClick={onClose} />
      <div className="relative z-10 flex h-full w-full flex-col bg-surface md:h-[80svh] md:max-w-container-md md:rounded-lg md:border md:border-border-subtle md:shadow-card">
        <header className="flex items-center justify-between gap-sm border-b border-border-subtle px-md py-sm">
          <div className="flex min-w-0 items-center gap-xs">
            <p className="truncate text-base font-semibold text-fg">{title}</p>
            {stockCode && <Badge variant="outline">{stockCode}</Badge>}
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Button variant="ghost" disabled aria-label="새 대화" title="Phase G에서 활성화">
              <MessageSquarePlus className="h-4 w-4" />
            </Button>
            <Button variant="ghost" onClick={onClose} aria-label="닫기">
              <X className="h-4 w-4" />
            </Button>
          </div>
        </header>

        <div className="flex-1 space-y-sm overflow-y-auto px-md py-md" aria-live="polite">
          {messages.length === 0 ? (
            <EmptyState
              icon={Bot}
              title="대화가 없어요"
              description="종목·용어·저널을 한곳에서 묻는 챗봇은 Phase G에서 열려요."
            />
          ) : (
            messages.map((m) => <MessageRow key={m.id} message={m} />)
          )}
        </div>

        <footer className="border-t border-border-subtle px-md py-sm">
          <form
            onSubmit={(e) => e.preventDefault()}
            className="flex items-end gap-xs"
          >
            <textarea
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={1}
              disabled
              placeholder="Phase G에서 활성화"
              className="min-h-[2.5rem] flex-1 resize-none rounded-lg border border-border bg-surface-muted px-sm py-xs text-sm text-fg placeholder:text-fg-subtle disabled:cursor-not-allowed"
            />
            <Button type="submit" disabled aria-label="전송">
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </footer>
      </div>
    </div>,
    document.body
  );
}

function MessageRow({ message }: { message: ChatMessage }) {
  if (message.role === "tool") {
    return (
      <details className="rounded-lg border border-border-subtle bg-surface-muted px-sm py-xs text-xs text-fg-muted">
        <summary className="flex cursor-pointer list-none items-center gap-1">
          <Wrench className="h-3.5 w-3.5" />
          {message.tool_name ?? "tool"}
        </summary>
        <pre className="mt-xs overflow-x-auto whitespace-pre-wrap break-words font-mono">
          {JSON.stringify({ input: message.tool_input, output: message.tool_output }, null, 2)}
        </pre>
      </details>
    );
  }
  const mine = message.role === "user";
  return (
    <div className={cn("flex items-start gap-xs", mine && "justify-end")}>
      {!mine && (
        <span aria-hidden className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand">
          <Bot className="h-4 w-4" />
        </span>
      )}
      <p
        className={cn(
          "max-w-[80%] whitespace-pre-wrap break-words rounded-lg px-sm py-xs text-sm",
          mine ? "bg-brand text-brand-foreground" : "bg-surface-muted text-fg"
        )}
      >
        {message.content}
      </p>
    </div>
  );
}
