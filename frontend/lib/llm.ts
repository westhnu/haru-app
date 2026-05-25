import OpenAI from "openai";
import { GoogleGenerativeAI } from "@google/generative-ai";
import type { Brief, BriefType, Source, VerifyResult } from "./types";
import type { MarketDateInfo } from "./market";
import { buildBriefPrompt, buildVerifyPrompt } from "./prompts";

export const OPENAI_MODEL = process.env.OPENAI_MODEL || "gpt-5-mini";
export const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash";

// GOOGLE_API_KEY / GEMINI_API_KEY 둘 다 허용
export const geminiKey = () =>
  process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;

export const hasOpenAI = () => !!process.env.OPENAI_API_KEY;
export const hasGemini = () => !!geminiKey();

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

/** 메인 LLM(GPT)으로 브리핑 생성 */
export async function generateBriefWithGPT(
  sources: Source[],
  type: BriefType,
  dateInfo?: MarketDateInfo
): Promise<Brief> {
  const openai = new OpenAI();
  const completion = await openai.chat.completions.create({
    model: OPENAI_MODEL,
    messages: [
      { role: "user", content: buildBriefPrompt(sources, type, dateInfo) },
    ],
    response_format: { type: "json_object" },
  });
  const content = completion.choices[0]?.message?.content ?? "";
  return extractJson<Brief>(content);
}

/** 보조 LLM(Gemini)으로 브리핑 생성 — GPT 장애 시 fallback */
export async function generateBriefWithGemini(
  sources: Source[],
  type: BriefType,
  dateInfo?: MarketDateInfo
): Promise<Brief> {
  const genAI = new GoogleGenerativeAI(geminiKey()!);
  const model = genAI.getGenerativeModel({
    model: GEMINI_MODEL,
    generationConfig: { responseMimeType: "application/json" },
  });
  const result = await model.generateContent(
    buildBriefPrompt(sources, type, dateInfo)
  );
  return extractJson<Brief>(result.response.text());
}

/** Gemini 교차검증 (LLM-as-judge) */
export async function verifyBriefWithGemini(
  sources: Source[],
  brief: Brief
): Promise<VerifyResult> {
  const genAI = new GoogleGenerativeAI(geminiKey()!);
  const model = genAI.getGenerativeModel({
    model: GEMINI_MODEL,
    generationConfig: { responseMimeType: "application/json" },
  });
  const result = await model.generateContent(
    buildVerifyPrompt(sources, JSON.stringify(brief))
  );
  const parsed = extractJson<Partial<VerifyResult>>(result.response.text());
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
