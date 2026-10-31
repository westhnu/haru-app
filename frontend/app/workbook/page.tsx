import type { Metadata } from "next";
import WorkbookList from "@/components/WorkbookList";

export const metadata: Metadata = {
  title: "내 워크북 — Haru",
  description: "종목별 분석 메모를 모아 보관합니다.",
};

export default function WorkbookPage() {
  return (
    // 하단 고정 BottomNav에 가리지 않도록 아래 여백을 둔다.
    <main className="mx-auto w-full max-w-[480px] px-5 pb-28 pt-8">
      <header className="mb-6">
        <h1 className="text-2xl font-black text-slate-950 dark:text-white">내 워크북</h1>
        <p className="mt-1.5 text-[13px] font-semibold text-slate-500 dark:text-slate-400">
          종목별로 남긴 분석 메모를 모아 봅니다. 카드를 누르면 해당 종목의 워크북 탭으로 이동해요.
        </p>
      </header>
      <WorkbookList />
    </main>
  );
}
