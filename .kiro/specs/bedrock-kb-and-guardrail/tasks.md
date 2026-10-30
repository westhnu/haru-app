# Tasks — Bedrock Knowledge Base & Guardrail 실물화

> Kiro는 각 태스크의 **HITL·타임아웃·재시도** 필드를 반드시 준수한다. Kiro Power에서 `boto3`·`aws` 관련 도구는 필요한 태스크에서만 활성화하여 컨텍스트를 절약한다.

## 실행 순서 원칙

1. 태스크는 위에서 아래로 순차 실행
2. 각 태스크의 **완료 기준(DoD)** 이 통과해야 다음으로 이동
3. `HITL: 필수` 태스크는 Kiro의 `Allow Once`만, `Allow Always` 절대 금지
4. 실패 시 즉시 중단하고 나(사용자)에게 보고
5. 각 단계 끝에 커밋 (Conventional Commits)

---

## Phase 1 — 스키마·설정 확장 (코드 변경만, AWS 리소스 X)

### T-101 · `.env.example` 확장

- [x] `backend/.env.example`에 다음 5개 키 추가 (값 없이):
  - `BEDROCK_KB_ID=`
  - `BEDROCK_GUARDRAIL_ID=`
  - `BEDROCK_GUARDRAIL_VERSION=DRAFT`
  - `HARU_KB_S3_BUCKET=`
  - `HARU_KB_S3_VECTOR_INDEX_ARN=`
- **DoD**: `.env.example` diff 확인, 실제 값 없이 키 이름만
- **HITL**: Allow Session
- **타임아웃**: 30초, 재시도 0

### T-102 · `Settings` 확장 + prod 검증

- [x] `app/config.py`에 5개 필드 추가
- [x] `model_validator(mode="after")` 신설 — REQ-ENV-01
- [x] `hide_input_in_errors=True` 유지
- **DoD**: `APP_ENV=prod BEDROCK_KB_ID= uv run uvicorn app.main:app` → `ValueError` 발생 확인
- **HITL**: Allow Once
- **타임아웃**: 60초, 재시도 0

### T-103 · `models/rag.py` 확장

- [x] `RagCitation` 신설 (text_snippet, source_uri, similarity)
- [x] `RagResponse`에 `citations: list[RagCitation]`, `guardrail_action`, `context_type`, `summary_source` 확장
- [x] `disclaimer` 필드 빈 문자열 금지 (Pydantic validator)
- **DoD**: `pytest tests/unit/test_models_rag.py` 통과
- **HITL**: Allow Once
- **타임아웃**: 60초, 재시도 0

### T-104 · 회귀 테스트 사전 작성 (TDD)

- [x] `tests/regression/test_guardrail_bedrock.py` 신설 (4개 케이스)
- [x] `tests/regression/test_stock_no_grounding.py` 신설 (REQ-RAG-04)
- [x] `tests/regression/test_disclaimer_never_empty.py` 신설
- [x] Red 대신 `@pytest.mark.skip`으로 Phase 2+ 보류 (사용자 지침 C — pytest 통과 유지)
- **DoD**: `pytest tests/regression/` → 신규 테스트 4개 이상 fail (구현 전이므로 정상)
- **HITL**: Allow Session
- **타임아웃**: 120초, 재시도 0

### T-105 · 커밋

- [x] `feat: expand config and models for Bedrock KB and Guardrail`
- **DoD**: `git log --oneline -1` 커밋 확인
- **HITL**: Allow Once
- **타임아웃**: 30초

---

## Phase 2 — Bedrock Client 확장 (Fake 모드)

> **설계 drift (Phase 2):** tasks/design의 `BedrockClient` 클래스 가정은 재해석했다. RAG 호출 로직이 이미 `rag_service`에 있으므로 `BedrockClient` 클래스는 만들지 않는다. RAG 호출 확장은 `rag_service._retrieve_and_generate`에서, KB 관리(sync/poll/status)는 신규 `services/kb_admin_service.py`에서 담당한다. 기존 `@lru_cache` 팩토리(`get_runtime_client`, `get_agent_runtime_client`)는 유지하고 `get_bedrock_agent_client`만 추가했다. 예외 3종은 `services/exceptions.py`에 둔다. design.md는 Phase 3에서 함께 재해석 예정.

