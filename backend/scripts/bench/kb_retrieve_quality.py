"""KI-020 A-3 — KB retrieve 품질 측정 (임베딩만, Sonnet 호출 없음).

KB에 있는 용어 6개를 영문 약어·한국어 정식 명칭 두 가지로, 질문 표현 5가지로 검색해
정답 문서(term_NNN)가 몇 위에 오는지 기록한다. --label before/after로 KI-022 수정 전후를 비교한다.
"""

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import BACKEND_DIR, get_settings
from app.services.bedrock_client import get_agent_runtime_client

GLOSSARY = Path("/Users/westhnu/Agent/Claude/jutopia_data/data/glossary.json")
OUT_DIR = BACKEND_DIR.parent / "planning" / "metrics" / "query_bench"
TOP_K = 10  # 정답이 3위 밖일 때도 순위를 잡기 위해 넉넉히 받는다
REPORT_K = 3
HANGUL_START, HANGUL_END, JONG_COUNT = 0xAC00, 0xD7A3, 28
# 영문 약어는 읽는 소리의 받침으로 조사를 고른다 (ROE=오이 → 가 아님, 알파벳 마지막 소리 기준).
ABBR_HAS_BATCHIM = {
    "ROE": False,
    "EPS": False,
    "PER": True,
    "PBR": True,
    "BPS": False,
    "RSI": False,
}
TARGETS = ["ROE", "EPS", "PER", "PBR", "BPS", "RSI"]


def has_batchim(word: str) -> bool:
    if word in ABBR_HAS_BATCHIM:
        return ABBR_HAS_BATCHIM[word]
    last = ord(word[-1])
    return HANGUL_START <= last <= HANGUL_END and (last - HANGUL_START) % JONG_COUNT != 0


def variations(term: str) -> list[tuple[str, str]]:
    b = has_batchim(term)
    return [
        ("단일", term),
        ("의문", f"{term}{'이' if b else '가'} 뭐야?"),
        ("설명", f"{term} 설명해줘"),
        ("란", f"{term}{'이란' if b else '란'}?"),
        ("뜻", f"{term} 뜻"),
    ]


def build_cases() -> list[dict[str, Any]]:
    g = json.loads(GLOSSARY.read_text(encoding="utf-8"))
    index = {k: i for i, k in enumerate(g, 1)}
    cases = []
    for abbr in TARGETS:
        full = g[abbr]["full_name"]
        target_file = f"term_{index[abbr]:03d}.txt"
        for lang, term in (("en", abbr), ("ko", full)):
            for vtype, q in variations(term):
                cases.append(
                    {
                        "target_term": abbr,
                        "target_full_name": full,
                        "target_file": target_file,
                        "query_lang": lang,
                        "variation_type": vtype,
                        "query": q,
                    }
                )
    return cases


def score_row(case: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    files = [r["location"]["s3Location"]["uri"].rsplit("/", 1)[-1] for r in results]
    row = {k: v for k, v in case.items() if k != "target_file"}
    for i in range(REPORT_K):
        row[f"rank_{i + 1}_score"] = round(results[i]["score"], 4) if i < len(results) else ""
        row[f"rank_{i + 1}_source"] = files[i] if i < len(files) else ""
    rank = files.index(case["target_file"]) + 1 if case["target_file"] in files else 0
    row["target_rank"] = rank
    row["target_rank_score"] = round(results[rank - 1]["score"], 4) if rank else ""
    return row


def run(label: str) -> Path:
    s = get_settings()
    agent = get_agent_runtime_client()
    rows = []
    for i, case in enumerate(build_cases(), 1):
        resp = agent.retrieve(
            knowledgeBaseId=s.bedrock_kb_id,
            retrievalQuery={"text": case["query"]},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": TOP_K}},
        )
        row = score_row(case, resp.get("retrievalResults", []))
        rows.append(row)
        print(
            f"[{i:2d}] {row['query_lang']} {row['variation_type']:2s} rank={row['target_rank']} "
            f"score={row['target_rank_score']} top1={row['rank_1_source']} {case['query']}",
            flush=True,
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"kb_quality_{label}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nCSV: {path}")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, choices=["before", "after"])
    run(ap.parse_args().label)


if __name__ == "__main__":
    main()
