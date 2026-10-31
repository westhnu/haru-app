// /backend/* 프록시(next.config rewrites → FastAPI /api/v1/*) 공통 호출.
// 로컬 백엔드(localhost:8000) 전제. 운영 Amplify에는 아직 백엔드가 없다.

export class BackendApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

export async function backendFetch<T>(url: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(url, { cache: "no-store", ...init });
  } catch (e) {
    if (init?.signal?.aborted) throw e; // 사용자 취소는 그대로 전달
    throw new BackendApiError("백엔드에 연결할 수 없습니다 (localhost:8000 실행 여부 확인)", 0);
  }
  if (!r.ok) {
    // FastAPI HTTPException은 {"detail": "사용자용 문구"}를 준다. 있으면 그 문구를 쓴다.
    let detail: string | null = null;
    try {
      const body = (await r.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* 본문 없음 */
    }
    // 프록시가 백엔드에 못 붙으면 Next가 500을 돌려준다.
    const hint = r.status >= 500 && !detail ? " — 백엔드 실행 여부를 확인하세요" : "";
    throw new BackendApiError(detail ?? `요청 실패 (${r.status})${hint}`, r.status);
  }
  return (r.status === 204 ? undefined : await r.json()) as T;
}

export function jsonBody(body: unknown): RequestInit {
  return { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
