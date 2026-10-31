"use client";

import { useState, type FormEvent } from "react";
import { Search } from "lucide-react";
import GlossaryResult, { type GlossaryAnswer } from "./GlossaryResult";

type Props = {
  suggestedTerms: string[];
};

// next.config rewrites: /backend/* → FastAPI /api/v1/* (Guardrail 경유, KI-018)
const ASK_ENDPOINT = "/backend/glossary/ask";

export default function GlossarySearch({ suggestedTerms }: Props) {
  const [query, setQuery] = useState("");
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
            className="w-full rounded-lg border border-slate-300 bg-white px-4 py-3 pl-11 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-900"
            disabled={loading}
          />
          <Search className="absolute left-3 top-3.5 h-5 w-5 text-slate-400" />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="mt-3 w-full rounded-lg bg-blue-600 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {loading ? "검색 중..." : "질문하기"}
        </button>
      </form>

      <div className="mb-6 flex flex-wrap gap-2">
        <span className="self-center text-sm text-slate-500 dark:text-slate-400">예시:</span>
        {suggestedTerms.map((term) => (
          <button
            key={term}
            type="button"
            onClick={() => onSuggested(term)}
            disabled={loading}
            className="rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700 hover:bg-slate-200 disabled:opacity-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
          >
            {term}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          {error}
        </div>
      )}

      {answer && <GlossaryResult answer={answer} />}
    </div>
  );
}
