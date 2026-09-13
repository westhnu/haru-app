# Sprint 2 Log — DART 통합 + 운영 안전장치

- **기간**: 2026-09-13
- **브랜치**: `sprint/2-dart-integration` (base: `main` = `sprint/1-bedrock-poc` fast-forward)
- **목표**: `GET /api/v1/stock/{code}/summary` → DART 재무 + AI 요약 + DART 출처 + disclaimer. 결정 1(컨텍스트 분기), 결정 2(prod fail-fast), v1.2 추가 지시 A~E 반영
- **상태**: 코드 완료 · mock 모드 검증 완료 · **실제 DART 호출은 PO의 `DART_API_KEY` 전달 후 1회 검증 예정**

---

## 1. jutopia_data 임포트 방식 결정 근거 (지시 A)

### 결론: 파일 단위 allowlist 로더 (`services/jutopia_loader.py`)
`importlib.util.spec_from_file_location`으로 **allowlist에 등록된 파일 하나만** 이름공간에 올린다(현재 `dart_client`만 등록). `sys.path`는 건드리지 않는다. 모듈을 실행하는 동안에는 `dotenv.load_dotenv`를 무력화한다.

PO 추천안 (2) 심볼릭 링크를 채택하지 않은 이유는 아래 비교 결과다.

| 후보 | 평가 | 결정적 문제 |
|---|---|---|
| (1) `sys.path.insert` | ❌ | jutopia_data 루트에 **`app.py`(Flask 서버)**가 있어 Haru `app` 패키지와 이름이 충돌함. insert 위치와 import 순서에 따라 `import app`이 엉뚱한 모듈로 해석될 수 있음. 또 `web_order.py`, `web_orderbook_ws.py`, `run_mock_trades.py` 같은 **주문 모듈이 import 경로에 노출**됨 (원칙 5) |
| (2) 심볼릭 링크 `vendor/jutopia_data` | ❌ | 링크만으로는 import가 안 되므로 결국 (1)이나 (4)가 필요함. 링크 대상이 절대경로라 다른 머신·CI·Lambda에서 깨지고, 디렉터리 전체를 노출하는 문제는 (1)과 같음 |
| (3) `pip install -e ../jutopia_data` | ❌ | jutopia_data에 `pyproject.toml`·`setup.py`가 없음 → 패키징 파일을 추가해야 해서 **원칙 4(jutopia 수정 금지) 위반** |
| **(4) 파일 단위 로더** | ✅ | 필요한 파일만 로드, 이름 충돌 없음, 주문 모듈은 allowlist에 없으면 로드 불가. 경로는 `Settings.jutopia_data_dir` 한 곳에서 관리 |

- `dart_client.py`는 jutopia 내부 모듈을 import하지 않는다(표준 라이브러리 + `requests` + `dotenv`만 사용). 그래서 파일 하나만 로드해도 동작한다. Haru 쪽에 `requests` 의존성을 추가함
- **M3 Lambda 배포 시**: jutopia 파일을 번들에 포함하고 `JUTOPIA_DATA_DIR`만 지정하면 됨 (결정 요청 3)

### 실측으로 발견한 import 시점 시크릿 유출 (KI-004 → 해결)
`dart_client.py` 22번째 줄 `load_dotenv()`가 import만으로 `jutopia_data/.env`를 읽는다. 별도 프로세스에서 import 전후의 환경변수 **이름**을 비교한 결과(값은 보지 않음):

```
DART_API_KEY, DRY_RUN, GEMINI_API_KEY, KIS_ACCOUNT_ID, KIS_ACCOUNT_SUFFIX, KIS_APP_KEY,
KIS_APP_KEY_PROD, KIS_APP_SECRET, KIS_APP_SECRET_PROD, KIS_ENV, OPENAI_API_KEY,
PINECONE_INDEX_NAME, TAVILY_API_KEY          ← 13개가 Haru 프로세스로 유입
```

