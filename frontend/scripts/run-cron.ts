// GitHub Actions에서 직접 실행하는 cron 워커.
// Amplify Hosting Compute의 30초 응답 한계를 피해 작업을 GHA 런너에서 수행하고
// 결과를 S3에 저장한다. Amplify 앱은 S3에서 읽기만 한다.
//
// 사용: STORAGE=s3 S3_BUCKET=... AWS_*=... OPENAI_API_KEY=... ...
//      npx tsx scripts/run-cron.ts <morning|evening>

import type { BriefType } from "@/lib/types";
import { generateBriefResponse } from "@/lib/pipeline";
import { writeBrief } from "@/lib/store";
import { generateThemeMap } from "@/lib/thememap";
import { writeThemes } from "@/lib/themestore";

async function main() {
  const slot = (process.argv[2] || "").toLowerCase();
  if (slot !== "morning" && slot !== "evening") {
    console.error("usage: run-cron.ts <morning|evening>");
    process.exit(2);
  }
  const briefType: BriefType = slot;

  console.log(`[cron] start slot=${briefType} ts=${new Date().toISOString()}`);

  const errors: string[] = [];

  try {
    console.log("[cron] generating brief…");
    const brief = await generateBriefResponse(briefType);
    console.log(`[cron] brief mode=${brief.meta.mode} model=${brief.meta.mainModel}`);
    await writeBrief(briefType, brief);
    console.log("[cron] brief saved to S3");
  } catch (e) {
    const msg = (e as Error).message;
    errors.push(`brief: ${msg}`);
    console.error(`[cron] brief ERROR: ${msg}`);
  }

  try {
    console.log("[cron] generating themes…");
    const themes = await generateThemeMap();
    console.log(`[cron] themes mode=${themes.meta.mode} count=${themes.items.length}`);
    await writeThemes(themes);
    console.log("[cron] themes saved to S3");
  } catch (e) {
    const msg = (e as Error).message;
    errors.push(`themes: ${msg}`);
    console.error(`[cron] themes ERROR: ${msg}`);
  }

  console.log(`[cron] done errors=${errors.length}`);
  process.exit(errors.length > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error("[cron] fatal:", e);
  process.exit(1);
});
