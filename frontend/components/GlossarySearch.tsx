"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Search } from "lucide-react";
import GlossaryResult, { type GlossaryAnswer } from "./GlossaryResult";

type Props = {
  suggestedTerms: string[];
  /** /glossary?q= 로 들어오면 입력을 채우고 한 번 바로 검색한다 (검색 다이얼로그 "용어 사전에서 찾기"). */
  initialQuery?: string;
};

// next.config rewrites: /backend/* → FastAPI /api/v1/* (Guardrail 경유, KI-018)
const ASK_ENDPOINT = "/backend/glossary/ask";

export default function GlossarySearch({ suggestedTerms, initialQuery }: Props) {
  const [query, setQuery] = useState(initialQuery ?? "");
  // Strict Mode(dev)는 effect를 두 번 돌린다. ref로 막아 Bedrock 호출(과금)을 한 번만 한다.
  const autoSearched = useRef(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<GlossaryAnswer | null>(null);

  async function doSearch(q: string) {
    const trimmed = q.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const r = await fetch(ASK_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });
      if (!r.ok) {
        throw new Error(`요청 실패 (${r.status})`);
      }
      setAnswer((await r.json()) as GlossaryAnswer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "알 수 없는 에러");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!initialQuery?.trim() || autoSearched.current) return;
    autoSearched.current = true;
    doSearch(initialQuery);
    // initialQuery가 바뀔 때만 (같은 값으로 재진입 시 재검색 안 함)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    doSearch(query);
  }

  function onSuggested(term: string) {
    setQuery(term);
    doSearch(term);
  }

  return (
    <div>
      <form onSubmit={onSubmit} className="mb-4">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="예: PER이 뭐야?"
            className="w-full rounded-lg border border-border bg-surface px-4 py-3 pl-11 focus:outline-none focus:ring-2 focus:ring-brand"
            disabled={loading}
          />
          <Search className="absolute left-3 top-3.5 h-5 w-5 text-fg-subtle" />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="mt-3 w-full rounded-lg bg-brand py-3 font-medium text-brand-foreground transition-colors hover:bg-brand/90 disabled:cursor-not-allowed disabled:bg-fg-subtle"
        >
          {loading ? "검색 중" : "검색"}
        </button>
      </form>

      <div className="mb-6 flex flex-wrap gap-2">
        <span className="self-center text-sm text-fg-muted">예시:</span>
        {suggestedTerms.map((term) => (
          <button
            key={term}
            type="button"
            onClick={() => onSuggested(term)}
            disabled={loading}
            className="rounded-full bg-surface-muted px-3 py-1 text-sm text-fg hover:bg-border disabled:opacity-50"
          >
            {term}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-danger/30 bg-danger/10 p-4 text-danger">
          {error}
        </div>
      )}

      {answer && <GlossaryResult answer={answer} />}
    </div>
  );
}
