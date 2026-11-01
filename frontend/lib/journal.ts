// Journal API 타입·호출 (backend app/models/journal.py와 1:1).
// 원칙 1: decision은 사용자 본인의 기록이다 (AI 권유 아님).
// 원칙 4: 가상 기록이며 실제 주문·거래를 만들지 않는다. 함수·파일 이름에 order/trade/bid/ask를 쓰지 않는다.
import { backendFetch, jsonBody } from "@/lib/backendFetch";

export type Decision = "buy" | "sell" | "hold" | "watch";

export const DECISION_LABELS: Record<Decision, string> = {
  buy: "매수 결정",
  sell: "매도 결정",
  hold: "보유",
  watch: "관망",
};
export const DECISION_ORDER: readonly Decision[] = ["watch", "hold", "buy", "sell"];
/** 가상 수량·단가를 받는 결정. 가상 포지션은 buy만 합산한다. */
export const DECISIONS_WITH_POSITION: readonly Decision[] = ["buy", "sell"];
export const REASONING_MAX_LENGTH = 1000;

export type JournalEntry = {
  id: string;
  stock_code: string;
  stock_name: string;
  decision: Decision;
  reasoning: string;
  checklist_id: string | null;
  workbook_id: string | null;
  virtual_price: number | null;
  virtual_quantity: number | null;
  created_at: string;
};

export type DecisionInput = {
  stock_code: string;
  stock_name: string;
  decision: Decision;
  reasoning: string;
  checklist_id?: string | null;
  workbook_id?: string | null;
  virtual_price?: number | null;
  virtual_quantity?: number | null;
};

/** 가상 포지션 (buy 합산). 시세 연동 전이라 현재가·손익은 없다. */
export type VirtualPosition = {
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_price: number;
};

const BASE = "/backend/journal";

export async function listEntries(stockCode?: string): Promise<JournalEntry[]> {
  const q = stockCode ? `?stock_code=${encodeURIComponent(stockCode)}` : "";
  return (await backendFetch<{ entries: JournalEntry[] }>(`${BASE}/entries${q}`)).entries;
}

export function recordDecision(input: DecisionInput): Promise<JournalEntry> {
  return backendFetch<JournalEntry>(`${BASE}/entries`, { method: "POST", ...jsonBody(input) });
}

export function deleteEntry(entryId: string): Promise<void> {
  return backendFetch<void>(`${BASE}/entries/${encodeURIComponent(entryId)}`, {
    method: "DELETE",
  });
}

export async function getVirtualPositions(): Promise<VirtualPosition[]> {
  return (await backendFetch<{ positions: VirtualPosition[] }>(`${BASE}/portfolio`)).positions;
}
