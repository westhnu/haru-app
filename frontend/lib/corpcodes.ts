/**
 * 종목코드(6자리) → DART 고유번호(corp_code) 매핑 + 종목명.
 *
 * DART 재무·공시 API는 종목코드가 아닌 corp_code(8자리)를 요구한다.
 * 전체 매핑은 DART corpCode.zip(약 10만 종목)을 받아야 하지만, PoC에서는
 * 주요 종목만 하드코딩한다. 미등록 종목은 자동으로 모킹 데이터로 폴백된다.
 *
 * TODO(운영): corpCode.zip을 받아 빌드 타임에 전체 매핑 JSON 생성.
 */
export const CORP: Record<string, { corp: string; name: string; market: string }> = {
  "005930": { corp: "00126380", name: "삼성전자", market: "KOSPI" },
  "000660": { corp: "00164779", name: "SK하이닉스", market: "KOSPI" },
  "035420": { corp: "00266961", name: "NAVER", market: "KOSPI" },
  "035720": { corp: "00258801", name: "카카오", market: "KOSPI" },
  "005380": { corp: "00164742", name: "현대차", market: "KOSPI" },
  "006400": { corp: "00126362", name: "삼성SDI", market: "KOSPI" },
  "051910": { corp: "00356361", name: "LG화학", market: "KOSPI" },
  "373220": { corp: "01515323", name: "LG에너지솔루션", market: "KOSPI" },
  "207940": { corp: "00877059", name: "삼성바이오로직스", market: "KOSPI" },
  "000270": { corp: "00106641", name: "기아", market: "KOSPI" },
};

export function corpInfo(code: string) {
  return CORP[code];
}

// 종목명 → 종목코드 (별칭 포함). 브리핑이 코드 없이 이름만 줄 때 링크 연결용.
const NAME_TO_CODE: Record<string, string> = (() => {
  const m: Record<string, string> = {};
  for (const [code, info] of Object.entries(CORP)) m[info.name] = code;
  // 흔한 별칭
  m["네이버"] = "035420";
  m["하이닉스"] = "000660";
  m["LG엔솔"] = "373220";
  m["엘지에너지솔루션"] = "373220";
  return m;
})();

/** 이름으로 종목코드 찾기 (정확 일치 → 부분 포함 순). 없으면 undefined. */
export function nameToCode(name: string): string | undefined {
  if (!name) return undefined;
  const n = name.replace(/\s/g, "");
  if (NAME_TO_CODE[n]) return NAME_TO_CODE[n];
  for (const [key, code] of Object.entries(NAME_TO_CODE)) {
    if (n.includes(key) || key.includes(n)) return code;
  }
  return undefined;
}
