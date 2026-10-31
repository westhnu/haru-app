// Checklist API 타입·호출 (backend app/models/checklist.py와 1:1).
// MVP: 사용자가 원칙별 상태를 직접 고른다. AI 채점은 다음 단계 (근거 출처 필수, 원칙 2).
import { backendFetch, jsonBody } from "@/lib/backendFetch";

export type ItemStatus = "satisfied" | "unsatisfied" | "uncertain";

export const STATUS_LABELS: Record<ItemStatus, string> = {
  satisfied: "충족",
  unsatisfied: "미충족",
  uncertain: "판단 어려움",
};
export const STATUS_ORDER: readonly ItemStatus[] = ["satisfied", "unsatisfied", "uncertain"];
export const PRINCIPLE_MAX_LENGTH = 200;
export const REASONING_MAX_LENGTH = 1000;

export type ChecklistItem = {
  id: string;
  principle: string;
  status: ItemStatus;
  reasoning: string;
};

export type Checklist = {
  id: string;
  stock_code: string;
  stock_name: string;
  items: ChecklistItem[];
  created_at: string;
  updated_at: string;
};

const BASE = "/backend/checklists";
const item = (clId: string, itemId?: string) =>
  `${BASE}/${encodeURIComponent(clId)}/items${itemId ? `/${encodeURIComponent(itemId)}` : ""}`;

export async function listChecklists(stockCode: string): Promise<Checklist[]> {
  const r = await backendFetch<{ checklists: Checklist[] }>(
    `${BASE}?stock_code=${encodeURIComponent(stockCode)}`
  );
  return r.checklists;
}

export function createChecklist(stockCode: string, stockName: string): Promise<Checklist> {
  return backendFetch<Checklist>(BASE, {
    method: "POST",
    ...jsonBody({ stock_code: stockCode, stock_name: stockName }),
  });
}

export function addItem(checklistId: string, principle: string): Promise<ChecklistItem> {
  return backendFetch<ChecklistItem>(item(checklistId), {
    method: "POST",
    ...jsonBody({ principle }),
  });
}

export function updateItem(
  checklistId: string,
  itemId: string,
  patch: { status?: ItemStatus; reasoning?: string }
): Promise<ChecklistItem> {
  return backendFetch<ChecklistItem>(item(checklistId, itemId), {
    method: "PATCH",
    ...jsonBody(patch),
  });
}

export function deleteItem(checklistId: string, itemId: string): Promise<void> {
  return backendFetch<void>(item(checklistId, itemId), { method: "DELETE" });
}

/** 화면 즉시 반영용 점수. backend GET /{id}/score와 같은 계산(충족 / 전체 × 100, 소수 1자리). */
export function scoreOf(items: ChecklistItem[]): { satisfied: number; total: number; pct: number } {
  const total = items.length;
  const satisfied = items.filter((i) => i.status === "satisfied").length;
  return { satisfied, total, pct: total ? Math.round((satisfied / total) * 1000) / 10 : 0 };
}

// --- Phase B: AI 평가 (제안만, 저장은 사용자가 updateItem으로) ---------------------------

export type EvaluationSource = "bedrock" | "template" | "mock";

export const EVALUATION_SOURCE_LABELS: Record<EvaluationSource, string> = {
  bedrock: "Bedrock AI 평가",
  template: "판단 보류 (데이터 부족·검증 실패)",
  mock: "개발용 데이터",
};

export type StockSource = { name: string; url: string };

export type AiEvaluation = {
  suggested_status: ItemStatus;
  reasoning: string;
  sources: StockSource[];
  used_facts: string[];
  evaluation_source: EvaluationSource;
  report_label: string;
  disclaimer: string;
};

/** AI 평가는 DART 종목(6자리 코드)만 지원한다. 해외 종목은 버튼을 숨긴다. */
export function supportsAiEvaluation(stockCode: string): boolean {
  return /^\d{6}$/.test(stockCode);
}

export function evaluateItem(
  checklistId: string,
  itemId: string,
  signal?: AbortSignal
): Promise<AiEvaluation> {
  return backendFetch<AiEvaluation>(`${item(checklistId, itemId)}/evaluate`, {
    method: "POST",
    signal,
  });
}
