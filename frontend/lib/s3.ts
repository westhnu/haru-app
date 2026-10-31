import "server-only";
import {
  S3Client,
  GetObjectCommand,
  PutObjectCommand,
} from "@aws-sdk/client-s3";

// 운영 영속 스토어 (Amplify/Lambda 파일시스템은 휘발성이므로 S3 사용)
// STORAGE=s3 + S3_BUCKET 설정 시 활성화. 아니면 파일 스토어 사용.

const bucket = () => process.env.S3_BUCKET;

export const s3Enabled = (): boolean =>
  process.env.STORAGE === "s3" && !!bucket();

let client: S3Client | null = null;
function c(): S3Client {
  if (!client) {
    client = new S3Client({
      region: process.env.AWS_REGION || "ap-northeast-2",
    });
  }
  return client;
}

export async function s3GetJson<T>(key: string): Promise<T | null> {
  try {
    const r = await c().send(
      new GetObjectCommand({ Bucket: bucket(), Key: key })
    );
    const text = await r.Body?.transformToString();
    return text ? (JSON.parse(text) as T) : null;
  } catch {
    return null;
  }
}

export async function s3PutJson(key: string, data: unknown): Promise<void> {
  await c().send(
    new PutObjectCommand({
      Bucket: bucket(),
      Key: key,
      Body: JSON.stringify(data),
      ContentType: "application/json",
    })
  );
}
