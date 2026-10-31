"""Journal 라우터 + 가상 포트폴리오."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_journal_entries_has_sample() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/journal/entries")
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_virtual_portfolio_empty_initially() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/journal/portfolio")
    assert r.status_code == 200
    # 샘플 entry는 watch라서 포지션 없음
    assert r.json()["total"] == 0
