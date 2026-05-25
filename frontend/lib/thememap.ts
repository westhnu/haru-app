import OpenAI from "openai";
import { GoogleGenerativeAI } from "@google/generative-ai";
import type { Source } from "./types";
import {
  OPENAI_MODEL,
  GEMINI_MODEL,
  hasOpenAI,
  hasGemini,
  geminiKey,
  extractJson,
} from "./llm";
import { searchIssues } from "./tavily";
import { getMarketDateInfo } from "./market";

// ── 이슈 → 테마 → 종목 매핑 타입 ──────────────────────────────

export type Confidence = "high" | "medium" | "low";

export interface ThemeStock {
  name: string;
  code?: string; // 국내 6자리
  symbol?: string; // 해외 티커
  reason?: string; // 이 종목이 묶이는 이유 (한 줄)
}

export interface ThemeItem {
  theme: string; // 테마명 (예: HBM·반도체)
  summary: string; // 한 줄 설명
  confidence: Confidence; // 매핑 신뢰도
  drivers: string[]; // 이 테마를 움직이는 이슈 키워드
  stocks: ThemeStock[]; // 관련 종목
}

export interface ThemeResponse {
  items: ThemeItem[];
  sources: Source[];
  meta: {
    mode: "live" | "mock";
    mainModel: string;
    fallbackUsed: boolean;
    warnings: string[];
    generatedAt: string;
    forDate?: string;
  };
}

// ── 모킹 ──────────────────────────────
const MOCK_ITEMS: ThemeItem[] = [
  {
    theme: "HBM·AI 반도체",
    summary: "(데모) AI 서버 수요로 고대역폭 메모리(HBM) 수요 전망이 강해졌어요.",
    confidence: "high",
    drivers: ["엔비디아 실적", "HBM 공급 부족", "AI 데이터센터 투자"],
    stocks: [
      { name: "SK하이닉스", code: "000660", reason: "HBM 핵심 공급사" },
      { name: "삼성전자", code: "005930", reason: "HBM 양산 확대" },
      { name: "엔비디아", symbol: "NVDA", reason: "AI 반도체 수요 견인" },
    ],
  },
  {
    theme: "2차전지",
    summary: "(데모) 미국 전기차 정책 뉴스로 변동성이 커질 수 있어요.",
    confidence: "medium",
    drivers: ["미 전기차 보조금", "전기차 수요 둔화 우려"],
    stocks: [
      { name: "LG에너지솔루션", code: "373220", reason: "정책 영향 직접" },
      { name: "삼성SDI", code: "006400", reason: "배터리 대형주" },
    ],
  },
  {
    theme: "금리·환율",
    summary: "(데모) 연준 신중론에 금리·환율 변동성이 부각됐어요.",
    confidence: "medium",
    drivers: ["연준 매파 발언", "원/달러 환율"],
    stocks: [{ name: "은행·금융주", reason: "금리 변화 민감" }],
  },
];

// ── 프롬프트 ──────────────────────────────
function buildThemePrompt(sources: Source[], dateLabel: string): string {
  const block = sources
    .map((s, i) => `[S${i + 1}] ${s.title}: ${s.content}`)
    .join("\n");
  return `당신은 한국 개인 투자자를 위한 "이슈 → 테마 → 종목" 매핑 분석가입니다. 오늘은 ${dateLabel}입니다.
아래 [원본 이슈]만 근거로, 오늘 시장에서 주목할 투자 테마 3~5개를 도출하세요.

규칙:
- 소스에 없는 사실·수치는 지어내지 마세요.
- 각 테마는 쉬운 한국어로. 어려운 용어는 짧게 풀어 쓰세요.
- 특정 종목 매수·매도 권유 금지. "관련 종목" 제시까지만.
- 관련 종목은 국내면 code(6자리), 해외면 symbol을 가능하면 채우고, 묶이는 이유를 한 줄로.
- confidence는 이슈 근거의 강도에 따라 high/medium/low.

아래 JSON만 출력 (코드블록 금지):
{
  "items": [
    {
      "theme": "테마명",
      "summary": "한 줄 설명",
      "confidence": "high|medium|low",
      "drivers": ["이 테마를 움직인 이슈 키워드", "..."],
      "stocks": [{"name":"종목명","code":"005930","reason":"한 줄 이유"}]
    }
  ]
}

[원본 이슈]
${block || "(수집된 이슈 없음 — 일반적 테마 위주로 작성)"}`;
}

