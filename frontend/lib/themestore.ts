import { promises as fs } from "fs";
import path from "path";
import type { ThemeResponse } from "./thememap";
import { s3Enabled, s3GetJson, s3PutJson } from "./s3";

// 테마 매핑 결과 캐시 (기본 파일 / STORAGE=s3 시 S3)
const FILE = path.join(process.cwd(), "data", "themes-latest.json");
const S3_KEY = "themes-latest.json";

export async function readThemes(): Promise<ThemeResponse | null> {
  if (s3Enabled()) return s3GetJson<ThemeResponse>(S3_KEY);
  try {
    return JSON.parse(await fs.readFile(FILE, "utf8")) as ThemeResponse;
  } catch {
    return null;
  }
}

export async function writeThemes(data: ThemeResponse): Promise<void> {
  if (s3Enabled()) {
    await s3PutJson(S3_KEY, data);
    return;
  }
  await fs.mkdir(path.dirname(FILE), { recursive: true });
  await fs.writeFile(FILE, JSON.stringify(data, null, 2), "utf8");
}
