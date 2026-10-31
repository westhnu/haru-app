"""KI-020 분석 — ApplyGuardrail로 RetrieveAndGenerate의 Guardrail 판정을 재현한다.

RetrieveAndGenerate는 guardrailAction만 돌려주고 정책별 trace를 주지 않는다(서비스 모델 확인).
그래서 쿼리마다 (1) KB retrieve (2) Guardrail 없이 RetrieveAndGenerate (3) ApplyGuardrail INPUT
(4) ApplyGuardrail OUTPUT(근거=KB 청크) 순으로 호출해 어떤 정책이 막는지 확인한다.

Guardrail 없는 원 답변은 민감할 수 있어 /tmp에만 저장한다. 커밋 대상 CSV에는
BLOCK 정책·점수·길이만 남기고 답변 텍스트는 넣지 않는다.
"""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3

from app.config import BACKEND_DIR, get_settings
from app.core.guardrail import mask_pii
from app.services.bedrock_client import get_agent_runtime_client
from app.services.rag_service import RagService

QUERIES = ["ROE 설명해줘", "우선주가 뭐야?", "WACC란?", "DCF 모델이 뭐야?", "주당순이익 설명해줘"]
CONTEXT_TYPE = "glossary"
SUMMARY_DIR = BACKEND_DIR.parent / "planning" / "metrics" / "query_bench"
PREVIEW_CHARS = 80
SUMMARY_FIELDS = [
    "query",
    "guardrail_action",
    "blocked_policies",
    "grounding_score_min",
    "grounding_filter_type",
    "blocked_topic_names",
    "answer_len",
    "status",
]


def _blocked(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [i for i in items if i.get("action") == "BLOCKED"]


def extract(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    """assessments에서 BLOCK된 정책과 grounding 점수를 뽑는다."""
    policies, topics, scores, gtypes = set(), [], [], set()
    for a in assessments:
        if t := _blocked(a.get("topicPolicy", {}).get("topics", [])):
            policies.add("topic")
            topics += [x["name"] for x in t]
        if _blocked(a.get("contentPolicy", {}).get("filters", [])):
            policies.add("content")
        wp = a.get("wordPolicy", {})
        if _blocked(wp.get("customWords", []) + wp.get("managedWordLists", [])):
            policies.add("word")
        sp = a.get("sensitiveInformationPolicy", {})
        if _blocked(sp.get("piiEntities", []) + sp.get("regexes", [])):
            policies.add("pii")
        for f in a.get("contextualGroundingPolicy", {}).get("filters", []):
            scores.append(f["score"])
            gtypes.add(f["type"])
            if f.get("action") == "BLOCKED":
                policies.add("grounding")
    return {
        "blocked_policies": ",".join(sorted(policies)),
        "blocked_topic_names": ",".join(topics),
        "grounding_score_min": min(scores) if scores else "",
        "grounding_filter_type": ",".join(sorted(gtypes)),
    }


def _grounding_content(chunks: list[str], query: str, answer: str) -> list[dict[str, Any]]:
    blocks = [{"text": {"text": c, "qualifiers": ["grounding_source"]}} for c in chunks]
    blocks.append({"text": {"text": query, "qualifiers": ["query"]}})
    blocks.append({"text": {"text": answer, "qualifiers": ["guard_content"]}})
    return blocks


def trace_one(ctx: dict[str, Any], query: str, raw_dir: Path, idx: int) -> dict[str, Any]:
    s, agent, rt, svc = ctx["settings"], ctx["agent"], ctx["runtime"], ctx["svc"]
    safe = mask_pii(query)
    gr = {
        "guardrailIdentifier": s.bedrock_guardrail_id,
        "guardrailVersion": s.bedrock_guardrail_version,
    }
    steps: dict[str, Any] = {}
    steps["1_retrieve"] = agent.retrieve(
        knowledgeBaseId=s.bedrock_kb_id, retrievalQuery={"text": safe}
    )
    chunks = [r["content"]["text"] for r in steps["1_retrieve"].get("retrievalResults", [])]
    steps["2_rag_no_guardrail"] = svc._retrieve_and_generate(
        safe, guardrail_id=None, context_type=CONTEXT_TYPE
    )
    answer = steps["2_rag_no_guardrail"]["output"]["text"]
    steps["3_apply_input"] = rt.apply_guardrail(
        **gr, source="INPUT", outputScope="FULL", content=[{"text": {"text": safe}}]
    )
    steps["4_apply_output"] = rt.apply_guardrail(
        **gr, source="OUTPUT", outputScope="FULL", content=_grounding_content(chunks, safe, answer)
    )
    (raw_dir / f"q{idx}.json").write_text(
        json.dumps(steps, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    intervened = any(
        steps[k]["action"] == "GUARDRAIL_INTERVENED" for k in ("3_apply_input", "4_apply_output")
    )
    assessments = steps["3_apply_input"]["assessments"] + steps["4_apply_output"]["assessments"]
    row = {
        "query": query,
        "guardrail_action": "INTERVENED" if intervened else "NONE",
        "answer_len": len(answer),
        "status": "ok",
        **extract(assessments),
    }
    return {"row": row, "preview": answer[:PREVIEW_CHARS], "chunks": len(chunks)}


def _error_row(query: str, exc: Exception) -> dict[str, Any]:
    row = dict.fromkeys(SUMMARY_FIELDS, "")
    row.update(query=query, status=f"error:{type(exc).__name__}", answer_len=0)
    return row


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    s = get_settings()
    agent = get_agent_runtime_client()
    ctx = {
        "settings": s,
        "agent": agent,
        "svc": RagService(s, agent_client=agent),
        "runtime": boto3.client("bedrock-runtime", region_name=s.aws_region),
    }
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = Path(f"/tmp/kb_trace_{stamp}/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows, private = [], []
    for i, q in enumerate(QUERIES, 1):
        try:
            res = trace_one(ctx, q, raw_dir, i)
            rows.append(res["row"])
            private.append(
                {**res["row"], "kb_chunks": res["chunks"], "answer_first_80chars": res["preview"]}
            )
        except Exception as exc:  # 실패도 기록하고 다음 쿼리로 진행한다
            rows.append(_error_row(q, exc))
            private.append({**rows[-1], "error_detail": str(exc)[:300]})
        r = rows[-1]
        print(
            f"[{i}/{len(QUERIES)}] {r['status']:8s} {r['guardrail_action']:10s} "
            f"blocked={r['blocked_policies'] or '-'} grounding_min={r['grounding_score_min']} {q}",
            flush=True,
        )
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    summary = SUMMARY_DIR / f"trace_summary_{stamp}.csv"
    write_csv(summary, rows, SUMMARY_FIELDS)
    write_csv(
        raw_dir.parent / "private_summary.csv",
        private,
        SUMMARY_FIELDS + ["kb_chunks", "answer_first_80chars", "error_detail"],
    )
    print(f"\n커밋용 요약: {summary}\n/tmp 원본: {raw_dir.parent}")


if __name__ == "__main__":
    main()
