"""Bedrock Guardrail 리소스 생성 (T-407, REQ-GR-01).

design.md GUARDRAIL_CONFIG의 6개 정책을 DRAFT 버전으로 등록한다.
--dry-run(기본) 무호출, --apply로만 실제 생성. 동명 Guardrail이 있으면 skip(idempotent).
프로덕션 버전 게시(v1)는 수동.
"""

import sys
from typing import Any

import structlog

from app.config import get_settings
from app.services.bedrock_client import get_bedrock_client
from scripts._cli import parse_dry_run

logger = structlog.get_logger(__name__)

GUARDRAIL_NAME = "haru-investment-guardrail"
BLOCKED_INPUT_MSG = "본 서비스는 종목 추천을 제공하지 않습니다."
BLOCKED_OUTPUT_MSG = "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."

# REQ-GR-01 — 6개 정책 (design.md GUARDRAIL_CONFIG).
TOPIC_POLICY = {
    "topicsConfig": [
        {
            "name": "investment-advice",
            "definition": "특정 종목의 매수·매도 권유",
            "examples": ["이 종목을 매수하세요", "지금 파세요"],
            "type": "DENY",
        },
        {
            "name": "future-price-guarantee",
            "definition": "미래 가격·수익률 보장 또는 예측",
            "examples": ["내일 급등합니다", "수익을 보장합니다"],
            "type": "DENY",
        },
    ]
}
WORD_POLICY = {"wordsConfig": [{"text": w} for w in ("리딩방", "한 방", "무조건 수익", "보장")]}
SENSITIVE_POLICY = {"piiEntitiesConfig": [{"type": "KR_RRN", "action": "ANONYMIZE"}]}
CONTENT_POLICY = {
    "filtersConfig": [
        {"type": t, "inputStrength": "HIGH", "outputStrength": "HIGH"}
        for t in ("HATE", "SEXUAL", "VIOLENCE")
    ]
}
GROUNDING_POLICY = {"filtersConfig": [{"type": "GROUNDING", "threshold": 0.75, "action": "BLOCK"}]}


def _build_kwargs() -> dict[str, Any]:
    return {
        "name": GUARDRAIL_NAME,
        "topicPolicyConfig": TOPIC_POLICY,
        "wordPolicyConfig": WORD_POLICY,
        "sensitiveInformationPolicyConfig": SENSITIVE_POLICY,
        "contentPolicyConfig": CONTENT_POLICY,
        "contextualGroundingPolicyConfig": GROUNDING_POLICY,
        "blockedInputMessaging": BLOCKED_INPUT_MSG,
        "blockedOutputsMessaging": BLOCKED_OUTPUT_MSG,
    }


def _existing_id(bedrock: Any) -> str | None:
    resp = bedrock.list_guardrails()
    for g in resp.get("guardrails", []):
        if g.get("name") == GUARDRAIL_NAME:
            return str(g["id"])
    return None


def run(dry_run: bool = True, bedrock: Any | None = None) -> bool:
    if dry_run:
        logger.info(
            "create_step",
            resource_type="guardrail",
            resource_id=GUARDRAIL_NAME,
            dry_run=True,
            result="would_create",
        )
        print(f"[dry-run] 생성 예정 Guardrail: {GUARDRAIL_NAME} (정책 6종, DRAFT)")
        print("  DeniedTopic x2, WordFilter x4, PII(KR_RRN), Content(H/S/V HIGH), Grounding 0.75")
        print("→ 생성 후 .env에 추가: BEDROCK_GUARDRAIL_ID=<id>, BEDROCK_GUARDRAIL_VERSION=DRAFT")
        return True
    bedrock = bedrock or get_bedrock_client()
    existing = _existing_id(bedrock)
    if existing:
        logger.info(
            "create_step",
            resource_type="guardrail",
            resource_id=existing,
            dry_run=False,
            result="already_exists",
        )
        guardrail_id = existing
    else:
        resp = bedrock.create_guardrail(**_build_kwargs())
        guardrail_id = str(resp["guardrailId"])
        logger.info(
            "create_step",
            resource_type="guardrail",
            resource_id=guardrail_id,
            dry_run=False,
            result="created",
        )
    print(f"Guardrail: {guardrail_id}")
    print(f"→ .env에 추가: BEDROCK_GUARDRAIL_ID={guardrail_id}, BEDROCK_GUARDRAIL_VERSION=DRAFT")
    return True


def main(argv: list[str] | None = None) -> int:
    dry_run = parse_dry_run("Guardrail 생성", argv)
    _ = get_settings()
    return 0 if run(dry_run=dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
