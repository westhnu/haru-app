"""KI-020 B — Denied Topic 재설계 후보 (planning/ki-020-topic-redesign.md).

모든 후보는 investment-advice 자리만 바꾸고 future-price-guarantee는 그대로 둔다.
examples에는 테스트셋(planning/testsets/principle_test_50.json)에 없는 문장만 넣어 과적합을 피한다.
Bedrock 제약: definition ≤ 200자, example ≤ 100자, examples ≤ 5개.
"""

import copy
from typing import Any

from scripts.guardrail.create_guardrail import GUARDRAIL_PROFILE_ID, TOPIC_POLICY

_FUTURE_PRICE = next(
    t for t in TOPIC_POLICY["topicsConfig"] if t["name"] == "future-price-guarantee"
)

CANDIDATE_TOPICS: dict[str, list[dict[str, Any]]] = {
    # A — 지목 + 행위 지시 (좁은 범위)
    "A": [
        {
            "name": "investment-advice",
            "definition": (
                "특정 종목명·종목코드·티커를 지목하면서 매수·매도·보유·손절·익절 같은 매매 행위를 "
                "지시하거나 권유하는 내용. 단순 용어 설명과 일반 투자 개념 설명은 해당하지 않음."
            ),
            "examples": [
                "카카오 지금 사세요",
                "000660은 매도하세요",
                "이 종목은 지금 들어가야 합니다",
                "네이버는 손절하는 게 맞습니다",
            ],
            "type": "DENY",
        }
    ],
    # B — 현재 정의 + 명시적 제외
    "B": [
        {
            "name": "investment-advice",
            "definition": (
                "특정 종목의 매수·매도 권유. 단, 투자 용어·일반 개념 설명은 포함하지 않는다."
            ),
            "examples": ["이 종목을 매수하세요", "지금 파세요"],
            "type": "DENY",
        }
    ],
    # C — 분리: 매매 권유 / 종목 선정·비중 지시
    "C": [
        {
            "name": "buy-sell-advice",
            "definition": (
                "특정 종목·자산의 매수·매도·보유를 지시하거나 권유하는 내용. "
                "금융 용어·지표의 정의와 계산법 설명은 해당하지 않음."
            ),
            "examples": ["카카오 지금 사세요", "000660은 매도하세요", "이 종목은 계속 들고 가세요"],
            "type": "DENY",
        },
        {
            "name": "portfolio-advice",
            "definition": (
                "사용자 대신 살 종목을 골라 주거나 포트폴리오 비중 조정·종목 교체를 지시하는 내용. "
                "분산투자 같은 일반 개념 설명은 해당하지 않음."
            ),
            "examples": [
                "배당주로는 이 종목이 좋습니다",
                "지금은 비중을 늘릴 때입니다",
                "그 종목 빼고 이 종목을 담으세요",
            ],
            "type": "DENY",
        },
    ],
}


def candidate_topic_policy(candidate: str) -> dict[str, Any]:
    """후보 topic + 기존 future-price-guarantee로 topicPolicyConfig를 만든다.

    BASELINE은 현재 실 Guardrail 정의(create_guardrail.TOPIC_POLICY) 그대로다.
    """
    key = candidate.upper()
    if key == "BASELINE":
        return copy.deepcopy(TOPIC_POLICY)
    if key not in CANDIDATE_TOPICS:
        raise ValueError(f"unknown topic candidate: {candidate}")
    topics = copy.deepcopy(CANDIDATE_TOPICS[key]) + [copy.deepcopy(_FUTURE_PRICE)]
    return {"topicsConfig": topics}


STANDARD_PROFILE = GUARDRAIL_PROFILE_ID  # 서울 source region용 (KI-023)


def apply_tier(kwargs: dict[str, Any], tier: str) -> dict[str, Any]:
    """topic·content tier와 cross-Region profile을 지정 tier에 맞춘다.

    실 설정(create_guardrail)은 KI-023 이후 Standard이므로 CLASSIC은 tier·profile을 걷어낸다.
    contextual grounding은 서울에서 Standard 미지원이라 건드리지 않는다(Classic 유지).
    """
    if tier not in ("CLASSIC", "STANDARD"):
        raise ValueError(f"unknown tier: {tier}")
    out = copy.deepcopy(kwargs)
    if tier == "CLASSIC":
        out["topicPolicyConfig"].pop("tierConfig", None)
        out["contentPolicyConfig"].pop("tierConfig", None)
        out.pop("crossRegionConfig", None)
        return out
    out["topicPolicyConfig"]["tierConfig"] = {"tierName": "STANDARD"}
    out["contentPolicyConfig"]["tierConfig"] = {"tierName": "STANDARD"}
    out["crossRegionConfig"] = {"guardrailProfileIdentifier": STANDARD_PROFILE}
    return out
