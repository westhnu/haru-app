import type { Metadata } from "next";
import GlossarySearch from "@/components/GlossarySearch";

export const metadata: Metadata = {
  title: "용어 사전 — Haru",
  description: "투자 용어 AI 설명. Bedrock Knowledge Base 기반.",
};

const SUGGESTED_TERMS = ["PER", "ROE", "EPS", "PBR", "ROA"];

export default function GlossaryPage({
  searchParams,
}: {
  searchParams: { q?: string | string[] };
}) {
  const q = typeof searchParams.q === "string" ? searchParams.q.slice(0, 200) : undefined;
  return (
    // 하단 고정 BottomNav에 가리지 않도록 아래 여백을 둔다.
    <main className="container mx-auto max-w-3xl px-4 pb-28 pt-8">
      <header className="mb-8">
        <h1 className="mb-2 text-3xl font-bold">용어 사전</h1>
        <p className="text-slate-600 dark:text-slate-400">
          용어 검색. AWS Bedrock Knowledge Base 색인 용어 302개에서 근거 검색.
        </p>
      </header>
      <GlossarySearch suggestedTerms={SUGGESTED_TERMS} initialQuery={q} />
    </main>
  );
}
