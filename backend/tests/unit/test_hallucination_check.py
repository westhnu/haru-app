"""T-514-4 hallucination_check — 외부 호출 없는 단위 테스트."""

from scripts.bench import hallucination_check as hc
from scripts.bench.topic_eval import TEMP_PREFIX
from scripts.guardrail.create_guardrail import _build_kwargs


def test_temp_kwargs_changes_only_grounding_threshold():
    kw, base = hc.temp_kwargs(0.5), _build_kwargs()
    assert kw["name"] == f"{TEMP_PREFIX}grounding-050"
    assert kw["contextualGroundingPolicyConfig"]["filtersConfig"][0]["threshold"] == 0.5
    for k in base:
        if k not in ("name", "contextualGroundingPolicyConfig"):
            assert kw[k] == base[k], k
    # 원본 설정 오염 없음
    assert (
        _build_kwargs()["contextualGroundingPolicyConfig"]
        == base["contextualGroundingPolicyConfig"]
    )


def test_classify():
    assert hc.classify({"status": "ok", "source": "guardrail_blocked"}).startswith("근거 없음")
    assert hc.classify({"status": "ok", "source": "general_knowledge"}) == "판정 필요"
    assert hc.classify({"status": "error:X", "source": ""}) == "에러"


def test_queries_are_eight():
    assert len(hc.QUERIES) == 8