### T-201 · `rag_service._retrieve_and_generate` 확장 (drift: BedrockClient 대체)

- [x] `rag_service._retrieve_and_generate`에 `guardrail_id`, `guardrail_version`, `context_type` 파라미터 추가 (하위 호환 default)
- [x] Fake 응답 모드 (KB_ID 미설정 시 `_mock_response`, `is_mock=True`)
- [x] 예외 3종 신설(`services/exceptions.py`): `BedrockRetrievalError`, `BedrockGuardrailBlockedError`, `BedrockNotAvailableError` — Phase 2에서 raise 안 함(실호출 없음)
- **DoD**: 유닛 테스트에서 Fake 응답 정상 파싱
- **HITL**: Allow Session
- **타임아웃**: 180초

### T-202 · `kb_admin_service` 신설 (drift: BedrockClient 대체)

- [x] `KbAdminService.start_sync` / `poll_sync` / `get_status` 추가 (실호출은 Phase 5에서)
- [x] 폴링 타임아웃 600초, 15초 간격 (`POLL_INTERVAL_S=15`)
- [x] 신규 팩토리 `get_bedrock_agent_client()` 추가
- **DoD**: 유닛 테스트 mock으로 통과
- **HITL**: Allow Session
- **타임아웃**: 120초

### T-203 · 통합 테스트 — mock 경로

- [x] `tests/integration/test_glossary_ask_mock_mode.py` — KB_ID 없을 때 mock 응답
- [x] `tests/integration/test_glossary_ask_with_fake_bedrock.py` — Fake 응답으로 citations 파싱
- [x] `tests/unit/test_kb_admin_service.py` — sync/poll/status Fake 검증
- [x] `conftest.py`에 `fake_agent_runtime` fixture 추가
- **DoD**: `pytest tests/integration/` 신규 2개 통과
- **HITL**: Allow Once

### T-204 · 커밋

- [x] `feat: extend rag_service with guardrail params and add kb_admin_service`

---

## Phase 3 — RAG 서비스 · API 라우터

> **설계 결정 (Phase 3):** `resolve_answer`는 `(text, source)` tuple 대신 `AnswerResolution` dataclass(text/source/summary_source/similarity_max)를 반환하도록 단일 소스로 통합했다(호출처 1곳 확인 완료). `source: AnswerSource`(근거 출처)와 `summary_source`(생성 방식)는 **분리된 레이어**로 유지한다 — 겹치는 값은 general_knowledge 하나뿐. similarity는 Bedrock 응답의 `metadata.score`→`relevanceScore` 후보 2경로로 파싱하며 실측 필드는 Phase 5에서 확정한다. admin 라우터는 KbStatus→KbStatusResponse로 필드명 매핑.

### T-301 · `services/rag_service.py` 확장

- [x] `ask(query, context_type)` 시그니처 (하위 호환 유지)
- [x] KB_ID 없으면 mock 응답 (`summary_source=template`)
- [x] `context_type=="stock"` 유사도 임계 미달 → 거절 문구 (REQ-RAG-04), glossary는 general_knowledge
- [x] `AnswerResolution` 도입 + similarity 파싱 + `event=rag_ask`(context_type/similarity_max/summary_source) 로그
- **DoD**: 유닛 3개 통과
- **HITL**: Allow Session

### T-302 · `api/v1/glossary.py` 신설

- [x] `POST /api/v1/glossary/ask` 엔드포인트 (main.py 등록)
- [x] `GlossaryAskRequest` + `RagResponse` 재사용
- [x] 예외 → 502 매핑 (poc.py 패턴, RagServiceError)
- **DoD**: `curl POST /api/v1/glossary/ask -d '{"query":"PER?"}'` mock 응답 200
- **HITL**: Allow Session

### T-303 · `api/v1/admin.py` 신설

- [x] `GET /api/v1/admin/kb-status` (인증 없이, read-only, main.py 등록)
- [x] `kb_admin_service.get_status` 호출, KB_ID 빈 값이면 is_mock=True; `KbStatusResponse` 매핑
- **DoD**: mock 상태로 200 응답
- **HITL**: Allow Session

