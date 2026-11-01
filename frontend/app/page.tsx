import Link from "next/link";
import {
  ArrowRight,
  Sunrise,
  Sunset,
  Sparkles,
  Network,
  BookOpen,
  NotebookPen,
  Book,
  ChevronDown,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import type { BriefType } from "@/lib/types";
import { readBrief } from "@/lib/store";
import { HARU_BACKEND_ENABLED } from "@/lib/featureFlags";
import TodayCard from "@/components/TodayCard";
import { Card } from "@/components/layout/Card";
import { PageHeader } from "@/components/layout/PageHeader";
import { PageShell } from "@/components/layout/PageShell";
import { Section } from "@/components/layout/Section";
import { Badge } from "@/components/ui/Badge";

// 현재 시각을 반영해야 하므로 매 요청 렌더
export const dynamic = "force-dynamic";

type Feature = {
  key: string;
  href: string;
  title: string;
  time: string;
  description: string;
  icon: typeof Sunrise;
  active: boolean;
  /** 로컬 FastAPI 백엔드가 있어야 동작 (NEXT_PUBLIC_HARU_BACKEND=1일 때만 노출) */
  backend?: boolean;
};

const features: Feature[] = [
  {
    key: "morning",
    href: "/brief/morning",
    title: "모닝 브리핑",
    time: "08:00",
    description: "간밤 글로벌 시장이 오늘 국내 장에 줄 영향을 정리해 드려요.",
    icon: Sunrise,
    active: true,
  },
  {
    key: "evening",
    href: "/brief/evening",
    title: "이브닝 브리핑",
    time: "17:00",
    description: "오늘 국내 장 마감을 짚고, 오늘 밤 미국 장 포인트를 챙겨 보세요.",
    icon: Sunset,
    active: true,
  },
  {
    key: "themes",
    href: "/themes",
    title: "이슈·테마 매핑",
    time: "신규",
    description: "하나의 이슈가 어떤 테마·종목으로 번지는지 살펴보세요.",
    icon: Network,
    active: true,
  },
  {
    key: "workbook",
    href: "/workbook",
    title: "내 워크북",
    time: "신규",
    description: "종목별 분석 메모를 한곳에 모아 두세요.",
    icon: BookOpen,
    active: true,
    backend: true,
  },
  {
    key: "journal",
    href: "/journal",
    title: "투자 저널",
    time: "신규",
    description: "지난 결정을 저널에서 되돌아보세요. 가상 포지션도 함께 볼 수 있어요.",
    icon: NotebookPen,
    active: true,
    backend: true,
  },
  {
    key: "glossary",
    href: "/glossary",
    title: "용어 사전",
    time: "AI",
    description: "어려운 투자 용어를 Bedrock Knowledge Base 근거로 풀어 드려요.",
    icon: Book,
    active: true,
    backend: true,
  },
];

// 사용법 3단계 (말투 가이드 F1.5: 제목은 L3 라벨, 설명은 L2 서비스 톤).
// 플래그 off(운영)는 브리핑 흐름, on(로컬)은 결정 흐름.
const STEPS_BRIEF = [
  { num: "01", title: "받기", desc: "아침 8시, 저녁 5시.\nAI가 시장을 정리해 하루 두 번 갱신해요." },
  {
    num: "02",
    title: "살펴보기",
    desc: "브리핑부터 종목 차트까지 한 흐름으로 이어져요.\n어려운 단어는 눌러서 바로 풀이를 볼 수 있어요.",
  },
  { num: "03", title: "결정하기", desc: "마지막 판단은 본인 증권사에서 하세요.\n추천 없이 정리만 해 드려요." },
];
const STEPS_BACKEND = [
  { num: "01", title: "종목 검색", desc: "궁금한 종목을 검색해요." },
  { num: "02", title: "체크리스트 · AI 평가", desc: "체크리스트를 채우고 AI 평가로 교차 확인해요." },
  { num: "03", title: "결정 기록 · 회고", desc: "결정을 저널에 기록하고 다시 돌아봐요." },
];

// 플래그 on(로컬): 지금 시간대 브리핑 + 투자 저널만 먼저 보여주고 나머지는 접는다 (선택 피로 감소).
const PRIMARY_KEYS_ON: Record<BriefType, string[]> = {
  morning: ["morning", "journal"],
  evening: ["evening", "journal"],
};

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

const TILE: Record<BriefType, string> = {
  morning: "bg-gradient-to-br from-amber-400 to-orange-500",
  evening: "bg-gradient-to-br from-indigo-400 to-violet-500",
};

const LABEL: Record<BriefType, string> = {
  morning: "모닝 브리핑",
  evening: "이브닝 브리핑",
};

function timeAgo(iso?: string): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return "";
  const m = Math.floor(ms / 60000);
  if (m < 1) return "방금";
  if (m < 60) return `${m}분 전`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
}

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

