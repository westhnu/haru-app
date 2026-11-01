import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** 페이지 공통 외곽: 모바일 우선 좁은 폭(28rem → md 42rem), 섹션 간격, BottomNav 여백. */
export function PageShell({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("container-page page-space py-md pb-nav", className)}>{children}</div>;
}
