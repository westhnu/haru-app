import { NextResponse } from "next/server";
import type { BriefType } from "@/lib/types";
import { generateBriefResponse } from "@/lib/pipeline";
import { writeBrief } from "@/lib/store";
import { generateThemeMap } from "@/lib/thememap";
import { writeThemes } from "@/lib/themestore";

// 브리핑 + 테마를 한 번에 생성·저장하는 통합 스케줄 엔드포인트.
export const dynamic = "force-dynamic";
export const maxDuration = 120;

/**
 * 시간대별 일괄 생성:
 *   - slot=morning: 모닝 브리핑 + 테마 매핑
 *   - slot=evening: 이브닝 브리핑 + 테마 매핑
 * cron/EventBridge에서 하루 2회 호출하면 전체가 갱신된다.
 * 보호: CRON_SECRET 설정 시 헤더 x-cron-secret 일치 필요.
 */
export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("x-cron-secret") !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const slotParam = new URL(req.url).searchParams.get("slot");
  const briefType: BriefType = slotParam === "evening" ? "evening" : "morning";

  const result: Record<string, unknown> = { slot: briefType };
  const errors: string[] = [];

  // 1) 해당 시간대 브리핑
  try {
    const brief = await generateBriefResponse(briefType);
    await writeBrief(briefType, brief);
    result.brief = { mode: brief.meta.mode, generatedAt: brief.meta.generatedAt };
  } catch (e) {
    errors.push(`brief: ${(e as Error).message}`);
  }

  // 2) 이슈·테마 매핑 (두 시간대 모두 갱신)
  try {
    const themes = await generateThemeMap();
    await writeThemes(themes);
    result.themes = { mode: themes.meta.mode, count: themes.items.length };
  } catch (e) {
    errors.push(`themes: ${(e as Error).message}`);
  }

  return NextResponse.json(
    { ok: errors.length === 0, ...result, errors },
    { status: errors.length === 0 ? 200 : 207 }
  );
}
