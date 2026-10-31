# Known Issues

기획안·재활용 자산과 실제 파일 사이의 불일치, 원칙 위반 위험 요소를 기록한다.
기획안 다음 리비전(v1.2) 작성 시 근거로 사용한다.

---

## KI-001 — jutopia_data 모듈 3개 부재

- **발견**: 2026-09-13, Bootstrap STEP 1 컨텍스트 파악 중
- **내용**: 아래 3개 파일이 `/Users/westhnu/Agent/Claude/jutopia_data/` 어디에도 없다 (`_archive/` 포함, `find`로 확인).
  - `dart_financial_loader.py`
  - `metrics_calculator.py`
  - `financial_analyzer.py`
- **영향받는 기획안 섹션**: §5.1(워크북 재활용 모듈), §5.2·§12(체크리스트 채점), §13.8(`search_dart_disclosures`, `evaluate_checklist` @tool 매핑)
- **원인 추정**: §12와 `docs/PROJECT_MODULES_SUMMARY.md`가 모듈 정리 이전 시점 기준으로 작성됨
- **결정 (PO, 2026-09-13)**: v1.2 이슈로 보류.
  - Sprint 2는 `dart_client.py`만 래핑해서 진행
  - PER/PBR/ROE 등 체크리스트 채점용 지표 계산기는 Haru에서 자체 구현 (v2)
  - 기획안 v1.2에서 §12를 실제 파일 기준으로 재작성

## KI-002 — `HantuStock` 클래스에 주문 함수 혼재 (원칙 5 위험)

- **발견**: 2026-09-13
- **내용**: `jutopia_data/HantuStock.py`의 `HantuStock` 클래스에 조회 메서드와 주문 메서드가 함께 있다.
  - 주문 계열: `bid` (L422), `ask` (L460), `cancel_order` (L637)
  - 같은 저장소의 `web_order.py`, `run_mock_trades.py`도 `HantuStock`을 import해 주문 흐름을 구성
- **위험**: 클래스를 통째로 import·상속하면 주문 실행 경로가 Haru 코드에 들어온다.
- **결정 (PO, 2026-09-13)**: 조회 전용 위임(delegation) 래퍼 승인. 한투 연동 스프린트에서 구현.
  - 파일: `backend/app/services/hantu_readonly.py`, 상속 금지
  - 노출 허용: `get_holding_stock_detail`, `get_holding_stock`, `get_holding_cash`, `get_transaction_history`, `get_transaction_summary`, `get_minute_chart`
  - 주문 메서드는 이름조차 코드에 등장시키지 않음 (테스트의 `hasattr` 회귀 검증은 예외)
  - `web_order.py`, `run_mock_trades.py` 참조 금지
- **관련 (2026-10-31 구현)**: `backend/app/services/hantu_readonly.py` — 위 6개 메서드 화이트리스트 위임만 허용, 서비스 코드에 주문 메서드 이름 없음. 회귀 테스트 `tests/regression/test_hantu_readonly.py`

## KI-003 — 기획안 부록의 `haru_web` 파일 일부 부재

- **발견**: 2026-09-13
- **내용**: 기획안 §12 "부록 위치"에 적힌 파일 중 다음이 없었다.
  - `haru_web/README.md` → Sprint 0에서 생성 (해결)
  - `haru_web/artifacts/haru_planning_board.html`, `morning_global_market.html`, `evening_korea_market.html` → 미해결, 이 저장소에 없음
- **조치**: 아티팩트 HTML은 PO 확인 전까지 생성·복원하지 않는다.

## KI-004 — `dart_client.py`의 환경변수 로딩 방식 (Sprint 2 확인 필요)

