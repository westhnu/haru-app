// Phase G 챗 타입 (backend app/models/chat.py와 1:1). API 호출은 Phase G.1에서 붙인다.

export type ChatRole = "user" | "assistant" | "tool";
export type ChatEvaluationSource = "bedrock" | "mock" | "template";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: Record<string, unknown> | null;
  evaluation_source: ChatEvaluationSource | null;
  created_at: string;
};

export type ChatSession = {
  id: string;
  stock_code: string | null;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type ChatSessionWithMessages = ChatSession & { messages: ChatMessage[] };

export const CHAT_CONTENT_MAX_LENGTH = 10000;
