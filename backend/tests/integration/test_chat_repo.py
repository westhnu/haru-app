"""Phase G scaffold — chat_repo (Bedrock 호출 없음, in-memory SQLite)."""

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db.models import ChatMessageORM
from app.db.repositories import chat_repo
from app.models.chat import DEFAULT_CHAT_TITLE


@pytest.fixture
def s(isolated_db: Engine):  # noqa: ANN201
    with Session(isolated_db) as session:
        yield session


def test_create_get_list_delete(s: Session) -> None:
    a = chat_repo.create_session(s)
    assert a.title == DEFAULT_CHAT_TITLE and a.stock_code is None and a.message_count == 0
    b = chat_repo.create_session(s, stock_code="005930", title="  삼성전자  ")
    assert b.title == "삼성전자"  # 앞뒤 공백 제거
    got = chat_repo.get_session(s, b.id)
    assert got is not None and got.messages == []
    assert {x.id for x in chat_repo.list_sessions(s)} == {a.id, b.id}
    assert chat_repo.delete_session(s, a.id) is True
    assert chat_repo.get_session(s, a.id) is None
    assert chat_repo.delete_session(s, a.id) is False


def test_message_sequence_preserved_and_counts(s: Session) -> None:
    cs = chat_repo.create_session(s)
    for i in range(6):
        chat_repo.append_message(s, cs.id, "user" if i % 2 == 0 else "assistant", f"m{i}")
    got = chat_repo.get_session(s, cs.id)
    assert got is not None
    assert [m.content for m in got.messages] == [f"m{i}" for i in range(6)]
    assert got.message_count == 6
    assert chat_repo.list_sessions(s)[0].message_count == 6


def test_list_sorting_filter_and_paging(s: Session) -> None:
    old = chat_repo.create_session(s, stock_code="000660")
    new = chat_repo.create_session(s, stock_code="005930")
    chat_repo.append_message(s, old.id, "user", "갱신")  # updated_at 갱신 → 맨 위로
    assert [x.id for x in chat_repo.list_sessions(s)] == [old.id, new.id]
    assert [x.id for x in chat_repo.list_sessions(s, stock_code="005930")] == [new.id]
    assert [x.id for x in chat_repo.list_sessions(s, limit=1, offset=1)] == [new.id]
    assert len(chat_repo.list_sessions(s, limit=0)) == 1  # limit 하한 1


def test_cascade_delete_removes_messages(s: Session) -> None:
    cs = chat_repo.create_session(s)
    chat_repo.append_message(s, cs.id, "user", "a")
    chat_repo.append_message(
        s, cs.id, "tool", "{}", tool_name="query_glossary", tool_input={"q": "PER"}
    )
    assert s.query(ChatMessageORM).count() == 2
    chat_repo.delete_session(s, cs.id)
    assert s.query(ChatMessageORM).count() == 0


def test_tool_message_fields_and_validation(s: Session) -> None:
    cs = chat_repo.create_session(s)
    m = chat_repo.append_message(
        s,
        cs.id,
        "tool",
        "ok",
        tool_name="get_dart_financials",
        tool_input={"code": "005930"},
        tool_output={"debt_ratio": 40.0},
        evaluation_source="mock",
    )
    assert (
        m is not None
        and m.tool_name == "get_dart_financials"
        and m.tool_output == {"debt_ratio": 40.0}
    )
    with pytest.raises(ValidationError):
        chat_repo.append_message(s, cs.id, "tool", "x")  # tool_name 누락
    with pytest.raises(ValidationError):
        chat_repo.append_message(s, cs.id, "user", "x", tool_name="q")  # tool_* 는 tool 전용
    with pytest.raises(ValidationError):
        chat_repo.append_message(s, cs.id, "system", "x")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        chat_repo.append_message(s, cs.id, "user", "가" * 10001)
    assert chat_repo.append_message(s, "nope", "user", "x") is None


def test_user_content_pii_masked(s: Session) -> None:
    cs = chat_repo.create_session(s)
    m = chat_repo.append_message(s, cs.id, "user", "주민번호 900101-1234567 저장해줘")
    assert m is not None and "900101-1234567" not in m.content


def test_session_title_and_stock_validation(s: Session) -> None:
    with pytest.raises(ValidationError):
        chat_repo.create_session(s, title="가" * 101)
    with pytest.raises(ValidationError):
        chat_repo.create_session(s, stock_code="")
