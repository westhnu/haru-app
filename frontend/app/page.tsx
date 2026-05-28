import Link from "next/link";
import {
  ArrowRight,
  Sunrise,
  Sunset,
  Sparkles,
  Network,
  ShieldCheck,
  Bot,
} from "lucide-react";
import type { BriefType } from "@/lib/types";

// 현재 시각을 반영해야 하므로 매 요청 렌더
export const dynamic = "force-dynamic";

const features = [
  {
    href: "/brief/morning",
    title: "모닝 브리핑",
    time: "08:00",
    description: "간밤 글로벌 시장이 오늘 국내 장에 줄 영향까지 정리해 드려요.",
    icon: Sunrise,
    active: true,
  },
  {
    href: "/brief/evening",
    title: "이브닝 브리핑",
    time: "17:00",
    description: "오늘 국내 장 마감을 짚고, 오늘 밤 미국 장 대비 포인트까지.",
    icon: Sunset,
    active: true,
  },
  {
    href: "/themes",
    title: "이슈·테마 매핑",
    time: "신규",
    description: "하나의 이슈가 어떤 테마·종목으로 번지는지 연결해 보여드려요.",
    icon: Network,
    active: true,
  },
  {
    href: "#",
    title: "AI 품질 리포트",
    time: "준비 중",
    description: "브리핑의 정확성과 교차검증 결과를 매일 누적해 기록해요.",
    icon: ShieldCheck,
    active: false,
  },
];

// 현재 KST 시각으로 지금 보여줄 브리핑 결정.
// cron 이 모닝 08:00 / 이브닝 17:00 KST 에 갱신하므로
//   08:00 ≤ hour < 17:00  → 오늘 모닝이 최신
//   그 외 (17:00~익일 07:59) → 오늘 또는 어제 이브닝이 최신
function currentPeriod(): BriefType {
  const hour = Number(
    new Intl.DateTimeFormat("en-US", {
      hour: "numeric",
      hour12: false,
      timeZone: "Asia/Seoul",
    }).format(new Date())
  );
  return hour >= 8 && hour < 17 ? "morning" : "evening";
}

const PREVIEW: Record<
  BriefType,
  { label: string; tile: string; rows: { label: string; value: string }[]; note: string }
> = {
  morning: {
    label: "모닝 브리핑",
    tile: "bg-gradient-to-br from-amber-400 to-orange-500",
    rows: [
      { label: "오늘 한 줄", value: "반도체 강세 동조" },
      { label: "교차검증", value: "통과" },
      { label: "주목 테마", value: "HBM · 2차전지" },
    ],
    note: "간밤 미국 반도체 강세에 동조해 국내 반도체 대형주가 주목받는 흐름이에요. 금리·환율 변수는 함께 확인하세요.",
  },
  evening: {
    label: "이브닝 브리핑",
    tile: "bg-gradient-to-br from-indigo-400 to-violet-500",
    rows: [
      { label: "오늘 한 줄", value: "외국인 순매수 마감" },
      { label: "교차검증", value: "통과" },
      { label: "밤 체크", value: "美 CPI 발표" },
    ],
    note: "오늘 코스피는 외국인 순매수로 강보합 마감했어요. 오늘 밤 미국 CPI 발표를 앞두고 변동성에 유의하세요.",
  },
};

// 현재 시간대(아침/밤)에 따른 색상 테마
const THEME: Record<
  BriefType,
  { glow: string; badge: string; badgeIcon: string; grad: string; close: string }
> = {
  morning: {
    glow: "radial-gradient(120% 70% at 50% -10%, rgba(251,191,36,0.16), rgba(244,63,94,0.10) 42%, transparent 72%)",
    badge: "bg-gradient-to-r from-amber-100 via-rose-100 to-violet-100",
    badgeIcon: "text-amber-500",
    grad: "from-amber-500 via-rose-500 to-violet-600",
    close: "from-amber-400 via-rose-400 to-violet-500",
  },
  evening: {
    glow: "radial-gradient(120% 70% at 50% -10%, rgba(99,102,241,0.18), rgba(139,92,246,0.12) 42%, transparent 72%)",
    badge: "bg-gradient-to-r from-indigo-100 via-violet-100 to-sky-100",
    badgeIcon: "text-indigo-500",
    grad: "from-indigo-500 via-violet-500 to-sky-600",
    close: "from-indigo-400 via-violet-400 to-sky-500",
  },
};

