"""Guardrail DRAFT 갱신 — 출력 차단 메시지를 면책 문구와 분리 (KI-020 D).

KI-023: tier(Standard)와 crossRegionConfig도 create_guardrail에서 그대로 가져온다.
UpdateGuardrail에서 정책 설정은 선택 항목이라, 빠뜨리면 해당 정책이 사라질 수 있다.
그래서 create_guardrail의 전체 설정(6종 정책 + 메시지)을 그대로 다시 보낸다.
--dry-run(기본) 무호출, --apply로만 실제 갱신. 버전 publish는 수동.
"""

import sys
from typing import Any

import structlog

from app.config import get_settings
from app.services.bedrock_client import get_bedrock_client
from scripts._cli import parse_dry_run
from scripts.guardrail.create_guardrail import _build_kwargs

logger = structlog.get_logger(__name__)
DRAFT = "DRAFT"


def build_update_kwargs(guardrail_id: str) -> dict[str, Any]:
    return {"guardrailIdentifier": guardrail_id, **_build_kwargs()}


def _print_plan(kwargs: dict[str, Any], dry_run: bool) -> None:
    label = "dry-run" if dry_run else "apply"
    print(f"[{label}] 갱신 대상 Guardrail: {kwargs['guardrailIdentifier']} ({DRAFT})")
    print(f"  blockedInputMessaging : {kwargs['blockedInputMessaging']}")
    print(f"  blockedOutputsMessaging: {kwargs['blockedOutputsMessaging']}")
    policies = [k for k in kwargs if k.endswith("PolicyConfig")]
    print(f"  재전송 정책 {len(policies)}종: {', '.join(policies)}")
    regexes = kwargs["sensitiveInformationPolicyConfig"]["regexesConfig"]
    print(f"  regexesConfig: {[r['name'] for r in regexes]} (KI-017 유지)")
    topic_tier = kwargs["topicPolicyConfig"].get("tierConfig", {}).get("tierName", "CLASSIC")
    content_tier = kwargs["contentPolicyConfig"].get("tierConfig", {}).get("tierName", "CLASSIC")
    grounding_tier = (
        kwargs["contextualGroundingPolicyConfig"].get("tierConfig", {}).get("tierName", "CLASSIC")
    )
    profile = kwargs.get("crossRegionConfig", {}).get("guardrailProfileIdentifier", "-")
    print(
        f"  topic tier={topic_tier}, content tier={content_tier}, grounding tier={grounding_tier}"
    )
    print(f"  crossRegion={profile} (KI-023)")
    g = kwargs["contextualGroundingPolicyConfig"]["filtersConfig"]
    print(f"  grounding: {[(f['type'], f['threshold'], f['action']) for f in g]} (T-514)")
    topics = kwargs["topicPolicyConfig"]["topicsConfig"]
    print(f"  topics: {[t['name'] for t in topics]}")


def run(dry_run: bool = True, bedrock: Any | None = None, guardrail_id: str | None = None) -> bool:
    guardrail_id = guardrail_id or get_settings().bedrock_guardrail_id
    if not guardrail_id:
        print("BEDROCK_GUARDRAIL_ID 미설정 — 갱신 대상이 없습니다.")
        return False
    kwargs = build_update_kwargs(guardrail_id)
    _print_plan(kwargs, dry_run)
    if dry_run:
        return True
    bedrock = bedrock or get_bedrock_client()
    resp = bedrock.update_guardrail(**kwargs)
    logger.info(
        "update_step",
        resource_type="guardrail",
        resource_id=guardrail_id,
        version=resp.get("version"),
        result="updated",
    )
    print(f"갱신 완료: {guardrail_id} version={resp.get('version')}")
    return True


def main(argv: list[str] | None = None) -> int:
    return 0 if run(dry_run=parse_dry_run("Guardrail DRAFT 갱신", argv)) else 1


if __name__ == "__main__":
    sys.exit(main())
