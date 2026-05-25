import { NextResponse } from "next/server";
import type { BriefType } from "@/lib/types";
import { generateBriefResponse } from "@/lib/pipeline";
import { writeBrief } from "@/lib/store";

// 생성은 LLM 호출이 길어질 수 있으므로 최대 실행시간을 넉넉히
export const dynamic = "force-dynamic";
export const maxDuration = 60;

function parseType(req: Request): BriefType {
  const t = new URL(req.url).searchParams.get("type");
  return t === "evening" ? "evening" : "morning";
}

/**
 * 브리핑을 생성·저장한다. 스케줄러(cron / EventBridge) 또는 수동 트리거용.
 *
 * 보호: CRON_SECRET 환경변수가 설정돼 있으면 헤더 `x-cron-secret` 가 일치해야 한다.
 *       (개발 환경에서 미설정이면 누구나 호출 가능 — 운영 배포 시 반드시 설정)
 */
export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("x-cron-secret") !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const type = parseType(req);
  try {
    const result = await generateBriefResponse(type);
    await writeBrief(type, result);
    return NextResponse.json({
      ok: true,
      type,
      mode: result.meta.mode,
      generatedAt: result.meta.generatedAt,
    });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: (e as Error).message },
      { status: 500 }
    );
  }
}
