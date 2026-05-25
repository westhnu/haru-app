import type { Brief, BriefType, Source, VerifyResult } from "./types";

/** 키가 없거나 LLM 장애 시 사용하는 데모용 모킹 데이터.
 *  실제 시세·수치가 아닌 구조 시연용 샘플임을 명시한다. */

const MORNING_SOURCES: Source[] = [
  {
    title: "[샘플] 미 증시, 반도체 강세에 나스닥 상승 마감",
    url: "https://example.com/news/1",
    content:
      "(데모 데이터) 간밤 뉴욕 증시에서 AI 반도체주가 강세를 보이며 나스닥이 상승 마감했다. HBM 수요 전망이 재차 부각됐다.",
    score: 0.94,
  },
  {
    title: "[샘플] 연준 위원 매파 발언에 채권 금리 소폭 상승",
    url: "https://example.com/news/2",
    content:
      "(데모 데이터) 한 연준 위원이 금리 인하에 신중해야 한다고 발언하면서 미 국채 금리가 소폭 올랐다.",
    score: 0.88,
  },
];

const EVENING_SOURCES: Source[] = [
  {
    title: "[샘플] 코스피, 외국인 순매수에 강보합 마감",
    url: "https://example.com/news/4",
    content:
      "(데모 데이터) 오늘 코스피는 외국인 순매수가 유입되며 강보합으로 마감했다. 반도체 대형주가 지수를 떠받쳤다.",
    score: 0.91,
  },
  {
    title: "[샘플] 오늘 밤 미국 CPI 발표 예정",
    url: "https://example.com/news/5",
    content:
      "(데모 데이터) 오늘 밤(한국시각) 미국 소비자물가지수(CPI) 발표가 예정돼 있어 시장의 관망세가 짙다.",
    score: 0.86,
  },
];

const MORNING_BRIEF: Brief = {
  oneLine:
    "(데모) 간밤 미국 증시는 AI 반도체 강세로 나스닥이 올랐고, 연준 매파 발언으로 금리가 소폭 상승했습니다. 오늘 국내 장은 반도체 동조·2차전지 변동성에 주목할 만합니다.",
  sections: [
    {
      title: "글로벌 야간 이슈",
      summary:
        "(데모) 뉴욕 증시는 AI 반도체주 강세로 나스닥이 상승 마감했고, 연준 위원의 신중론에 미 국채 금리가 소폭 올랐습니다.",
      bullets: [
        "AI 반도체·HBM 수요 전망 재부각",
        "연준 매파 발언으로 금리 인하 기대 일부 후퇴",
      ],
    },
    {
      title: "영향 테마·주식 (해외)",
      summary: "(데모) 반도체·AI 인프라 관련 종목이 상승을 주도했습니다.",
      tickers: [
        { name: "엔비디아", symbol: "NVDA", note: "AI 반도체 대장주" },
        { name: "마이크론", symbol: "MU", note: "HBM 수혜" },
      ],
    },
    {
      title: "원인 분석",
      summary:
        "(데모) HBM 공급 부족·수요 강세 전망이 반도체 섹터 투자심리를 끌어올린 것으로 해석됩니다. 다만 금리 변수는 단기 변동성 요인입니다.",
    },
    {
      title: "국내 장 영향 예측",
      summary:
        "(데모) 미국 반도체 강세에 동조해 국내 반도체 대형주가 강세를 보일 가능성이 있으나, 금리·환율 변수로 상승폭은 제한될 수 있습니다.",
    },
    {
      title: "관련 국내 테마·종목",
      summary: "(데모) 오늘 국내 장에서 주목할 후보 테마입니다.",
      tickers: [
        { name: "삼성전자", code: "005930", note: "미국 반도체 동조 기대" },
        { name: "SK하이닉스", code: "000660", note: "HBM 공급망 수혜 관심" },
        { name: "LG에너지솔루션", code: "373220", note: "미 정책 뉴스로 변동성 확대" },
      ],
    },
  ],
  dataGaps: [
    "실시간 지수·환율 수치는 본 데모에 포함되지 않았습니다 (시세 API 연동은 V2).",
  ],
};

const EVENING_BRIEF: Brief = {
  oneLine:
    "(데모) 오늘 코스피는 외국인 순매수로 강보합 마감했습니다. 오늘 밤 미국 CPI 발표를 앞두고 관망세가 짙어, 변동성에 유의할 시점입니다.",
  sections: [
    {
      title: "국내 장중 이슈",
      summary:
        "(데모) 외국인 순매수가 유입되며 반도체 대형주 중심으로 코스피가 강보합 마감했습니다.",
      bullets: ["외국인 순매수 유입", "반도체 대형주가 지수 견인"],
    },
    {
      title: "영향 테마·주식 (국내)",
      summary: "(데모) 반도체·AI 관련주가 상대적으로 견조했습니다.",
      tickers: [
        { name: "삼성전자", code: "005930", note: "외국인 매수 집중" },
        { name: "NAVER", code: "035420", note: "AI 소프트웨어 테마 강세" },
      ],
    },
    {
      title: "원인 분석",
      summary:
        "(데모) 미국 반도체 강세 흐름이 국내로 이어지며 외국인 수급이 개선된 것으로 보입니다.",
    },
    {
      title: "미국 장 대비",
      summary:
        "(데모) 오늘 밤 미국 CPI 발표가 최대 변수입니다. 결과에 따라 금리·기술주 변동성이 커질 수 있습니다.",
      tickers: [{ name: "美 CPI 발표", note: "오늘 밤 한국시각 예정" }],
    },
    {
      title: "내일 아침 체크포인트",
      summary:
        "(데모) CPI 결과와 미국 기술주 마감 흐름을 확인한 뒤 내일 국내 장 방향을 가늠하세요.",
    },
  ],
  dataGaps: ["실시간 지수·종목 등락률은 본 데모에 포함되지 않았습니다 (V2)."],
};

const PASS_VERIFY: VerifyResult = {
  hallucinations: [],
  inconsistencies: [],
  advice_violations: [],
  passed: true,
};

export function getMockSources(type: BriefType): Source[] {
  return type === "morning" ? MORNING_SOURCES : EVENING_SOURCES;
}

export function getMockBrief(type: BriefType): Brief {
  return type === "morning" ? MORNING_BRIEF : EVENING_BRIEF;
}

export function getMockVerify(): VerifyResult {
  return PASS_VERIFY;
}