→ 로더가 모듈 실행 중에만 `load_dotenv`를 no-op으로 바꿔 차단한다. 회귀 테스트는 세 가지다.
- **대조군**: 차단 없이 import하면 가짜 `.env`의 canary 변수가 실제로 올라오는지 확인
- **차단 확인**: 로더를 거치면 canary가 올라오지 않는지 확인
- **실제 jutopia**: 로드 전후 환경변수 집합이 같은지 확인

### 재사용 범위: "순수 계산만 jutopia, I/O는 Haru" (KI-006)
`dart_client.py`의 HTTP 경로는 서버에서 그대로 쓰기 부적합했다.

| jutopia 동작 | 문제 | Haru 대응 |
|---|---|---|
| 오류를 `print` 후 `None`/`{"error": ...}` 반환 | 장애와 "데이터 없음"을 구분 불가, structlog 규칙 위반 | 명시적 예외 4종 (`DartStockNotFoundError` / `DartNoFinancialsError` / `DartRateLimitError` / `DartUnavailableError`) |
| `requests` 예외 메시지를 `print` | 예외 문자열에 `crtfc_key=<키>`가 든 URL 포함 → **키가 로그로 샐 수 있음** | 예외 타입만 로그, `raise ... from None`으로 원본 예외를 트레이스백에서 제거 (테스트로 검증) |
| 캐시를 `jutopia_data/data/dart_cache/`에 기록 | 원칙 4 위반 | `DartClient.__init__`을 호출하지 않음(`object.__new__`). 캐시는 `backend/.cache/dart/`(git 제외)에 기록 |
| status `020`(한도 초과)을 `013`(데이터 없음)처럼 처리 | 한도 초과 상태에서 개별재무제표로 재요청 → 한도를 더 소모 | 020이면 즉시 `DartRateLimitError` (테스트로 호출 1회 검증) |
| 결과에서 `rcept_no`·회사명을 버림 | 지시 E의 DART 원문 URL과 `name`을 만들 수 없음 | 원본 `list[0].rcept_no` 보존. 회사명은 corpCode.xml의 `corp_name`에서 가져옴 |

**재사용하는 것**: `_compute_metrics`(계정과목 이름 변형 매핑, 부채비율·영업이익률·시계열 계산), `_determine_report_attempts`(공시 시점 기준 보고서 시도 순서). 둘 다 **비공개 메서드**라서, 시그니처가 바뀌면 계약 테스트(`test_jutopia_dart_client_contract`)가 깨지도록 해 두었다.

## 2. DART 응답 형태 검증 결과

키가 없어 새로 호출하지는 못했다. 대신 **jutopia가 과거에 받아 둔 실제 응답**(`fin_00126380_2024_11011_CFS.json`, 삼성전자 2024 사업보고서, 213행)과 **OpenDART 공식 가이드**로 검증했다.

| 항목 | 예상 | 실제 | 비고 |
|---|---|---|---|
| 항목 필드 | rcept_no 포함? | `rcept_no, reprt_code, bsns_year, corp_code, sj_div, sj_nm, account_id, account_nm, account_detail, thstrm_nm, thstrm_amount, frmtrm_nm, frmtrm_amount, bfefrmtrm_nm, bfefrmtrm_amount, ord, currency` | ✅ 일치. 파일 전체에서 `rcept_no`는 1종(`20250311001085`) → 첫 행 값을 출처로 사용 |
| 금액 형식 | 숫자 | **문자열** `"300870903000000"` (원 단위) | jutopia `_parse_amount`가 처리 |
| `sj_div` | BS/IS/CF | `BS, CF, CIS, IS, SCE` | 가이드와 일치 |
| `currency` | — | `KRW` | 응답 `financials.currency`로 노출 |
| status 코드 | 000/013/020 | 가이드 기준 13종 (000, 010, 011, 012, 013, 014, 020, 021, 100, 101, 800, 900, 901) | 000·013만 정상 처리, 020은 한도 초과, 나머지는 `DartUnavailableError` |
| jutopia `corp_codes.json` | 이름 포함? | **종목코드 → 고유번호만** (3,946개), 회사명 없음 | **예상과 다름** → Haru는 corpCode.xml을 직접 받아 `corp_name`까지 저장 |
| 계산 결과 | — | 매출액 300,870,903,000,000원, 부채비율·영업이익률 계산됨, 시계열 3기 | 실데이터 테스트(`test_jutopia_metrics_on_real_dart_response_fit_haru_schema`)로 Haru 스키마 호환 확인 |

