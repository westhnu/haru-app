import { NextResponse } from "next/server";
import type { BriefResponse, BriefType } from "@/lib/types";
import { OPENAI_MODEL, GEMINI_MODEL } from "@/lib/llm";
import { readBrief } from "@/lib/store";
import { getMarketDateInfo } from "@/lib/market";

export const dynamic = "force-dynamic";

function parseType(req: Request): BriefType {
  const t = new URL(req.url).searchParams.get("type");
  return t === "evening" ? "evening" : "morning";
}

/** 저장된 최신 브리핑을 즉시 반환 (LLM 호출 없음 → 빠름). */
export async function GET(req: Request) {
  const type = parseType(req);
  const saved = await readBrief(type);

  if (saved) return NextResponse.json(saved);

  // 아직 생성된 브리핑이 없는 경우
  const info = getMarketDateInfo();
  const empty: BriefResponse = {
    type,
    empty: true,
    brief: null,
    verify: null,
    sources: [],
    meta: {
      mode: "mock",
      mainModel: OPENAI_MODEL,
      verifyModel: GEMINI_MODEL,
      fallbackUsed: false,
      warnings: ["아직 생성된 브리핑이 없습니다. 생성이 필요합니다."],
      generatedAt: "",
      forDate: info.label,
      marketNote: info.note,
    },
  };
  return NextResponse.json(empty);
}
