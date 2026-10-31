"""Checklist 라우터 채점."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_checklist_score_sample() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/checklists/sample-value/score")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert body["satisfied"] == 2
    assert body["unsatisfied"] == 1
    assert body["score_pct"] == pytest.approx(66.7, abs=0.1)


def test_checklist_404() -> None:
    client = TestClient(create_app())
    r = client.get("/api/v1/checklists/missing/score")
    assert r.status_code == 404
