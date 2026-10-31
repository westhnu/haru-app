"""query_cost 재시도·간격 — 외부 호출 없는 단위 테스트."""

from pathlib import Path
from typing import Any

from scripts.bench import query_cost as qc


class FlakySvc:
    def __init__(self, fails: int) -> None:
        self.fails, self.calls = fails, 0

    def ask(self, q: str, context_type: str) -> Any:
        self.calls += 1
        if self.calls <= self.fails:
            raise ValueError("ValidationException: Model use case details have not been submitted")
        return type(
            "R",
            (),
            {
                "source": "knowledge_base",
                "summary_source": "model",
                "answer": "a",
                "citations": [],
                "is_mock": False,
                "disclaimer": "d",
            },
        )()


def _run(fails: int) -> tuple[dict[str, Any], list[float], FlakySvc]:
    waits: list[float] = []
    svc = FlakySvc(fails)
    rec = qc.RecordingClient(inner=None)
    row = qc.run_one(svc, rec, 1, "kb_sample", "PER", sleep=waits.append)
    return row, waits, svc


def test_success_without_retry() -> None:
    row, waits, svc = _run(0)
    assert row["status"] == "ok" and row["retries"] == 0 and waits == [] and svc.calls == 1


def test_retry_then_success_records_first_error() -> None:
    row, waits, svc = _run(2)
    assert row["status"] == "ok" and row["retries"] == 2
    assert row["first_error"] == "ValueError" and waits == [1, 2] and svc.calls == 3


def test_gives_up_after_three_retries() -> None:
    row, waits, svc = _run(10)
    assert row["status"] == "error" and row["error"] == "ValueError"
    assert row["retries"] == 3 and waits == [1, 2, 4] and svc.calls == 4


def test_summary_reports_retries_and_title() -> None:
    ok, _, _ = _run(1)
    bad, _, _ = _run(10)
    md = qc.summarize([ok, bad], Path("run_x.csv"), ("2026-10-31T00:00:00", "x"), "2차 벤치")
    assert "2차 벤치 (2건 실측)" in md
    assert "재시도: 2건 쿼리, 총 4회 (재시도 후 성공 1건, 첫 에러 {'ValueError': 2})" in md
