// ── 하루(Haru) 공유 타입 정의 ──────────────────────────────

/** 브리핑 종류 */
export type BriefType = "morning" | "evening";

export type Region = "해외" | "국내";

/** 종류별 메타 (라벨·시각·섹션 구성·섹션별 국내/해외 구분) */
export const BRIEF_META: Record<
  BriefType,
  {
    label: string;
    time: string;
    subtitle: string;
    sectionTitles: string[];
    regions: Region[];
  }
> = {
  morning: {
    label: "모닝 브리핑",
    time: "08:00",
    subtitle: "간밤 글로벌 시장에서 오늘 국내 장 영향까지",
    sectionTitles: [
      "글로벌 야간 이슈",
      "영향 테마·주식 (해외)",
      "원인 분석",
      "국내 장 영향 예측",
      "관련 국내 테마·종목",
    ],
    regions: ["해외", "해외", "해외", "국내", "국내"],
  },
  evening: {
    label: "이브닝 브리핑",
    time: "17:00",
    subtitle: "오늘 국내 장 마감에서 오늘 밤 미국 장 대비까지",
    sectionTitles: [
      "국내 장중 이슈",
      "영향 테마·주식 (국내)",
      "원인 분석",
      "미국 장 대비",
      "내일 아침 체크포인트",
    ],
    regions: ["국내", "국내", "국내", "해외", "해외"],
  },
};

/** Tavily 검색으로 수집한 원본 소스 1건 */
export interface Source {
  title: string;
  url: string;
  content: string;
  score?: number;
}

/** 브리핑 한 섹션 */
export interface BriefSection {
  title: string;
  summary: string;
  bullets?: string[];
  tickers?: { name: string; symbol?: string; code?: string; note?: string }[];
}

/** 완성된 브리핑 */
export interface Brief {
  oneLine: string;
  sections: BriefSection[];
  dataGaps?: string[];
}

/** Gemini 교차검증 결과 (LLM-as-judge) */
export interface VerifyResult {
  hallucinations: string[];
  inconsistencies: string[];
  advice_violations: string[];
  passed: boolean;
}

/** 저장·응답 단위 */
export interface BriefResponse {
  type: BriefType;
  /** 아직 생성된 브리핑이 없을 때 true */
  empty?: boolean;
  brief: Brief | null;
  verify: VerifyResult | null;
  sources: Source[];
  meta: {
    mode: "live" | "mock";
    mainModel: string;
    verifyModel: string;
    fallbackUsed: boolean;
    warnings: string[];
    /** 생성(저장) 시각 ISO */
    generatedAt: string;
    /** 브리핑 기준일 라벨 (예: "2026년 5월 25일 (월)") */
    forDate?: string;
    /** 휴장 안내 (개장일이면 없음) */
    marketNote?: string;
  };
}

export const DISCLAIMER =
  "본 브리핑은 공개 정보를 AI가 정리한 참고 자료이며, 특정 종목 매수·매도 권유가 아닙니다. 모든 투자 판단과 책임은 본인에게 있습니다.";