### 키 준비 후 첫 실호출에서 확인할 것
1. corpCode.xml 실제 ZIP 구조와 `corp_name` 필드 (가이드 기준으로 구현)
2. **반기·분기보고서의 손익 금액 기준**: 사업보고서 캐시에는 누적 금액 필드가 없음. 반기·분기의 `thstrm_amount`가 3개월치인지 누적인지 확인 필요. jutopia는 `thstrm_amount`만 사용하므로 3개월 기준이면 영업이익률 해석에 주석이 필요함
3. 2026-09-13 기준 시도 순서: 2026 반기 → 2026 1분기 → 2025 사업보고서. 반기보고서는 8월 중순 공시라 첫 시도에서 조회될 것으로 예상
4. Bedrock 요약이 수치 검증(§4)을 얼마나 자주 통과하는지 → `stock_summary_ungrounded` 로그 관찰

## 3. 결정 1·2 구현

### 결정 1: `context_type` 분기
- `RagRequest.context_type: Literal["stock", "glossary", "general"] = "general"`
- `core/prompts.py`: `SYSTEM_PROMPT_STOCK` / `SYSTEM_PROMPT_GLOSSARY` / `SYSTEM_PROMPT_GENERAL`. 모두 기본 `SYSTEM_PROMPT`(출처 인용 원칙 포함)를 그대로 포함하고 컨텍스트별 규칙을 덧붙임. RAG 템플릿도 컨텍스트별 3종
- `rag_service.resolve_answer`: KB 근거(citations) 유무에 따라 분기

| citations | stock | glossary / general |
|---|---|---|
| 있음 | 모델 답변, `source: "knowledge_base"` | 모델 답변, `source: "knowledge_base"` |
| 없음 | **고정 문구로 대체** `"확인된 자료가 없습니다. DART 공시 데이터가 아직 인덱싱되지 않았을 수 있습니다."`, `source: "no_evidence"` | 모델 답변 유지, `source: "general_knowledge"` |

- 브리핑의 `source: "general_knowledge"` 태그는 `RagResponse.source` 필드로 구현함. 기존 `RagCitation.source`(문서 URI)와 이름이 같지만 위치(최상위 vs 인용 항목)로 구분됨

### 결정 2: `APP_ENV=prod` fail-fast
- `Settings.app_env: Literal["local", "dev", "staging", "prod"] = "local"`
- `model_validator(mode="after")`: prod일 때 `BEDROCK_KB_ID`, `BEDROCK_GUARDRAIL_ID`, `DART_API_KEY`, **`JUTOPIA_DATA_DIR`** 중 하나라도 비어 있으면 `ValueError`
  - 브리핑의 3개에 `JUTOPIA_DATA_DIR`을 추가함. DART 키가 있어도 이 경로가 없으면 첫 요청에서야 실패하므로, 기동 단계에서 막는다는 결정 2의 취지에 맞춤
- **검증 중 발견**: Pydantic `ValidationError`는 기본적으로 메시지에 **입력값 전체(`input_value={... 'dart_api_key': '...'}`)를 출력**함 → prod 기동이 실패하면 uvicorn 로그에 키가 찍힐 수 있음. `hide_input_in_errors=True`로 막고 테스트로 고정 (`test_prod_failure_message_hides_secret_values`)
- `create_app()`에서 설정을 로드하므로 실패하면 uvicorn이 기동하지 않음 (`test_create_app_fails_fast_in_prod_without_required_keys`)
- 부수 수정: Sprint 0 리팩토링 후보였던 "`.env` 경로가 CWD 기준" 문제를 `BACKEND_DIR / ".env"`로 해결

