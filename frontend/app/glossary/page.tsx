import type { Metadata } from "next";
import GlossarySearch from "@/components/GlossarySearch";

export const metadata: Metadata = {
  title: "용어 사전 — Haru",
  description: "투자 용어를 AI가 설명합니다. Bedrock Knowledge Base 기반.",
};

const SUGGESTED_TERMS = ["PER", "ROE", "EPS", "PBR", "ROA"];

export default function GlossaryPage() {
  return (
    // 하단 고정 BottomNav에 가리지 않도록 아래 여백을 둔다.
    <main className="container mx-auto max-w-3xl px-4 pb-28 pt-8">
      <header className="mb-8">
        <h1 className="mb-2 text-3xl font-bold">용어 사전</h1>
        <p className="text-slate-600 dark:text-slate-400">
          투자 용어를 궁금한 대로 물어보세요. AWS Bedrock Knowledge Base에 색인된 302개 용어에서
          근거를 찾아 답변합니다.
        </p>
      </header>
      <GlossarySearch suggestedTerms={SUGGESTED_TERMS} />
    </main>
  );
}