- **발견**: 2026-09-13
- **내용**: `dart_client.py`가 `import os`, `from dotenv import load_dotenv`를 사용한다. 모듈 import 시점에 `.env`를 읽거나 `os.getenv`로 키를 직접 참조할 가능성이 있다.
- **위험**: Haru 규칙 "환경변수는 `Settings` 하나로만 관리"와 충돌하고, `python-dotenv` 의존성이 추가된다.
- **조치**: Sprint 2에서 실제 동작을 확인한 뒤 래퍼(`dart_tool.py`)에서 키를 명시적으로 주입하는 방식을 결정한다.
- **실측 (2026-09-13, Sprint 2)**: 우려보다 심각했다. `dart_client.py`를 **import만 해도** `load_dotenv()`가 `jutopia_data/.env`를 읽어 **13개 변수가 Haru 프로세스 환경변수로 들어온다**. `DART_API_KEY`, `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_APP_KEY_PROD`, `KIS_APP_SECRET_PROD`, `KIS_ACCOUNT_ID`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `TAVILY_API_KEY` 등 (값은 보지 않고 이름만 수집)
- **해결 (Sprint 2)**: `services/jutopia_loader.py`가 모듈을 실행하는 동안 `dotenv.load_dotenv`를 무력화한다. DART 키는 `Settings.dart_api_key`에서 명시적으로 주입한다. 회귀 테스트 `tests/test_jutopia_loader.py`로 보장 (차단하지 않으면 실제로 새는지 확인하는 대조군 포함)
- **관련 (2026-10-31)**: `hantu_readonly.py`는 `jutopia_loader.load_hantu_stock_class`로 HantuStock을 로드한다. HantuStock.py도 import 시점에 `load_dotenv()`를 호출하므로 같은 차단을 적용. `load_jutopia_module("HantuStock")`은 여전히 거부됨. 행동 검증: `test_hantu_loader_blocks_dotenv_leak`

## KI-005 — 데이터 처리 리전 이슈 (`global.` 추론 프로파일)

> Sprint 1 브리핑에서는 "KI-002"로 지정했으나, KI-002는 HantuStock 항목이 이미 사용 중이라 KI-005로 기록한다.

- **발견**: 2026-09-13, Sprint 0 모델 ID 확인 중
- **내용**: 서울 리전(`ap-northeast-2`)에서 Claude Sonnet/Haiku 4.5 이상은 ON_DEMAND 호출이 불가하고, `apac.` 프로파일도 없어 **`global.` 크로스 리전 추론 프로파일만** 사용 가능하다. 요청이 한국 밖 리전에서 처리될 수 있다.
- **결정 (PO, 2026-09-13)**: 승인. MVP는 공개 정보(DART·용어사전) 위주이고 PII는 마스킹하므로 리스크 낮음.
- **완화 조치**
  - Sprint 1: `core/guardrail.py`의 `mask_pii()`를 RAG 호출 직전에 적용 — 주민등록번호·카드·휴대전화·계좌번호를 라벨 토큰으로 치환한 뒤에만 Bedrock으로 전송
  - Sprint 1: 로그에는 질의 원문 대신 길이만 기록
  - 예정: Bedrock Guardrail Sensitive Information 필터(입력·출력 마스킹, 기획안 §13.5)
- **재검토 트리거**
  - 사용자별 데이터(투자 저널, 한투·키움 잔고/거래내역)를 프롬프트에 넣기 시작할 때 (Sprint 2.5 이후)
  - 서울 리전 native 또는 `apac.` 프로파일로 4.5+ 모델이 제공될 때
  - 개인정보 국외 이전 고지·동의 필요 여부 법무 검토 시 (퍼블릭 런칭 M6 전)

## KI-006 — `dart_client.py`의 HTTP 경로는 서버에서 그대로 쓰기 부적합

- **발견**: 2026-09-13, Sprint 2
- **내용**
  - 오류를 `print` 후 `None`/`{"error": ...}`로 삼킨다 → 네트워크 장애와 "데이터 없음"을 구분할 수 없음
  - `requests` 예외 메시지에 `crtfc_key=<API 키>`가 든 URL이 포함되어, `print`·트레이스백을 통해 **키가 로그에 남을 수 있음**
  - 디스크 캐시를 `jutopia_data/data/dart_cache/`에 쓴다 → 원칙 4(jutopia 수정 금지) 위반
  - 상태 코드 `020`(요청 제한 초과)을 `013`(데이터 없음)과 같이 취급해 개별재무제표로 재요청 → 한도 초과 상황에서 호출을 더 소모
  - 결과에서 `rcept_no`(접수번호)와 회사명을 버린다 → DART 원문 URL과 응답의 `name`을 만들 수 없음
- **조치 (Sprint 2)**: jutopia에서는 순수 계산 로직(`_compute_metrics`, `_determine_report_attempts`, 계정과목 이름 매핑)만 재사용하고, HTTP·오류 처리·캐시는 `services/dart_tool.py`에서 구현. jutopia의 비공개 메서드에 의존하므로 계약 테스트(`tests/test_jutopia_loader.py`)로 시그니처 변경을 감지한다