async function genGPT(sources: Source[], dateLabel: string): Promise<ThemeItem[]> {
  const openai = new OpenAI();
  const r = await openai.chat.completions.create({
    model: OPENAI_MODEL,
    messages: [{ role: "user", content: buildThemePrompt(sources, dateLabel) }],
    response_format: { type: "json_object" },
  });
  const parsed = extractJson<{ items: ThemeItem[] }>(
    r.choices[0]?.message?.content ?? ""
  );
  return parsed.items ?? [];
}

async function genGemini(
  sources: Source[],
  dateLabel: string
): Promise<ThemeItem[]> {
  const genAI = new GoogleGenerativeAI(geminiKey()!);
  const model = genAI.getGenerativeModel({
    model: GEMINI_MODEL,
    generationConfig: { responseMimeType: "application/json" },
  });
  const res = await model.generateContent(buildThemePrompt(sources, dateLabel));
  const parsed = extractJson<{ items: ThemeItem[] }>(res.response.text());
  return parsed.items ?? [];
}

/** 이슈 수집 → LLM zero-shot 테마 매핑 (graceful degradation) */
export async function generateThemeMap(): Promise<ThemeResponse> {
  const warnings: string[] = [];
  let mode: "live" | "mock" = "live";
  let fallbackUsed = false;
  const dateInfo = getMarketDateInfo();

  let sources: Source[] = [];
  try {
    const r = await searchIssues("morning");
    sources = r.sources;
    if (r.warning) warnings.push(r.warning);
  } catch (e) {
    warnings.push(`이슈 수집 실패: ${(e as Error).message}`);
  }
  if (sources.length === 0) {
    mode = "mock";
    if (!warnings.length) warnings.push("수집 이슈 없음 → 모킹");
  }

  let items: ThemeItem[] | null = null;
  if (mode === "live" && hasOpenAI()) {
    try {
      items = await genGPT(sources, dateInfo.label);
    } catch (e) {
      warnings.push(`GPT 매핑 실패: ${(e as Error).message}`);
    }
  } else if (!hasOpenAI()) {
    warnings.push("OPENAI_API_KEY 없음");
  }

  if ((!items || items.length === 0) && mode === "live" && hasGemini()) {
    try {
      items = await genGemini(sources, dateInfo.label);
      fallbackUsed = true;
      warnings.push("GPT 불가 → Gemini로 매핑(fallback)");
    } catch (e) {
      warnings.push(`Gemini 매핑(fallback) 실패: ${(e as Error).message}`);
    }
  }

  if (!items || items.length === 0) {
    items = MOCK_ITEMS;
    mode = "mock";
    if (!warnings.some((w) => w.includes("모킹")))
      warnings.push("LLM 사용 불가 → 모킹 매핑");
  }

  return {
    items,
    sources,
    meta: {
      mode,
      mainModel: OPENAI_MODEL,
      fallbackUsed,
      warnings,
      generatedAt: new Date().toISOString(),
      forDate: dateInfo.label,
    },
  };
}

export function emptyThemeResponse(): ThemeResponse {
  const dateInfo = getMarketDateInfo();
  return {
    items: [],
    sources: [],
    meta: {
      mode: "mock",
      mainModel: OPENAI_MODEL,
      fallbackUsed: false,
      warnings: ["아직 분석된 테마가 없습니다."],
      generatedAt: "",
      forDate: dateInfo.label,
    },
  };
}
