"""T-514 — 2차 벤치에서 차단된 정상 질문의 grounding score를 ApplyGuardrail로 재획득한다.

쿼리마다 실경로를 재현한다.
1. KB retrieve (RagService와 같은 기본 top-5) → grounding_source
2. Guardrail 없이 RetrieveAndGenerate로 답변 생성 (실서비스와 같은 프롬프트)
   - 원 답변은 민감할 수 있어 /tmp 캐시에만 둔다(커밋 금지, 원칙 1 보수적)
   - topic_eval 캐시(/tmp/haru_topic_eval)에 같은 질문이 있으면 재사용
3. ApplyGuardrail INPUT(질문) + OUTPUT(근거·질문·답변), 실 Guardrail(현재 Standard + grounding 0.75)

grounding score는 threshold와 무관하게 반환되므로, 후보 threshold별 차단 여부는
같은 점수로 오프라인 계산한다(blocked_at_<t> 열). 커밋용 CSV에는 답변 텍스트를 넣지 않는다.
"""

import argparse
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import BACKEND_DIR, get_settings
from app.core.guardrail import mask_pii
from app.services.bedrock_client import get_agent_runtime_client, get_runtime_client
from app.services.rag_service import RagService
from scripts.bench.guardrail_trace import extract, write_csv
from scripts.bench.topic_eval import CACHE_PATH as TOPIC_EVAL_CACHE
from scripts.bench.topic_eval import _with_retry

T514_DIR = BACKEND_DIR.parent / "planning" / "metrics" / "t514"
QUERIES_PATH = T514_DIR / "blocked_normal_queries.json"
CACHE_PATH = Path("/tmp/haru_t514/answers.json")
CONTEXT_TYPE = "glossary"
THRESHOLDS = (0.75, 0.60, 0.50, 0.30)
SLEEP_S = 0.3
FIELDS = [
    "idx",
    "query",
    "group",
    "stage_guess",
    "retrieve_top1_score",
    "retrieve_top1_file",
    "chunk_count",
    "generated_answer_len",
    "answer_cached",
    "input_action",
    "output_action",
    "blocked_policies",
    "blocked_topic_names",
    "grounding_type",
    "grounding_score",
    "grounding_action",
    *[f"blocked_at_{t:.2f}" for t in THRESHOLDS],
    "status",
]


def _grounding(assessments: list[dict[str, Any]]) -> dict[str, Any] | None:
    for a in assessments:
        for f in a.get("contextualGroundingPolicy", {}).get("filters", []):
            if f.get("type") == "GROUNDING":
                return f
    return None


def blocked_at(
    threshold: float, score: float | None, input_hit: bool, other_policies: set[str]
) -> bool:
    """threshold만 바꿨을 때의 최종 차단 여부. grounding 외 정책 차단은 그대로 유지된다."""
    if input_hit or other_policies:
        return True
    return score is not None and score < threshold


def summarize_row(
    q: dict[str, Any],
    ret: dict[str, Any],
    answer: dict[str, Any],
    inp: dict[str, Any],
    out: dict[str, Any],
) -> dict[str, Any]:
    results = ret.get("retrievalResults", [])
    top = results[0] if results else {}
    ex = extract(inp.get("assessments", []) + out.get("assessments", []))
    policies = set(filter(None, ex["blocked_policies"].split(",")))
    g = _grounding(out.get("assessments", []))
    score = g["score"] if g else None
    input_hit = inp["action"] == "GUARDRAIL_INTERVENED"
    row = {
        **q,
        "retrieve_top1_score": round(top.get("score", 0.0), 4) if top else "",
        "retrieve_top1_file": (
            top.get("location", {}).get("s3Location", {}).get("uri", "").rsplit("/", 1)[-1]
        ),
        "chunk_count": len(results),
        "generated_answer_len": len(answer["answer"]),
        "answer_cached": answer.get("cached", False),
        "input_action": "INTERVENED" if input_hit else "NONE",
        "output_action": "INTERVENED" if out["action"] == "GUARDRAIL_INTERVENED" else "NONE",
        "blocked_policies": ex["blocked_policies"],
        "blocked_topic_names": ex["blocked_topic_names"],
        "grounding_type": g["type"] if g else "",
        "grounding_score": score if score is not None else "",
        "grounding_action": g.get("action", "") if g else "",
        "status": "ok",
    }
    for t in THRESHOLDS:
        row[f"blocked_at_{t:.2f}"] = blocked_at(t, score, input_hit, policies - {"grounding"})
    return row


def _load_cache(path: Path) -> dict[str, Any]:
    cache: dict[str, Any] = {}
    if TOPIC_EVAL_CACHE.exists():
        for q, v in json.loads(TOPIC_EVAL_CACHE.read_text(encoding="utf-8")).items():
            cache[q] = {"answer": v["answer"], "cached": True}
    if path.exists():
        cache.update(json.loads(path.read_text(encoding="utf-8")))
    return cache