## KI-007 — Bedrock Anthropic 모델 사용 사례 양식 미제출

- **발견**: 2026-09-13, Sprint 2 실측
- **내용**: `global.anthropic.claude-sonnet-4-5-20250929-v1:0` Converse 호출이 `ResourceNotFoundException: Model use case details have not been submitted for this account`로 실패함. `GetUseCaseForModelAccess` 결과는 "You have not filled out the request form". Sprint 1에서는 같은 호출이 성공했었음
- **영향**: 종목 요약이 항상 템플릿으로 폴백됨(`summary_source: "template"`). KB를 연결하면 RetrieveAndGenerate도 같은 이유로 실패할 것으로 예상
- **조치**: PO가 AWS 콘솔에서 Anthropic use case 양식을 제출한 뒤 재검증

## KI-008 — 반기·분기보고서 손익의 기간 혼재와 계정 매칭 누락

- **발견**: 2026-09-13, Sprint 2 실측 (삼성전자 2026 반기)
- **내용**
  - 손익 `thstrm_amount`는 **3개월(분기 단독)** 금액이고 누적은 `thstrm_add_amount`에 있음. jutopia는 `thstrm_amount`를 사용
  - 현금흐름은 누적, 재무상태는 기말 시점 값인데 `financials`에는 보고서 라벨 하나뿐이라 **기간이 섞여 보임**
  - 순이익 계정명이 `반기순이익`/`분기순이익`이라 jutopia 이름 목록에 매칭되지 않음 → `net_income: null`
  - 반기·분기 IS의 비교값은 `frmtrm_q_amount`에 있어 시계열이 1점뿐 → 증감률 계산 불가
- **영향**: 원칙 2(정확한 수치 전달) 측면에서 오해 소지. 체크리스트 채점(§5.2)에 그대로 쓰면 3개월 기준으로 판정됨
- **조치**: PO 결정 대기 (sprint-2-log §12의 ① 기간 라벨 추가 / ② 누적 기준 통일, ② 권장)

## KI-009 — Sonnet 4.5 base ID LEGACY (추론 프로파일 사용 중, Phase 5 재검증 예정)

- **발견**: 2026-10-30, `bedrock-kb-and-guardrail` 스펙 Phase 4 사전 실측
- **상태**: resolved
- **내용**: `aws bedrock list-foundation-models`(서울 리전) 조회 결과 `anthropic.claude-sonnet-4-5-20250929-v1:0`의 `modelLifecycle.status`가 **`LEGACY`**다. (Titan Embeddings v2는 `ACTIVE`.) 실제 호출은 base ID가 아닌 `global.anthropic...` 크로스 리전 추론 프로파일을 경유하므로(KI-005), list의 LEGACY 표기와 호출 경로는 별개다.
- **영향**: Phase 5 실호출(RetrieveAndGenerate 생성 모델)에서 쓰는 `BEDROCK_MODEL_ID`가 이 Sonnet 4.5다. base ID가 LEGACY로 EOL 수순에 들어가면 추론 프로파일도 영향받을 수 있어, 실호출 전 유효성 확인이 필요하다.
- **조치**: Phase 5의 **T-500**에서 `aws bedrock get-inference-profile`로 `ACTIVE` 확인 후 진행. 유효하지 않으면 모델 ID를 후속 Sonnet 버전으로 교체.
- **해결 (2026-10-30)**: T-500 선행 실측에서 `global.anthropic.claude-sonnet-4-5-20250929-v1:0`가 `SYSTEM_DEFINED` 프로파일이며 status `ACTIVE`임을 확인. list-foundation-models의 base ID `LEGACY`는 수명주기 라벨일 뿐, 실제 호출 경로인 global 추론 프로파일은 ACTIVE로 두 축이 별개임을 검증. 현재 모델 ID 유지.
- **관련**: KI-005(global. 추론 프로파일), KI-007(use case 양식)

## KI-010 — Bedrock KB S3_VECTORS: indexArn과 indexName 동시 전달 금지

