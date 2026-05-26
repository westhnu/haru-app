// KRX 전체 상장종목 "이름 → 6자리 종목코드" 매핑을 생성한다.
// 사용: (네트워크가 되는 본인 PC에서) node scripts/build-krx.mjs
// 결과: lib/krx-codes.json 갱신 → 이후 모든 국내 종목이 KIS 라이브로 연결(데모 없음).
//
// 출처: KRX KIND 전체 상장법인 목록(corpList.do) — EUC-KR HTML 테이블.

import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, "..", "lib", "krx-codes.json");

// searchType=13: 전체(코스피+코스닥+코넥스)
const URL =
  "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13";

function decode(buf) {
  try {
    return new TextDecoder("euc-kr").decode(buf);
  } catch {
    return buf.toString("latin1");
  }
}

function stripTags(s) {
  return s
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&nbsp;/g, " ")
    .trim();
}

async function main() {
  console.log("KRX 상장종목 목록 내려받는 중…");
  const res = await fetch(URL, {
    headers: { "User-Agent": "Mozilla/5.0" },
  });
  if (!res.ok) throw new Error(`KRX 응답 ${res.status}`);
  const html = decode(Buffer.from(await res.arrayBuffer()));

  const map = {};
  let count = 0;
  for (const row of html.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)) {
    const tds = [...row[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((m) =>
      stripTags(m[1])
    );
    if (tds.length < 2) continue;
    const name = tds[0];
    if (!name) continue;
    const code = tds.slice(1).map((t) => t.replace(/[^0-9]/g, "")).find((s) => /^\d{1,6}$/.test(s));
    if (!code) continue;
    map[name] = code.padStart(6, "0");
    count++;
  }

  if (count === 0) {
    throw new Error(
      "파싱된 종목이 없습니다. KRX 페이지 형식이 바뀌었을 수 있어요."
    );
  }

  // 이름 길이 긴 것부터 저장(정렬은 의미 없지만 가독성)
  const sorted = Object.fromEntries(
    Object.entries(map).sort((a, b) => a[0].localeCompare(b[0], "ko"))
  );
  await writeFile(OUT, JSON.stringify(sorted, null, 0), "utf8");
  console.log(`완료: ${count}개 종목 → ${OUT}`);
}

main().catch((e) => {
  console.error("실패:", e.message);
  process.exit(1);
});
