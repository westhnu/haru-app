import type { ReactNode } from "react";
import type { ItemStatus } from "@/lib/checklist";
import { cn } from "@/lib/utils";

export type BadgeVariant = "default" | "success" | "warning" | "danger" | "outline";

const VARIANTS: Record<BadgeVariant, string> = {
  default: "bg-brand/10 text-brand",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  danger: "bg-danger/10 text-danger",
  // 결정 라벨처럼 중립이어야 하는 표시 (추천처럼 보이지 않게 색을 쓰지 않는다)
  outline: "border border-border text-fg-muted",
};

/** 체크리스트 상태 → 배지 색: 충족=success, 미충족=danger, 판단 보류=warning */
export const STATUS_VARIANT: Record<ItemStatus, BadgeVariant> = {
  satisfied: "success",
  unsatisfied: "danger",
  uncertain: "warning",
};

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold",
        VARIANTS[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
