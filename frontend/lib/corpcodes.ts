import krxCodes from "./krx-codes.json";

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

/**
 * 종목명 → 6자리 종목코드 (KIS 시세·지표·수급 조회용).
 * DART corp_code(CORP)와 별개로, 브리핑/테마가 코드 없이 이름만 줄 때 링크를 코드로 변환한다.
 * 인기·빈출 종목 위주의 큐레이션 목록(연 1회 갱신/확장 권장). 미등록 종목은 데모로 폴백.
 */
const EXTRA_CODES: Record<string, string> = {
  삼성전기: "009150",
  에코프로: "086520",
  에코프로비엠: "247540",
  삼화콘덴서: "001820",
  POSCO홀딩스: "005490",
  포스코퓨처엠: "003670",
  현대모비스: "012330",
  KB금융: "105560",
  신한지주: "055550",
  하나금융지주: "086790",
  셀트리온: "068270",
  한미반도체: "042700",
  한화에어로스페이스: "012450",
  두산에너빌리티: "034020",
  카카오뱅크: "323410",
  크래프톤: "259960",
  LG전자: "066570",
  SK이노베이션: "096770",
  고려아연: "010130",
  삼성물산: "028260",
  HD현대중공업: "329180",
  삼성생명: "032830",
  현대글로비스: "086280",
  엔씨소프트: "036570",
};

// 별칭 + 큐레이션 (부분 일치 폴백은 이 작은 집합에만 적용)
const CURATED: Record<string, string> = (() => {
  const m: Record<string, string> = {};
  for (const [code, info] of Object.entries(CORP)) m[info.name] = code;
  for (const [name, code] of Object.entries(EXTRA_CODES)) m[name] = code;
  m["네이버"] = "035420";
  m["하이닉스"] = "000660";
  m["LG엔솔"] = "373220";
  m["엘지에너지솔루션"] = "373220";
  m["포스코홀딩스"] = "005490";
  m["에코프로BM"] = "247540";
  return m;
})();

// KRX 전체 매핑(scripts/build-krx.mjs로 생성). 비어 있으면 큐레이션만 사용.
const KRX = krxCodes as Record<string, string>;

// 정확 일치 조회용 (공백 제거 키도 함께 등록, 큐레이션이 우선)
const EXACT: Record<string, string> = (() => {
  const m: Record<string, string> = {};
  for (const [k, v] of Object.entries({ ...KRX, ...CURATED })) {
    m[k] = v;
    m[k.replace(/\s/g, "")] = v;
  }
  return m;
})();

/** 이름으로 종목코드 찾기.
 *  1) 정확 일치(KRX 전체 + 큐레이션) → 2) 큐레이션 대상 부분 일치. 없으면 undefined. */
export function nameToCode(name: string): string | undefined {
  if (!name) return undefined;
  const n = name.replace(/\s/g, "");
  if (EXACT[n]) return EXACT[n];
  // 공백 제거 후 KRX 키와 정확 일치도 시도
  for (const [key, code] of Object.entries(CURATED)) {
    if (n.includes(key) || key.includes(n)) return code;
  }
  return undefined;
}
