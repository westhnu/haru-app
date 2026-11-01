"""Journal 라우터 + 가상 포트폴리오."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.mark.usefixtures("seeded_db")
def test_journal_entries_has_sample() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/journal/entries")
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.usefixtures("seeded_db")
def test_virtual_portfolio_empty_initially() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/journal/portfolio")
    assert r.status_code == 200
    # 샘플 entry는 watch라서 포지션 없음
    assert r.json()["total"] == 0


# --- Sprint 3c: 생성 요청 검증, 삭제, 필터 -----------------------------------------------

ENTRIES = "/api/v1/journal/entries"


def _entry(**over: object) -> dict:
    body: dict = {
        "stock_code": "000660",
        "stock_name": "SK하이닉스",
        "decision": "watch",
        "reasoning": "실적 발표 후 다시 판단",
    }
    body.update(over)
    return body


@pytest.mark.usefixtures("seeded_db")
def test_sample_entry_has_no_numbers_principle2() -> None:
    client = TestClient(create_app())
    sample = next(e for e in client.get(ENTRIES).json()["entries"] if e["id"] == "sample-1")
    assert not any(ch.isdigit() for ch in sample["reasoning"])


def test_create_entry_server_generates_id_and_rejects_client_fields() -> None:
    client = TestClient(create_app())
    r = client.post(ENTRIES, json=_entry())
    assert r.status_code == 200
    body = r.json()
    assert body["id"] and body["created_at"]
    assert client.post(ENTRIES, json=_entry(id="mine")).status_code == 422
    assert client.post(ENTRIES, json=_entry(created_at="2020-01-01T00:00:00Z")).status_code == 422
    assert client.delete(f"{ENTRIES}/{body['id']}").status_code == 204


def test_create_entry_rejects_negative_price() -> None:
    client = TestClient(create_app())
    assert client.post(ENTRIES, json=_entry(virtual_price=-1)).status_code == 422
    assert client.post(ENTRIES, json=_entry(virtual_quantity=-1)).status_code == 422
    assert client.post(ENTRIES, json=_entry(decision="strong_buy")).status_code == 422


def test_create_entry_rejects_empty_reasoning() -> None:
    client = TestClient(create_app())
    for reasoning in ("", "   ", "가" * 1001):
        assert client.post(ENTRIES, json=_entry(reasoning=reasoning)).status_code == 422


def test_delete_entry() -> None:
    client = TestClient(create_app())
    entry_id = client.post(ENTRIES, json=_entry(decision="hold")).json()["id"]
    r = client.delete(f"{ENTRIES}/{entry_id}")
    assert r.status_code == 204 and r.content == b""
    assert all(e["id"] != entry_id for e in client.get(ENTRIES).json()["entries"])
    assert client.delete(f"{ENTRIES}/{entry_id}").status_code == 404


def test_filter_entries_by_stock_code() -> None:
    client = TestClient(create_app())
    entry_id = client.post(ENTRIES, json=_entry(stock_code="051910", stock_name="LG화학")).json()[
        "id"
    ]
    data = client.get(ENTRIES, params={"stock_code": "051910"}).json()
    assert data["total"] >= 1 and {e["stock_code"] for e in data["entries"]} == {"051910"}
    assert client.get(ENTRIES, params={"stock_code": "999999"}).json()["total"] == 0
    client.delete(f"{ENTRIES}/{entry_id}")


def test_portfolio_aggregates_buy_without_pnl_and_cleans_up() -> None:
    client = TestClient(create_app())
    ids = [
        client.post(
            ENTRIES,
            json=_entry(
                stock_code="035720",
                stock_name="카카오",
                decision="buy",
                virtual_price=p,
                virtual_quantity=q,
            ),
        ).json()["id"]
        for p, q in ((100.0, 1), (200.0, 3))
    ]
    pos = next(
        p
        for p in client.get("/api/v1/journal/portfolio").json()["positions"]
        if p["stock_code"] == "035720"
    )
    assert pos == {
        "stock_code": "035720",
        "stock_name": "카카오",
        "quantity": 4,
        "avg_price": 175.0,
    }
    for entry_id in ids:  # 다른 테스트(포트폴리오 비어 있음)에 영향 주지 않도록 정리
        assert client.delete(f"{ENTRIES}/{entry_id}").status_code == 204
    assert all(
        p["stock_code"] != "035720"
        for p in client.get("/api/v1/journal/portfolio").json()["positions"]
    )
