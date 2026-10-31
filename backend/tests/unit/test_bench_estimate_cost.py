"""KI-021 회귀 방지: CloudWatch 토큰 지표를 차원 중복 없이 집계한다."""

from datetime import UTC, datetime
from typing import Any

from scripts.bench.estimate_cost import cloudwatch_tokens

MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
MODEL_DIMS = [{"Name": "ModelId", "Value": MODEL_ID}]
# 실측과 같은 구조: 계정 전체 합(차원 없음)과 모델별 값이 같은 토큰을 이중 보고한다.
SERIES = {
    ("InputTokenCount", ()): 80388.0,
    ("InputTokenCount", (MODEL_ID,)): 79187.0,
    ("OutputTokenCount", ()): 14153.0,
    ("OutputTokenCount", (MODEL_ID,)): 14153.0,
}


class FakeCloudWatch:
    def __init__(self) -> None:
        self.requested: list[list[dict[str, str]]] = []

    def list_metrics(self, **kwargs: Any) -> dict[str, Any]:
        return {"Metrics": [{"Dimensions": []}, {"Dimensions": MODEL_DIMS}]}

    def get_metric_statistics(self, **kwargs: Any) -> dict[str, Any]:
        dims = kwargs["Dimensions"]
        self.requested.append(dims)
        key = (kwargs["MetricName"], tuple(d["Value"] for d in dims))
        return {"Datapoints": [{"Sum": SERIES[key]}]}


def _run(cw: FakeCloudWatch) -> dict[str, float]:
    t = datetime(2026, 10, 31, tzinfo=UTC)
    return cloudwatch_tokens(t, t, "ap-northeast-2", MODEL_ID, cw=cw)


def test_cloudwatch_tokens_counts_model_dimension_only_ki021() -> None:
    totals = _run(FakeCloudWatch())
    assert totals == {"InputTokenCount": 79187.0, "OutputTokenCount": 14153.0}


def test_cloudwatch_tokens_never_requests_dimensionless_total_ki021() -> None:
    cw = FakeCloudWatch()
    _run(cw)
    assert cw.requested and all(dims == MODEL_DIMS for dims in cw.requested)
