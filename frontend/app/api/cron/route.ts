import { NextResponse } from "next/server";
import type { BriefType } from "@/lib/types";
import { generateBriefResponse } from "@/lib/pipeline";
import { writeBrief } from "@/lib/store";
import { generateThemeMap } from "@/lib/thememap";
import { writeThemes } from "@/lib/themestore";

// 브리핑 + 테마를 한 번에 생성·저장하는 통합 스케줄 엔드포인트.
export const dynamic = "force-dynamic";
export const maxDuration = 300;

/**
 * 시간대별 일괄 생성:
 *   - slot=morning: 모닝 브리핑 + 테마 매핑
 *   - slot=evening: 이브닝 브리핑 + 테마 매핑
 *
 * Amplify Hosting Compute의 게이트웨이 응답 한계(약 30초)를 피하려고
 * 작업은 비동기로 시작하고 202를 즉시 반환한다. Lambda는 응답 이후에도
 * 이벤트 루프가 비기 전까지 살아 있으므로 백그라운드 작업이 완료된다.
 */
async function runWork(briefType: BriefType) {
  const errs: string[] = [];
  try {
    const brief = await generateBriefResponse(briefType);
    await writeBrief(briefType, brief);
  } catch (e) {
    errs.push(`brief: ${(e as Error).message}`);
  }
  try {
    const themes = await generateThemeMap();
    await writeThemes(themes);
  } catch (e) {
    errs.push(`themes: ${(e as Error).message}`);
  }
  if (errs.length) console.error("[cron]", briefType, errs.join(" | "));
  else console.log("[cron]", briefType, "완료");
}

export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("x-cron-secret") !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const slotParam = new URL(req.url).searchParams.get("slot");
  const briefType: BriefType = slotParam === "evening" ? "evening" : "morning";

  // fire-and-forget: 응답 후에도 이벤트 루프에 남아 작업 진행
  void runWork(briefType);

  return NextResponse.json(
    { ok: true, slot: briefType, status: "started" },
    { status: 202 }
  );
}
