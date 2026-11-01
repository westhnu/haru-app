// Workbook API 타입·호출 (backend app/models/workbook.py와 1:1).
// 호출은 lib/backendFetch.ts 공통 helper를 쓴다.
import { backendFetch } from "@/lib/backendFetch";

export { formatDateTime } from "@/lib/backendFetch";

export type BlockType = "memo" | "financial" | "news" | "chart" | "checklist_ref";

export const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  memo: "메모",
  financial: "재무",
  news: "뉴스",
  chart: "차트",
  checklist_ref: "체크리스트",
};

/** MVP(Sprint 3b)에서 추가 가능한 블록. backend SUPPORTED_BLOCK_TYPES와 맞춘다. */
export const SUPPORTED_BLOCK_TYPES: readonly BlockType[] = ["memo"];
export const MEMO_MAX_LENGTH = 1000;

export type WorkbookBlock = {
  id: string;
  block_type: BlockType;
  content: Record<string, unknown>;
  created_at: string;
};

export type Workbook = {
  id: string;
  stock_code: string;
  stock_name: string;
  title: string;
  blocks: WorkbookBlock[];
  created_at: string;
  updated_at: string;
};

type WorkbookListResponse = { workbooks: Workbook[]; total: number };

const BASE = "/backend/workbooks";
const request = backendFetch;

export async function listWorkbooks(stockCode?: string): Promise<Workbook[]> {
  const q = stockCode ? `?stock_code=${encodeURIComponent(stockCode)}` : "";
  return (await request<WorkbookListResponse>(`${BASE}${q}`)).workbooks;
}

export function createWorkbook(stockCode: string, stockName: string): Promise<Workbook> {
  return request<Workbook>(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      stock_code: stockCode,
      stock_name: stockName,
      title: `${stockName} 분석`,
    }),
  });
}

export function addMemoBlock(workbookId: string, text: string): Promise<WorkbookBlock> {
  return request<WorkbookBlock>(`${BASE}/${encodeURIComponent(workbookId)}/blocks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ block_type: "memo", content: { text } }),
  });
}

export function deleteBlock(workbookId: string, blockId: string): Promise<void> {
  return request<void>(
    `${BASE}/${encodeURIComponent(workbookId)}/blocks/${encodeURIComponent(blockId)}`,
    { method: "DELETE" }
  );
}

export function memoText(block: WorkbookBlock): string | null {
  const t = block.content.text;
  return block.block_type === "memo" && typeof t === "string" ? t : null;
}
