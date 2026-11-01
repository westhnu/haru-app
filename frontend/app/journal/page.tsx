import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/PageHeader";
import { PageShell } from "@/components/layout/PageShell";
import JournalList from "@/components/JournalList";

export const metadata: Metadata = {
  title: "투자 저널 — Haru",
  description: "결정과 근거를 기록하고 가상 포지션을 추적해요.",
};

export default function JournalPage() {
  return (
    // PageShell이 BottomNav 여백(pb-nav)과 모바일 우선 폭을 맡는다 (Phase F2).
    <PageShell>
      <PageHeader title="투자 저널" subtitle="결정 근거를 기록해 두고 다시 돌아봐요. 모든 기록은 본인의 판단이에요." />
      <JournalList />
    </PageShell>
  );
}
