import { promises as fs } from "fs";
import path from "path";
import type { BriefResponse, BriefType } from "./types";
import { s3Enabled, s3GetJson, s3PutJson } from "./s3";

/**
 * 생성된 브리핑 저장/조회.
 * - 기본: 로컬 파일 (data/<type>-latest.json) — 개발·단일 서버용
 * - STORAGE=s3 + S3_BUCKET: S3 (Amplify/Lambda 등 휘발성 환경의 운영용)
 */
const DATA_DIR = path.join(process.cwd(), "data");
const fileFor = (type: BriefType) => path.join(DATA_DIR, `${type}-latest.json`);
const s3Key = (type: BriefType) => `brief-${type}.json`;

export async function readBrief(
  type: BriefType
): Promise<BriefResponse | null> {
  if (s3Enabled()) return s3GetJson<BriefResponse>(s3Key(type));
  try {
    const raw = await fs.readFile(fileFor(type), "utf8");
    return JSON.parse(raw) as BriefResponse;
  } catch {
    return null;
  }
}

export async function writeBrief(
  type: BriefType,
  data: BriefResponse
): Promise<void> {
  if (s3Enabled()) {
    await s3PutJson(s3Key(type), data);
    return;
  }
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(fileFor(type), JSON.stringify(data, null, 2), "utf8");
}
