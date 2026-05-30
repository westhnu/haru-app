import Link from "next/link";
import {
  Newspaper,
  TrendingUp,
  Search,
  LineChart,
  ListChecks,
  ChevronRight,
  type LucideIcon,
} from "lucide-react";
import type { BriefSection } from "@/lib/types";
import { nameToCode } from "@/lib/corpcodes";
import GlossaryText from "@/components/GlossaryText";

// 5섹션 위치별 아이콘 (모닝/이브닝 공통 의미축: 이슈→테마→원인→전망→체크)
const ICONS: LucideIcon[] = [Newspaper, TrendingUp, Search, LineChart, ListChecks];

export default function SectionCard({
  index,
  section,
}: {
  index: number;
  section: BriefSection;
}) {
  const Icon = ICONS[index] ?? Newspaper;

  return (
    <section
      className="animate-fade-up rounded-[24px] border border-slate-200 bg-white p-5 shadow-soft"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-start gap-3.5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1 pt-0.5">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-black tabular-nums text-slate-400">
              {String(index + 1).padStart(2, "0")}
            </span>
            <h2 className="text-[15.5px] font-black tracking-tight text-slate-950">
              {section.title}
            </h2>
          </div>
          <GlossaryText
            text={section.summary}
            className="mt-3 block text-[15px] font-medium leading-[1.85] text-slate-800"
          />
        </div>
      </div>

      {section.bullets && section.bullets.length > 0 && (
        <ul className="mt-4 space-y-3 pl-[54px]">
          {section.bullets.map((b, i) => (
            <li key={i} className="flex gap-2.5 text-[14.5px] font-medium leading-[1.8] text-slate-800">
              <span className="mt-[11px] h-1.5 w-1.5 shrink-0 rounded-full bg-slate-900" />
              <GlossaryText text={b} />
            </li>
          ))}
        </ul>
      )}

      {section.tickers && section.tickers.length > 0 && (
        <div className="mt-4 space-y-2 pl-[54px]">
          {section.tickers.map((t, i) => {
            // 클릭 가능 조건을 엄격히 — 진짜 종목 코드가 있어야 함.
            // - 한국: 6자리 code 또는 nameToCode 매핑 성공
            // - 해외: 미국식 티커 (영문 대문자 1~5자)
            // 그 외 ("미국 실적(예시)", "美 CPI 발표" 같은 메타 항목)는 정보 카드로만.
            const krCode = t.code || nameToCode(t.name);
            const usTicker =
              t.symbol && /^[A-Z]{1,5}$/.test(t.symbol) ? t.symbol : null;
            const target = krCode || usTicker;
            const Inner = (
              <>
                <div className="flex min-w-0 flex-1 items-baseline gap-1.5">
                  <span
                    title={t.name}
                    className="truncate text-[14px] font-bold text-slate-900"
                  >
                    {t.name}
                  </span>
                  {t.symbol && (
                    <span className="shrink-0 text-[11px] font-semibold tabular-nums text-slate-400">
                      {t.symbol}
                    </span>
                  )}
                </div>
                <div className="flex max-w-[52%] shrink-0 items-center gap-1.5">
                  {t.note && (
                    <span
                      title={t.note}
                      className="truncate text-right text-[12px] font-semibold text-slate-500"
                    >
                      {t.note}
                    </span>
                  )}
                  {target && (
                    <ChevronRight className="h-4 w-4 shrink-0 text-slate-300" />
                  )}
                </div>
              </>
            );
            const baseCls =
              "flex items-center justify-between gap-3 rounded-2xl px-4 py-3";
            return target ? (
              <Link
                key={i}
                href={`/stock/${encodeURIComponent(target)}?name=${encodeURIComponent(t.name)}`}
                className={`${baseCls} bg-slate-50 transition hover:bg-slate-100`}
              >
                {Inner}
              </Link>
            ) : (
              // 메타 항목 — 클릭 불가, 살짝 옅은 톤으로 정보 카드 인상
              <div
                key={i}
                className={`${baseCls} bg-slate-50/60 cursor-default`}
              >
                {Inner}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
