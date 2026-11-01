import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/PageHeader";
import { PageShell } from "@/components/layout/PageShell";
import GlossarySearch from "@/components/GlossarySearch";

export const metadata: Metadata = {
  title: "용어 사전 — Haru",
  description: "투자 용어를 AI가 설명해요. Bedrock Knowledge Base 기반.",
};

const SUGGESTED_TERMS = ["PER", "ROE", "EPS", "PBR", "ROA"];

export default function GlossaryPage({
  searchParams,
}: {
  searchParams: { q?: string | string[] };
}) {
  const q = typeof searchParams.q === "string" ? searchParams.q.slice(0, 200) : undefined;
  return (
    // PageShell이 BottomNav 여백(pb-nav)과 모바일 우선 폭을 맡는다 (Phase F2).
    <PageShell>
      <PageHeader title="용어 사전" subtitle="용어를 검색해 보세요. AWS Bedrock Knowledge Base에 색인된 용어 302개에서 근거를 찾아 답해요." />
      <GlossarySearch suggestedTerms={SUGGESTED_TERMS} initialQuery={q} />
    </PageShell>
  );
}
