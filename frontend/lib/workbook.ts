// Workbook API 타입·호출 (backend app/models/workbook.py와 1:1).
// next.config rewrites: /backend/* → FastAPI /api/v1/* (로컬 백엔드, 운영 Amplify에는 아직 없음)

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

export class WorkbookApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(url, { cache: "no-store", ...init });
  } catch {
    throw new WorkbookApiError("백엔드에 연결할 수 없습니다 (localhost:8000 실행 여부 확인)", 0);
  }
  if (!r.ok) {
    // 프록시가 백엔드에 못 붙으면 Next가 500을 돌려준다.
    const hint = r.status >= 500 ? " — 백엔드 실행 여부를 확인하세요" : "";
    throw new WorkbookApiError(`요청 실패 (${r.status})${hint}`, r.status);
  }
  return (r.status === 204 ? undefined : await r.json()) as T;
}

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

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
