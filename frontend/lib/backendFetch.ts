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
  } catch {
    throw new BackendApiError("백엔드에 연결할 수 없습니다 (localhost:8000 실행 여부 확인)", 0);
  }
  if (!r.ok) {
    // 프록시가 백엔드에 못 붙으면 Next가 500을 돌려준다.
    const hint = r.status >= 500 ? " — 백엔드 실행 여부를 확인하세요" : "";
    throw new BackendApiError(`요청 실패 (${r.status})${hint}`, r.status);
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