- **발견**: 2026-10-31, `bedrock-kb-and-guardrail` 스펙 Phase ⑥(T-404) `--apply` 1차 시도
- **상태**: resolved
- **증상**: `bedrock-agent.create_knowledge_base` 호출이 `ValidationException: Vector index name should not be present with namespace arn.`로 실패
- **재현**: `aws bedrock-agent create-knowledge-base ... --storage-configuration type=S3_VECTORS,s3VectorsConfiguration={vectorBucketArn,indexArn,indexName}` — indexArn과 indexName을 함께 전달
- **원인**: `s3VectorsConfiguration`의 `indexArn`과 `indexName`은 상호 배타적이다. indexArn(namespace arn)에 이미 인덱스 식별이 포함되므로 indexName을 함께 주면 거부된다.
- **완화 (해결)**: `scripts/kb/create_or_sync_kb.py`의 `_storage_config`에서 `indexName`을 제거하고 `indexArn`만 유지. 회귀 테스트 `test_storage_config_omits_index_name_ki010` 추가.
- **교훈**: Bedrock agent SDK/문서상 Optional 필드 간 상호 배타성이 명시되지 않아, 실제 호출로만 검증 가능했다. S3_VECTORS 같은 신규 스토리지 타입은 dry-run·메타 검증을 넘어 1차 실호출에서 ValidationException을 확인하는 단계가 필요하다.
- **관련**: T-404, Phase 4 ⑥

## KI-011 — fresh create→sync 플로우에서 불필요한 list_data_sources 호출

- **발견**: 2026-10-31, `bedrock-kb-and-guardrail` 스펙 Phase ⑥(T-405) `--apply` 2차 시도
- **상태**: resolved
- **증상**: KB(`XBBETDQEY4`)·DataSource(`LPMVBACVJ0`) 생성은 성공했으나, 이어진 sync 단계에서 `AccessDeniedException: User ... is not authorized to perform: bedrock:ListDataSources`
- **재현**: `create_or_sync_kb.py --create --sync --apply` — create는 ds_id를 반환하는데, sync의 `_resolve_ds_id`가 그 값을 버리고 `agent.list_data_sources(...)`로 다시 조회
- **원인**: "방금 만든 리소스의 ID를 버리고 다시 조회"하는 안티패턴. 불필요한 list 호출이 최소권한 원칙을 위반(해당 사용자에 ListDataSources 권한 없음)
- **완화 (해결)**: `_do_create`가 `(ok, kb_id, ds_id)`를 반환하고 `run()`이 이를 `_do_sync(kb_id=..., ds_id=...)`로 직접 전달. 전달받으면 `_resolve_ds_id`(= list_data_sources)를 건너뛴다. 단독 `--sync`일 때만 fallback으로 재조회. 추가로 `KbAdminService._is_fake(kb_id)`가 전달 kb_id를 고려하도록 수정해 fresh 경로가 mock으로 빠지지 않게 함.
- **교훈**: 생성 직후의 ID를 그대로 흘려보내지 않고 재조회하면 (1) 중복 왕복, (2) 불필요한 read 권한 요구가 발생한다. create→sync를 한 실행에서 할 때는 반환값을 스레딩하는 게 최소권한·최소호출.
- **회귀 방지**: `test_sync_uses_create_result_ds_id_ki011`
- **관련**: T-405, KI-010, Phase 4 ⑥

## KI-012 — teardown.py가 all-or-nothing 설계 — 부분 롤백 불가

- **발견**: 2026-10-31, Phase ⑥ 2차 실패 후 KB만 롤백하려 했으나 `teardown.py --dry-run`이 vector store·S3까지 삭제 대상에 포함
- **상태**: resolved-ad-hoc / 근본해결-deferred-to-phase6 (T-603)
- **증상**: 2차 생성물(KB `XBBETDQEY4`)만 지우려는데, teardown dry-run은 vector index·vector bucket·S3 객체·S3 버킷을 전부 삭제 대상으로 표시. 게다가 KB는 `.env`에 `BEDROCK_KB_ID`가 없어 `skip_empty`로 정작 안 지워짐.
- **원인**: 스크립트가 `settings.bedrock_kb_id` 하나로 "스택 전체" 역순 삭제를 가정. 선택적 삭제 범위(scope)를 지원하지 않음.
- **임시 완화 (resolved-ad-hoc)**: `aws bedrock-agent delete-knowledge-base --knowledge-base-id XBBETDQEY4`로 KB만 직접 삭제. vector store·S3는 보존해 멱등성 재사용.
- **근본 완화 (deferred, T-603 / Phase 6)**: teardown에 `--scope {kb-only, vector-only, s3-only, all}` + `--kb-id` 인자 추가.
- **교훈**: IaC의 "되돌리기"는 생성과 대칭적이어야 하지만, 운영에선 부분 롤백 요구가 더 흔하다. teardown은 전체/부분 둘 다 지원해야 한다.
- **관련**: T-451, T-603, KI-011