### T-304 · 커밋

- [x] `feat: glossary and admin routers with context_type routing`

---

## Phase 4 — AWS 리소스 생성 스크립트 ⚠️ HITL 필수 구간

> ⚠️ **여기서부터 실제 AWS 자원이 생성된다. 각 태스크마다 사용자(나)의 명시적 승인 없이 절대 실행 금지.**

> **[설계 drift — 사전 실측 반영 (2026-10-30)]**
>
> 실측 결과 **S3 Vector Store는 일반 S3 버킷과 별개 리소스**다. 따라서 Phase 4는 세 리소스를 만든다:
> 1. **데이터소스용 일반 S3 버킷** (`HARU_KB_S3_BUCKET`) — glossary JSONL 원문 저장 (T-401·T-403)
> 2. **벡터용 S3 vector bucket** (`HARU_KB_VECTOR_BUCKET_ARN`) — 임베딩 저장, `s3vectors.create_vector_bucket` (T-401.5-A)
> 3. **vector index** (`HARU_KB_S3_VECTOR_INDEX_ARN`) — vector bucket 내 인덱스, `s3vectors.create_index` (T-401.5-B)
>
> KB(T-404)는 `storageConfiguration.type=S3_VECTORS`로 위 2·3을 참조하고, 데이터소스로 1을 읽는다.
>
> **플래그 패턴 (비대칭):**
> - 생성 스크립트: `--dry-run`이 **기본값**, 실제 생성은 `--apply` 명시.
> - teardown 스크립트(Phase 4.5): `--dry-run`이 **기본값**, 실제 삭제는 `--confirm` 명시.
> - 실측 확인: Titan Embeddings v2 `ACTIVE`(dim 1024), S3 Vectors 서울 리전 지원 확정.

### T-401 · 데이터소스용 일반 S3 버킷 생성 스크립트

- [ ] `scripts/kb/create_s3_bucket.py`
- [ ] 버킷 이름: `haru-kb-data-{account_id}-ap-northeast-2` (데이터소스용 '일반' 버킷)
- [ ] 버킷 정책: private, versioning 활성화, 서버측 암호화 (SSE-S3)
- [ ] Idempotent (이미 존재 시 skip)
- [ ] 플래그: `--dry-run` 기본, `--apply`로 실제 생성
- **DoD**: `--dry-run`(기본) 실행 시 아무 것도 생성 안 됨을 출력으로 확인
- **HITL**: 필수 승인 (`--apply` 실행 시 나에게 물어볼 것)
- **타임아웃**: 120초

### T-401.5 · S3 Vector Store 리소스 생성 (실측으로 신설)

#### T-401.5-A · Vector Bucket 생성

- [ ] `scripts/kb/create_vector_bucket.py`
- [ ] `s3vectors.create_vector_bucket(name="haru-kb-vectors-{account_id}")`
- [ ] stdout에 `vectorBucketArn` 출력 (→ `HARU_KB_VECTOR_BUCKET_ARN`)
- [ ] Idempotent (이미 존재 시 skip)
- [ ] 플래그: `--dry-run` 기본, `--apply`로 실제 생성
- **DoD**: `--dry-run` 시 생성 없음 확인 / `--apply` 시 ARN 출력
- **HITL**: 필수 승인
- **타임아웃**: 120초

#### T-401.5-B · Vector Index 생성

- [ ] `scripts/kb/create_vector_index.py`
- [ ] `s3vectors.create_index(vectorBucketName=..., indexName="haru-glossary", dimension=1024, dataType="float32", distanceMetric="cosine")`
- [ ] dimension=1024 — Titan Embeddings v2 차원 (실측 반영)
- [ ] stdout에 `indexArn` 출력 (→ `HARU_KB_S3_VECTOR_INDEX_ARN`)
- [ ] 플래그: `--dry-run` 기본, `--apply`로 실제 생성
- **DoD**: `--dry-run` 시 생성 없음 확인 / `--apply` 시 indexArn 출력
- **HITL**: 필수 승인
- **타임아웃**: 120초

### T-402 · 용어 사전 → JSONL 변환 스크립트