export default async function Home() {
  const period = currentPeriod();
  const theme = THEME[period];
  const periodLabel = period === "morning" ? "모닝" : "이브닝";
  const HeroIcon = period === "morning" ? Sunrise : Sunset;
  // S3에서 저장된 라이브 브리핑을 가져와 메인 카드에 노출.
  const data = await readBrief(period).catch(() => null);
  const briefResp = data && !data.empty ? data : null;
  const oneLine = briefResp?.brief?.oneLine ?? null;
  const verifyPassed = briefResp?.verify?.passed ?? null;
  const generatedAt = briefResp?.meta?.generatedAt;
  const isLive = briefResp?.meta?.mode === "live";

  // 플래그 off(운영 Amplify): 기존 목록 그대로 두되, 백엔드가 있어야 동작하는 카드는 뺀다.
  // 플래그 on(로컬): 핵심 2개 + "모든 기능 보기" 접힘.
  const visible = features.filter((f) => HARU_BACKEND_ENABLED || !f.backend);
  const primaryKeys = PRIMARY_KEYS_ON[period];
  const primary = HARU_BACKEND_ENABLED
    ? primaryKeys.map((k) => visible.find((f) => f.key === k)).filter((f): f is Feature => !!f)
    : visible;
  const more = HARU_BACKEND_ENABLED ? visible.filter((f) => !primaryKeys.includes(f.key)) : [];

  const renderFeature = (f: Feature) => {
    const Icon = f.icon;
    const Inner = (
      <div className="flex items-center gap-4 p-5">
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${
            f.active
              ? "bg-surface-muted text-fg"
              : "bg-surface-muted text-fg-subtle"
          }`}
        >
          <Icon className="h-6 w-6" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3
              className={`text-base font-black ${
                f.active ? "text-fg" : "text-fg-subtle"
              }`}
            >
              {f.title}
            </h3>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-bold tabular-nums ${
                f.active
                  ? "bg-surface-muted text-fg-muted"
                  : "bg-surface-muted text-fg-subtle"
              }`}
            >
              {f.time}
            </span>
          </div>
          <p className="mt-1 text-sm font-semibold leading-6 text-fg-muted">
            {f.description}
          </p>
        </div>
        {f.active && (
          <ArrowRight className="h-5 w-5 shrink-0 text-fg-subtle" />
        )}
      </div>
    );
    return f.active ? (
      <Link
        key={f.key}
        href={f.href}
        className="block transition hover:bg-surface-muted"
      >
        {Inner}
      </Link>
    ) : (
      <div key={f.key}>{Inner}</div>
    );
  };

  return (
    // Phase F2: PageShell(모바일 우선 폭·BottomNav 여백). 시간대 glow는 셸 뒤 배경으로 둔다.
    <div className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 z-0 h-80"
        style={{ background: theme.glow }}
      />
      <PageShell className="relative z-10">
          {/* 상단 바 — 브랜드 헤더 (뒤로가기 없음) */}
          <PageHeader title="하루 HARU" action={<Badge variant="outline">Daily 2-Brief</Badge>} />

          {/* 히어로 */}
          <section className="pt-8 pb-4">
            <div
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold text-fg ${theme.badge}`}
            >
              <Sparkles className={`h-3.5 w-3.5 ${theme.badgeIcon}`} />
              AI 마켓 브리핑
            </div>

            <h1 className="mt-5 text-[2.4rem] font-black leading-[1.12] tracking-tight text-fg">
              매일 아침·저녁,
              <br />
              시장을 정리하고
              <br />
              <span
                className={`bg-gradient-to-r bg-clip-text text-transparent ${theme.grad}`}
              >
                투자 결정을 기록하세요.
              </span>
            </h1>

            <p className="mt-5 text-[1.05rem] font-semibold leading-8 text-fg-muted">
              흩어진 뉴스와 시세를 Haru가 정리해 드려요. 판단은 본인의 몫이에요.
            </p>

            <Link
              href={`/brief/${period}`}
              className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-fg px-5 py-4 text-base font-bold text-surface transition hover:bg-fg/90"
            >
              지금은 {periodLabel} 브리핑 보기
              <ArrowRight className="h-5 w-5" />
            </Link>

            {/* Today 카드 — S3에 저장된 실제 라이브 브리핑 사용 */}
            <Link
              href={`/brief/${period}`}
              className="group relative mt-10 block overflow-hidden rounded-[28px] border border-border bg-surface p-6 shadow-card transition hover:-translate-y-0.5 hover:border-border hover:shadow-lg"
            >
              {/* 상단 그라데이션 hint (시간대 색) */}
              <span
                aria-hidden
                className={`absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r ${theme.grad}`}
              />

              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-black uppercase tracking-[0.18em] text-fg-subtle">
                    Today · 하루
                  </p>
                  <p className="mt-1.5 text-[22px] font-black tracking-tight text-fg">
                    {LABEL[period]}
                  </p>
                  {/* editorial inline meta — 점(·)으로 구분 */}
                  <div className="mt-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs font-bold leading-none">
                    {verifyPassed === true && (
                      <span className="inline-flex items-center gap-1 text-emerald-700">
                        <CheckCircle2 className="h-3 w-3" />
                        교차검증 통과
                      </span>
                    )}
                    {verifyPassed === false && (
                      <span className="inline-flex items-center gap-1 text-amber-700">
                        <AlertCircle className="h-3 w-3" />
                        검증 주의
                      </span>
                    )}
                    {generatedAt && (
                      <>
                        {verifyPassed !== null && (
                          <span aria-hidden className="text-fg-subtle">·</span>
                        )}
                        <span className="text-fg-subtle">
                          업데이트 {timeAgo(generatedAt)}
                        </span>
                      </>
                    )}
                    {!isLive && oneLine && (
                      <>
                        <span aria-hidden className="text-fg-subtle">·</span>
                        <span className="text-amber-600">직전 라이브 데이터</span>
                      </>
                    )}
                  </div>
                </div>
                <div
                  className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-white shadow-soft ${TILE[period]}`}
                >
                  <HeroIcon className="h-6 w-6" />
                </div>
              </div>

              {/* 본문 — 좌측 accent line + 살짝 editorial 톤 */}
              <blockquote className="relative mt-6 pl-4">
                <span
                  aria-hidden
                  className={`absolute inset-y-1 left-0 w-[3px] rounded-full bg-gradient-to-b ${theme.grad}`}
                />
                <p className="text-sm font-semibold leading-[1.7] text-fg">
                  {oneLine ??
                    "첫 브리핑을 기다리고 있어요. 매일 08:00·17:00 KST에 자동으로 갱신돼요."}
                </p>
              </blockquote>

              {/* 우측 정렬 CTA */}
              <div className="mt-5 flex items-center justify-end gap-1.5 text-xs font-bold text-fg-muted transition group-hover:text-fg">
                자세히 보기
                <ArrowRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
              </div>
            </Link>
          </section>

          {/* 오늘의 흐름 — 플래그 off거나 백엔드에 닿지 않으면 렌더링 안 함 */}
          <TodayCard />

          {/* 기능 */}
          <Section title="기능" className="pt-lg">
            <p className="text-2xl font-black leading-tight tracking-tight text-fg">
              투자 판단에 필요한 화면을
              <br />
              한곳에 모았어요.
            </p>
            <Card padded={false} className="divide-y divide-border-subtle">
              {primary.map(renderFeature)}
            </Card>
            {more.length > 0 && (
              <details className="group rounded-lg border border-border-subtle bg-surface-elevated">
                <summary className="flex cursor-pointer list-none items-center justify-between px-5 py-4 text-sm font-black text-fg [&::-webkit-details-marker]:hidden">
                  모든 기능 보기
                  <span className="flex items-center gap-1 text-xs font-bold text-fg-subtle">
                    {more.length}개
                    <ChevronDown className="h-4 w-4 transition group-open:rotate-180" />
                  </span>
                </summary>
                <div className="divide-y divide-border-subtle border-t border-border-subtle">
                  {more.map(renderFeature)}
                </div>
              </details>
            )}
          </Section>
          {/* 사용법 — 매거진 스타일 numbered */}
          <Section title="사용법" className="pt-lg pb-xl">
            <p className="text-2xl font-black leading-tight tracking-tight text-fg">
              세 단계면
              <br />
              충분해요.
            </p>

            <ol className="mt-10 space-y-9">
              {(HARU_BACKEND_ENABLED ? STEPS_BACKEND : STEPS_BRIEF).map((s) => (
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
                    <p className="text-base font-black tracking-tight text-fg">
                      {s.title}
                    </p>
                    <p className="mt-2 whitespace-pre-line text-sm font-medium leading-7 text-fg-muted">
                      {s.desc}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </Section>

          {/* 마무리 메시지 — 플래그 on(로컬)에서는 '오늘의 흐름'과 역할이 겹쳐 숨긴다 */}
          {!HARU_BACKEND_ENABLED && (
          <section className="rounded-[32px] bg-surface-muted p-6">
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br text-white ${theme.close}`}
            >
              <Sparkles className="h-6 w-6" />
            </div>
            <h2 className="mt-5 text-2xl font-black leading-tight text-fg">
              읽고, 판단은
              <br />
              본인 증권사에서.
            </h2>
            <p className="mt-3 text-sm font-semibold leading-6 text-fg-muted">
              자동매매나 종목 추천은 하지 않아요. 하루 두 번, 결정에 필요한 맥락만 전해 드려요.
            </p>
          </section>
          )}

          <p className="px-1 pt-8 text-xs font-medium leading-relaxed text-fg-subtle">
            본 브리핑은 공개 정보를 AI가 정리한 참고 자료이며, 특정 종목의 매수·매도 권유가
            아니에요. 투자 판단과 책임은 본인에게 있어요.
          </p>
      </PageShell>
    </div>
  );
}
