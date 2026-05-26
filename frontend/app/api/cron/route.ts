import { NextResponse } from "next/server";
import type { BriefType } from "@/lib/types";
import { generateBriefResponse } from "@/lib/pipeline";
import { writeBrief } from "@/lib/store";
import { generateThemeMap } from "@/lib/thememap";
import { writeThemes } from "@/lib/themestore";
import { s3PutJson } from "@/lib/s3";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

// 단계별 진단용 — S3에 cron-status.json 으로 흔적 남김
async function mark(stage: string, detail?: unknown) {
  try {
    await s3PutJson("cron-status.json", {
      stage,
      detail,
      ts: new Date().toISOString(),
    });
  } catch {}
}

async function runWork(briefType: BriefType) {
  await mark("brief:start", { briefType });
  try {
    const brief = await generateBriefResponse(briefType);
    await mark("brief:generated", { mode: brief.meta.mode });
    await writeBrief(briefType, brief);
    await mark("brief:saved");
  } catch (e) {
    await mark("brief:error", String((e as Error).message));
  }
  await mark("themes:start");
  try {
    const themes = await generateThemeMap();
    await mark("themes:generated", { mode: themes.meta.mode, count: themes.items.length });
    await writeThemes(themes);
    await mark("themes:saved");
  } catch (e) {
    await mark("themes:error", String((e as Error).message));
  }
  await mark("done");
}

export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("x-cron-secret") !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const slotParam = new URL(req.url).searchParams.get("slot");
  const briefType: BriefType = slotParam === "evening" ? "evening" : "morning";

  await mark("received", { briefType });
  void runWork(briefType);
  await mark("kicked-off");

  return NextResponse.json(
    { ok: true, slot: briefType, status: "started" },
    { status: 202 }
  );
}