- [x] `scripts/kb/convert_glossary.py` (로컬 변환, AWS 0, 실행·검증 완료)
- [x] `/Users/westhnu/Agent/Claude/jutopia_data/data/glossary.json` → `len(glossary.json)`개 라인의 JSONL (실측 302개, 하드코딩 금지)
- [x] 출력: `backend/data/kb/glossary.jsonl` (gitignore)
- [x] 각 라인: `id=glossary_{idx:03d}`, `term`(키), jutopia 속성 보존(빈 값 생략), `source` 폴백
- **DoD**: 파일 라인 수 == `len(glossary.json)`, 스키마 검증 통과
- **HITL**: Allow Once (읽기만)
- **타임아웃**: 30초

### T-403 · JSONL을 S3에 업로드

- [ ] `scripts/kb/upload_glossary.py`
- [ ] `s3://haru-kb-.../glossary/glossary.jsonl` 업로드
- [ ] Idempotent (md5 비교)
- **DoD**: `aws s3 ls s3://haru-kb-.../glossary/` 확인
- **HITL**: 필수 승인
- **타임아웃**: 120초

### T-404 · Bedrock Knowledge Base 생성

- [ ] `scripts/kb/create_or_sync_kb.py --create` (`--dry-run` 기본, `--apply`로 실행)
- [ ] `storageConfiguration.type = "S3_VECTORS"`
- [ ] `storageConfiguration.s3VectorsConfiguration = {vectorBucketArn, indexArn, indexName}` (T-401.5 산출물 사용)
- [ ] `embeddingModelArn`: `amazon.titan-embed-text-v2:0` + `embeddingModelConfiguration`(Titan v2, dim 1024)
- [ ] Data source: 일반 S3 버킷(`HARU_KB_S3_BUCKET`)의 `glossary/` 프리픽스
- [ ] Chunking: no-chunking (용어 사전은 라인 단위가 이미 최적)
- [ ] 생성된 `kb_id`, `data_source_id`를 stdout에 표시
- **DoD**: `aws bedrock-agent get-knowledge-base --knowledge-base-id ...` → status Available
- **HITL**: 필수 승인
- **타임아웃**: 600초, 재시도 0

### T-405 · KB 데이터 소스 초기 sync

- [ ] `scripts/kb/create_or_sync_kb.py --sync --wait`
- [ ] `start_kb_sync` 호출 후 `poll_kb_sync`로 완료 대기
- **DoD**: ingestion job status == `COMPLETE`, 인덱싱된 청크 수 >= `len(glossary.json)`
- **HITL**: 필수 승인
- **타임아웃**: 900초

### T-406 · `.env` 업데이트 (수동)

- [ ] 사용자(나)가 `.env`에 다음 4개 값 입력:
  - `BEDROCK_KB_ID=`
  - `HARU_KB_S3_BUCKET=`
  - `HARU_KB_VECTOR_BUCKET_ARN=` (신규 — vector bucket)
  - `HARU_KB_S3_VECTOR_INDEX_ARN=`
- Kiro는 값을 절대 화면·로그에 노출하지 않음
- **DoD**: `env | grep BEDROCK_KB_ID` (값은 노출 X, 존재만 확인)
- **HITL**: 사용자가 직접 편집

### T-407 · Bedrock Guardrail 리소스 생성

- [ ] `scripts/guardrail/create_guardrail.py`
- [ ] REQ-GR-01의 6개 정책 등록
- [ ] 버전 DRAFT
- **DoD**: `aws bedrock get-guardrail --guardrail-identifier ...` → 정책 6종 확인
- **HITL**: 필수 승인
- **타임아웃**: 120초

### T-408 · `.env`에 `BEDROCK_GUARDRAIL_ID` 입력

- **DoD**: 앱 시작 시 `Settings` 검증 통과 확인
- **HITL**: 사용자 직접 편집

### T-409 · 커밋 (AWS 리소스 ID는 절대 커밋 X)

- [ ] `feat: scripts to bootstrap Bedrock KB and Guardrail`
- [ ] `.env`는 여전히 gitignore

---

## Phase 4.5 — Teardown 스크립트 (Phase 4 직후)

