import { NextResponse } from "next/server";
import { s3Enabled, s3PutJson, s3GetJson } from "@/lib/s3";

export const dynamic = "force-dynamic";

// 운영 환경 진단용. CRON_SECRET 헤더로 보호.
export async function GET(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("x-cron-secret") !== secret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const env = {
    STORAGE: process.env.STORAGE ?? null,
    S3_BUCKET: process.env.S3_BUCKET ?? null,
    AWS_REGION: process.env.AWS_REGION ?? null,
    AWS_LAMBDA_FUNCTION_NAME: process.env.AWS_LAMBDA_FUNCTION_NAME ?? null,
    AWS_EXECUTION_ENV: process.env.AWS_EXECUTION_ENV ?? null,
    hasOpenAI: !!process.env.OPENAI_API_KEY,
    hasGemini: !!process.env.GEMINI_API_KEY,
    hasTavily: !!process.env.TAVILY_API_KEY,
    hasDart: !!process.env.DART_API_KEY,
    hasKisProd: !!process.env.KIS_APP_KEY_PROD,
    s3Enabled: s3Enabled(),
  };

  let s3Test: Record<string, unknown> = { skipped: true };
  if (env.s3Enabled) {
    s3Test = { skipped: false };
    const key = "_debug-ping.json";
    try {
      await s3PutJson(key, { ts: new Date().toISOString() });
      s3Test.put = "ok";
    } catch (e) {
      s3Test.put = `error: ${(e as Error).message}`;
    }
    try {
      const got = await s3GetJson<{ ts: string }>(key);
      s3Test.get = got ? `ok (${got.ts})` : "not found";
    } catch (e) {
      s3Test.get = `error: ${(e as Error).message}`;
    }
  }

  return NextResponse.json({ env, s3Test });
}
