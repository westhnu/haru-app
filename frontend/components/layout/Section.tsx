import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** 제목(선택)·우측 액션(선택)이 붙는 반복 섹션 블록. */
export function Section({
  title,
  action,
  children,
  className,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("space-y-sm", className)}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-sm">
          {title && <h2 className="text-base font-medium text-fg">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
