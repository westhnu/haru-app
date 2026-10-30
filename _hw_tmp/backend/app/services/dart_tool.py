"""DART Open API 조회 도구.

jutopia_data/dart_client.py에서는 보고서 시도 순서(`_determine_report_attempts`)만 빌려 쓴다.
금액 매핑은 `dart_financials`에서 누적 기준으로 새로 구현했다 (KI-008).

HTTP·오류 처리·캐시는 여기서 구현한다. jutopia 구현은 서버에서 그대로 쓰기 부적합하다 (KI-006):
오류를 print 후 삼키고, 예외 속 URL의 crtfc_key가 로그로 새고, 캐시를 jutopia_data 안에 쓰며,
출처 URL에 필요한 rcept_no·회사명을 버린다.
"""

import io
import json
import re
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple, Protocol

import requests
import structlog

from app.config import Settings, get_settings
from app.core.cache import TTLCache
from app.models.stock import STATEMENT_LABELS, DartResult, StockFinancials, StockSource
from app.services.dart_financials import build_financials
from app.services.jutopia_loader import load_jutopia_module

DART_API_BASE = "https://opendart.fss.or.kr/api"
DART_VIEWER_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
DART_HOME_URL = "https://opendart.fss.or.kr/"
REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_CACHE_TTL_SECONDS = 1800
CORP_INDEX_FILE = "corp_codes.json"
CORP_INDEX_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
STATUS_OK = "000"
STATUS_NO_DATA = "013"
STATUS_RATE_LIMITED = "020"
# 연결재무제표가 없는 회사는 개별재무제표로 조회한다.
STATEMENT_TYPES = ("CFS", "OFS")
_XML_STATUS = re.compile(rb"<status>(\d{3})</status>")

HttpGet = Callable[..., Any]
CorpInfo = dict[str, str]

logger = structlog.get_logger(__name__)


class DartError(Exception):
    """DART 조회 실패 공통 부모."""


class DartStockNotFoundError(DartError):
    """DART에 등록되지 않은 종목코드."""


class DartNoFinancialsError(DartError):
    """조회 가능한 정기보고서 재무제표가 없음 (ETF·신규상장 등)."""


class DartRateLimitError(DartError):
    """일일 호출 한도 초과 (status 020)."""


class DartUnavailableError(DartError):
    """네트워크·인증·DART 시스템 오류."""


class StatementLookup(NamedTuple):
    items: list[dict[str, Any]]
    statement_type: str


class DartTool(Protocol):
    def fetch_dart_financial(self, stock_code: str) -> DartResult: ...


