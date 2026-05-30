// AWS Lambda handler — EventBridge Scheduler가 호출.
// 페이로드: { "slot": "morning" | "evening" }
//
// 빌드: npm run build:lambda
//   → dist/lambda-handler.mjs 단일 파일 (esbuild 번들).
// 배포된 Lambda는 이 파일과 package.json만 zip해서 올린다.

import type { BriefType } from "@/lib/types";
import { generateBriefResponse } from "@/lib/pipeline";
import { readBrief, writeBrief } from "@/lib/store";
import { generateThemeMap } from "@/lib/thememap";
import { readThemes, writeThemes } from "@/lib/themestore";

interface Event {
  slot?: string;
}

export const handler = async (event: Event) => {
  const slot = (event?.slot || "").toLowerCase();
  if (slot !== "morning" && slot !== "evening") {
    throw new Error(`invalid slot: ${JSON.stringify(event)}`);
  }
  const briefType: BriefType = slot;
  console.log(`[cron] start slot=${briefType} ts=${new Date().toISOString()}`);

  const errors: string[] = [];

  try {
    console.log("[cron] generating brief…");
    const brief = await generateBriefResponse(briefType);
    console.log(`[cron] brief mode=${brief.meta.mode} model=${brief.meta.mainModel}`);
    if (brief.meta.mode === "mock") {
      // LLM 둘 다 실패한 경우 — 직전 라이브가 S3에 있으면 덮어쓰지 않는다.
      const prev = await readBrief(briefType);
      if (prev && !prev.empty && prev.meta?.mode === "live") {
        console.log("[cron] LLM unavailable → keep previous live brief (skip overwrite)");
      } else {
        await writeBrief(briefType, brief);
        console.log("[cron] brief saved to S3 (mock — no prior live)");
      }
    } else {
      await writeBrief(briefType, brief);
      console.log("[cron] brief saved to S3");
    }
  } catch (e) {
    const msg = (e as Error).message;
    errors.push(`brief: ${msg}`);
    console.error(`[cron] brief ERROR: ${msg}`);
  }

  try {
    console.log("[cron] generating themes…");
    const themes = await generateThemeMap();
    console.log(`[cron] themes mode=${themes.meta.mode} count=${themes.items.length}`);
    if (themes.meta.mode === "mock") {
      const prev = await readThemes();
      if (prev && prev.meta?.mode === "live" && prev.items?.length) {
        console.log("[cron] LLM unavailable → keep previous live themes (skip overwrite)");
      } else {
        await writeThemes(themes);
        console.log("[cron] themes saved to S3 (mock — no prior live)");
      }
    } else {
      await writeThemes(themes);
      console.log("[cron] themes saved to S3");
    }
  } catch (e) {
    const msg = (e as Error).message;
    errors.push(`themes: ${msg}`);
    console.error(`[cron] themes ERROR: ${msg}`);
  }

  console.log(`[cron] done errors=${errors.length}`);
  if (errors.length) throw new Error(errors.join(" | "));
  return { ok: true, slot: briefType };
};
