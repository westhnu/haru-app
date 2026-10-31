"""Checklist 라우터 채점."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_checklist_score_sample() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/checklists/sample-value/score")
    assert r.status_code == 200
    body = r.json()
    # 원칙 2 교정 후 샘플은 판단 전 상태(uncertain)로만 제공한다.
    assert body["total"] == 3
    assert body["satisfied"] == 0
    assert body["uncertain"] == 3
    assert body["score_pct"] == pytest.approx(0.0)


def test_checklist_404() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/checklists/missing/score")
    assert r.status_code == 404


# --- Sprint 3c: 종목별 생성, 원칙 추가·상태 변경·삭제, 필터 --------------------------------


def _new_checklist(client: TestClient, code: str = "000660", name: str = "SK하이닉스") -> str:
    """샘플을 건드리지 않도록 테스트마다 새 체크리스트를 만든다 (in-memory 저장소는 모듈 전역)."""
    r = client.post("/api/v1/checklists", json={"stock_code": code, "stock_name": name})
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == [] and body["stock_code"] == code
    return str(body["id"])


def _add(client: TestClient, cl_id: str, principle: str) -> dict:
    r = client.post(f"/api/v1/checklists/{cl_id}/items", json={"principle": principle})
    assert r.status_code == 200, r.text
    return r.json()


def test_sample_has_no_unsourced_figures_principle2() -> None:
    # 원칙 문장의 기준값("3년", "10%")은 사용자가 정한 기준이라 허용한다.
    # 금지 대상은 종목 수치를 사실처럼 적은 근거(예: "현재 PER 11.2")와 미리 채운 판정이다.
    client = TestClient(create_app())
    cl = client.get("/api/v1/checklists/sample-value").json()
    assert len(cl["items"]) == 3
    for item in cl["items"]:
        assert item["status"] == "uncertain"
        assert item["reasoning"] == ""


def test_create_checklist() -> None:
    client = TestClient(create_app())
    cl_id = _new_checklist(client)
    assert client.get(f"/api/v1/checklists/{cl_id}").status_code == 200
    assert (
        client.post("/api/v1/checklists", json={"stock_code": "", "stock_name": "x"}).status_code
        == 422
    )


def test_add_item_and_validate_principle_length() -> None:
    client = TestClient(create_app())
    cl_id = _new_checklist(client)
    item = _add(client, cl_id, "  영업이익률이 개선되는가?  ")
    assert item["principle"] == "영업이익률이 개선되는가?"
    assert item["status"] == "uncertain" and item["id"]
    url = f"/api/v1/checklists/{cl_id}/items"
    for bad in ({"principle": ""}, {"principle": "   "}, {"principle": "가" * 201}, {}):
        assert client.post(url, json=bad).status_code == 422, bad
    assert client.post(url, json={"principle": "가" * 200}).status_code == 200
    assert client.post("/api/v1/checklists/nope/items", json={"principle": "x"}).status_code == 404


def test_update_item_status() -> None:
    client = TestClient(create_app())
    cl_id = _new_checklist(client)
    item = _add(client, cl_id, "현금흐름이 플러스인가?")
    url = f"/api/v1/checklists/{cl_id}/items/{item['id']}"
    before = client.get(f"/api/v1/checklists/{cl_id}").json()["updated_at"]
    r = client.patch(url, json={"status": "satisfied", "reasoning": "사업보고서 현금흐름표 확인"})
    assert r.status_code == 200
    assert r.json()["status"] == "satisfied"
    assert r.json()["reasoning"] == "사업보고서 현금흐름표 확인"
    # 부분 변경: reasoning만 바꾸면 status는 유지
    assert client.patch(url, json={"reasoning": ""}).json()["status"] == "satisfied"
    score = client.get(f"/api/v1/checklists/{cl_id}/score").json()
    assert score["satisfied"] == 1 and score["score_pct"] == 100.0
    assert client.get(f"/api/v1/checklists/{cl_id}").json()["updated_at"] >= before
    assert client.patch(url, json={"status": "maybe"}).status_code == 422
    assert client.patch(url, json={}).status_code == 422
    assert client.patch(url, json={"reasoning": "가" * 1001}).status_code == 422
    assert (
        client.patch(
            f"/api/v1/checklists/{cl_id}/items/nope", json={"status": "satisfied"}
        ).status_code
        == 404
    )


def test_delete_item() -> None:
    client = TestClient(create_app())
    cl_id = _new_checklist(client)
    a, b = _add(client, cl_id, "A"), _add(client, cl_id, "B")
    r = client.delete(f"/api/v1/checklists/{cl_id}/items/{a['id']}")
    assert r.status_code == 204 and r.content == b""
    assert [i["id"] for i in client.get(f"/api/v1/checklists/{cl_id}").json()["items"]] == [b["id"]]
    assert client.delete(f"/api/v1/checklists/{cl_id}/items/{a['id']}").status_code == 404
    assert client.delete("/api/v1/checklists/nope/items/x").status_code == 404


def test_filter_by_stock_code() -> None:
    client = TestClient(create_app())
    _new_checklist(client, code="051910", name="LG화학")
    data = client.get("/api/v1/checklists", params={"stock_code": "005930"}).json()
    assert data["total"] == len(data["checklists"]) >= 1
    assert {c["stock_code"] for c in data["checklists"]} == {"005930"}
    assert client.get("/api/v1/checklists", params={"stock_code": "999999"}).json()["total"] == 0
