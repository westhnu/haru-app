// 홈 '오늘의 흐름' (backend app/models/today.py와 1:1).
import { backendFetch } from "@/lib/backendFetch";

export type NextAction = "empty" | "checklist_incomplete" | "review_decision" | "start_new";

export type TodayCard = {
  next_action: NextAction;
  message: string;
  cta_label: string;
  /** empty는 링크 대신 종목 검색 다이얼로그를 연다 (빈 문자열). */
  cta_href: string;
  context: Record<string, string | number>;
  disclaimer: string;
};

export function fetchTodayCard(signal?: AbortSignal): Promise<TodayCard> {
  return backendFetch<TodayCard>("/backend/today", { signal });
}
