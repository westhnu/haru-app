import { ShieldCheck, ShieldAlert } from "lucide-react";
import type { VerifyResult } from "@/lib/types";

/** Gemini 교차검증 결과 배지 — 평가 아키텍처를 화면에 가시화 */
export default function VerifyBadge({
  verify,
  verifyModel,
}: {
  verify: VerifyResult | null;
  verifyModel: string;
}) {
  if (!verify) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 dark:bg-slate-800 px-3 py-1.5 text-[12px] font-bold text-slate-500 dark:text-slate-400">
        교차검증 미수행
      </span>
    );
  }

  const issues =
    verify.hallucinations.length +
    verify.inconsistencies.length +
    verify.advice_violations.length;

  if (verify.passed && issues === 0) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-900 px-3 py-1.5 text-[12px] font-bold text-white">
        <ShieldCheck className="h-3.5 w-3.5" />
        교차검증 통과
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 dark:bg-slate-800 px-3 py-1.5 text-[12px] font-bold text-slate-900 dark:text-slate-100">
      <ShieldAlert className="h-3.5 w-3.5" />
      검증 불일치 {issues}건
    </span>
  );
}