## KI-013 — create_knowledge_base 후 KB ACTIVE 대기 누락 → ConflictException on start_ingestion_job

- **발견**: 2026-10-31, Phase ⑥ 3차 `--apply` (KI-010·KI-011 수정 후 처음 도달한 지점)
- **상태**: resolved
- **증상**: KB(`LEWVDQRRRK`)·DS 생성 성공 직후 `start_ingestion_job`이 `ConflictException: You cannot start an ingestion job on a knowledgeBase with status CREATING`로 실패
- **원인**: AWS Bedrock KB 생성은 비동기다(`CREATING` → `ACTIVE`). `create_knowledge_base` 반환은 "요청 접수"일 뿐 "사용 가능"이 아닌데, 코드가 대기 없이 sync를 시작했다.
- **재현**: `create_knowledge_base` 반환 직후 `start_ingestion_job` 호출 → ConflictException
- **완화 (해결)**: `create_or_sync_kb.py`에 `_wait_kb_active`(get_knowledge_base 폴링, 최대 120s / 2s 간격) 추가. create·멱등 재사용 두 경로 모두 sync 전에 ACTIVE 확인. FAILED/DELETING은 즉시 RuntimeError, 초과 시 TimeoutError. structlog `event=kb_wait_active`.
- **교훈**: AWS 비동기 리소스 생성에서 "API 반환 == 사용 가능"이 아니다. 상태 폴링은 선택이 아니라 필수다. (KI-011의 "반환값 스레딩"으로도 못 막는, 리소스 수명주기 레벨의 문제)
- **회귀 방지**: `test_create_waits_for_kb_active_ki013` 외 2건
- **관련**: T-405, KI-010, KI-011, Phase 4 ⑥

## KI-014 — get_ingestion_job 호출에 dataSourceId 파라미터 누락 → ParamValidationError

- **발견**: 2026-10-31, Phase ⑥ 3차 재개 — ingestion start 성공 후 폴링 1차 호출에서 즉시 실패
- **상태**: resolved
- **증상**: `start_ingestion_job`(job `XMUUKHIRZP`)은 성공했으나, `poll_sync`의 첫 `get_ingestion_job` 호출이 `botocore ParamValidationError: Missing required parameter in input: "dataSourceId"`
- **원인**: `KbAdminService.poll_sync`/`_fetch_ingestion_status`가 `get_ingestion_job`에 `knowledgeBaseId`+`ingestionJobId`만 넘김. 실 API는 `dataSourceId`도 필수. Phase 2에서 KbAdminService를 Fake 클라이언트로만 테스트해 실 API 필수 파라미터를 미검증.
- **재현**: `client.get_ingestion_job(knowledgeBaseId=.., ingestionJobId=..)` (dataSourceId 누락)
- **완화 (해결)**: `poll_sync` 시그니처에 `*, data_source_id` keyword-only 필수 인자 추가. `_fetch_ingestion_status`가 `dataSourceId`를 전달. `create_or_sync_kb._do_sync`가 create 결과 ds_id를 `poll_sync`에 전달(KI-011 스레딩 재활용).
- **교훈**: mock은 "메서드 존재 여부"만 검증한다. "실 API 파라미터 스키마"는 contract test 또는 실호출로만 보장된다. 신규 AWS API 래퍼는 1차 실호출 검증이 필수.
- **회귀 방지**: `test_poll_sync_passes_data_source_id_ki014`, `test_poll_sync_rejects_missing_data_source_id_ki014`
- **관련**: T-405, KI-011, KI-013, Phase 4 ⑥

## KI-015 — Bedrock KB가 glossary.jsonl 전체를 1개 문서로 취급 → 50KB maxLength 초과

