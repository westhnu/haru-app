"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Home, Sunrise, Network, Search, Book, BookOpen, NotebookPen } from "lucide-react";
import SearchDialog from "@/components/SearchDialog";
import { HARU_BACKEND_ENABLED } from "@/lib/featureFlags";

/**
 * 모바일 하단 고정 5탭 + iOS safe-area 대응.
 * - 플래그 off(운영): 홈 / 브리핑 / 테마 / 용어 / 검색 (기존 그대로)
 * - 플래그 on(로컬 백엔드): 홈 / 종목 / 저널 / 브리핑 / 검색
 *   테마·용어 진입점은 홈 "모든 기능 보기"와 검색 다이얼로그의 "용어 사전"으로 옮긴다.
 * 브리핑은 현재 시간대(KST, 클라이언트 시간)로 모닝/이브닝을 고른다.
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

  type NavItem = {
    label: string;
    href?: string;
    onClick?: () => void;
    icon: typeof Home;
    active: boolean;
  };
  const home: NavItem = { label: "홈", href: "/", icon: Home, active: pathname === "/" };
  const brief: NavItem = {
    label: "브리핑",
    href: briefPath,
    icon: Sunrise,
    active: pathname.startsWith("/brief"),
  };
  const search: NavItem = {
    label: "검색",
    onClick: () => setSearchOpen(true),
    icon: Search,
    active: searchOpen,
  };
  const items: NavItem[] = HARU_BACKEND_ENABLED
    ? [
        home,
        {
          label: "종목",
          href: "/workbook",
          icon: BookOpen,
          active: pathname.startsWith("/workbook") || pathname.startsWith("/stock"),
        },
        {
          label: "저널",
          href: "/journal",
          icon: NotebookPen,
          active: pathname.startsWith("/journal"),
        },
        brief,
        search,
      ]
    : [
        home,
        brief,
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
        search,
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
