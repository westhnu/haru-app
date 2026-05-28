import { s3Enabled, s3GetJson, s3PutJson } from "./s3";

/**
 * 다중 Lambda 인스턴스가 공유하는 캐시.
 *
 * 1차: 모듈 메모리 (warm-start 안에서 빠름)
 * 2차: S3 (`cache/<key>.json`) — 콜드스타트·다른 인스턴스끼리도 공유
 *
 * S3 가 비활성화(로컬)면 메모리만 사용.
 *
 * Race condition 주의 — 두 인스턴스가 거의 동시에 miss → 둘 다 producer 호출하는 가능성.
 * 트래픽이 매우 낮은 현 수준에선 허용. 토큰 발급이 60초 cooldown 인 KIS 케이스가 가장
 * 민감한 영역이라 호출자(getToken)가 자체 메모리 캐시를 함께 둠.
 */

interface Cached<T> {
  value: T;
  expiresAt: number; // epoch ms
}

const mem = new Map<string, Cached<unknown>>();

const keyToS3 = (key: string) => `cache/${key}.json`;

export async function readCache<T>(key: string): Promise<T | null> {
  const hit = mem.get(key) as Cached<T> | undefined;
  if (hit && hit.expiresAt > Date.now()) return hit.value;

  if (!s3Enabled()) return null;
  try {
    const remote = await s3GetJson<Cached<T>>(keyToS3(key));
    if (!remote) return null;
    if (remote.expiresAt <= Date.now()) return null;
    mem.set(key, remote);
    return remote.value;
  } catch {
    return null;
  }
}

export async function writeCache<T>(
  key: string,
  value: T,
  ttlMs: number
): Promise<void> {
  if (ttlMs <= 0) return;
  const entry: Cached<T> = { value, expiresAt: Date.now() + ttlMs };
  mem.set(key, entry);
  if (s3Enabled()) {
    try {
      await s3PutJson(keyToS3(key), entry);
    } catch {
      // S3 실패해도 메모리 캐시는 유지 — 호출자에는 silent
    }
  }
}
