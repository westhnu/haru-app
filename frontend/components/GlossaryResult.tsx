import { AlertCircle, FileText } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";

export type GlossaryCitation = {
  excerpt?: string;
  source?: string;
  similarity?: number | null;
};

// backend RagResponse.source (AnswerSource)와 동일한 값.
export type AnswerSource =
  | "knowledge_base"
  | "general_knowledge"
  | "no_evidence"
  | "mock"
  | "guardrail_blocked";

export type GlossaryAnswer = {
  answer: string;
  citations?: GlossaryCitation[];
  source?: AnswerSource;
  context_type?: string;
  disclaimer: string;
  is_mock?: boolean;
};

const SOURCE_LABELS: Record<AnswerSource, string> = {
  knowledge_base: "Bedrock KB",
  general_knowledge: "LLM 일반 지식",
  no_evidence: "근거 없음",
  mock: "Mock",
  guardrail_blocked: "답변 제한",
};

// backend가 answer 말미에 disclaimer를 이미 붙여 보낸다(core.guardrail.enforce_disclaimer).
// 본문에서는 떼어내고 footer에 한 번만 보여준다. 원칙 5 문구는 footer로 항상 노출된다.
function stripTrailingDisclaimer(text: string, disclaimer: string): string {
  const trimmed = text.trimEnd();
  return trimmed.endsWith(disclaimer) ? trimmed.slice(0, -disclaimer.length).trimEnd() : text;
}

type Props = {
  answer: GlossaryAnswer;
};

// Bedrock Sonnet 답변은 **굵게**·목록·소제목 markdown으로 온다. typography 플러그인 대신
// 요소별 Tailwind 클래스를 직접 매핑한다(다크 모드 포함).
// react-markdown은 기본적으로 raw HTML을 렌더링하지 않는다(rehype-raw 미사용) → 답변 속 HTML은 텍스트로 남는다.
const MARKDOWN_COMPONENTS: Components = {
  p: ({ children }) => (
    <p className="mb-3 leading-relaxed text-slate-700 last:mb-0 dark:text-slate-200">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-900 dark:text-slate-100">{children}</strong>
  ),
  ul: ({ children }) => (
    <ul className="mb-3 ml-4 list-disc space-y-1 text-slate-700 dark:text-slate-200">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-3 ml-4 list-decimal space-y-1 text-slate-700 dark:text-slate-200">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => (
    <h1 className="mb-2 mt-4 text-base font-bold text-slate-900 first:mt-0 dark:text-slate-100">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-2 mt-4 text-sm font-bold text-slate-900 first:mt-0 dark:text-slate-100">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-2 mt-3 text-sm font-semibold text-slate-900 first:mt-0 dark:text-slate-100">
      {children}
    </h3>
  ),
  code: ({ children }) => (
    <code className="rounded bg-slate-100 px-1 py-0.5 text-xs dark:bg-slate-800">{children}</code>
  ),
};

export default function GlossaryResult({ answer }: Props) {
  const isMock = answer.is_mock === true;
  const sourceLabel = answer.source ? SOURCE_LABELS[answer.source] ?? answer.source : "응답";
  const body = stripTrailingDisclaimer(answer.answer, answer.disclaimer);

  return (
    <article className="overflow-hidden rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <header className="flex flex-wrap items-center gap-2 border-b border-slate-200 px-5 py-3 dark:border-slate-800">
        <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
          {sourceLabel}
        </span>
        {isMock && (
          <span className="flex items-center gap-1 rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
            <AlertCircle className="h-3 w-3" />
            Mock 응답 (BEDROCK_KB_ID 미설정)
          </span>
        )}
      </header>

      <div className="break-words px-5 py-4 text-slate-800 dark:text-slate-200">
        <ReactMarkdown components={MARKDOWN_COMPONENTS}>{body}</ReactMarkdown>
      </div>

      {answer.citations && answer.citations.length > 0 && (
        <div className="border-t border-slate-100 px-5 pb-4 pt-3 dark:border-slate-800">
          <h3 className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            <FileText className="h-3 w-3" />
            근거
          </h3>
          <ul className="space-y-2">
            {answer.citations.map((c, i) => (
              <li
                key={`${c.source ?? "src"}-${i}`}
                className="rounded border border-slate-100 bg-slate-50 px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-800/50"
              >
                {c.excerpt && (
                  <p className="mb-1 line-clamp-3 whitespace-pre-wrap break-words text-slate-700 dark:text-slate-300">
                    {c.excerpt}
                  </p>
                )}
                <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  {c.source && (
                    <span className="truncate" title={c.source}>
                      출처: {c.source.split("/").pop()}
                    </span>
                  )}
                  {typeof c.similarity === "number" && (
                    <span className="ml-auto">유사도 {c.similarity.toFixed(2)}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <footer className="border-t border-slate-100 bg-slate-50 px-5 py-3 dark:border-slate-800 dark:bg-slate-800/50">
        <p className="text-xs italic text-slate-500 dark:text-slate-400">{answer.disclaimer}</p>
      </footer>
    </article>
  );
}