- **발견**: 2026-10-31, Phase ⑥ 3차 재개, ingestion job `XMUUKHIRZP` FAILED
- **상태**: strategy-decided / implementation-deferred-to-next-block
- **증거**: `statistics.numberOfDocumentsScanned=1`(302 아님), `failureReasons="expected maxLength: 50000, actual: 194198 ... file: glossary/glossary.jsonl"`
- **원인**: `chunkingStrategy=NONE`의 의미 오해. NONE은 "파일 1개 = 문서 1개로 취급하고 쪼개지 말라"는 뜻. 302줄 JSONL이 단일 문서가 돼 길이 초과. Bedrock KB의 문서 모델은 **S3 object 1개 = 문서 1개**이고, "JSONL 라인별 record"라는 의미는 KB 추상화에 없다.
- **채택 전략 (옵션 1 — 302개 개별 .txt 파일)**:
  - S3 레이아웃: `glossary/term_001.txt` ~ `glossary/term_302.txt` (3자리 zero-pad)
  - 포맷: 평문 txt, 비어있지 않은 필드만 `용어/영문/정의/예시/해석/사용 시점/주의` 라벨로 나열
  - 각 파일 평균 ~500자, 최대 ~2KB → 50KB 한도 여유
  - `chunkingStrategy=NONE` 유지 (파일=문서=청크 1:1)
  - 평문 txt는 Bedrock KB 네이티브 지원 포맷
- **왜 다른 옵션 아닌가**:
  - FIXED_SIZE 청킹: 용어 경계가 깨져 Context Precision 하락 → RAGAS 지표 악화
  - CSV: Bedrock CSV는 메타데이터 매핑용 특수 포맷, row=문서 보장 없음
  - md/html 등 blob: JSON과 동일하게 파일=문서로 처리됨
- **영향 범위 (다음 블록 구현)**:
  - `scripts/kb/convert_glossary.py` 재작성 (302 .txt 생성)
  - `scripts/kb/upload_glossary.py` 재작성 (302 객체, 파일 단위 md5 idempotency)
  - `backend/data/kb/`: glossary.jsonl 폐기, 302개 .txt 신규 (gitignore 유지)
  - S3: 기존 `glossary/glossary.jsonl` 삭제 + 302개 업로드
  - tasks.md T-402/T-403 DoD 갱신 (파일 1개 → 302개)
  - convert/upload 테스트 재작성
  - KB·DS·vector store·S3 bucket: **전부 재사용**(삭제 불필요)
- **교훈**: "chunking=NONE = 라인별 문서"라는 가정이 틀렸다. KB 문서 경계는 청킹이 아니라 **S3 객체 단위**로 정해진다. 데이터 모델 가정은 실 ingestion으로만 검증 가능.
- **관련**: T-402, T-403, KI-010~014, Phase 4 ⑥

## KI-016 — S3 Vectors filterable metadata 2048 bytes 한도 → 158/302 색인 실패

- **발견**: 2026-10-31, Phase ⑥ 4차 ingestion job `R6QMUSL1AU` (status=COMPLETE지만 158 실패)
- **상태**: strategy-decided (옵션 A), implementation-in-progress
- **증상**: `numberOfDocumentsScanned=302`, `numberOfNewDocumentsIndexed=144`, `numberOfDocumentsFailed=158`. 실패 로그 전부 `Filterable metadata must have at most 2048 bytes (Service: S3Vectors, 400)`
- **원인**: vector index 생성 시 `nonFilterableMetadataKeys` 미지정 → 모든 metadata가 filterable로 처리됨. Bedrock KB가 chunk 본문을 저장하는 `AMAZON_BEDROCK_TEXT` 키가 filterable 2048B 한도에 걸림. 긴 용어(최대 ~3KB) 158개가 초과.
- **증거**:
  - 성공 벡터 샘플 metadata 키: `AMAZON_BEDROCK_TEXT`(본문), `AMAZON_BEDROCK_METADATA`(출처 JSON), `x-amz-bedrock-kb-source-file-modality`, `x-amz-bedrock-kb-data-source-id`
  - AWS Bedrock kb-chunking 가이드: S3 vector bucket 사용 시 `AMAZON_BEDROCK_TEXT`·`AMAZON_BEDROCK_METADATA`를 non-filterable metadata key로 지정 권고 (내용은 라이선스 준수를 위해 재서술)
  - S3 Vectors 한도: filterable 2048 bytes/벡터, filterable+non-filterable 합산 40KB/벡터
