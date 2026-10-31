"""convert/upload 스크립트 KI-015 재설계 검증 (T-402/T-403).

용어별 .txt 생성 + 302개 개별 S3 업로드 + per-file md5 멱등.
실제 AWS 호출 없음 (Spy S3).
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError

from scripts.kb import convert_glossary as cv
from scripts.kb import upload_glossary as up

JUTOPIA_GLOSSARY = Path("/Users/westhnu/Agent/Claude/jutopia_data/data/glossary.json")

SAMPLE = {
    "PER": {
        "english": "Price Earnings Ratio",
        "description": "주가수익비율",
        "formula": "",  # 빈 값 — 생략돼야 함
        "related_terms": [],  # 빈 배열 — 생략
        "example": "PER 10배",
    },
    "PBR": {"description": "주가순자산비율"},
    "ROE": {"description": "자기자본이익률", "caution": "업종 비교 필요"},
}


def _not_found(op: str) -> ClientError:
    return ClientError({"Error": {"Code": "404", "Message": "x"}}, op)


# --- convert ---------------------------------------------------------------


def test_convert_glossary_writes_302_txt_files(tmp_path: Path) -> None:
    src = tmp_path / "g.json"
    src.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "terms"

    total, written = cv.convert(src, out_dir)

    assert total == 3
    assert written == 3
    names = sorted(p.name for p in out_dir.glob("term_*.txt"))
    assert names == ["term_001.txt", "term_002.txt", "term_003.txt"]


def test_convert_glossary_format_and_omits_empty(tmp_path: Path) -> None:
    src = tmp_path / "g.json"
    src.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "terms"

    cv.convert(src, out_dir)
    text = (out_dir / "term_001.txt").read_text(encoding="utf-8")

    assert "용어: PER" in text
    assert "정의: 주가수익비율" in text
    assert "예시: PER 10배" in text
    assert "formula" not in text  # 빈 필드 라벨 자체가 없음
    assert "주의:" not in text  # PER엔 caution 없음


def test_convert_idempotent_second_run_writes_nothing(tmp_path: Path) -> None:
    src = tmp_path / "g.json"
    src.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "terms"

    cv.convert(src, out_dir)
    _, written_again = cv.convert(src, out_dir)

    assert written_again == 0  # 내용 동일 → 재기록 없음


KI022_SAMPLE = {
    "EPS": {
        "full_name": "주당순이익",
        "english": "Earnings Per Share",
        "description": "순이익을 발행 주식수로 나눈 값",
        "formula": "EPS = 순이익 / 발행주식수",
        "related_terms": ["PER", "ROE"],
    },
    "PBR": {"full_name": "주가순자산비율", "description": "주가 / BPS", "formula": None},
    "RSI": {"description": "과매수·과매도 지표", "related_terms": []},
}


def _convert_ki022(tmp_path: Path) -> Path:
    src = tmp_path / "g.json"
    src.write_text(json.dumps(KI022_SAMPLE, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "terms"
    cv.convert(src, out_dir)
    return out_dir


def test_convert_includes_full_name_formula_related_terms_ki022(tmp_path: Path) -> None:
    lines = (_convert_ki022(tmp_path) / "term_001.txt").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "용어: EPS"
    assert lines[1] == "정식 명칭: 주당순이익"  # 용어 바로 다음 (검색 신호)
    assert "공식: EPS = 순이익 / 발행주식수" in lines
    assert "관련 용어: PER, ROE" in lines
    assert lines[-1] == "관련 용어: PER, ROE"


def test_convert_handles_missing_optional_fields_ki022(tmp_path: Path) -> None:
    out_dir = _convert_ki022(tmp_path)
    pbr = (out_dir / "term_002.txt").read_text(encoding="utf-8")
    rsi = (out_dir / "term_003.txt").read_text(encoding="utf-8")
    assert "정식 명칭: 주가순자산비율" in pbr
    assert "공식:" not in pbr  # None → 라인 생략
    assert "정식 명칭:" not in rsi  # 키 없음 → 생략
    assert "관련 용어:" not in rsi  # 빈 리스트 → 생략


def test_convert_glossary_full_count() -> None:
    # 실제 jutopia glossary.json으로 파일 수만 검증.
    if not JUTOPIA_GLOSSARY.exists():
        return  # 환경에 원본 없으면 skip (CI 격리)
    data = json.loads(JUTOPIA_GLOSSARY.read_text(encoding="utf-8"))
    count, _ = cv._preview(JUTOPIA_GLOSSARY)
    assert count == len(data)


# --- upload ----------------------------------------------------------------


class SpyS3:
    def __init__(self, calls: list[str], etags: dict[str, str] | None = None) -> None:
        self._calls = calls
        self._etags = etags or {}

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append(f"head:{kwargs['Key']}")
        key = kwargs["Key"]
        if key not in self._etags:
            raise _not_found("HeadObject")
        return {"ETag": f'"{self._etags[key]}"'}

    def put_object(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append(f"put:{kwargs['Key']}")
        return {}


def _make_terms(dir_: Path, n: int) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        (dir_ / f"term_{i:03d}.txt").write_text(f"용어: T{i}\n", encoding="utf-8")


def test_upload_glossary_dry_run_no_s3_calls(tmp_path: Path, monkeypatch: Any) -> None:
    _make_terms(tmp_path, 3)
    monkeypatch.setattr(up, "LOCAL_DIR", tmp_path)
    calls: list[str] = []

    assert up.run(dry_run=True, s3=SpyS3(calls), bucket="b") is True
    assert calls == []


def test_upload_glossary_apply_uploads_all(tmp_path: Path, monkeypatch: Any) -> None:
    _make_terms(tmp_path, 5)
    monkeypatch.setattr(up, "LOCAL_DIR", tmp_path)
    calls: list[str] = []

    up.run(dry_run=False, s3=SpyS3(calls), bucket="b")

    puts = [c for c in calls if c.startswith("put:")]
    assert len(puts) == 5  # 전부 신규 → 5회 업로드


def test_upload_glossary_apply_skips_unchanged_ki015(tmp_path: Path, monkeypatch: Any) -> None:
    _make_terms(tmp_path, 4)
    monkeypatch.setattr(up, "LOCAL_DIR", tmp_path)
    # 원격 ETag를 로컬 md5와 동일하게 세팅 → 전부 skip.
    etags = {
        f"glossary/term_{i:03d}.txt": hashlib.md5(
            (tmp_path / f"term_{i:03d}.txt").read_bytes()
        ).hexdigest()
        for i in range(1, 5)
    }
    calls: list[str] = []

    up.run(dry_run=False, s3=SpyS3(calls, etags=etags), bucket="b")

    puts = [c for c in calls if c.startswith("put:")]
    assert puts == []  # md5 동일 → put 0회 (멱등)


def test_upload_glossary_missing_local_fails(tmp_path: Path, monkeypatch: Any) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(up, "LOCAL_DIR", empty)

    assert up.run(dry_run=False, s3=SpyS3([]), bucket="b") is False
