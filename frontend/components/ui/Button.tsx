import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "destructive";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-brand text-brand-foreground hover:bg-brand/90",
  secondary: "bg-surface-muted text-fg hover:bg-border-subtle",
  ghost: "text-fg-muted hover:bg-surface-muted hover:text-fg",
  destructive: "bg-danger text-surface hover:bg-danger/90",
};

/** 공통 버튼. size는 이번 단계에서 하나(rounded-full, text-sm)만 둔다. */
export function Button({
  variant = "primary",
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-full px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40",
        VARIANTS[variant],
        className
      )}
      {...props}
    />
  );
}

/** 체크리스트 상태 버튼 선택 색 (진한 배경 + 대비 글씨). 충족/미충족/판단 보류 색을 Badge와 맞춘다. */
export const STATUS_SOLID = {
  satisfied: "bg-success text-surface",
  unsatisfied: "bg-danger text-surface",
  uncertain: "bg-warning text-surface",
} as const;
