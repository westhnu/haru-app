"""Phase B POST /checklists/{id}/items/{item_id}/evaluate — Fake 서비스 주입."""

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.checklist_eval_service import ChecklistEvalService, get_checklist_eval_service
from app.services.dart_tool import DartRateLimitError
from tests.unit.test_checklist_eval_service import DART_URL, FakeDartTool, FakeRuntime, make_dart


class RaisingDart:
    def fetch_dart_financial(self, stock_code: str):  # noqa: ANN201
        raise DartRateLimitError("limit")


def client_with(dart_tool, runtime) -> TestClient:  # noqa: ANN001
    app = create_app()
    svc = ChecklistEvalService(Settings(_env_file=None), dart_tool, runtime_client=runtime)
    app.dependency_overrides[get_checklist_eval_service] = lambda: svc
    return TestClient(app)


def _new(client: TestClient, code: str) -> tuple[str, str]:
    cl = client.post("/api/v1/checklists", json={"stock_code": code, "stock_name": "x"}).json()
    item = client.post(
        f"/api/v1/checklists/{cl['id']}/items", json={"principle": "부채비율이 200% 미만인가?"}
    ).json()
    return cl["id"], item["id"]


@pytest.mark.usefixtures("seeded_db")
def test_evaluate_endpoint_success_does_not_persist() -> None:
    payload = {
        "suggested_status": "satisfied",
        "reasoning": "부채비율 40.0%입니다.",
        "used_facts": ["부채비율(%)"],
    }
    client = client_with(
        FakeDartTool(make_dart()), FakeRuntime(json.dumps(payload, ensure_ascii=False))
    )
    r = client.post("/api/v1/checklists/sample-value/items/sample-value-1/evaluate")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["suggested_status"] == "satisfied" and body["evaluation_source"] == "bedrock"
    assert body["sources"][0]["url"] == DART_URL and body["disclaimer"]
    item = client.get("/api/v1/checklists/sample-value").json()["items"][0]
    assert item["status"] == "uncertain" and item["reasoning"] == ""  # 제안만, 저장 안 함


def test_evaluate_endpoint_item_not_found() -> None:
    client = client_with(FakeDartTool(make_dart()), FakeRuntime("{}"))
    cl_id, _ = _new(client, "005930")
    assert client.post(f"/api/v1/checklists/{cl_id}/items/nope/evaluate").status_code == 404
    assert client.post("/api/v1/checklists/nope/items/x/evaluate").status_code == 404


def test_evaluate_endpoint_unsupported_market() -> None:
    dart = FakeDartTool(make_dart())
    client = client_with(dart, FakeRuntime("{}"))
    cl_id, item_id = _new(client, "NVDA")
    r = client.post(f"/api/v1/checklists/{cl_id}/items/{item_id}/evaluate")
    assert r.status_code == 422 and "DART" in r.json()["detail"]
    assert dart.calls == []


def test_evaluate_endpoint_maps_dart_errors() -> None:
    client = client_with(RaisingDart(), FakeRuntime("{}"))
    cl_id, item_id = _new(client, "005930")
    r = client.post(f"/api/v1/checklists/{cl_id}/items/{item_id}/evaluate")
    assert r.status_code == 503
