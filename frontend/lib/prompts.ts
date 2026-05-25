import type { BriefType, Source } from "./types";
import { BRIEF_META } from "./types";
import type { MarketDateInfo } from "./market";

/** 종류별 브리핑 작성 지침 */
const FRAMING: Record<BriefType, string> = {
  morning:
    "지금은 한국 시각 아침, 국내 장 시작 전입니다. 간밤 미국·유럽 장과 야간 거시 이벤트가 오늘 국내 장에 어떤 영향을 줄지 정리합니다.",
  evening:
    "지금은 한국 시각 저녁, 국내 장 마감 후입니다. 오늘 국내 장의 핵심 이슈와, 오늘 밤 미국 장에서 주목할 포인트를 정리합니다.",
};

/** 브리핑 생성 프롬프트 — 메인 LLM(GPT) & fallback(Gemini) 공용 */
export function buildBriefPrompt(
  sources: Source[],
  type: BriefType,
  dateInfo?: MarketDateInfo
): string {
  const titles = BRIEF_META[type].sectionTitles;
  const dateLine = dateInfo
    ? `오늘은 ${dateInfo.label}입니다.${
        dateInfo.isOpen
          ? ""
          : ` ${dateInfo.note ?? ""} 국내 장이 열리지 않으므로, 국내 섹션은 직전 거래일 기준이거나 다음 개장일 관전 포인트로 작성하고 그 사실을 한 문장으로 안내하세요.`
      }`
    : "";
  const sourceBlock = sources
    .map((s, i) => `[S${i + 1}] ${s.title}\nURL: ${s.url}\n발췌: ${s.content}`)
    .join("\n\n");

  const sectionList = titles
    .map((t, i) => `${i + 1}. ${t}`)
    .join("\n");

  return `당신은 개인 투자자를 위한 한국어 마켓 브리핑 작성자입니다. 독자는 투자 초보부터 중급까지 다양합니다.
${FRAMING[type]}
${dateLine}

아래 [원본 소스]에 **명시된 내용만** 근거로 사용하세요. 소스에 없는 수치·사실을 지어내지 마세요.
근거가 부족한 섹션은 추측하지 말고 dataGaps 에 "정보 없음"으로 명시하세요.
특정 종목의 매수·매도를 권유하는 표현(예: "지금 사세요", "비중 확대 추천")은 절대 쓰지 마세요. 사실·전망·관심 후보 제시까지만 합니다.

[작성 원칙 — 가독성·명확성]
1. 쉬운 표현을 우선하세요. 전문용어는 꼭 필요할 때만 쓰고, 쓸 경우 같은 문장 안에서 한 번 풀어 설명하세요. (예: "PER(주가가 이익의 몇 배인지)")
2. 결론을 먼저, 이유는 그다음. 각 summary는 핵심 메시지로 시작하세요.
3. 한 문장은 짧고 명확하게(가능하면 60자 이내). 한 문장에 한 가지 정보만 담으세요.
4. summary는 2~3문장으로 핵심만. 군더더기·중복·수식어를 줄이세요.
5. bullets는 명사형으로 짧게(각 20자 내외). 가장 중요한 포인트 2~3개만.
6. 숫자가 소스에 있으면 구체적으로 인용하고, 없으면 만들지 마세요.
7. 단정·과장 금지. 불확실하면 "~할 수 있다", "~가능성" 처럼 신중하게 쓰세요.
8. oneLine은 오늘의 핵심을 한 문장으로, 초보도 이해되게 쉽게 쓰세요.

[브리핑 구조] 정확히 5개 섹션, 순서·제목 고정:
${sectionList}

[종목 표기] tickers의 각 종목은 가능하면 식별자를 채우세요. 국내 종목은 "code"에 6자리 종목코드(예: 삼성전자 "005930"), 해외 종목은 "symbol"에 티커(예: "NVDA")를 넣으세요. 모르면 생략 가능.

[출력 형식] 아래 JSON 스키마를 정확히 따르세요. 코드블록·설명 없이 JSON만:
{
  "oneLine": "핵심을 종합한 한 단락 요약",
  "sections": [
    { "title": "${titles[0]}", "summary": "...", "bullets": ["...", "..."] },
    { "title": "${titles[1]}", "summary": "...", "tickers": [{"name":"종목명","symbol":"티커","note":"한 줄 메모"}] },
    { "title": "${titles[2]}", "summary": "..." },
    { "title": "${titles[3]}", "summary": "..." },
    { "title": "${titles[4]}", "summary": "...", "tickers": [{"name":"...","note":"..."}] }
  ],
  "dataGaps": ["소스에 없어 채우지 못한 항목"]
}

[원본 소스]
${sourceBlock || "(소스 없음 — dataGaps에 '수집된 소스 없음'을 명시하고 일반적 안내만 작성)"}`;
}

/** Gemini 교차검증 프롬프트 (LLM-as-judge) */
export function buildVerifyPrompt(sources: Source[], briefJson: string): string {
  return `당신은 금융 AI 출력물의 품질 검증자입니다.
아래 [브리핑]이 [원본 소스]에만 근거하는지 엄격히 검증하세요.

검증 항목:
1. hallucinations: 소스에 근거가 없는 주장·수치
2. inconsistencies: 소스 내용과 어긋나는 서술
3. advice_violations: 특정 종목 매수·매도를 권유하는 표현 (자본시장법 의식)

각 항목에 해당하는 문장을 배열로 담아 아래 JSON만 출력하세요 (코드블록 금지):
{ "hallucinations": [], "inconsistencies": [], "advice_violations": [], "passed": true }
세 배열이 모두 비어 있으면 passed=true, 하나라도 있으면 passed=false.

[원본 소스]
${sources.map((s, i) => `[S${i + 1}] ${s.title}: ${s.content}`).join("\n")}

[브리핑]
${briefJson}`;
}