- **완화 (옵션 A)**: vector index 재생성 시 `metadataConfiguration.nonFilterableMetadataKeys=["AMAZON_BEDROCK_TEXT","AMAZON_BEDROCK_METADATA"]` 지정. index 설정은 생성 시 immutable → 삭제·재생성 체인(KB·DS cascade) 필요. S3 302 txt·vector bucket은 보존.
- **교훈**: 벡터 스토어 metadata 모델은 서비스마다 다르고, filterable 필드에 숨은 바이트 한도가 있을 수 있다. 큰 chunk 본문은 non-filterable에 넣는 것이 S3 Vectors + Bedrock KB의 정석. citation 출처(`AMAZON_BEDROCK_METADATA.sourceLocation`)는 non-filterable로 빼도 retrieval 결과에 보존됨.
- **회귀 방지**: `test_create_index_sets_non_filterable_metadata_ki016`
- **관련**: T-401.5-B, KI-015, Phase 4 ⑥

## KI-017 — Bedrock Guardrail piiEntitiesConfig가 한국 PII(KR_RRN) 미지원

- **발견**: 2026-10-31, Phase ⑦ 1차 `--apply` ValidationException
- **상태**: resolved
- **증상**: `CreateGuardrail` 호출 시 `Value at 'sensitiveInformationPolicyConfig.piiEntitiesConfig.1.member.type' failed to satisfy constraint: Member must satisfy enum value set: [US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER, ..., AGE]` — enum에 US/UK/CA 등 서구 PII만 포함, KR_RRN 미지원.
- **조사 방법**: botocore service model(authoritative) + AWS Bedrock guardrails-sensitive-filters 공식 문서 교차 확인으로 `regexesConfig` 스키마(name/pattern/action 필수, action enum=BLOCK/ANONYMIZE/NONE) 확인.
- **완화**: `piiEntitiesConfig`에서 KR_RRN 제거, `regexesConfig`로 커스텀 패턴(`\d{6}-[1-8]\d{6}`) 지정. `core/guardrail.py`의 `_RRN` 정규식과 정합(성별코드 1-8). lookaround는 Bedrock 호환성 불확실 → 제외.
- **교훈**: 지역화된 PII는 Bedrock 내장 enum이 아니라 regexesConfig로 커스텀 지정하는 것이 정석. 공식 schema를 service model에서 직접 확인하는 것이 재작업 비용 최소화.
- **회귀 방지**: `test_guardrail_uses_regexes_config_for_kr_rrn_ki017`
- **관련**: T-407, 원칙 1 이중 방어

## KI-018 — 기존 /brief, /themes 경로가 Bedrock Guardrail·core.guardrail 이중 방어 미적용

- **발견**: 2026-10-31, 세션 2 frontend 구조 조사
- **상태**: open (중장기 리팩토링 과제)
- **증상**: haru-app frontend의 Daily 2-Brief 경로는 GPT(openai sdk) + Gemini를 쓴다. FastAPI 백엔드·Bedrock Guardrail·`core/guardrail.py` 어느 것도 거치지 않는다.
- **영향 범위**: `/brief/morning`, `/brief/evening`, `/themes`, `/api/brief`, `/api/brief/generate`, `/api/themes`
- 특히 `/themes`는 이슈를 종목에 연결하는 기능이라 원칙 1(종목 매수·매도 권유 금지)에 가까운 민감 경로.
- **현재 완화**: 기존 코드의 자체 가드(GPT→Gemini 교차검증). Bedrock Guardrail의 Denied Topic·Content Filter·KR_RRN(KI-017) 같은 상위 레이어 보호는 없음.
- **중장기 완화 (세션 4+)**: LLM 호출을 FastAPI `/api/v1/glossary/ask` 패턴으로 통일 → Bedrock Claude Sonnet 4.5 + Guardrail + core.guardrail 자동 통과. 또는 openai sdk 호출을 자체 wrapper로 감싸 `enforce_disclaimer` 후처리 적용.
- **세션 2 범위**: 수정 안 함. 신규 경로(/workbook, /checklist, /journal, /glossary)는 `/backend/*` 프록시로 FastAPI를 경유해 이중 방어를 통과.
- **교훈**: 안전 레이어 적용 범위를 명시적으로 관리하는 것이 "암묵적 미적용"보다 안전하다.