export default function Home() {
  const period = currentPeriod();
  const pv = PREVIEW[period];
  const theme = THEME[period];
  const periodLabel = period === "morning" ? "모닝" : "이브닝";

  return (
    <div className="min-h-svh bg-slate-50">
      <div className="relative mx-auto min-h-svh w-full max-w-[480px] overflow-hidden bg-white px-5 pb-12">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 z-0 h-80"
          style={{ background: theme.glow }}
        />

        <div className="relative z-10">
          {/* 상단 바 */}
          <header className="flex items-center justify-between py-5">
            <div className="flex items-baseline gap-1.5">
              <span className="text-lg font-black tracking-tight text-slate-950">
                하루
              </span>
              <span className="text-[13px] font-bold tracking-[0.18em] text-slate-300">
                HARU
              </span>
            </div>
            <span className="rounded-full bg-slate-100 px-3.5 py-2 text-[13px] font-bold text-slate-600">
              Daily 2-Brief
            </span>
          </header>

          {/* 히어로 */}
          <section className="pt-8 pb-4">
            <div
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold text-slate-700 ${theme.badge}`}
            >
              <Sparkles className={`h-3.5 w-3.5 ${theme.badgeIcon}`} />
              AI 마켓 브리핑
            </div>

            <h1 className="mt-5 text-[2.4rem] font-black leading-[1.12] tracking-tight text-slate-950">
              매일 아침과 저녁,
              <br />
              시장을 읽는 시간을
              <br />
              <span
                className={`bg-gradient-to-r bg-clip-text text-transparent ${theme.grad}`}
              >
                하루가 대신할게요.
              </span>
            </h1>

            <p className="mt-5 text-[1.05rem] font-semibold leading-8 text-slate-500">
              흩어진 뉴스와 시세를 모아, 무엇에 왜 투자할지 판단할 맥락만 정리해
              드려요.
            </p>

            <Link
              href={`/brief/${period}`}
              className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 py-4 text-base font-bold text-white transition hover:bg-slate-800"
            >
              지금은 {periodLabel} 브리핑 보기
              <ArrowRight className="h-5 w-5" />
            </Link>

            {/* Today 프리뷰 카드 — 현재 시간대에 맞춰 표시 */}
            <Link
              href={`/brief/${period}`}
              className="mt-10 block rounded-[28px] border border-slate-200 bg-white p-5 shadow-card transition hover:border-slate-300"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-slate-400">Today 하루</p>
                  <p className="mt-1 text-xl font-black text-slate-950">
                    {pv.label}
                  </p>
                </div>
                <div
                  className={`flex h-11 w-11 items-center justify-center rounded-2xl text-white ${pv.tile}`}
                >
                  <Bot className="h-6 w-6" />
                </div>
              </div>
              <div className="mt-5 space-y-2.5">
                {pv.rows.map((r) => (
                  <div
                    key={r.label}
                    className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3"
                  >
                    <span className="text-sm font-semibold text-slate-500">
                      {r.label}
                    </span>
                    <span className="text-sm font-black text-slate-900">
                      {r.value}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-3 rounded-2xl bg-slate-50 p-4">
                <p className="text-sm font-semibold leading-6 text-slate-700">
                  {pv.note}
                </p>
              </div>
            </Link>
          </section>

          {/* 기능 */}
          <section className="pt-12 pb-4">
            <p className="text-sm font-black text-slate-500">기능</p>
            <h2 className="mt-3 text-3xl font-black leading-tight tracking-tight text-slate-950">
              투자 판단에 필요한 화면을
              <br />
              하나로 모았어요.
            </h2>

            <div className="mt-7 divide-y divide-slate-100 rounded-[28px] border border-slate-200 bg-white">
              {features.map((f) => {
                const Icon = f.icon;
                const Inner = (
                  <div className="flex items-center gap-4 p-5">
                    <div
                      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${
                        f.active
                          ? "bg-slate-100 text-slate-700"
                          : "bg-slate-50 text-slate-300"
                      }`}
                    >
                      <Icon className="h-6 w-6" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3
                          className={`text-base font-black ${
                            f.active ? "text-slate-950" : "text-slate-400"
                          }`}
                        >
                          {f.title}
                        </h3>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-bold tabular-nums ${
                            f.active
                              ? "bg-slate-100 text-slate-600"
                              : "bg-slate-50 text-slate-400"
                          }`}
                        >
                          {f.time}
                        </span>
                      </div>
                      <p className="mt-1 text-sm font-semibold leading-6 text-slate-500">
                        {f.description}
                      </p>
                    </div>
                    {f.active && (
                      <ArrowRight className="h-5 w-5 shrink-0 text-slate-300" />
                    )}
                  </div>
                );
                return f.active ? (
                  <Link
                    key={f.title}
                    href={f.href}
                    className="block transition hover:bg-slate-50/60"
                  >
                    {Inner}
                  </Link>
                ) : (
                  <div key={f.title}>{Inner}</div>
                );
              })}
            </div>
          </section>

          {/* 사용법 — 매거진 스타일 numbered */}
          <section className="pt-12 pb-14">
            <p className="text-sm font-black text-slate-500">사용법</p>
            <h2 className="mt-3 text-3xl font-black leading-tight tracking-tight text-slate-950">
              세 단계면
              <br />
              충분해요.
            </h2>

            <ol className="mt-10 space-y-9">
              {[
                {
                  num: "01",
                  title: "받기",
                  desc:
                    "아침 8시, 저녁 5시.\nAI가 시장을 정리해 매일 두 번 갱신해요.",
                },
                {
                  num: "02",
                  title: "살펴보기",
                  desc:
                    "브리핑부터 종목 차트까지 한 흐름으로.\n어려운 단어는 짚으면 바로 풀이가 떠요.",
                },
                {
                  num: "03",
                  title: "결정하기",
                  desc:
                    "마지막 판단은 본인의 증권사에서.\n하루는 추천하지 않고, 정리만 해드려요.",
                },
              ].map((s) => (
                <li
                  key={s.num}
                  className="grid grid-cols-[auto_1fr] items-start gap-5"
                >
                  <span
                    aria-hidden
                    className={`bg-gradient-to-br bg-clip-text text-[2.5rem] font-black leading-none tracking-tight text-transparent ${theme.grad}`}
                  >
                    {s.num}
                  </span>
                  <div>
                    <p className="text-[17px] font-black tracking-tight text-slate-950">
                      {s.title}
                    </p>
                    <p className="mt-2 whitespace-pre-line text-[14px] font-medium leading-7 text-slate-500">
                      {s.desc}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {/* 마무리 메시지 */}
          <section className="rounded-[32px] bg-slate-100 p-6">
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br text-white ${theme.close}`}
            >
              <Sparkles className="h-6 w-6" />
            </div>
            <h2 className="mt-5 text-2xl font-black leading-tight text-slate-950">
              읽고, 판단은
              <br />
              본인 증권사에서.
            </h2>
            <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">
              하루는 자동매매나 종목 추천을 하지 않아요. 매일 두 번, 결정에
              필요한 맥락만 전해드릴게요.
            </p>
          </section>

          <p className="px-1 pt-8 text-[11px] font-medium leading-relaxed text-slate-400">
            본 브리핑은 공개 정보를 AI가 정리한 참고 자료이며, 특정 종목
            매수·매도 권유가 아닙니다. 모든 투자 판단과 책임은 본인에게 있습니다.
          </p>
        </div>
      </div>
    </div>
  );
}
