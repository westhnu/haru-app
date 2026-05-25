import raw from "./glossary.json";

export interface GlossaryEntry {
  name: string; // 한글 풀네임
  en: string; // 영문
  desc: string; // 쉬운 설명
}

const GLOSSARY = raw as Record<string, GlossaryEntry>;

export function lookup(term: string): GlossaryEntry | undefined {
  return GLOSSARY[term];
}

// 긴 용어 우선 매칭 (예: "주가수익비율"이 "주가"보다 먼저)
const TERMS = Object.keys(GLOSSARY)
  .filter((t) => t.length >= 2)
  .sort((a, b) => b.length - a.length);

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

const PATTERN = new RegExp(TERMS.map(escapeRe).join("|"), "g");

export interface Segment {
  text: string;
  entry?: GlossaryEntry;
  key: string;
}

const ALNUM_OR_HANGUL = /[가-힣A-Za-z0-9]/;
const ASCII_TERM = /^[A-Za-z0-9]+$/;

/** 텍스트에서 사전 용어를 찾아 세그먼트로 분할. 같은 용어는 블록당 1회만 강조.
 *  합성어의 부분문자열 오매칭을 막기 위해 경계 검사를 한다:
 *  - 매칭 앞 글자가 한글/영숫자면 더 큰 단어의 일부로 보고 제외 (예: "신호가"→"호가", "순매수"→"매수")
 *  - 영문 약어는 뒤 글자가 영숫자면 제외 (예: "SUPER" 안의 가짜 매칭 방지) */
export function annotate(text: string): Segment[] {
  const segs: Segment[] = [];
  const used = new Set<string>();
  let last = 0;
  let i = 0;
  let m: RegExpExecArray | null;
  PATTERN.lastIndex = 0;
  while ((m = PATTERN.exec(text)) !== null) {
    const word = m[0];
    const start = m.index;
    const prev = start > 0 ? text[start - 1] : "";
    const next = text[start + word.length] ?? "";
    const badPrev = ALNUM_OR_HANGUL.test(prev);
    const badNext = ASCII_TERM.test(word) && /[A-Za-z0-9]/.test(next);
    if (used.has(word) || badPrev || badNext) continue; // 평문으로 남김

    if (start > last) {
      segs.push({ text: text.slice(last, start), key: `t${i++}` });
    }
    segs.push({ text: word, entry: GLOSSARY[word], key: `g${i++}` });
    used.add(word);
    last = start + word.length;
  }
  if (last < text.length) segs.push({ text: text.slice(last), key: `t${i++}` });
  return segs;
}
