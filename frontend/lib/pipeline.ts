import type { Brief, BriefResponse, BriefType, Source, VerifyResult } from "./types";
import { searchIssues } from "./tavily";
import {
  OPENAI_MODEL,
  GEMINI_MODEL,
  hasOpenAI,
  hasGemini,
  generateBriefWithGPT,
  generateBriefWithGemini,
  verifyBriefWithGemini,
} from "./llm";
import { getMockBrief, getMockSources, getMockVerify } from "./mock";
import { getMarketDateInfo } from "./market";

/**
 * 브리핑 1건을 생성하는 전체 오케스트레이션:
 *   수집(Tavily) → 생성(GPT, 실패 시 Gemini) → 교차검증(Gemini) → graceful degradation.
 * 무거운 LLM 호출이 여기 모여 있다. 스케줄러/생성 엔드포인트에서만 호출하고,
 * 페이지 조회는 저장된 결과(store)를 읽는다.
 */
export async function generateBriefResponse(
  type: BriefType
): Promise<BriefResponse> {
  const warnings: string[] = [];
  let mode: "live" | "mock" = "live";
  let fallbackUsed = false;
  const dateInfo = getMarketDateInfo();

  // 1) 이슈 수집
  let sources: Source[] = [];
  try {
    const r = await searchIssues(type);
    sources = r.sources;
    if (r.warning) warnings.push(r.warning);
  } catch (e) {
    warnings.push(`이슈 수집 실패: ${(e as Error).message}`);
  }
  if (sources.length === 0) {
    sources = getMockSources(type);
    mode = "mock";
    if (!warnings.length) warnings.push("수집 소스 없음 → 모킹 소스 사용");
  }

  // 2) 브리핑 생성 (GPT → Gemini fallback → 모킹)
  let brief: Brief | null = null;
  if (hasOpenAI()) {
    try {
      brief = await generateBriefWithGPT(sources, type, dateInfo);
    } catch (e) {
      warnings.push(`GPT 생성 실패: ${(e as Error).message}`);
    }
  } else {
    warnings.push("OPENAI_API_KEY 없음");
  }

  if (!brief && hasGemini()) {
    try {
      brief = await generateBriefWithGemini(sources, type, dateInfo);
      fallbackUsed = true;
      warnings.push("GPT 불가 → Gemini로 브리핑 생성(fallback)");
    } catch (e) {
      warnings.push(`Gemini 생성(fallback) 실패: ${(e as Error).message}`);
    }
  }

  if (!brief) {
    brief = getMockBrief(type);
    mode = "mock";
    if (!warnings.some((w) => w.includes("모킹")))
      warnings.push("LLM 사용 불가 → 모킹 브리핑 사용");
  }

  // 3) 교차검증 (Gemini) — fallback으로 Gemini가 생성했다면 자기검증 생략
  let verify: VerifyResult | null = null;
  if (mode === "live" && hasGemini() && !fallbackUsed) {
    try {
      verify = await verifyBriefWithGemini(sources, brief);
    } catch (e) {
      warnings.push(`교차검증 실패: ${(e as Error).message}`);
    }
  } else if (mode === "mock") {
    verify = getMockVerify();
  }

  return {
    type,
    brief,
    verify,
    sources,
    meta: {
      mode,
      mainModel: OPENAI_MODEL,
      verifyModel: GEMINI_MODEL,
      fallbackUsed,
      warnings,
      generatedAt: new Date().toISOString(),
      forDate: dateInfo.label,
      marketNote: dateInfo.note,
    },
  };
}