## 4. 종목 요약 설계 — 원칙 2의 코드 레벨 검증

Sprint 1 로그에서 "AI가 만든 수치 반환 금지를 코드로 검증하지 않음"을 기술 부채로 남겼고, 이번에 해결했다.

```
DART(LiveDartTool) ─→ financials (원본 금액 + 코드로 계산한 비율)  ── 그대로 응답
        │
        └→ ratio_facts: 부채비율·영업이익률·증감률 (코드로 계산)
                │
                ├→ Bedrock Converse (SYSTEM_PROMPT_STOCK_SUMMARY: "금액 금지, 제공된 비율만 그대로")
                │        │
                │        └→ find_ungrounded_figures(요약, 허용 비율)
                │               ├ 통과 → summary_source: "bedrock"
                │               └ 위반(금액 단위 수치 / 허용되지 않은 %) → 템플릿 요약, "template"
                └→ Bedrock 실패·stopReason≠end_turn → 템플릿 요약, "template"
  모든 경로 → apply_output_guard (금지 표현 교체 + 면책 문구)
```

- 모델에게 금액을 쓰지 못하게 한 이유: "302조 2,314억원" 같은 표기 변환은 원본과 대조하기 어렵다. 금액은 `financials`에 DART 원본으로 따로 있으므로, 요약은 해석과 비율만 담당한다
- mock 데이터는 Bedrock에 보내지 않음: 가짜 수치로 그럴듯한 요약이 만들어지면 오해 소지가 큼. 비용도 들지 않음
- `StockSummaryResponse.sources`는 `min_length=1` → 출처 없는 응답은 스키마 차원에서 만들 수 없음 (지시 E)
- 추가 필드 2개: `summary_source` (`bedrock`/`template`/`mock`)와 `is_mock`. 프론트엔드에서 "AI 요약" 배지와 "개발용 데이터" 배너를 구분하는 데 필요해서 넣음

## 5. 캐시 (지시 D)

| 대상 | 방식 | 키 | TTL |
|---|---|---|---|
| 재무제표 | 인메모리 `TTLCache` (스레드 안전) | `(corp_code, year, reprt_code)`. 연결/개별 구분은 값에 포함 | `DART_CACHE_TTL_SECONDS` = 1800초 |
| 종목코드 → 고유번호·회사명 | 디스크 JSON (`backend/.cache/dart/corp_codes.json`) | — | 30일 (jutopia와 동일) |

- **"데이터 없음"도 캐시함**: 2026 1분기처럼 아직 공시되지 않았거나 없는 보고서를 요청마다 다시 조회하지 않기 위해서
- hit/miss는 `cache_hit` / `cache_miss` structlog 이벤트로 기록 (`cache`, `key`, 누적 `hit_rate`)
- **히트율 대략치**: 실제 키가 없어 **운영 수치는 관측하지 못함**. 테스트 시나리오 기준 수치는 다음과 같음
  - 같은 종목 첫 요청: 캐시 미스 2회(최신 보고서 없음 + 직전 보고서), DART 호출 3회(연결·개별·직전)
  - TTL 안의 재요청: 캐시 히트 2회, **DART 호출 0회**
  - 즉 한 종목을 30분 안에 N번 조회하면 히트율은 (N−1)/N로 수렴하고, DART 호출은 첫 요청의 2~3회뿐. 키를 받으면 로컬 반복 호출로 실측해 보완 예정

## 6. 테스트

```
$ uv run pytest
86 passed        (Sprint 1: 28 → Sprint 2: +58)
```

