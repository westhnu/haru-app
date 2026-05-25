import { NextResponse } from "next/server";
import { emptyThemeResponse, generateThemeMap } from "@/lib/thememap";
import { readThemes, writeThemes } from "@/lib/themestore";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

/** 저장된 테마 매핑 즉시 반환. 없으면 empty. */
export async function GET() {
  const saved = await readThemes();
  return NextResponse.json(saved ?? { ...emptyThemeResponse(), empty: true });
}

/** 이슈→테마 매핑 생성·저장. 스케줄러/수동 트리거용. */
export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("x-cron-secret") !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const result = await generateThemeMap();
    await writeThemes(result);
    return NextResponse.json({ ok: true, count: result.items.length, mode: result.meta.mode });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: (e as Error).message },
      { status: 500 }
    );
  }
}
