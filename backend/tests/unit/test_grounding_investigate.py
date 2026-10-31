"""T-514 grounding_investigate — 외부 호출 없는 단위 테스트."""

import json
from pathlib import Path

from scripts.bench import grounding_investigate as gi

QUERIES = (
    Path(__file__).resolve().parents[3]
    / "planning"
    / "metrics"
    / "t514"
    / "blocked_normal_queries.json"
)


def _resp(action, grounding=None, topics=()):
    a = {}
    if grounding is not None:
        a["contextualGroundingPolicy"] = {
            "filters": [
                {
                    "type": "GROUNDING",
                    "threshold": 0.75,
                    "score": grounding[0],
                    "action": grounding[1],
                }
            ]
        }
    if topics:
        a["topicPolicy"] = {"topics": [{"name": t, "action": "BLOCKED"} for t in topics]}
    return {"action": action, "assessments": [a] if a else []}


Q = {"idx": 1, "query": "PER?", "group": "common_term", "stage_guess": "output", "latency_ms": 1.0}
RET = {
    "retrievalResults": [
        {
            "score": 0.66,
            "content": {"text": "c"},
            "location": {"s3Location": {"uri": "s3://b/glossary/term_001.txt"}},
        }
    ]
}
ANS = {"answer": "PER은 ...", "cached": True}


def test_threshold_sweep_grounding_only():
    row = gi.summarize_row(
        Q, RET, ANS, _resp("NONE"), _resp("GUARDRAIL_INTERVENED", (0.55, "BLOCKED"))
    )
    assert row["grounding_score"] == 0.55 and row["retrieve_top1_file"] == "term_001.txt"
    assert row["blocked_at_0.75"] and row["blocked_at_0.60"]
    assert not row["blocked_at_0.50"] and not row["blocked_at_0.30"]


def test_other_policy_block_survives_lower_threshold():
    row = gi.summarize_row(
        Q,
        RET,
        ANS,
        _resp("NONE"),
        _resp("GUARDRAIL_INTERVENED", (0.9, "NONE"), topics=["investment-advice"]),
    )
    assert all(row[f"blocked_at_{t:.2f}"] for t in gi.THRESHOLDS)


def test_input_block_survives_lower_threshold():
    row = gi.summarize_row(
        Q,
        RET,
        ANS,
        _resp("GUARDRAIL_INTERVENED", topics=["investment-advice"]),
        _resp("NONE", (0.9, "NONE")),
    )
    assert row["input_action"] == "INTERVENED"
    assert all(row[f"blocked_at_{t:.2f}"] for t in gi.THRESHOLDS)


def test_queries_file_is_normal_blocked_only():
    qs = json.loads(QUERIES.read_text(encoding="utf-8"))
    assert len(qs) == 40
    assert {q["group"] for q in qs} == {"kb_sample", "common_term"}
