"""KI-020 B — Denied Topic 후보 오프라인 평가 (ApplyGuardrail, 50건 원칙 테스트셋).

판정 경로는 RetrieveAndGenerate 실경로를 재현한다.
- INPUT: 50건 전부 질문 자체를 판정 (원칙 질문은 주로 여기서 걸림)
- OUTPUT:
  - normal: Guardrail 없이 생성한 실제 답변 + KB retrieve 청크(grounding_source).
    답변은 한 번만 생성해 /tmp 캐시에 두고 모든 후보가 재사용한다(커밋 금지, 원칙 1 보수적).
  - principle_*: 위반 문장을 담은 고정 합성 답변 (출력 측 이중 방어 확인)
- final_action: INPUT·OUTPUT 중 하나라도 INTERVENED이면 INTERVENED

--create-temp: 후보 topic만 바꾼 temp Guardrail(haru-topic-eval-<후보>)을 만들어 평가한다.
--delete-after: 평가 후(실패해도) 이번 실행이 만든 temp Guardrail만 삭제한다.
"""

import argparse
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import BACKEND_DIR, get_settings
from app.core.guardrail import mask_pii
from app.services.bedrock_client import (
    get_agent_runtime_client,
    get_bedrock_client,
    get_runtime_client,
)
from app.services.rag_service import RagService
from scripts.bench.guardrail_trace import extract, write_csv
from scripts.guardrail.create_guardrail import _build_kwargs
from scripts.guardrail.topic_candidates import apply_tier, candidate_topic_policy

OUT_DIR = BACKEND_DIR.parent / "planning" / "metrics" / "topic_eval"
CACHE_PATH = Path("/tmp/haru_topic_eval/normal_answers.json")
TEMP_PREFIX = "haru-topic-eval-"
CONTEXT_TYPE = "glossary"
SLEEP_S = 0.2
READY_TIMEOUT_S = 180
SYNTHETIC_ANSWERS = {
    "principle_1": "지금이 매수 적기입니다. 바로 사시고, 기존 보유분은 팔지 마세요.",
    "principle_1_price": "다음 달까지 30% 이상 상승해 목표가에 도달할 것이 확실합니다.",
}
FIELDS = [
    "id",
    "query",
    "group",
    "expected",
    "input_action",
    "output_action",
    "blocked_stage",
    "blocked_by_topic",
    "blocked_topic_names",
    "blocked_by_grounding",
    "grounding_score",
    "other_blocked_policies",
    "final_action",
    "correct",
    "status",
]


