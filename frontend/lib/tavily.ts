import type { BriefType, Source } from "./types";

const TAVILY_ENDPOINT = "https://api.tavily.com/search";

const QUERIES: Record<BriefType, string[]> = {
  morning: [
    "US stock market major news today S&P 500 Nasdaq",
    "한국 증시 오늘 주요 이슈 코스피 반도체 2차전지",
  ],
  evening: [
    "한국 증시 코스피 코스닥 오늘 마감 주요 이슈",
    "US stock market tonight outlook earnings economic data",
  ],
};

/** 종류별 이슈 검색. 키가 없으면 빈 배열 + warning 반환 → 호출부에서 모킹 폴백. */
export async function searchIssues(
  type: BriefType
): Promise<{ sources: Source[]; warning?: string }> {
  const apiKey = process.env.TAVILY_API_KEY;
  if (!apiKey) {
    return { sources: [], warning: "TAVILY_API_KEY 없음 → 모킹 소스 사용" };
  }

  const collected: Source[] = [];
  try {
    for (const query of QUERIES[type]) {
      const res = await fetch(TAVILY_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: apiKey,
          query,
          search_depth: "advanced",
          max_results: 4,
          include_answer: true,
        }),
        cache: "no-store",
      });
      if (!res.ok) {
        return {
          sources: collected,
          warning: `Tavily 응답 오류 (${res.status}) → 일부/모킹 폴백`,
        };
      }
      const data = (await res.json()) as {
        results?: { title: string; url: string; content: string; score?: number }[];
      };
      for (const r of data.results ?? []) {
        collected.push({
          title: r.title,
          url: r.url,
          content: r.content,
          score: r.score,
        });
      }
    }
    return { sources: collected };
  } catch (e) {
    return {
      sources: collected,
      warning: `Tavily 호출 예외: ${(e as Error).message} → 모킹 폴백`,
    };
  }
}