> 실측 반영 신설. 생성 리소스를 안전하게 되돌린다. 모든 삭제는 `--dry-run` 기본, `--confirm`으로만 실행.
> 삭제는 생성의 **역순**: KB → vector index → vector bucket → S3 객체 → S3 버킷.

### T-451 · `scripts/kb/teardown.py`

- [x] 역순 삭제: `delete_knowledge_base` → `s3vectors.delete_index` → `s3vectors.delete_vector_bucket` → S3 객체 삭제 → 일반 S3 버킷 삭제
- [x] 각 리소스 삭제 전 존재 확인 / 빈 설정·NotFound는 skip·성공 처리
- [x] `--dry-run` 기본(AWS 무호출), `--confirm`으로만 실제 삭제
- **DoD**: `--dry-run`(기본)에서 어떤 삭제 API도 호출되지 않음 (mock 유닛으로 검증, T-453)
- **HITL**: 필수 승인 (`--confirm` 실행 시)
- **타임아웃**: 600초

### T-452 · `scripts/guardrail/teardown.py`

- [x] `get_guardrail`로 존재 확인 후 `delete_guardrail`
- [x] `--dry-run` 기본, `--confirm`으로만 실제 삭제
- **DoD**: `--dry-run`에서 삭제 API 미호출 (mock 유닛, T-453)
- **HITL**: 필수 승인
- **타임아웃**: 120초

### T-453 · `tests/unit/test_teardown_dry_run.py`

- [x] 두 teardown이 `--dry-run` 모드에서 어떤 AWS API도 실제 호출하지 않음을 Spy로 검증 (delete·list 모두 0회)
- [x] `--confirm` 없이(플래그 생략 포함) 호출 시 dry-run으로 동작 + confirm 역순 호출 검증
- **DoD**: `pytest tests/unit/test_teardown_dry_run.py` 통과
- **HITL**: Allow Session

---

## Phase 5 — 실호출 통합 및 회귀 통과

### T-500 · 추론 프로파일 유효성 사전 확인 (실측 반영 신설)

- [ ] `aws bedrock get-inference-profile --inference-profile-identifier global.anthropic.claude-sonnet-4-5-20250929-v1:0`
- [ ] status `ACTIVE` 확인 후에만 Phase 5 진행
- [ ] Sonnet 4.5 base ID가 `LEGACY`이므로, 추론 프로파일이 유효하지 않으면 모델 ID 교체 필요 (KI-009 참조)
- **DoD**: 추론 프로파일 ACTIVE 확인 (read-only 호출)
- **HITL**: Allow Once (read-only)
- **타임아웃**: 30초

### T-501 · `BedrockClient.retrieve_and_generate` 실호출 경로

- [ ] KB_ID 존재 시 실제 `bedrock-agent-runtime.retrieve_and_generate` 호출
- [ ] `guardrailIdentifier`, `guardrailVersion` 파라미터 필수 포함
- [ ] Fake 모드는 유지 (테스트용)
- **DoD**: 실제 호출 1회, 로그에 `event=bedrock_call, status=success`
- **HITL**: 필수 승인 (실호출)
- **타임아웃**: 60초, 재시도 2

### T-502 · Guardrail 감지 및 대체 응답

- [ ] `guardrail_action=INTERVENED` 시 표준 대체 문구 반환
- [ ] `structlog`에 `event=guardrail_blocked` 로그
- [ ] `core/guardrail.py`의 코드 후처리도 유지 (이중 방어)
- **DoD**: 회귀 테스트 T-104의 4개 케이스 Green
- **HITL**: Allow Once
- **타임아웃**: 60초

### T-503 · 관측성 로그 확인

- [ ] `event=kb_retrieve`, `event=guardrail_blocked`, `event=bedrock_call` 3종 로그 기록 확인
- [ ] 유닛 테스트: 로그 캡처 후 필드 검증
- **DoD**: 유닛 3개 통과
- **HITL**: Allow Session

### T-504 · admin/kb-status 실호출 연결

- [ ] `services/kb_admin_service.py`에서 `bedrock-agent.get_knowledge_base` 호출
- [ ] 마지막 sync 시각, 청크 수, 상태 반환
- **DoD**: `curl /api/v1/admin/kb-status` → 실 KB 상태 표시
- **HITL**: Allow Once
- **타임아웃**: 30초