| 파일 | 수 | 내용 |
|---|---|---|
| `test_health.py` | 1 | — |
| `test_guardrail.py` | 22 | Sprint 1 그대로 |
| `test_poc.py` | 12 (+7) | 결정 1: stock에서 근거 없으면 거절 / glossary·general은 general_knowledge 태그 / 컨텍스트별 템플릿 선택 / 잘못된 context_type → 422 |
| `test_config.py` | 9 | local 통과, **prod에서 필수 키 4종 각각 누락 시 실패**, 전부 있으면 통과, 오류 메시지에 비밀값 비노출, 잘못된 APP_ENV, `create_app` fail-fast |
| `test_jutopia_loader.py` | 10 | allowlist(주문 모듈 등 4종 거부), 빈 경로, **.env 유출 대조군과 차단**, 실제 jutopia 로드 시 환경변수 불변, jutopia 계약, **실제 DART 응답으로 계산·스키마 호환** |
| `test_dart_tool.py` | 9 | 출처 URL·회사명·rcept_no / 개별재무제표 폴백 / 이전 보고서 폴백 / **캐시 히트 시 DART 호출 0회** / 디스크 인덱스 재사용 / 미등록 종목 / 보고서 없음 / **020이면 재요청 없이 예외** / **네트워크 오류 시 키 비노출** |
| `test_cache.py` | 2 | hit/miss 통계, TTL 만료 |
| `test_grounding.py` | 8 | 허용 비율·정수 반올림·부호 없는 증감률 통과, 금액 단위 수치 차단, 허용되지 않은 % 차단 |
| `test_stock.py` | 13 | mock 표시 + Bedrock 미호출 / 검증 통과 AI 요약 + DART 출처 / 근거 없는 수치 → 템플릿 / 금지 표현 교체 / Bedrock 실패·잘림 → 템플릿 / DART 오류 4종 → 404·404·503·502 / 잘못된 종목코드 3종 → 422 |

모든 테스트는 실제 DART·Bedrock을 호출하지 않는다. 실제 jutopia 파일에 기대는 3개는 저장소가 없으면 skip된다.

## 7. mock 모드 실행 결과

```bash
$ curl http://localhost:8000/api/v1/stock/005930/summary
{
  "code": "005930", "name": "삼성전자",
  "financials": { "report_label": "2026년 반기보고서", "statement_type": "CFS", "currency": "KRW",
                  "revenue": 1000000000000.0, "debt_ratio": 40.0, "operating_margin": 10.0, ... },
  "summary": "[MOCK] DART 2026년 반기보고서(연결재무제표) 기준 부채비율 40.0%, 영업이익률 10.0%입니다. 세부 금액은 DART 원문을 확인하세요.\n\n본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다.",
  "summary_source": "mock",
  "sources": [{ "name": "[MOCK] 개발용 가짜 데이터 — 실제 DART 수치 아님", "url": "https://opendart.fss.or.kr/" }],
  "disclaimer": "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다.",
  "is_mock": true
}
$ curl -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/stock/abc/summary
422
```

## 8. 이후 리팩토링 후보

- **Bedrock 요약 캐시**: DART는 30분 캐시되지만 요약은 요청마다 Converse를 호출함 → 비용이 조회 수에 비례. `(rcept_no, model_id)` 키로 캐시 권장 (결정 요청 1)
- **라우터 집계**: 라우터가 3개(`health`, `poc`, `stock`)이고 `/api/v1` prefix가 반복됨 → `api/v1/__init__.py`에서 한 번에 등록
- **`TTLCache` 크기 상한 없음**: 만료 항목은 조회될 때만 제거됨. 키 공간(종목 × 보고서)이 유한해서 당장 문제는 없지만, 사용자별 데이터를 캐시하기 시작하면 LRU 상한 필요
- **mock 데이터의 연도(2026) 하드코딩**
- **`_determine_report_attempts`가 `datetime.now()`(서버 로컬 시간) 기준**: Lambda(UTC)에서는 월 경계에서 KST와 하루 차이가 날 수 있음. 영향은 경계일 하루뿐이라 M3 배포 때 확인
- **corpCode.xml 파싱에 표준 `xml.etree` 사용**: 신뢰할 수 있는 DART HTTPS 응답이라 수용했지만, 외부 XML 입력이 늘어나면 `defusedxml` 검토

