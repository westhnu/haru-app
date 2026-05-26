import type { BriefType } from "@/lib/types";
import { generateBriefResponse } from "@/lib/pipeline";
import { writeBrief } from "@/lib/store";
import { generateThemeMap } from "@/lib/thememap";
import { writeThemes } from "@/lib/themestore";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

/**
 * 브리핑 + 테마를 통합 생성·저장.
 * Amplify Hosting Compute에서 응답 후 Lambda가 즉시 종료되는 이슈가 있어
 * NDJSON 스트리밍으로 작업이 끝날 때까지 응답을 유지한다.
 */
export async function POST(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("x-cron-secret") !== secret) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }
  const slotParam = new URL(req.url).searchParams.get("slot");
  const briefType: BriefType = slotParam === "evening" ? "evening" : "morning";

  const enc = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const emit = (obj: unknown) =>
        controller.enqueue(enc.encode(JSON.stringify(obj) + "\n"));

      emit({ stage: "started", briefType, ts: new Date().toISOString() });
      try {
        const brief = await generateBriefResponse(briefType);
        emit({ stage: "brief:generated", mode: brief.meta.mode });
        await writeBrief(briefType, brief);
        emit({ stage: "brief:saved" });
      } catch (e) {
        emit({ stage: "brief:error", error: String((e as Error).message) });
      }
      try {
        const themes = await generateThemeMap();
        emit({ stage: "themes:generated", mode: themes.meta.mode, count: themes.items.length });
        await writeThemes(themes);
        emit({ stage: "themes:saved" });
      } catch (e) {
        emit({ stage: "themes:error", error: String((e as Error).message) });
      }
      emit({ stage: "done", ts: new Date().toISOString() });
      controller.close();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "application/x-ndjson",
      "Cache-Control": "no-store",
      "X-Accel-Buffering": "no",
    },
  });
}
