import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/PageHeader";
import { PageShell } from "@/components/layout/PageShell";
import WorkbookList from "@/components/WorkbookList";

export const metadata: Metadata = {
  title: "내 워크북 — Haru",
  description: "종목별 분석 메모를 모아 둬요.",
};

export default function WorkbookPage() {
  return (
    // PageShell이 BottomNav 여백(pb-nav)과 모바일 우선 폭을 맡는다 (Phase F2).
    <PageShell>
      <PageHeader title="내 워크북" subtitle="종목별 분석 메모를 모아 봐요. 카드를 누르면 해당 종목의 워크북 탭으로 이동해요." />
      <WorkbookList />
    </PageShell>
  );
}
