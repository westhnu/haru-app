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
    <p className="mb-3 leading-relaxed text-fg last:mb-0">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-fg">{children}</strong>
  ),
  ul: ({ children }) => (
    <ul className="mb-3 ml-4 list-disc space-y-1 text-fg">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-3 ml-4 list-decimal space-y-1 text-fg">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => (
    <h1 className="mb-2 mt-4 text-base font-bold text-fg first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mb-2 mt-4 text-sm font-bold text-fg first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mb-2 mt-3 text-sm font-semibold text-fg first:mt-0">
      {children}
    </h3>
  ),
  code: ({ children }) => (
    <code className="rounded bg-surface-muted px-1 py-0.5 text-xs">{children}</code>
  ),
};

export default function GlossaryResult({ answer }: Props) {
  const isMock = answer.is_mock === true;
  const sourceLabel = answer.source ? SOURCE_LABELS[answer.source] ?? answer.source : "응답";
  const body = stripTrailingDisclaimer(answer.answer, answer.disclaimer);

  return (
    <article className="overflow-hidden rounded-lg border border-border bg-surface">
      <header className="flex flex-wrap items-center gap-2 border-b border-border px-5 py-3">
        <span className="rounded bg-brand/10 px-2 py-0.5 text-xs font-medium text-brand">
          {sourceLabel}
        </span>
        {isMock && (
          <span className="flex items-center gap-1 rounded bg-warning/15 px-2 py-0.5 text-xs font-medium text-warning">
            <AlertCircle className="h-3 w-3" />
            Mock 응답 (BEDROCK_KB_ID 미설정)
          </span>
        )}
      </header>

      <div className="break-words px-5 py-4 text-fg">
        <ReactMarkdown components={MARKDOWN_COMPONENTS}>{body}</ReactMarkdown>
      </div>

      {answer.citations && answer.citations.length > 0 && (
        <div className="border-t border-border-subtle px-5 pb-4 pt-3">
          <h3 className="mb-2 flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-fg-muted">
            <FileText className="h-3 w-3" />
            근거
          </h3>
          <ul className="space-y-2">
            {answer.citations.map((c, i) => (
              <li
                key={`${c.source ?? "src"}-${i}`}
                className="rounded border border-border-subtle bg-surface-muted px-3 py-2 text-sm"
              >
                {c.excerpt && (
                  <p className="mb-1 line-clamp-3 whitespace-pre-wrap break-words text-fg">
                    {c.excerpt}
                  </p>
                )}
                <div className="flex items-center gap-2 text-xs text-fg-muted">
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

      <footer className="border-t border-border-subtle bg-surface-muted px-5 py-3">
        <p className="text-xs italic text-fg-muted">{answer.disclaimer}</p>
      </footer>
    </article>
  );
}
