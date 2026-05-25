import type { FinancialRow } from "./stocktypes";

const BASE = "https://opendart.fss.or.kr/api";

const key = () => process.env.DART_API_KEY || "";

const WANTED: { label: string; names: string[] }[] = [
  { label: "매출액", names: ["매출액", "수익(매출액)", "영업수익", "매출"] },
  { label: "영업이익", names: ["영업이익", "영업이익(손실)"] },
  { label: "당기순이익", names: ["당기순이익", "당기순이익(손실)"] },
  { label: "자산총계", names: ["자산총계"] },
  { label: "부채총계", names: ["부채총계"] },
  { label: "자본총계", names: ["자본총계"] },
];

async function fetchYear(
  corpCode: string,
  year: string
): Promise<FinancialRow[] | null> {
  const url = `${BASE}/fnlttSinglAcntAll.json?crtfc_key=${key()}&corp_code=${corpCode}&bsns_year=${year}&reprt_code=11011&fs_div=CFS`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) return null;
  const data = (await res.json()) as {
    status: string;
    list?: { account_nm: string; thstrm_amount: string }[];
  };
  if (data.status !== "000" || !data.list) return null;

  const findAmount = (names: string[]): number | null => {
    for (const item of data.list!) {
      const nm = item.account_nm?.replace(/\s/g, "");
      if (names.some((n) => nm === n.replace(/\s/g, ""))) {
        const v = Number(item.thstrm_amount?.replace(/,/g, ""));
        return Number.isFinite(v) ? v : null;
      }
    }
    return null;
  };

  return WANTED.map((w) => ({ label: w.label, value: findAmount(w.names) }));
}

/** 재무제표 핵심 계정 (DART 단일회사 전체 재무제표) — 최신 연도부터 시도 */
export async function fetchFinancials(
  corpCode: string
): Promise<{ year: string | null; rows: FinancialRow[]; warning?: string }> {
  if (!key()) return { year: null, rows: [], warning: "DART_API_KEY 없음" };
  const thisYear = new Date().getFullYear();
  for (const year of [thisYear - 1, thisYear - 2]) {
    try {
      const rows = await fetchYear(corpCode, String(year));
      if (rows && rows.some((r) => r.value !== null)) {
        return { year: String(year), rows };
      }
    } catch {
      // 다음 연도 시도
    }
  }
  return { year: null, rows: [], warning: "DART 재무 데이터 없음" };
}
