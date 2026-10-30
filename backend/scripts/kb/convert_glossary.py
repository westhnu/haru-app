"""용어 사전 JSON → KB용 JSONL 변환 (T-402, 로컬 전용·AWS 호출 0).

jutopia_data/data/glossary.json(dict: 용어→속성)을 라인당 한 용어인 JSONL로 변환한다.
- id = glossary_{idx:03d} (1부터)
- 빈 값/None 필드는 key 자체를 생략 (확정 B)
- source 없으면 폴백 (확정 D)
- 라인 수 == 입력 항목 수 (하드코딩 금지, 확정 A)
jutopia_data는 읽기 전용 — 원본을 수정하지 않는다 (원칙 4).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import structlog

from app.config import BACKEND_DIR

logger = structlog.get_logger(__name__)

DEFAULT_INPUT = Path("/Users/westhnu/Agent/Claude/jutopia_data/data/glossary.json")
DEFAULT_OUTPUT = BACKEND_DIR / "data" / "kb" / "glossary.jsonl"
SOURCE_FALLBACK = "Haru glossary v1 (jutopia_data)"
# term을 제외한 보존 대상 속성 (값이 있으면 그대로 싣는다).
PRESERVED_FIELDS: tuple[str, ...] = (
    "full_name",
    "english",
    "category",
    "description",
    "formula",
    "example",
    "interpretation",
    "when_to_use",
    "caution",
    "related_terms",
)


def _is_empty(value: Any) -> bool:
    # 0·False는 유효값이므로 빈 문자열·None·빈 컬렉션만 생략한다.
    return value is None or value == "" or value == [] or value == {}


def _to_record(idx: int, term: str, attrs: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {"id": f"glossary_{idx:03d}", "term": term}
    for field in PRESERVED_FIELDS:
        value = attrs.get(field)
        if not _is_empty(value):
            record[field] = value
    record["source"] = attrs.get("source") or SOURCE_FALLBACK
    return record


def convert(input_path: Path, output_path: Path) -> int:
    data: dict[str, Any] = json.loads(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(_to_record(idx, term, attrs), ensure_ascii=False)
        for idx, (term, attrs) in enumerate(data.items(), start=1)
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if len(lines) != len(data):
        raise ValueError(f"라인 수 불일치: {len(lines)} != {len(data)}")
    return len(lines)


def run(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> int:
    count = convert(input_path, output_path)
    logger.info("glossary_converted", count=count, output=str(output_path))
    print(f"변환 완료: {count} 항목 → {output_path}")
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="glossary.json → JSONL 변환 (로컬)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    run(args.input, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