## 9. 알려진 이슈 · 기술 부채

- **실제 DART 미검증** (§2 체크리스트): 키 전달 후 1회 검증 필요
- **jutopia 비공개 메서드 의존**: 계약 테스트로 변경은 감지하지만, jutopia를 고쳐 달라고 할 수는 없음(원칙 4). 계속 깨지면 계산 로직을 Haru로 옮기는 것도 검토
- **수치 검증이 보수적임**: 모델이 "40.0%"를 "40%대"로 쓰거나 새 비율을 계산하면 템플릿으로 대체됨 → 운영에서 템플릿 비율이 높으면 프롬프트 조정 필요
- **glossary·general 답변은 수치 검증 대상이 아님**: 프롬프트로 "특정 기업 수치 금지"만 지시함. KB 인용이 있는 stock 경로와 종목 요약에만 코드 검증이 적용됨
- 남은 pytest 경고: starlette/anyio deprecation (Sprint 0에서 무시하기로 승인)
- [`known-issues.md`](known-issues.md): KI-004 해결로 갱신, KI-006 신규

## 10. Sprint 2.5 진입 전 PO 결정 요청

1. **Bedrock 요약 캐시 도입 여부**: 같은 보고서(rcept_no)에 대한 요약을 캐시할지. 재무 수치가 같으면 요약도 같아야 하므로 캐시가 일관성에도 유리함. **도입을 권장하고, Sprint 2.5 첫 작업으로 30분 내외 작업량**
2. **HantuStock 조회 래퍼 구현 방식 (원칙 5 해석)**: 파일 로더로 `HantuStock.py`를 읽으면 조회 메서드만 위임해 노출하더라도 **`bid`·`ask`·`cancel_order`를 가진 클래스 객체가 메모리에 올라옴**. 원칙 5의 "주문 관련 함수는 아예 import 하지 않음"을 문자 그대로 적용하면 ② 방식이 됨
   - ① 파일 로더 + 위임 래퍼 + `hasattr` 회귀 테스트 (작업 적음, 클래스는 메모리에 존재)
   - ② 조회용 KIS API 호출만 Haru에서 새로 구현, HantuStock.py는 참고만 (작업 많음, 주문 코드 경로 원천 차단). KIS 인증 토큰 발급 로직을 옮겨야 함
   - 키움 통합(§14.5 회귀 방지 4단)과 같은 기준을 쓰려면 **② 권장**. 참고로 `HantuStock.py`에도 import 시점 `load_dotenv` 패턴이 있을 가능성이 높아 진입 전에 확인하겠음
3. **jutopia 파일의 배포 방식 (M3 대비)**: Lambda 번들에 jutopia 경로를 넣으려면 ① 배포 시 `dart_client.py`를 스냅샷 복사하고 해시를 기록하거나, ② 계산 로직을 Haru로 이관해야 함. 지금 결정할 필요는 없고 M3 전에만 정하면 됨

## PO 액션 아이템 (Sprint 2 마무리용)

```bash
cd /Users/westhnu/Agent/Claude/haru_web/backend
cp .env.example .env        # 처음 한 번만
# .env 에서 DART_API_KEY=발급받은키 입력 (JUTOPIA_DATA_DIR은 기본값 그대로)
```
→ "DART_API_KEY 준비 완료"라고 알려 주시면 삼성전자 1건으로 실제 DART + Bedrock 요약을 검증하고, §2 체크리스트와 캐시 히트율 실측을 이 로그에 추가하겠습니다.
