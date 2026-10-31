"""용어 사전 JSON → 용어별 평문 .txt 변환 (T-402, KI-015 재설계, 로컬 전용·AWS 0).

Bedrock KB 문서 경계 = S3 객체 1개 = 문서 1개. 따라서 용어 하나당 파일 하나로 쪼갠다.
jutopia_data/data/glossary.json(dict: 용어→속성)을 term_001.txt ~ term_NNN.txt로 변환한다.
- 파일명: term_{idx:03d}.txt (1-based)
- 포맷: 비어있지 않은 필드만 고정 순서로 라벨링
- 멱등: 기존 파일과 내용이 같으면 다시 쓰지 않음
jutopia_data는 읽기 전용 (원칙 4).
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
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "data" / "kb" / "terms"
LEGACY_JSONL = BACKEND_DIR / "data" / "kb" / "glossary.jsonl"

# (jutopia 필드, 출력 라벨) — 이 순서로, 값이 있을 때만 싣는다.
# KI-022: full_name·formula·related_terms를 빠뜨리면 한국어 정식 명칭(예: "주당순이익")으로
# 검색했을 때 해당 문서(EPS)를 찾지 못한다. KI-015 B 결정(모든 필드 보존)대로 전부 싣는다.
FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("full_name", "정식 명칭"),
    ("english", "영문"),
    ("description", "정의"),
    ("formula", "공식"),
    ("example", "예시"),
    ("interpretation", "해석"),
    ("when_to_use", "사용 시점"),
    ("caution", "주의"),
    ("related_terms", "관련 용어"),
)


def _flatten(value: Any) -> str:
    # interpretation은 dict(저/고/표준)일 수 있어 한 줄 문자열로 평탄화한다.
    if isinstance(value, dict):
        return " / ".join(f"{k}: {v}" for k, v in value.items() if v)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value)


def _render(term: str, attrs: dict[str, Any]) -> str:
    lines = [f"용어: {term}"]
    for field, label in FIELD_LABELS:
        value = attrs.get(field)
        if value is None or value == "" or value == [] or value == {}:
            continue
        lines.append(f"{label}: {_flatten(value)}")
    return "\n".join(lines) + "\n"


def _write_if_changed(path: Path, content: str) -> bool:
    # 멱등: 내용 동일하면 쓰지 않는다. 변경(또는 신규)이면 True.
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def convert(input_path: Path, output_dir: Path) -> tuple[int, int]:
    data: dict[str, Any] = json.loads(input_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for idx, (term, attrs) in enumerate(data.items(), start=1):
        path = output_dir / f"term_{idx:03d}.txt"
        if _write_if_changed(path, _render(term, attrs)):
            written += 1
    if LEGACY_JSONL.exists():
        logger.warning("legacy_jsonl_present", path=str(LEGACY_JSONL))
    return len(data), written


def _preview(input_path: Path) -> tuple[int, str]:
    data: dict[str, Any] = json.loads(input_path.read_text(encoding="utf-8"))
    first_term, first_attrs = next(iter(data.items()))
    return len(data), _render(first_term, first_attrs)


def run(dry_run: bool, input_path: Path, output_dir: Path) -> int:
    if dry_run:
        count, sample = _preview(input_path)
        print(f"[dry-run] {count} files would be written → {output_dir}/term_NNN.txt")
        print("--- 샘플 term_001.txt ---")
        print(sample, end="")
        return count
    total, written = convert(input_path, output_dir)
    logger.info("glossary_converted", total=total, written=written, output=str(output_dir))
    print(f"wrote {written} files (total {total}) → {output_dir}")
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="glossary.json → 용어별 .txt (로컬)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="미리보기만 (기본)")
    group.add_argument("--apply", action="store_true", help="실제 파일 생성")
    args = parser.parse_args(argv)
    run(not args.apply, args.input, args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