def investigate_one(ctx: dict[str, Any], q: dict[str, Any]) -> dict[str, Any]:
    s, agent, rt, svc, cache = (
        ctx["settings"],
        ctx["agent"],
        ctx["runtime"],
        ctx["svc"],
        ctx["cache"],
    )
    safe = mask_pii(q["query"])
    ret = _with_retry(
        lambda: agent.retrieve(knowledgeBaseId=s.bedrock_kb_id, retrievalQuery={"text": safe})
    )
    chunks = [r["content"]["text"] for r in ret.get("retrievalResults", [])]
    if q["query"] not in cache:
        gen = _with_retry(
            lambda: svc._retrieve_and_generate(safe, guardrail_id=None, context_type=CONTEXT_TYPE)
        )
        cache[q["query"]] = {"answer": gen["output"]["text"], "cached": False}
        ctx["save"]()
    answer = cache[q["query"]]
    gr = {
        "guardrailIdentifier": s.bedrock_guardrail_id,
        "guardrailVersion": s.bedrock_guardrail_version,
        "outputScope": "FULL",
    }
    inp = rt.apply_guardrail(**gr, source="INPUT", content=[{"text": {"text": safe}}])
    time.sleep(SLEEP_S)
    blocks = [{"text": {"text": c, "qualifiers": ["grounding_source"]}} for c in chunks]
    blocks.append({"text": {"text": safe, "qualifiers": ["query"]}})
    blocks.append({"text": {"text": answer["answer"], "qualifiers": ["guard_content"]}})
    out = rt.apply_guardrail(**gr, source="OUTPUT", content=blocks)
    time.sleep(SLEEP_S)
    return summarize_row(q, ret, answer, inp, out)


def report(rows: list[dict[str, Any]]) -> None:
    ok = [r for r in rows if r["status"] == "ok"]
    scores = sorted(r["grounding_score"] for r in ok if r["grounding_score"] != "")
    print(f"\n=== grounding score ({len(scores)}/{len(rows)}건) ===")
    if scores:
        print(
            f"  min {scores[0]:.2f} / median {statistics.median(scores):.2f} / max {scores[-1]:.2f}"
        )
        below = sum(x < 0.75 for x in scores)
        print(f"  0.75 미만 {below}/{len(scores)} ({below * 100 // len(scores)}%)")
        for lo, hi in ((0, 0.3), (0.3, 0.5), (0.5, 0.6), (0.6, 0.75), (0.75, 1.01)):
            print(f"  [{lo:.2f}, {hi:.2f}) {sum(lo <= x < hi for x in scores)}건")
    mismatch = [
        r["query"]
        for r in ok
        if r["grounding_score"] != ""
        and (r["grounding_action"] == "BLOCKED") != (r["grounding_score"] < 0.75)
    ]
    print(f"  action·score 불일치(threshold 0.75 기준): {mismatch or '없음'}")
    print("\n=== threshold별 차단 (이 40건 기준, 다른 정책 차단 유지) ===")
    for t in THRESHOLDS:
        n = sum(r[f"blocked_at_{t:.2f}"] is True for r in ok)
        print(f"  {t:.2f}: {n}/{len(ok)}")
    still = [r for r in ok if r["blocked_policies"] and r["blocked_policies"] != "grounding"]
    print(f"\ngrounding 외 정책 차단 {len(still)}건:")
    for r in still:
        print(f"  {r['query']} | {r['blocked_policies']} {r['blocked_topic_names']}")
    print(f"재현 안 됨(현재 판정 NONE) {sum(1 for r in ok if not r['blocked_at_0.75'])}건")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="T-514 grounding score 재획득")
    p.add_argument("--queries", type=Path, default=QUERIES_PATH)
    a = p.parse_args(argv)
    queries = json.loads(a.queries.read_text(encoding="utf-8"))
    s = get_settings()
    agent = get_agent_runtime_client()
    cache = _load_cache(CACHE_PATH)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    def save() -> None:
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    ctx = {
        "settings": s,
        "agent": agent,
        "runtime": get_runtime_client(),
        "svc": RagService(s, agent_client=agent),
        "cache": cache,
        "save": save,
    }
    pending = [q for q in queries if q["query"] not in cache]
    print(f"쿼리 {len(queries)}건, 답변 생성 필요 {len(pending)}건 (나머지 캐시)", flush=True)
    rows = []
    for i, q in enumerate(queries, 1):
        try:
            row = investigate_one(ctx, q)
        except Exception as exc:  # 실패도 기록하고 진행
            row = {
                **dict.fromkeys(FIELDS, ""),
                **q,
                "status": f"error:{type(exc).__name__}:{exc}"[:300],
            }
        rows.append(row)
        print(
            f"[{i:02d}/{len(queries)}] {row['status'][:30]:6s} in={row['input_action'] or '-':10s} "
            f"out={row['output_action'] or '-':10s} g={row['grounding_score']} "
            f"top1={row['retrieve_top1_score']} {row['blocked_policies'] or '-'} {q['query']}",
            flush=True,
        )
    report(rows)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    T514_DIR.mkdir(parents=True, exist_ok=True)
    out = T514_DIR / f"grounding_scores_{stamp}.csv"
    write_csv(out, rows, FIELDS)
    print(f"\nCSV: {out}\n/tmp 답변 캐시: {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
