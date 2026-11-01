import Link from "next/link";
import type { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";

/** 페이지 제목 영역. 뒤로가기는 링크(back.href)로 둔다 — 히스토리 의존 없이 항상 같은 곳으로 간다. */
export function PageHeader({
  title,
  subtitle,
  back,
  action,
}: {
  title: string;
  subtitle?: ReactNode;
  back?: { href: string; label?: string };
  action?: ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-sm border-b border-border-subtle pb-md">
      <div className="min-w-0 flex-1">
        {back && (
          <Link
            href={back.href}
            className="mb-xs inline-flex items-center gap-1 text-sm text-fg-muted transition hover:text-fg"
          >
            <ChevronLeft className="h-4 w-4" />
            {back.label ?? "뒤로"}
          </Link>
        )}
        <h1 className="truncate text-xl font-semibold text-fg">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-fg-muted">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
  );
}
