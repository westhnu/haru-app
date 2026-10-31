"""query_cost.py CSV → 쿼리당 비용 산정.

두 가지를 함께 낸다.
- 추정치: CSV의 길이 정보 × 가정치(토큰 환산·프롬프트 크기). RetrieveAndGenerate 응답에는
  토큰 사용량이 없어서 이 방식만으로는 '실측'이 아니다.
- 실측치(--cloudwatch): 벤치 실행 구간의 CloudWatch AWS/Bedrock 토큰 지표(read-only).
  BEDROCK_MODEL_ID 차원만 집계한다 (KI-021: 차원 중복 합산 방지).
  같은 계정·모델의 다른 호출이 섞이면 그만큼 부풀므로 벤치 중 다른 호출은 피한다.
"""

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import boto3

from app.config import get_settings

# Claude Sonnet 4.5 on Bedrock (USD / 1M tokens). 가격표 변경 시 이 값만 갱신한다.
INPUT_PER_M = 3.0
OUTPUT_PER_M = 15.0
# 가정치 — 실측(CloudWatch) 결과로 보정 대상.
SYSTEM_PROMPT_TOKENS = 500
TOKENS_PER_CHUNK = 500
CHARS_PER_TOKEN = 2.5
# Guardrail은 차단 여부와 무관하게 평가한 모든 호출에 과금된다(입력+출력 평가).
GUARDRAIL_PER_CALL = 0.001
SCENARIOS = {"혼자 테스트 (20회/일)": 20, "활성 100명 × 5회/일": 500}
DAYS_PER_MONTH = 30
METRIC_PERIOD_S = 60
WINDOW_PAD_MIN = 5


def load(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def estimate_row(r: dict[str, Any]) -> float:
    inp = (
        len(r["query"]) / CHARS_PER_TOKEN
        + SYSTEM_PROMPT_TOKENS
        + int(r["citation_count"]) * TOKENS_PER_CHUNK
    )
    out = int(r["answer_len"]) / CHARS_PER_TOKEN
    return inp * INPUT_PER_M / 1e6 + out * OUTPUT_PER_M / 1e6 + GUARDRAIL_PER_CALL


def cloudwatch_tokens(
    start: datetime, end: datetime, region: str, model_id: str, cw: Any | None = None
) -> dict[str, float]:
    """지정 모델 차원만 합산한다 (KI-021).

    CloudWatch는 같은 토큰을 '차원 없는 계정 전체 합'과 '모델별'로 이중 보고한다.
    list_metrics의 모든 차원을 더하면 2배가 되므로 ModelId 차원 하나만 조회한다.
    """
    cw = cw or boto3.client("cloudwatch", region_name=region)
    dims = [{"Name": "ModelId", "Value": model_id}]
    totals = {"InputTokenCount": 0.0, "OutputTokenCount": 0.0}
    for metric in totals:
        pts = cw.get_metric_statistics(
            Namespace="AWS/Bedrock",
            MetricName=metric,
            Dimensions=dims,
            StartTime=start,
            EndTime=end,
            Period=METRIC_PERIOD_S,
            Statistics=["Sum"],
        )["Datapoints"]
        totals[metric] = sum(pt["Sum"] for pt in pts)
    return totals


def report(rows: list[dict[str, Any]], per_query: float, label: str) -> None:
    total = per_query * len(rows)
    print(f"\n[{label}] 쿼리당 평균 ${per_query:.5f} / {len(rows)}건 합계 ${total:.4f}")
    for name, per_day in SCENARIOS.items():
        print(f"  월 비용 — {name}: ${per_query * per_day * DAYS_PER_MONTH:,.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path", type=Path)
    ap.add_argument("--cloudwatch", action="store_true", help="실행 구간 CloudWatch 토큰 실측 조회")
    ap.add_argument("--region", default="ap-northeast-2")
    args = ap.parse_args()
    rows = load(args.csv_path)
    ok = [r for r in rows if r["status"] == "ok" and r["is_mock"] != "True"]
    report(ok, sum(estimate_row(r) for r in ok) / max(len(ok), 1), "추정 (가정치 기반)")
    if args.cloudwatch:
        stamps = sorted(datetime.fromisoformat(r["timestamp_utc"]) for r in rows)
        pad = timedelta(minutes=WINDOW_PAD_MIN)
        model_id = get_settings().bedrock_model_id
        tok = cloudwatch_tokens(stamps[0] - pad, stamps[-1] + pad, args.region, model_id)
        model = (
            tok["InputTokenCount"] * INPUT_PER_M / 1e6
            + tok["OutputTokenCount"] * OUTPUT_PER_M / 1e6
        )
        inp, out = tok["InputTokenCount"], tok["OutputTokenCount"]
        print(f"\nCloudWatch 토큰: input {inp:.0f}, output {out:.0f}")
        report(
            ok,
            model / max(len(ok), 1) + GUARDRAIL_PER_CALL,
            "실측 (CloudWatch 토큰 + Guardrail 가정)",
        )


if __name__ == "__main__":
    main()
