"""KI-020 B topic_eval — 외부 호출 없는 단위 테스트 (fake 클라이언트)."""

import json
from pathlib import Path

import pytest

from scripts.bench import topic_eval as te
from scripts.guardrail.create_guardrail import _build_kwargs
from scripts.guardrail.topic_candidates import CANDIDATE_TOPICS, candidate_topic_policy

TESTSET = Path(__file__).resolve().parents[3] / "planning" / "testsets" / "principle_test_50.json"


def test_testset_shape():
    rows = te.load_testset(TESTSET)
    groups = [r["group"] for r in rows]
    assert len(rows) == 50
    assert groups.count("principle_1") == 25
    assert groups.count("principle_1_price") == 10
    assert groups.count("normal") == 15
    assert all((r["expected"] == "ALLOW") == (r["group"] == "normal") for r in rows)


@pytest.mark.parametrize("cand", ["A", "B", "C"])
def test_candidate_limits_and_future_price_kept(cand):
    topics = candidate_topic_policy(cand)["topicsConfig"]
    assert "future-price-guarantee" in [t["name"] for t in topics]
    for t in topics:
        assert len(t["definition"]) <= 200 and len(t["examples"]) <= 5
        assert all(len(e) <= 100 for e in t["examples"])


def test_candidate_examples_not_in_testset():
    queries = {r["query"] for r in te.load_testset(TESTSET)}
    examples = {e for ts in CANDIDATE_TOPICS.values() for t in ts for e in t["examples"]}
    assert not examples & queries


class FakeBedrock:
    def __init__(self, name="haru-topic-eval-a"):
        self.name, self.created, self.deleted = name, None, []

    def create_guardrail(self, **kw):
        self.created = kw
        return {"guardrailId": "tmp123"}

    def get_guardrail(self, **kw):
        return {"status": "READY", "name": self.name}

    def delete_guardrail(self, guardrailIdentifier):
        self.deleted.append(guardrailIdentifier)


def test_create_temp_replaces_only_topics():
    fb = FakeBedrock()
    assert te.create_temp(fb, "A") == "tmp123"
    base = _build_kwargs()
    assert fb.created["name"] == "haru-topic-eval-a-classic"
    assert "crossRegionConfig" not in fb.created
    assert fb.created["topicPolicyConfig"] == candidate_topic_policy("A")
    # CLASSIC 평가는 tier·profile을 걷어낸다 (실 설정은 KI-023 이후 Standard)
    assert "tierConfig" not in fb.created["topicPolicyConfig"]
    assert "tierConfig" not in fb.created["contentPolicyConfig"]
    assert (
        fb.created["contentPolicyConfig"]["filtersConfig"]
        == base["contentPolicyConfig"]["filtersConfig"]
    )
    for k in base:
        if k not in ("name", "topicPolicyConfig", "contentPolicyConfig", "crossRegionConfig"):
            assert fb.created[k] == base[k]


def test_delete_temp_refuses_real_guardrail():
    fb = FakeBedrock(name="haru-investment-guardrail")
    with pytest.raises(RuntimeError):
        te.delete_temp(fb, "gtulvril25hb")
    assert fb.deleted == []


def _resp(action, topics=(), grounding=None):
    a = {}
    if topics:
        a["topicPolicy"] = {"topics": [{"name": t, "action": "BLOCKED"} for t in topics]}
    if grounding is not None:
        a["contextualGroundingPolicy"] = {
            "filters": [{"type": "GROUNDING", "score": grounding[0], "action": grounding[1]}]
        }
    return {"action": action, "assessments": [a] if a else []}


class FakeRuntime:
    def __init__(self, plan):
        self.plan, self.calls = plan, []

    def apply_guardrail(self, **kw):
        self.calls.append(kw)
        return self.plan[(kw["content"][-1]["text"]["text"], kw["source"])]


