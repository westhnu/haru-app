// EventBridge Scheduler 타깃 Lambda (Node.js 20+)
// 정해진 시각에 배포된 Haru의 통합 생성 엔드포인트를 호출한다.
//
// 환경변수:
//   HARU_URL     배포 도메인 (예: https://main.xxxx.amplifyapp.com)
//   CRON_SECRET  앱과 동일한 시크릿
//
// 스케줄 입력(JSON): { "slot": "morning" } 또는 { "slot": "evening" }

export const handler = async (event) => {
  const slot = event?.slot === "evening" ? "evening" : "morning";
  const url = `${process.env.HARU_URL}/api/cron?slot=${slot}`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "x-cron-secret": process.env.CRON_SECRET ?? "" },
  });
  const text = await res.text();
  console.log(`[haru-cron] slot=${slot} status=${res.status} ${text}`);

  if (!res.ok) {
    throw new Error(`haru cron failed: ${res.status} ${text}`);
  }
  return { ok: true, slot, status: res.status };
};
