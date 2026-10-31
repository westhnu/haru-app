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


# --- Sprint 3b: memo 블록 추가·삭제, stock_code 필터 ---------------------------------


def _new_workbook(client: TestClient, code: str = "000660", name: str = "SK하이닉스") -> str:
    """샘플을 건드리지 않도록 테스트마다 새 워크북을 만든다 (in-memory 저장소는 모듈 전역)."""
    r = client.post(
        "/api/v1/workbooks", json={"stock_code": code, "stock_name": name, "title": f"{name} 분석"}
    )
    assert r.status_code == 200
    return str(r.json()["id"])


def test_list_workbooks_filter_by_stock_code() -> None:
    client = TestClient(create_app())
    _new_workbook(client, code="051910", name="LG화학")
    r = client.get("/api/v1/workbooks", params={"stock_code": "005930"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == len(data["workbooks"]) >= 1
    assert {w["stock_code"] for w in data["workbooks"]} == {"005930"}
    none = client.get("/api/v1/workbooks", params={"stock_code": "999999"}).json()
    assert none == {"workbooks": [], "total": 0}


def test_sample_memo_has_stable_id() -> None:
    client = TestClient(create_app())
    wb = client.get("/api/v1/workbooks/sample-samsung").json()
    assert any(b["id"] == "sample-memo-001" and b["block_type"] == "memo" for b in wb["blocks"])


def test_add_block_to_workbook_memo() -> None:
    client = TestClient(create_app())
    wb_id = _new_workbook(client)
    before = client.get(f"/api/v1/workbooks/{wb_id}").json()["updated_at"]
    r = client.post(
        f"/api/v1/workbooks/{wb_id}/blocks",
        json={"block_type": "memo", "content": {"text": "  HBM 비중 확인  "}},
    )
    assert r.status_code == 200
    block = r.json()
    assert block["block_type"] == "memo"
    assert block["content"] == {"text": "HBM 비중 확인"}  # 앞뒤 공백 제거
    assert block["id"]
    wb = client.get(f"/api/v1/workbooks/{wb_id}").json()
    assert [b["id"] for b in wb["blocks"]] == [block["id"]]
    assert wb["updated_at"] >= before


def test_add_block_memo_text_required() -> None:
    client = TestClient(create_app())
    wb_id = _new_workbook(client)
    url = f"/api/v1/workbooks/{wb_id}/blocks"
    for content in (
        {"text": ""},
        {"text": "   "},
        {"text": "가" * 1001},
        {},
        {"text": "a", "x": 1},
    ):
        r = client.post(url, json={"block_type": "memo", "content": content})
        assert r.status_code == 422, content
    ok = client.post(url, json={"block_type": "memo", "content": {"text": "가" * 1000}})
    assert ok.status_code == 200
    assert len(client.get(f"/api/v1/workbooks/{wb_id}").json()["blocks"]) == 1


def test_add_block_invalid_type_rejected() -> None:
    client = TestClient(create_app())
    wb_id = _new_workbook(client)
    url = f"/api/v1/workbooks/{wb_id}/blocks"
    unknown = client.post(url, json={"block_type": "stock_tip", "content": {"text": "x"}})
    assert unknown.status_code == 422  # Literal 밖
    not_yet = client.post(url, json={"block_type": "financial", "content": {"x": 1}})
    assert not_yet.status_code == 422  # Literal 안이지만 MVP 미지원
    missing_wb = client.post(
        "/api/v1/workbooks/nope/blocks", json={"block_type": "memo", "content": {"text": "x"}}
    )
    assert missing_wb.status_code == 404
    assert client.get(f"/api/v1/workbooks/{wb_id}").json()["blocks"] == []


def test_delete_block() -> None:
    client = TestClient(create_app())
    wb_id = _new_workbook(client)
    url = f"/api/v1/workbooks/{wb_id}/blocks"
    a = client.post(url, json={"block_type": "memo", "content": {"text": "A"}}).json()
    b = client.post(url, json={"block_type": "memo", "content": {"text": "B"}}).json()
    r = client.delete(f"{url}/{a['id']}")
    assert r.status_code == 204
    assert r.content == b""
    assert [x["id"] for x in client.get(f"/api/v1/workbooks/{wb_id}").json()["blocks"]] == [b["id"]]


def test_delete_block_404() -> None:
    client = TestClient(create_app())
    wb_id = _new_workbook(client)
    assert client.delete(f"/api/v1/workbooks/{wb_id}/blocks/nope").status_code == 404
    assert client.delete("/api/v1/workbooks/nope/blocks/nope").status_code == 404
