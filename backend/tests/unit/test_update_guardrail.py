"""KI-020 D: Guardrail 갱신이 차단 메시지만 바꾸고 기존 정책은 보존하는지 검증."""

from typing import Any

from app.core.guardrail import DISCLAIMER, GUARDRAIL_BLOCKED_ANSWER
from scripts.guardrail import create_guardrail as cg
from scripts.guardrail import update_guardrail as ug

GUARDRAIL_ID = "gr-test"


class FakeBedrock:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def update_guardrail(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"guardrailId": kwargs["guardrailIdentifier"], "version": "DRAFT"}


def _apply() -> dict[str, Any]:
    fake = FakeBedrock()
    assert ug.run(dry_run=False, bedrock=fake, guardrail_id=GUARDRAIL_ID) is True
    assert len(fake.calls) == 1
    return fake.calls[0]


def test_update_sets_new_output_message_distinct_from_disclaimer() -> None:
    kw = _apply()
    assert kw["blockedOutputsMessaging"] == GUARDRAIL_BLOCKED_ANSWER
    assert kw["blockedOutputsMessaging"] != DISCLAIMER
    assert DISCLAIMER not in kw["blockedOutputsMessaging"]


def test_update_keeps_input_message() -> None:
    assert _apply()["blockedInputMessaging"] == cg.BLOCKED_INPUT_MSG


def test_update_resends_all_policies_and_keeps_kr_rrn_regex_ki017() -> None:
    kw = _apply()
    assert kw["guardrailIdentifier"] == GUARDRAIL_ID
    for key in (
        "topicPolicyConfig",
        "wordPolicyConfig",
        "sensitiveInformationPolicyConfig",
        "contentPolicyConfig",
        "contextualGroundingPolicyConfig",
    ):
        assert kw[key] == cg._build_kwargs()[key], key
    regexes = kw["sensitiveInformationPolicyConfig"]["regexesConfig"]
    assert [r["name"] for r in regexes] == ["KR_RRN"]


def test_update_dry_run_makes_no_call() -> None:
    fake = FakeBedrock()
    assert ug.run(dry_run=True, bedrock=fake, guardrail_id=GUARDRAIL_ID) is True
    assert fake.calls == []


def test_build_kwargs_standard_tier_and_cross_region_ki023() -> None:
    kw = cg._build_kwargs()
    assert kw["topicPolicyConfig"]["tierConfig"] == {"tierName": "STANDARD"}
    assert kw["contentPolicyConfig"]["tierConfig"] == {"tierName": "STANDARD"}
    assert kw["crossRegionConfig"] == {"guardrailProfileIdentifier": "apac.guardrail.v1:0"}
    # 서울은 grounding Standard 미지원 → tierConfig 미지정(Classic)
    assert "tierConfig" not in kw["contextualGroundingPolicyConfig"]
    # topic 정의는 baseline-S 그대로 (KI-020 B: 정의 재설계 효과 없음)
    names = [t["name"] for t in kw["topicPolicyConfig"]["topicsConfig"]]
    assert names == ["investment-advice", "future-price-guarantee"]


def test_update_sends_standard_tier_and_cross_region_ki023() -> None:
    kw = _apply()
    assert kw["topicPolicyConfig"]["tierConfig"] == {"tierName": "STANDARD"}
    assert kw["contentPolicyConfig"]["tierConfig"] == {"tierName": "STANDARD"}
    assert kw["crossRegionConfig"] == {"guardrailProfileIdentifier": "apac.guardrail.v1:0"}


def test_grounding_threshold_050_t514() -> None:
    kw = _apply()
    filters = kw["contextualGroundingPolicyConfig"]["filtersConfig"]
    assert filters == [{"type": "GROUNDING", "threshold": 0.50, "action": "BLOCK"}]