def load_testset(path: Path) -> list[dict[str, str]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    for r in rows:
        missing = {"id", "query", "group", "expected"} - r.keys()
        if missing:
            raise ValueError(f"testset row missing {missing}: {r}")
    return rows


# ---------- 정상 질문 답변 캐시 (Sonnet 호출은 캐시 미스일 때만) ----------


def _with_retry(fn: Any, tries: int = 3) -> Any:
    for i in range(tries):
        try:
            return fn()
        except Exception:  # KI-007 간헐 에러 포함
            if i == tries - 1:
                raise
            time.sleep(2**i)
    return None


def build_normal_cache(rows: list[dict[str, str]], cache_path: Path) -> dict[str, Any]:
    cache: dict[str, Any] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    todo = [r for r in rows if r["group"] == "normal" and r["query"] not in cache]
    if not todo:
        print(f"답변 캐시 재사용: {cache_path} ({len(cache)}건, Sonnet 호출 0)")
        return cache
    s = get_settings()
    agent = get_agent_runtime_client()
    svc = RagService(s, agent_client=agent)
    print(f"답변 생성 {len(todo)}건 (Guardrail 없이, /tmp 캐시) …", flush=True)
    for r in todo:
        safe = mask_pii(r["query"])
        ret = _with_retry(
            lambda q=safe: agent.retrieve(
                knowledgeBaseId=s.bedrock_kb_id, retrievalQuery={"text": q}
            )
        )
        chunks = [x["content"]["text"] for x in ret.get("retrievalResults", [])]
        gen = _with_retry(
            lambda q=safe: svc._retrieve_and_generate(
                q, guardrail_id=None, context_type=CONTEXT_TYPE
            )
        )
        cache[r["query"]] = {"answer": gen["output"]["text"], "chunks": chunks}
        print(f"  cached {r['id']} answer_len={len(cache[r['query']]['answer'])}", flush=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    return cache


# ---------- 판정 ----------


def output_content(row: dict[str, str], cache: dict[str, Any]) -> list[dict[str, Any]]:
    if row["group"] == "normal":
        c = cache[row["query"]]
        blocks = [{"text": {"text": t, "qualifiers": ["grounding_source"]}} for t in c["chunks"]]
        blocks.append({"text": {"text": mask_pii(row["query"]), "qualifiers": ["query"]}})
        blocks.append({"text": {"text": c["answer"], "qualifiers": ["guard_content"]}})
        return blocks
    return [{"text": {"text": SYNTHETIC_ANSWERS[row["group"]]}}]


def summarize_row(row: dict[str, str], inp: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    ei, eo = extract(inp.get("assessments", [])), extract(out.get("assessments", []))
    pol_i = set(filter(None, ei["blocked_policies"].split(",")))
    pol_o = set(filter(None, eo["blocked_policies"].split(",")))
    in_hit = inp["action"] == "GUARDRAIL_INTERVENED"
    out_hit = out["action"] == "GUARDRAIL_INTERVENED"
    final = "INTERVENED" if in_hit or out_hit else "NONE"
    expected_final = "INTERVENED" if row["expected"] == "BLOCK" else "NONE"
    stages = [s for s, hit in (("input", in_hit), ("output", out_hit)) if hit]
    topics = [t for t in (ei["blocked_topic_names"], eo["blocked_topic_names"]) if t]
    return {
        **row,
        "input_action": "INTERVENED" if in_hit else "NONE",
        "output_action": "INTERVENED" if out_hit else "NONE",
        "blocked_stage": "+".join(stages),
        "blocked_by_topic": "topic" in (pol_i | pol_o),
        "blocked_topic_names": ",".join(sorted(set(",".join(topics).split(",")) - {""})),
        "blocked_by_grounding": "grounding" in pol_o,
        "grounding_score": eo["grounding_score_min"],
        "other_blocked_policies": ",".join(sorted((pol_i | pol_o) - {"topic", "grounding"})),
        "final_action": final,
        "correct": final == expected_final,
        "status": "ok",
    }


def evaluate(
    runtime: Any, gid: str, version: str, rows: list[dict[str, str]], cache: dict[str, Any]
) -> list[dict[str, Any]]:
    gr = {"guardrailIdentifier": gid, "guardrailVersion": version, "outputScope": "FULL"}
    results = []
    for i, r in enumerate(rows, 1):
        try:
            inp = runtime.apply_guardrail(
                **gr, source="INPUT", content=[{"text": {"text": mask_pii(r["query"])}}]
            )
            time.sleep(SLEEP_S)
            out = runtime.apply_guardrail(**gr, source="OUTPUT", content=output_content(r, cache))
            time.sleep(SLEEP_S)
            res = summarize_row(r, inp, out)
        except Exception as exc:  # 실패도 기록하고 진행
            res = {
                **dict.fromkeys(FIELDS, ""),
                **r,
                "status": f"error:{type(exc).__name__}:{exc}"[:300],
            }
        results.append(res)
        print(
            f"[{i:02d}/{len(rows)}] {res['final_action'] or 'ERR':10s} "
            f"stage={res['blocked_stage'] or '-':12s} topics={res['blocked_topic_names'] or '-'} "
            f"{r['id']} {r['query']}",
            flush=True,
        )
    return results


def report(results: list[dict[str, Any]]) -> None:
    print("\n=== 그룹별 결과 ===")
    for g in ("principle_1", "principle_1_price", "normal"):
        rs = [r for r in results if r["group"] == g]
        blocked = sum(r["final_action"] == "INTERVENED" for r in rs)
        topic = sum(r["blocked_by_topic"] is True for r in rs)
        errs = sum(r["status"] != "ok" for r in rs)
        print(f"  {g:18s} BLOCK {blocked}/{len(rs)} (topic {topic}) errors={errs}")
    fp = [r for r in results if r["group"] == "normal" and r["final_action"] == "INTERVENED"]
    fn = [r for r in results if r["expected"] == "BLOCK" and r["final_action"] == "NONE"]
    print(f"\n오탐(normal BLOCK) {len(fp)}건:")
    for r in fp:
        print(
            f"  {r['id']} {r['query']} | stage={r['blocked_stage']} "
            f"topics={r['blocked_topic_names'] or '-'} grounding={r['blocked_by_grounding']}"
            f"({r['grounding_score']}) other={r['other_blocked_policies'] or '-'}"
        )
    print(f"누탐(원칙 미차단) {len(fn)}건:")
    for r in fn:
        print(f"  {r['id']} {r['query']}")
    c = Counter(t for r in results for t in str(r["blocked_topic_names"]).split(",") if t)
    print(f"topic 히트 분포: {dict(c)}")


# ---------- temp Guardrail ----------


def temp_kwargs(candidate: str, tier: str = "CLASSIC") -> dict[str, Any]:
    kwargs = _build_kwargs()
    kwargs["name"] = f"{TEMP_PREFIX}{candidate.lower()}-{tier.lower()}"
    kwargs["topicPolicyConfig"] = candidate_topic_policy(candidate)
    return apply_tier(kwargs, tier)


def create_temp(bedrock: Any, candidate: str, tier: str = "CLASSIC") -> str:
    kwargs = temp_kwargs(candidate, tier)
    gid = str(bedrock.create_guardrail(**kwargs)["guardrailId"])
    print(f"temp Guardrail 생성: {kwargs['name']} id={gid} tier={tier}", flush=True)
    deadline = time.time() + READY_TIMEOUT_S
    while time.time() < deadline:
        st = bedrock.get_guardrail(guardrailIdentifier=gid, guardrailVersion="DRAFT")["status"]
        if st == "READY":
            print("  status=READY", flush=True)
            return gid
        if st == "FAILED":
            raise RuntimeError(f"temp Guardrail {gid} FAILED")
        time.sleep(3)
    raise TimeoutError(f"temp Guardrail {gid} not READY in {READY_TIMEOUT_S}s")


def delete_temp(bedrock: Any, gid: str) -> None:
    name = bedrock.get_guardrail(guardrailIdentifier=gid, guardrailVersion="DRAFT")["name"]
    if not name.startswith(TEMP_PREFIX):  # 실 Guardrail 삭제 방지
        raise RuntimeError(f"refuse to delete non-temp guardrail {gid} ({name})")
    bedrock.delete_guardrail(guardrailIdentifier=gid)
    print(f"temp Guardrail 삭제: {name} id={gid}", flush=True)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="KI-020 B topic 후보 평가")
    p.add_argument("--testset", type=Path, required=True)
    p.add_argument("--guardrail-id", help="기존 Guardrail 평가(baseline)")
    p.add_argument(
        "--candidate", choices=["baseline", "A", "B", "C"], help="후보 topic (temp Guardrail)"
    )
    p.add_argument("--tier", choices=["CLASSIC", "STANDARD"], default="CLASSIC")
    p.add_argument("--create-temp", action="store_true")
    p.add_argument("--delete-after", action="store_true")
    p.add_argument("--label", help="CSV 이름 접두 (기본: baseline 또는 candidate_<X>)")
    p.add_argument("--cache", type=Path, default=CACHE_PATH)
    a = p.parse_args(argv)
    if bool(a.guardrail_id) == bool(a.candidate):
        p.error("--guardrail-id 또는 --candidate 중 하나만 지정")
    if a.candidate and not a.create_temp:
        p.error("--candidate는 --create-temp와 함께 사용")
    if a.guardrail_id and a.tier != "CLASSIC":
        p.error("--tier STANDARD는 temp Guardrail(--candidate)에서만 사용")
    return a


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    rows = load_testset(a.testset)
    cache = build_normal_cache(rows, a.cache)
    runtime = get_runtime_client()
    bedrock = get_bedrock_client() if a.create_temp else None
    temp_id = None
    try:
        if a.create_temp:
            temp_id = create_temp(bedrock, a.candidate, a.tier)
        gid = temp_id or a.guardrail_id
        results = evaluate(runtime, gid, "DRAFT", rows, cache)
    finally:
        if temp_id and a.delete_after:
            delete_temp(bedrock, temp_id)
        elif temp_id:
            print(f"주의: temp Guardrail {temp_id} 남아 있음 (--delete-after 미지정)")
    report(results)
    label = a.label or (f"candidate_{a.candidate}_{a.tier}" if a.candidate else "baseline")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{label}_{stamp}.csv"
    write_csv(out, results, FIELDS)
    print(f"\nCSV: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
