"""Phase E GET /api/v1/today — '오늘의 흐름' 분기. 테스트마다 빈 in-memory DB (conftest)."""

import re

import pytest
from fastapi.testclient import TestClient

from app.core.guardrail import find_tone_violations
from app.main import create_app

TODAY = "/api/v1/today"
# 근거 없는 날짜·일정 문구 금지 (Phase E 설계 결정)
DATE_GUESS = re.compile(r"다음 분기|다음 주|내일|\d+\s*일\s*(뒤|후|전)|공시 일정")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _checklist(client: TestClient, code: str, statuses: list[str]) -> str:
    cl = client.post(
        "/api/v1/checklists", json={"stock_code": code, "stock_name": "SK하이닉스"}
    ).json()
    for i, st in enumerate(statuses):
        item = client.post(
            f"/api/v1/checklists/{cl['id']}/items", json={"principle": f"원칙 {i}"}
        ).json()
        client.patch(f"/api/v1/checklists/{cl['id']}/items/{item['id']}", json={"status": st})
    return str(cl["id"])


def _entry(client: TestClient, **over: object) -> dict:
    body: dict = {
        "stock_code": "000660",
        "stock_name": "SK하이닉스",
        "decision": "buy",
        "reasoning": "근거",
    }
    body.update(over)
    r = client.post("/api/v1/journal/entries", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_empty_state(client: TestClient) -> None:
    card = client.get(TODAY).json()
    assert card["next_action"] == "empty"
    assert card["cta_label"] == "검색" and card["cta_href"] == ""
    assert card["context"] == {}


def test_checklist_incomplete(client: TestClient) -> None:
    cl_id = _checklist(client, "000660", ["satisfied", "unsatisfied", "uncertain"])
    _entry(client, checklist_id=cl_id)
    card = client.get(TODAY).json()
    assert card["next_action"] == "checklist_incomplete"
    assert "매수 결정 (본인 기록)" in card["message"]
    assert "1/3 충족" in card["message"] and "1건 판단 보류" in card["message"]
    assert card["cta_href"].startswith("/stock/000660?") and card["cta_href"].endswith(
        "&tab=workbook"
    )
    assert card["context"]["score_satisfied"] == 1 and card["context"]["score_total"] == 3
    assert card["context"]["score_uncertain"] == 1


def test_review_decision(client: TestClient) -> None:
    cl_id = _checklist(client, "000660", ["satisfied", "unsatisfied"])
    _entry(client, checklist_id=cl_id, decision="watch")
    card = client.get(TODAY).json()
    assert card["next_action"] == "review_decision"
    assert "관망 (본인 기록)" in card["message"]
    assert card["cta_href"] == "/journal"
    assert card["context"]["score_total"] == 2


def test_review_decision_without_checklist(client: TestClient) -> None:
    _entry(client, decision="hold")
    card = client.get(TODAY).json()
    assert card["next_action"] == "review_decision" and "보유 (본인 기록)" in card["message"]


def test_start_new(client: TestClient) -> None:
    client.post(
        "/api/v1/workbooks", json={"stock_code": "035720", "stock_name": "카카오", "title": "t"}
    )
    card = client.get(TODAY).json()
    assert card["next_action"] == "start_new"
    assert "카카오" in card["message"]
    assert card["cta_href"].startswith("/stock/035720?name=%EC%B9%B4%EC%B9%B4%EC%98%A4")


def test_latest_entry_wins(client: TestClient) -> None:
    _entry(client, stock_code="005930", stock_name="삼성전자", decision="watch")
    _entry(client, stock_code="000660", stock_name="SK하이닉스", decision="sell")
    card = client.get(TODAY).json()
    assert card["context"]["stock_code"] == "000660" and "매도 결정 (본인 기록)" in card["message"]


@pytest.mark.usefixtures("seeded_db")
def test_seeded_sample_points_to_unfinished_checklist(client: TestClient) -> None:
    # 샘플 저널(관망)이 판단 전 상태의 샘플 체크리스트와 연결돼 있다
    card = client.get(TODAY).json()
    assert card["next_action"] == "checklist_incomplete"
    assert "관망 (본인 기록)" in card["message"]


def test_disclaimer_always_present_and_no_date_guess(client: TestClient) -> None:
    cards = [client.get(TODAY).json()]
    client.post(
        "/api/v1/workbooks", json={"stock_code": "035720", "stock_name": "카카오", "title": "t"}
    )
    cards.append(client.get(TODAY).json())
    cl_id = _checklist(client, "000660", ["uncertain"])
    _entry(client, checklist_id=cl_id)
    cards.append(client.get(TODAY).json())
    _entry(client)
    cards.append(client.get(TODAY).json())
    assert {c["next_action"] for c in cards} == {
        "empty",
        "start_new",
        "checklist_incomplete",
        "review_decision",
    }
    for c in cards:
        assert c["disclaimer"] == "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."
        assert not DATE_GUESS.search(c["message"]), c["message"]
        # 말투 가이드 (F1): message·CTA 모두 명사형
        assert find_tone_violations(c["message"]) == [], c["message"]
        assert find_tone_violations(c["cta_label"]) == [], c["cta_label"]