def test_evaluate_stages_and_correctness(monkeypatch):
    monkeypatch.setattr(te, "SLEEP_S", 0)
    rows = [
        {"id": "p1_01", "query": "삼성전자 사?", "group": "principle_1", "expected": "BLOCK"},
        {"id": "normal_01", "query": "PER?", "group": "normal", "expected": "ALLOW"},
    ]
    cache = {"PER?": {"answer": "PER은 ...", "chunks": ["doc"]}}
    syn = te.SYNTHETIC_ANSWERS["principle_1"]
    rt = FakeRuntime(
        {
            ("삼성전자 사?", "INPUT"): _resp("GUARDRAIL_INTERVENED", ["investment-advice"]),
            (syn, "OUTPUT"): _resp("NONE"),
            ("PER?", "INPUT"): _resp("NONE"),
            ("PER은 ...", "OUTPUT"): _resp(
                "GUARDRAIL_INTERVENED", ["investment-advice"], (0.3, "BLOCKED")
            ),
        }
    )
    p1, nm = te.evaluate(rt, "gid", "DRAFT", rows, cache)
    assert p1["final_action"] == "INTERVENED" and p1["correct"] and p1["blocked_stage"] == "input"
    assert nm["final_action"] == "INTERVENED" and not nm["correct"]
    assert nm["blocked_by_topic"] and nm["blocked_by_grounding"] and nm["grounding_score"] == 0.3
    qualifiers = [b["text"].get("qualifiers") for b in rt.calls[3]["content"]]
    assert qualifiers == [["grounding_source"], ["query"], ["guard_content"]]


def test_cache_hit_skips_generation(tmp_path, monkeypatch):
    rows = [{"id": "normal_01", "query": "PER?", "group": "normal", "expected": "ALLOW"}]
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"PER?": {"answer": "a", "chunks": []}}), encoding="utf-8")
    monkeypatch.setattr(te, "get_agent_runtime_client", lambda: pytest.fail("no network"))
    assert te.build_normal_cache(rows, p)["PER?"]["answer"] == "a"


def test_args_validation():
    with pytest.raises(SystemExit):
        te.parse_args(["--testset", "x.json", "--candidate", "A"])  # --create-temp 누락
    with pytest.raises(SystemExit):
        te.parse_args(["--testset", "x.json"])


def test_standard_tier_kwargs():
    kw = te.temp_kwargs("A", "STANDARD")
    base = _build_kwargs()
    assert kw["name"] == "haru-topic-eval-a-standard"
    assert kw["topicPolicyConfig"]["tierConfig"] == {"tierName": "STANDARD"}
    assert kw["contentPolicyConfig"]["tierConfig"] == {"tierName": "STANDARD"}
    assert kw["crossRegionConfig"] == {"guardrailProfileIdentifier": "apac.guardrail.v1:0"}
    # grounding은 서울 Standard 미지원 → Classic 유지 (tierConfig 없음)
    assert kw["contextualGroundingPolicyConfig"] == base["contextualGroundingPolicyConfig"]
    assert (
        kw["contentPolicyConfig"]["filtersConfig"] == base["contentPolicyConfig"]["filtersConfig"]
    )
    # CLASSIC 변환이 원본 설정 객체를 오염시키지 않아야 한다
    te.temp_kwargs("A", "CLASSIC")
    assert _build_kwargs()["topicPolicyConfig"]["tierConfig"] == {"tierName": "STANDARD"}


def test_baseline_candidate_is_current_definition():
    from scripts.guardrail.create_guardrail import TOPIC_POLICY

    assert candidate_topic_policy("baseline") == TOPIC_POLICY
    assert te.temp_kwargs("baseline", "STANDARD")["topicPolicyConfig"] == TOPIC_POLICY
    assert te.temp_kwargs("baseline", "STANDARD")["name"] == "haru-topic-eval-baseline-standard"


def test_standard_tier_rejected_for_real_guardrail():
    with pytest.raises(SystemExit):
        te.parse_args(["--testset", "x.json", "--guardrail-id", "g", "--tier", "STANDARD"])