### T-505 · 전체 실측 curl (사용자 승인 후)

- [ ] `curl -X POST localhost:8000/api/v1/glossary/ask -d '{"query":"PER이 뭐야?"}'` → citations 1개+, disclaimer 정확
- [ ] `curl -X POST localhost:8000/api/v1/glossary/ask -d '{"query":"삼성전자를 지금 매수해도 되나요?"}'` → 대체 응답, guardrail_action="intervened"
- **DoD**: 응답 JSON을 `planning/spec-kb-guardrail-实측-log.md`에 기록
- **HITL**: 필수 승인 (실호출 2회, Bedrock 크레딧 소모)
- **타임아웃**: 60초 × 2

### T-506 · 회귀 테스트 최종 통과

- [ ] `pytest tests/regression/` 전 케이스 Green
- [ ] `pytest tests/` 전체 (Sprint 2의 100개 + 이 스펙 신규 15개+)
- **DoD**: `pytest -v` 모두 통과
- **HITL**: Allow Once
- **타임아웃**: 300초

### T-507 · 커밋 + 브랜치 병합 준비

- [ ] `feat: integrate real Bedrock KB and Guardrail (spec complete)`
- [ ] `sprint-2-log.md`와 별도로 `planning/spec-kb-guardrail-log.md` 작성
- [ ] `main` 병합 여부는 사용자에게 물어볼 것 (T-508)

### T-508 · 사용자 승인 후 `main` 병합

- [ ] fast-forward 병합
- [ ] `git tag spec-kb-and-guardrail-v1`
- **HITL**: 필수 승인

---

## Phase 6 — 후속 Agent Hooks 설정 (선택)

### T-601 · pre-commit hook

- [ ] `.pre-commit-config.yaml` 신설
- [ ] ruff, black, pytest (unit만) 자동 실행
- **DoD**: `git commit -m "test"` 시 자동 실행 확인
- **HITL**: Allow Once

### T-602 · Kiro Agent Hook — 파일 저장 시 회귀 실행

- [ ] `core/guardrail.py` 저장 시 `pytest tests/regression/` 자동 실행
- [ ] `services/hantu_readonly.py` 저장 시 원칙 4 검증 자동
- **DoD**: 파일 저장 후 자동 실행 로그 확인
- **HITL**: Allow Session

---

## 완료 정의 (Definition of Done for this Spec)

이 스펙 전체가 완료됐다고 판단하는 종합 기준:

1. ✅ `.env` 5개 신규 키 모두 설정, prod에서 앱 정상 시작
2. ✅ Bedrock KB에 `len(glossary.json)`개(실측 302) 용어 인덱싱 완료, admin 엔드포인트로 확인 가능
3. ✅ Guardrail 리소스 존재, 6개 정책 적용, 실호출 시 `guardrailIdentifier` 파라미터 포함
4. ✅ `POST /api/v1/glossary/ask` 정상 질의 → citations 포함 응답 (실측)
5. ✅ 위험 질의 → Guardrail 차단 → 표준 대체 문구 (실측)
6. ✅ 회귀 테스트 4종 Green, 전체 pytest Green
7. ✅ 관측성 로그 3종 확인
8. ✅ 브랜치 `spec/bedrock-kb-and-guardrail` → `main` fast-forward 병합
9. ✅ `planning/spec-kb-guardrail-log.md` 작성 (실측 값, 결정 로그, KI 추가)

## 크레딧 절약 팁 (강사 §Kiro Power 반영)

- Kiro Power에서 이 스펙 실행 시 활성화할 도구:
  - `boto3` (Phase 2, 4, 5)
  - `pytest` (Phase 1, 2, 3, 5)
- **비활성화**: Notion, Canva, Playwright, Figma 등 (이 스펙과 무관)
- 각 Phase 시작 전 Kiro Power에서 필요한 도구만 켜기

## Out of Scope (재확인)

- 종목 워크북 KB
- 사용자 원칙 KB
- RAGAS 자동 평가
- AgentCore 이관
- 프론트엔드
