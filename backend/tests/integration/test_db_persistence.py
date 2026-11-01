"""Phase A: SQLite 영속성 — 재기동 후 데이터 유지, seed idempotent, FK 동작."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import engine as db_engine
from app.db.init import init_db, seed_if_empty
from app.db.models import JournalEntryORM, WorkbookORM
from app.main import create_app


def _use_engine(monkeypatch: pytest.MonkeyPatch, engine: Engine) -> None:
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    for target in ("app.db.engine", "app.main"):
        monkeypatch.setattr(f"{target}.get_engine", lambda: engine)
        monkeypatch.setattr(f"{target}.get_sessionmaker", lambda: factory)


def test_data_survives_restart_with_file_db(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'nested' / 'haru.db'}"  # 상위 디렉터리 자동 생성 확인
    first = db_engine.build_engine(url)
    _use_engine(monkeypatch, first)
    with TestClient(create_app()) as client:  # with → lifespan(init_db + seed) 실행
        wb = client.get("/api/v1/workbooks/sample-samsung").json()
        client.post(
            f"/api/v1/workbooks/{wb['id']}/blocks",
            json={"block_type": "memo", "content": {"text": "재시작 후에도 남아야 함"}},
        )
    first.dispose()
    assert (tmp_path / "nested" / "haru.db").exists()

    second = db_engine.build_engine(url)  # "uvicorn 재시작"
    _use_engine(monkeypatch, second)
    with TestClient(create_app()) as client:
        texts = [
            b["content"]["text"]
            for b in client.get("/api/v1/workbooks/sample-samsung").json()["blocks"]
        ]
        assert texts == ["매출 성장 둔화, 메모리 사이클 확인 필요", "재시작 후에도 남아야 함"]
        assert client.get("/api/v1/workbooks").json()["total"] == 1  # seed 재삽입 없음
    second.dispose()


def test_seed_is_idempotent_and_skips_non_empty_tables(isolated_db: Engine) -> None:
    with Session(isolated_db) as s:
        assert seed_if_empty(s) == ["workbooks", "checklists", "journal_entries"]
    with Session(isolated_db) as s:
        assert seed_if_empty(s) == []
        assert s.scalar(select(func.count()).select_from(WorkbookORM)) == 1


def test_seed_does_not_touch_user_data(isolated_db: Engine) -> None:
    with Session(isolated_db) as s:
        s.add(WorkbookORM(stock_code="000660", stock_name="SK하이닉스", title="내 분석"))
        s.commit()
        assert "workbooks" not in seed_if_empty(s)
        assert [w.stock_code for w in s.scalars(select(WorkbookORM))] == ["000660"]


def test_timestamps_are_utc_aware_in_api(isolated_db: Engine) -> None:
    client = TestClient(create_app())
    wb = client.post(
        "/api/v1/workbooks", json={"stock_code": "1", "stock_name": "a", "title": "t"}
    ).json()
    # SQLite naive 저장 → UTC aware 복원. 오프셋이 없으면 브라우저가 로컬 시각으로 오해한다.
    assert wb["created_at"].endswith(("Z", "+00:00"))


def test_journal_link_must_exist_and_survives_checklist_delete(isolated_db: Engine) -> None:
    client = TestClient(create_app())
    base = {
        "stock_code": "000660",
        "stock_name": "SK하이닉스",
        "decision": "watch",
        "reasoning": "r",
    }
    bad = client.post("/api/v1/journal/entries", json={**base, "checklist_id": "nope"})
    assert bad.status_code == 422
    assert (
        client.post("/api/v1/journal/entries", json={**base, "workbook_id": "nope"}).status_code
        == 422
    )

    wb_id = client.post(
        "/api/v1/workbooks", json={"stock_code": "000660", "stock_name": "x", "title": "t"}
    ).json()["id"]
    entry = client.post("/api/v1/journal/entries", json={**base, "workbook_id": wb_id})
    assert entry.status_code == 200 and entry.json()["workbook_id"] == wb_id
    # 워크북이 지워지면 기록은 남고 연결만 끊긴다 (ON DELETE SET NULL, PRAGMA foreign_keys)
    with Session(isolated_db) as s:
        s.delete(s.get(WorkbookORM, wb_id))
        s.commit()
        left = s.get(JournalEntryORM, entry.json()["id"])
        assert left is not None and left.workbook_id is None


def test_block_order_is_insertion_order(isolated_db: Engine) -> None:
    client = TestClient(create_app())
    wb_id = client.post(
        "/api/v1/workbooks", json={"stock_code": "1", "stock_name": "a", "title": "t"}
    ).json()["id"]
    for t in ("1", "2", "3", "4", "5"):
        client.post(
            f"/api/v1/workbooks/{wb_id}/blocks", json={"block_type": "memo", "content": {"text": t}}
        )
    texts = [
        b["content"]["text"] for b in client.get(f"/api/v1/workbooks/{wb_id}").json()["blocks"]
    ]
    assert texts == ["1", "2", "3", "4", "5"]


def test_init_db_is_safe_to_rerun(isolated_db: Engine) -> None:
    init_db(isolated_db)
    init_db(isolated_db)


# --- Phase G scaffold: chat_sessions·chat_messages ---------------------------------------


def test_chat_tables_created(isolated_db: Engine) -> None:
    from sqlalchemy import inspect

    tables = set(inspect(isolated_db).get_table_names())
    assert {"chat_sessions", "chat_messages"} <= tables
    fks = inspect(isolated_db).get_foreign_keys("chat_messages")
    assert (
        fks[0]["referred_table"] == "chat_sessions"
        and fks[0]["options"].get("ondelete") == "CASCADE"
    )


def test_chat_cascade_at_db_level(isolated_db: Engine) -> None:
    # ORM을 거치지 않은 삭제에서도 FK ON DELETE CASCADE(PRAGMA foreign_keys)로 메시지가 지워진다
    from sqlalchemy import text

    from app.db.models import ChatMessageORM, ChatSessionORM

    with Session(isolated_db) as s:
        s.add(
            ChatSessionORM(id="cs1", title="t", messages=[ChatMessageORM(role="user", content="a")])
        )
        s.commit()
        s.execute(text("DELETE FROM chat_sessions WHERE id = 'cs1'"))
        s.commit()
        assert s.scalar(select(func.count()).select_from(ChatMessageORM)) == 0


def test_chat_survives_restart_with_file_db(tmp_path: Path) -> None:
    from app.db.repositories import chat_repo

    url = f"sqlite:///{tmp_path / 'chat.db'}"
    first = db_engine.build_engine(url)
    init_db(first)
    with Session(first) as s:
        cs = chat_repo.create_session(s, stock_code="005930", title="삼성전자 질문")
        chat_repo.append_message(s, cs.id, "user", "PER이 뭐야?")
    first.dispose()
    second = db_engine.build_engine(url)
    init_db(second)
    with Session(second) as s:
        loaded = chat_repo.get_session(s, cs.id)
        assert loaded is not None and loaded.title == "삼성전자 질문"
        assert [m.content for m in loaded.messages] == ["PER이 뭐야?"]
    second.dispose()
