"""Phase G 챗 에이전트 저장 모델 (scaffold). Bedrock 호출·tool 실행은 Phase G.1에서 붙인다.

원칙 4: 이름에 주문 계열 단어(파일명 CI 스캔 대상)를 쓰지 않는다.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models import CHAT_CONTENT_MAX_LENGTH, CHAT_TITLE_MAX_LENGTH

ChatRole = Literal["user", "assistant", "tool"]
ChatEvaluationSource = Literal["bedrock", "mock", "template"]
DEFAULT_CHAT_TITLE = "새 대화"


class ChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: ChatRole
    content: str = Field(..., max_length=CHAT_CONTENT_MAX_LENGTH)
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    evaluation_source: ChatEvaluationSource | None = None
    created_at: datetime


class ChatSession(BaseModel):
    id: str
    stock_code: str | None = None
    title: str = Field(..., max_length=CHAT_TITLE_MAX_LENGTH)
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ChatSessionWithMessages(ChatSession):
    messages: list[ChatMessage] = Field(default_factory=list)


class ChatSessionCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    stock_code: str | None = Field(default=None, min_length=1, max_length=32)
    title: str | None = Field(default=None, min_length=1, max_length=CHAT_TITLE_MAX_LENGTH)


class ChatMessageAppend(BaseModel):
    """append_message 입력 검증. role=tool이면 tool_name이 필요하다."""

    model_config = ConfigDict(str_strip_whitespace=False, extra="forbid")

    role: ChatRole
    content: str = Field(..., max_length=CHAT_CONTENT_MAX_LENGTH)
    tool_name: str | None = Field(default=None, max_length=64)
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    evaluation_source: ChatEvaluationSource | None = None

    @model_validator(mode="after")
    def _tool_fields(self) -> "ChatMessageAppend":
        if self.role == "tool" and not self.tool_name:
            raise ValueError("role=tool 메시지에는 tool_name이 필요합니다")
        if self.role != "tool" and (self.tool_name or self.tool_input or self.tool_output):
            raise ValueError("tool_* 필드는 role=tool 메시지에만 씁니다")
        return self
