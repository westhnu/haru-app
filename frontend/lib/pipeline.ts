import type { Brief, BriefResponse, BriefType, Source, VerifyResult } from "./types";
import { searchIssues } from "./tavily";
import {
  OPENAI_MODEL,
  VERIFY_MODEL,
  hasOpenAI,
  generateBriefWithGPT,
  verifyBriefWithGPT,
} from "./llm";
import { getMockBrief, getMockSources, getMockVerify } from "./mock";
import { getMarketDateInfo } from "./market";

/**
 * 브리핑 1건을 생성하는 전체 오케스트레이션:
 *   수집(Tavily) → 생성(gpt-5-mini, retry × 2) → 교차검증(gpt-4o-mini) → graceful degradation.
 *
 * 단일 vendor (OpenAI) — 자세한 결정 근거는 lib/llm.ts 참고.
 * 무거운 LLM 호출이 여기 모여 있다. 스케줄러/생성 엔드포인트에서만 호출하고,
 * 페이지 조회는 저장된 결과(store)를 읽는다.
 */
export async function generateBriefResponse(
  type: BriefType
): Promise<BriefResponse> {
  const warnings: string[] = [];
  let mode: "live" | "mock" = "live";
  let retried = false;
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

  // 2) 브리핑 생성 (gpt-5-mini, 일과성 장애 시 retry × 2)
  let brief: Brief | null = null;
  if (hasOpenAI()) {
    try {
      const result = await generateBriefWithGPT(sources, type, dateInfo);
      brief = result.brief;
      retried = result.retried;
      if (retried) {
        warnings.push("메인 모델 일과성 실패 → 재시도 후 회복");
      }
    } catch (e) {
      warnings.push(`GPT 생성 실패 (3회 재시도 모두): ${(e as Error).message}`);
    }
  } else {
    warnings.push("OPENAI_API_KEY 없음");
  }

  if (!brief) {
    brief = getMockBrief(type);
    mode = "mock";
    if (!warnings.some((w) => w.includes("모킹")))
      warnings.push("LLM 사용 불가 → 모킹 브리핑 사용");
  }

  // 3) 교차검증 (gpt-4o-mini, 다른 model family)
  let verify: VerifyResult | null = null;
  if (mode === "live" && hasOpenAI()) {
    try {
      verify = await verifyBriefWithGPT(sources, brief);
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
      verifyModel: VERIFY_MODEL,
      // 의미 재정의: vendor fallback 이 아니라 메인 모델 retry 가 발생했는지
      fallbackUsed: retried,
      warnings,
      generatedAt: new Date().toISOString(),
      forDate: dateInfo.label,
      marketNote: dateInfo.note,
    },
  };
}