class LiveDartTool:
    def __init__(
        self,
        api_key: str,
        calculator: Any,
        cache_dir: Path,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
        http_get: HttpGet = requests.get,
    ) -> None:
        self._api_key = api_key
        # jutopia DartClient 인스턴스. 보고서 시도 순서 계산에만 쓴다.
        self._calculator = calculator
        self._statement_cache: TTLCache[StatementLookup] = TTLCache(
            "dart_statements", cache_ttl_seconds
        )
        # 결산월(acc_mt). 없으면 빈 문자열로 저장한다 (None은 캐시 미스를 뜻하므로).
        self._company_cache: TTLCache[str] = TTLCache("dart_company", cache_ttl_seconds)
        self._corp_index_path = cache_dir / CORP_INDEX_FILE
        self._http_get = http_get
        self._corp_index: dict[str, CorpInfo] = {}
        self._corp_lock = threading.Lock()

    def fetch_dart_financial(self, stock_code: str) -> DartResult:
        corp = self._corp_info(stock_code)
        for report in self._calculator._determine_report_attempts():
            year, reprt_code, _label = report
            lookup = self._statements(corp["corp_code"], year, reprt_code)
            if lookup.items:
                return self._to_result(stock_code, corp, lookup, report)
        raise DartNoFinancialsError(f"{stock_code}: 조회 가능한 정기보고서 재무제표 없음")

    # --- 결과 변환 -------------------------------------------------------------------

    def _to_result(
        self,
        stock_code: str,
        corp: CorpInfo,
        lookup: StatementLookup,
        report: tuple[int, str, str],
    ) -> DartResult:
        fiscal_month = self._fiscal_month(corp["corp_code"])
        financials = build_financials(lookup.items, report, lookup.statement_type, fiscal_month)
        rcept_no = str(lookup.items[0]["rcept_no"])
        return DartResult(
            code=stock_code,
            name=corp["corp_name"],
            corp_code=corp["corp_code"],
            rcept_no=rcept_no,
            financials=financials,
            source=dart_source(report[2], lookup.statement_type, rcept_no),
        )

    def _fiscal_month(self, corp_code: str) -> str | None:
        """결산월(MM). period_covered 계산에 쓴다 (12월 결산이 아니면 기간을 추정하지 않음)."""
        cached = self._company_cache.get(corp_code)
        if cached is not None:
            return cached or None
        data = self._get_json("company.json", {"corp_code": corp_code})
        fiscal_month = str(data.get("acc_mt") or "")
        self._company_cache.set(corp_code, fiscal_month)
        return fiscal_month or None

    # --- 재무제표 (TTL 캐시) ------------------------------------------------------------

    def _statements(self, corp_code: str, year: int, reprt_code: str) -> StatementLookup:
        key = (corp_code, year, reprt_code)
        cached = self._statement_cache.get(key)
        if cached is not None:
            return cached
        lookup = self._fetch_statements(corp_code, year, reprt_code)
        # "데이터 없음"도 캐시해 아직 공시되지 않은 보고서를 반복 조회하지 않는다.
        self._statement_cache.set(key, lookup)
        return lookup

    def _fetch_statements(self, corp_code: str, year: int, reprt_code: str) -> StatementLookup:
        for statement_type in STATEMENT_TYPES:
            params = {
                "corp_code": corp_code,
                "bsns_year": str(year),
                "reprt_code": reprt_code,
                "fs_div": statement_type,
            }
            data = self._get_json("fnlttSinglAcntAll.json", params)
            if data.get("status") == STATUS_OK and data.get("list"):
                return StatementLookup(items=data["list"], statement_type=statement_type)
        return StatementLookup(items=[], statement_type="CFS")

    # --- 종목코드 → 고유번호·회사명 (디스크 캐시 30일) -----------------------------------

    def _corp_info(self, stock_code: str) -> CorpInfo:
        # 첫 요청이 동시에 몰려도 corpCode.xml(수 MB)을 한 번만 받도록 락을 잡는다.
        with self._corp_lock:
            if not self._corp_index:
                self._corp_index = self._load_corp_index()
        corp = self._corp_index.get(stock_code)
        if corp is None:
            raise DartStockNotFoundError(f"DART에 등록되지 않은 종목코드: {stock_code}")
        return corp

    def _load_corp_index(self) -> dict[str, CorpInfo]:
        cached = self._read_corp_index_file()
        if cached is not None:
            logger.info("dart_corp_index_loaded", source="disk", entries=len(cached))
            return cached
        index = parse_corp_codes(self._download_corp_codes())
        self._corp_index_path.parent.mkdir(parents=True, exist_ok=True)
        self._corp_index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        logger.info("dart_corp_index_loaded", source="download", entries=len(index))
        return index

    def _read_corp_index_file(self) -> dict[str, CorpInfo] | None:
        path = self._corp_index_path
        if not path.is_file() or time.time() - path.stat().st_mtime > CORP_INDEX_MAX_AGE_SECONDS:
            return None
        try:
            index: dict[str, CorpInfo] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None  # 깨진 캐시는 무시하고 새로 받는다.
        return index

    def _download_corp_codes(self) -> bytes:
        content: bytes = self._request("corpCode.xml", {}).content
        if content[:2] == b"PK":
            return content
        # 정상 응답은 ZIP이고, 오류는 status가 담긴 XML로 온다.
        match = _XML_STATUS.search(content)
        raise _status_error("corpCode.xml", match.group(1).decode() if match else "unknown", "")

    # --- HTTP ------------------------------------------------------------------------

    def _get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        response = self._request(endpoint, params)
        try:
            data: dict[str, Any] = response.json()
        except ValueError:
            logger.error("dart_invalid_json", endpoint=endpoint)
            raise DartUnavailableError(f"DART 응답 파싱 실패: {endpoint}") from None
        status = str(data.get("status", ""))
        if status not in (STATUS_OK, STATUS_NO_DATA):
            raise _status_error(endpoint, status, str(data.get("message", "")))
        return data

    def _request(self, endpoint: str, params: dict[str, str]) -> Any:
        started = time.perf_counter()
        try:
            response = self._http_get(
                f"{DART_API_BASE}/{endpoint}",
                params={"crtfc_key": self._api_key, **params},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            # requests 예외 메시지에는 crtfc_key가 든 URL이 포함된다.
            # 타입만 기록하고 `from None`으로 원본 예외를 트레이스백에서 끊는다.
            logger.error("dart_request_failed", endpoint=endpoint, error_type=type(exc).__name__)
            raise DartUnavailableError(
                f"DART 요청 실패: {endpoint} ({type(exc).__name__})"
            ) from None
        latency_ms = round((time.perf_counter() - started) * 1000)
        logger.info("dart_request_succeeded", endpoint=endpoint, latency_ms=latency_ms)
        return response


def dart_source(report_label: str, statement_type: str, rcept_no: str) -> StockSource:
    return StockSource(
        name=f"DART {report_label} ({STATEMENT_LABELS[statement_type]}재무제표)",
        url=DART_VIEWER_URL.format(rcept_no=rcept_no),
    )


def parse_corp_codes(zip_bytes: bytes) -> dict[str, CorpInfo]:
    """corpCode.xml ZIP → {종목코드: {corp_code, corp_name}}. 비상장사(종목코드 없음)는 제외."""
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            root = ET.fromstring(archive.read(archive.namelist()[0]))
    except (zipfile.BadZipFile, ET.ParseError, IndexError):
        raise DartUnavailableError("DART corpCode.xml 파싱 실패") from None
    index: dict[str, CorpInfo] = {}
    for item in root.iter("list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        if stock_code:
            index[stock_code] = {
                "corp_code": (item.findtext("corp_code") or "").strip(),
                "corp_name": (item.findtext("corp_name") or "").strip(),
            }
    return index


def _status_error(endpoint: str, status: str, message: str) -> DartError:
    logger.error("dart_status_error", endpoint=endpoint, status=status, message=message)
    if status == STATUS_RATE_LIMITED:
        return DartRateLimitError("DART 일일 호출 한도 초과")
    return DartUnavailableError(f"DART 오류 응답: status={status}")


# --- mock (DART_API_KEY 미설정) ----------------------------------------------------------

MOCK_COMPANY_NAMES = {"005930": "삼성전자", "000660": "SK하이닉스"}


class MockDartTool:
    """개발용 가짜 데이터. 수치는 눈에 띄는 자리표시값이며 실제 DART 수치가 아니다."""

    def fetch_dart_financial(self, stock_code: str) -> DartResult:
        financials = StockFinancials(
            report_year=2026,
            report_code="11012",
            report_label="2026년 반기보고서",
            report_type="half_cumulative",
            period_covered="2026-01-01 ~ 2026-06-30",
            statement_type="CFS",
            revenue=1_000_000_000_000.0,
            operating_income=100_000_000_000.0,
            net_income=80_000_000_000.0,
            total_liabilities=400_000_000_000.0,
            total_equity=1_000_000_000_000.0,
            debt_ratio=40.0,
            operating_margin=10.0,
        )
        source = StockSource(
            name="[MOCK] 개발용 가짜 데이터 — 실제 DART 수치 아님", url=DART_HOME_URL
        )
        return DartResult(
            code=stock_code,
            name=MOCK_COMPANY_NAMES.get(stock_code, f"종목 {stock_code}"),
            corp_code="00000000",
            rcept_no="00000000000000",
            financials=financials,
            source=source,
            is_mock=True,
        )


def build_live_dart_tool(settings: Settings) -> LiveDartTool:
    dart_client = load_jutopia_module("dart_client", settings.jutopia_data_dir)
    # __init__을 건너뛴다: jutopia 쪽 디스크 캐시 생성·로드 없이 순수 계산 메서드만 빌려 쓴다.
    calculator = object.__new__(dart_client.DartClient)
    return LiveDartTool(
        settings.dart_api_key,
        calculator,
        settings.dart_cache_dir,
        cache_ttl_seconds=settings.dart_cache_ttl_seconds,
    )


@lru_cache
def get_dart_tool() -> DartTool:
    settings = get_settings()
    if not settings.dart_api_key:
        logger.warning("dart_mock_mode", reason="DART_API_KEY 미설정")
        return MockDartTool()
    return build_live_dart_tool(settings)
