import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

/** 빈 상태 블록. 문구는 말투 가이드 L2(서비스 톤)로 넘긴다. */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-xs rounded-lg border border-dashed border-border bg-surface-muted px-md py-xl text-center">
      {Icon && <Icon aria-hidden className="h-6 w-6 text-fg-subtle" />}
      <p className="text-sm font-semibold text-fg">{title}</p>
      {description && <p className="text-xs text-fg-muted">{description}</p>}
      {action && <div className="mt-xs">{action}</div>}
    </div>
  );
}
