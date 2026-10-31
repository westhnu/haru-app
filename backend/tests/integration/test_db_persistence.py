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
