"""Workbook 라우터 기본 CRUD."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_list_workbooks_has_sample() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/workbooks")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert any(w["stock_code"] == "005930" for w in data["workbooks"])


def test_create_workbook() -> None:
    client = TestClient(create_app())
    r = client.post(
        "/api/v1/workbooks",
        json={"stock_code": "035720", "stock_name": "카카오", "title": "카카오 분석"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stock_code"] == "035720"
    assert "id" in body


def test_get_workbook_404() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/workbooks/nonexistent-id")
    assert r.status_code == 404
