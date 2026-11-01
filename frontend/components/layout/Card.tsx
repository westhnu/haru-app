import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** shadcn 스타일 간소화 카드. padded=false면 목록처럼 내부에서 여백을 직접 잡는다. */
export function Card({
  children,
  className,
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border-subtle bg-surface-elevated",
        padded && "space-y-sm p-md",
        className
      )}
    >
      {children}
    </div>
  );
}
