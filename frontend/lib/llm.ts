import OpenAI from "openai";
import type { Brief, BriefType, Source, VerifyResult } from "./types";
import type { MarketDateInfo } from "./market";
import { buildBriefPrompt, buildVerifyPrompt } from "./prompts";

/**
 * LLM 오케스트레이션 — OpenAI 단일 vendor, 다른 model family 로 교차검증.
 *
 * - 메인 생성: OPENAI_MODEL (기본 gpt-5-mini)
 * - 교차검증(LLM-as-judge): VERIFY_MODEL (기본 gpt-4o-mini, 다른 model family)
 * - 일과성 장애 대비: 메인 호출은 retry × 2 with exponential backoff
 *
 * 멀티 vendor (Gemini 등) 대신 단일 vendor 를 택한 이유:
 *   1) 운영 단순화 — API key·SDK·응답 schema 모두 1개
 *   2) Vendor outage 자체보다 일과성 rate-limit/timeout 이 압도적으로 흔함
 *      → 같은 vendor 안의 retry + backoff 가 가성비 좋음
 *   3) 모델 family 다양화 (gpt-5-mini vs gpt-4o-mini) 만으로도 LLM-as-judge
 *      confirmation bias 가 상당 부분 완화됨
 *   4) Vendor 자체 outage 가 일어나면 어차피 mock-skip 패턴 (lambda-handler)
 *      이 사용자에게 직전 라이브를 그대로 노출
 */

export const OPENAI_MODEL = process.env.OPENAI_MODEL || "gpt-5-mini";
export const VERIFY_MODEL = process.env.VERIFY_MODEL || "gpt-4o-mini";

export const hasOpenAI = () => !!process.env.OPENAI_API_KEY;

/** 모델이 가끔 코드블록(```json ... ```)으로 감싸 보내는 경우를 안전하게 파싱 */
export function extractJson<T>(raw: string): T {
  let text = raw.trim();
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) text = fence[1].trim();
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start !== -1 && end !== -1) text = text.slice(start, end + 1);
  return JSON.parse(text) as T;
}

async function callOpenAI(prompt: string, model: string): Promise<string> {
  const openai = new OpenAI();
  const completion = await openai.chat.completions.create({
    model,
    messages: [{ role: "user", content: prompt }],
    response_format: { type: "json_object" },
  });
  return completion.choices[0]?.message?.content ?? "";
}

/**
 * 메인 LLM 브리핑 생성 — gpt-5-mini.
 * 일과성 rate-limit/timeout 대비 retry × 2 (1.5s, 4s exponential backoff).
 *
 * @returns 생성된 Brief 와 retried 플래그 (첫 시도 실패 후 회복했는지)
 */
export async function generateBriefWithGPT(
  sources: Source[],
  type: BriefType,
  dateInfo?: MarketDateInfo
): Promise<{ brief: Brief; retried: boolean }> {
  const prompt = buildBriefPrompt(sources, type, dateInfo);
  const delays = [0, 1500, 4000]; // 즉시 → 1.5s → 4s (총 3 시도)
  let lastErr: Error | null = null;
  for (let i = 0; i < delays.length; i++) {
    if (delays[i] > 0) await new Promise((r) => setTimeout(r, delays[i]));
    try {
      const text = await callOpenAI(prompt, OPENAI_MODEL);
      return { brief: extractJson<Brief>(text), retried: i > 0 };
    } catch (e) {
      lastErr = e as Error;
    }
  }
  throw lastErr ?? new Error("GPT 생성 실패 (재시도 3회 모두 실패)");
}

/**
 * 교차검증 (LLM-as-judge) — gpt-4o-mini.
 * 메인과 다른 model family 를 써서 confirmation bias 완화.
 */
export async function verifyBriefWithGPT(
  sources: Source[],
  brief: Brief
): Promise<VerifyResult> {
  const text = await callOpenAI(
    buildVerifyPrompt(sources, JSON.stringify(brief)),
    VERIFY_MODEL
  );
  const parsed = extractJson<Partial<VerifyResult>>(text);
  const hallucinations = parsed.hallucinations ?? [];
  const inconsistencies = parsed.inconsistencies ?? [];
  const advice_violations = parsed.advice_violations ?? [];
  return {
    hallucinations,
    inconsistencies,
    advice_violations,
    passed:
      typeof parsed.passed === "boolean"
        ? parsed.passed
        : hallucinations.length === 0 &&
          inconsistencies.length === 0 &&
          advice_violations.length === 0,
  };
}
