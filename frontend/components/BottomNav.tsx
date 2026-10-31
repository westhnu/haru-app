"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Home, Sunrise, Network, Search, Book } from "lucide-react";
import SearchDialog from "@/components/SearchDialog";

/**
 * 모바일 하단 고정 4탭 + iOS safe-area 대응.
 * - 홈 / 브리핑 (현재 시간대로 결정 — 클라이언트 시간 사용) / 테마 / 검색
 */
export default function BottomNav() {
  const pathname = usePathname();
  const [searchOpen, setSearchOpen] = useState(false);

  // 클라이언트 시간으로 브리핑 페이지 결정
  const hour =
    typeof window !== "undefined"
      ? Number(
          new Intl.DateTimeFormat("en-US", {
            hour: "numeric",
            hour12: false,
            timeZone: "Asia/Seoul",
          }).format(new Date())
        )
      : 12;
  const briefPath =
    hour >= 8 && hour < 17 ? "/brief/morning" : "/brief/evening";

  const items: {
    label: string;
    href?: string;
    onClick?: () => void;
    icon: typeof Home;
    active: boolean;
  }[] = [
    { label: "홈", href: "/", icon: Home, active: pathname === "/" },
    {
      label: "브리핑",
      href: briefPath,
      icon: Sunrise,
      active: pathname.startsWith("/brief"),
    },
    {
      label: "테마",
      href: "/themes",
      icon: Network,
      active: pathname.startsWith("/themes"),
    },
    {
      label: "용어",
      href: "/glossary",
      icon: Book,
      active: pathname.startsWith("/glossary"),
    },
    {
      label: "검색",
      onClick: () => setSearchOpen(true),
      icon: Search,
      active: searchOpen,
    },
  ];

  return (
    <>
      <nav
        aria-label="하단 네비게이션"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/85 backdrop-blur-md"
        style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
      >
        <div className="mx-auto flex w-full max-w-[480px] items-stretch">
          {items.map((it) => {
            const Icon = it.icon;
            const inner = (
              <div className="flex flex-col items-center justify-center gap-0.5 py-2.5">
                <Icon
                  className={`h-5 w-5 transition ${
                    it.active ? "text-slate-900 dark:text-slate-100" : "text-slate-400 dark:text-slate-500"
                  }`}
                />
                <span
                  className={`text-[10.5px] font-bold transition ${
                    it.active ? "text-slate-900 dark:text-slate-100" : "text-slate-500 dark:text-slate-400"
                  }`}
                >
                  {it.label}
                </span>
              </div>
            );
            return it.href ? (
              <Link key={it.label} href={it.href} className="flex-1">
                {inner}
              </Link>
            ) : (
              <button
                key={it.label}
                type="button"
                onClick={it.onClick}
                className="flex-1"
              >
                {inner}
              </button>
            );
          })}
        </div>
      </nav>

      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  );
}
