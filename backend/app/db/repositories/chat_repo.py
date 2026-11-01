"""Chat 저장소 (Phase G scaffold). ORM ↔ Pydantic(app.models.chat) 변환을 여기서만 한다."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.guardrail import mask_pii
from app.db.models import ChatMessageORM, ChatSessionORM, utcnow
from app.models.chat import (
    DEFAULT_CHAT_TITLE,
    ChatEvaluationSource,
    ChatMessage,
    ChatMessageAppend,
    ChatRole,
    ChatSession,
    ChatSessionCreateRequest,
    ChatSessionWithMessages,
)

MAX_LIST_LIMIT = 100


def _session_model(orm: ChatSessionORM, message_count: int) -> ChatSession:
    return ChatSession(
        id=orm.id,
        stock_code=orm.stock_code,
        title=orm.title,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        message_count=message_count,
    )


def create_session(
    session: Session, stock_code: str | None = None, title: str | None = None
) -> ChatSession:
    req = ChatSessionCreateRequest(stock_code=stock_code, title=title)
    orm = ChatSessionORM(stock_code=req.stock_code, title=req.title or DEFAULT_CHAT_TITLE)
    session.add(orm)
    session.commit()
    return _session_model(orm, 0)


def get_session(session: Session, session_id: str) -> ChatSessionWithMessages | None:
    orm = session.get(ChatSessionORM, session_id)
    if orm is None:
        return None
    base = _session_model(orm, len(orm.messages))
    return ChatSessionWithMessages(
        **base.model_dump(),
        messages=[ChatMessage.model_validate(m) for m in orm.messages],
    )


def list_sessions(
    session: Session, limit: int = 20, offset: int = 0, stock_code: str | None = None
) -> list[ChatSession]:
    """최근 갱신 순. limit은 1~100으로 자른다."""
    limit = max(1, min(limit, MAX_LIST_LIMIT))
    offset = max(0, offset)
    counts = (
        select(ChatMessageORM.session_id, func.count().label("n"))
        .group_by(ChatMessageORM.session_id)
        .subquery()
    )
    stmt = (
        select(ChatSessionORM, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.session_id == ChatSessionORM.id)
        .order_by(ChatSessionORM.updated_at.desc(), ChatSessionORM.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if stock_code is not None:
        stmt = stmt.where(ChatSessionORM.stock_code == stock_code)
    return [_session_model(orm, int(n)) for orm, n in session.execute(stmt)]


def append_message(
    session: Session,
    session_id: str,
    role: ChatRole,
    content: str,
    tool_name: str | None = None,
    tool_input: dict[str, Any] | None = None,
    tool_output: dict[str, Any] | None = None,
    evaluation_source: ChatEvaluationSource | None = None,
) -> ChatMessage | None:
    """세션이 없으면 None. 사용자 입력은 저장 전에 PII(주민번호·카드·휴대폰·계좌)를 가린다."""
    data = ChatMessageAppend(
        role=role,
        content=content,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        evaluation_source=evaluation_source,
    )
    orm_session = session.get(ChatSessionORM, session_id)
    if orm_session is None:
        return None
    stored = mask_pii(data.content) if data.role == "user" else data.content
    msg = ChatMessageORM(**{**data.model_dump(), "content": stored})
    orm_session.messages.append(msg)
    orm_session.updated_at = utcnow()
    session.commit()
    return ChatMessage.model_validate(msg)


def delete_session(session: Session, session_id: str) -> bool:
    """삭제했으면 True. 메시지는 FK ON DELETE CASCADE(+ ORM delete-orphan)로 함께 지워진다."""
    orm = session.get(ChatSessionORM, session_id)
    if orm is None:
        return False
    session.delete(orm)
    session.commit()
    return True
