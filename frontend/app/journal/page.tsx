import type { Metadata } from "next";
import JournalList from "@/components/JournalList";

export const metadata: Metadata = {
  title: "투자 저널 — Haru",
  description: "본인의 결정과 근거를 기록하고 가상 포지션을 추적합니다.",
};

export default function JournalPage() {
  return (
    // 하단 고정 BottomNav에 가리지 않도록 아래 여백을 둔다.
    <main className="mx-auto w-full max-w-[480px] px-5 pb-28 pt-8">
      <header className="mb-6">
        <h1 className="text-2xl font-black text-slate-950 dark:text-white">투자 저널</h1>
        <p className="mt-1.5 text-[13px] font-semibold text-slate-500 dark:text-slate-400">
          왜 그렇게 결정했는지 기록해 두고 나중에 돌아봅니다. 모든 기록은 본인의 판단이에요.
        </p>
      </header>
      <JournalList />
    </main>
  );
}
