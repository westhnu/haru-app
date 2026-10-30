# Requirements — Bedrock Knowledge Base & Guardrail 실물화

## Introduction

Sprint 2 완료 시점의 Haru 백엔드는 Bedrock 파운데이션 모델은 실호출하지만, RAG 파이프라인은 mock 응답이고 Guardrail은 코드 후처리만 존재한다. 이 스펙은 **강의 §RAG와 §Guardrail을 그대로 실물화**하여:

1. Bedrock Knowledge Base (S3 벡터스토어)에 glossary.json의 모든 용어 사전을 인덱싱하고
2. Bedrock Guardrail 리소스를 생성해 원칙 1·5를 상위 방어층으로 강제하며
3. 기존 코드 가드레일과 이중 방어를 이루도록 통합한다.

## 참조 문서

- 기획안 §13.3 KB 전략, §13.5 Guardrail 정책, §13.6 RAGAS
- steering: `product.md`, `tech.md`, `principles.md`, `structure.md`
- 강의 대본 §RAG, §Guardrail (Bedrock 실물 리소스 사용)

## User Stories

### US-1 — 용어 사전 KB 조회 (일반 사용자)

**AS AN** 워크북에서 모르는 용어를 발견한 사용자,
**I WANT** 그 용어를 질의하면 KB에서 검색된 정의를 인용과 함께 받고 싶다,
**SO THAT** 문맥에서 벗어나지 않고 학습할 수 있다.

### US-2 — 종목 요약 응답 안전성 (일반 사용자)

**AS A** 종목 요약을 요청한 사용자,
**I WANT** AI 응답에 매수·매도 권유 표현이 절대 포함되지 않기를,
**SO THAT** 오해 없이 의사결정 자료로 쓸 수 있다.

### US-3 — 관리자 관측성 (프로덕트 오너)

**AS A** Haru 프로덕트 오너,
**I WANT** KB 검색 hit/miss와 Guardrail 차단 이벤트를 로그로 볼 수 있기를,
**SO THAT** 서비스 품질과 원칙 준수 여부를 지속 모니터링할 수 있다.

### US-4 — 환경 격리 (개발자)

**AS A** Haru 개발자,
**I WANT** prod 환경에서 KB·Guardrail 리소스 ID가 미설정이면 앱이 시작조차 되지 않기를,
**SO THAT** 안전장치 없는 배포가 원천 차단된다.

### US-5 — 폴백 동작 (개발자)

**AS A** local·dev 환경 개발자,
**I WANT** KB/Guardrail이 없어도 mock 응답으로 계속 개발할 수 있기를,
**SO THAT** AWS 없이도 프론트엔드·다른 서비스 개발이 막히지 않는다.

---

## Acceptance Criteria (EARS)

### KB 구축

**REQ-KB-01** WHEN 배포 스크립트가 실행되면, THE SYSTEM SHALL S3 버킷 (`HARU_KB_S3_BUCKET`)에 `glossary/` 프리픽스로 glossary.json의 모든 용어 문서를 JSON Lines 형식으로 업로드해야 한다.

**REQ-KB-02** WHEN 사용자가 관리자 CLI로 `sync-kb` 명령을 실행하면, THE SYSTEM SHALL Bedrock Knowledge Base 데이터 소스 동기화를 트리거하고 상태를 폴링하여 `Available` 완료를 확인해야 한다.

**REQ-KB-03** IF S3 벡터스토어 인덱스가 존재하지 않으면, THE SYSTEM SHALL Titan Text Embeddings v2로 새 인덱스를 자동 생성해야 한다.

### RAG 응답

**REQ-RAG-01** WHEN 사용자가 `POST /api/v1/glossary/ask`로 용어 질의를 보내면, THE SYSTEM SHALL Bedrock `RetrieveAndGenerate` API를 호출하여 KB 근거를 포함한 응답을 반환해야 한다.

**REQ-RAG-02** THE SYSTEM SHALL 모든 응답의 `citations[]` 필드에 최소 1개 이상의 KB 청크 참조(청크 텍스트 스니펫, 원본 문서 경로)를 포함해야 한다.

**REQ-RAG-03** IF 검색 결과가 임계치(similarity < 0.5) 미만이면, THE SYSTEM SHALL LLM 일반지식으로 답변하되 `source: "general_knowledge"` 태그를 응답에 명시해야 한다.

**REQ-RAG-04** WHEN 컨텍스트 타입이 `stock`(재무·종목 요약)이고 KB 근거를 찾지 못하면, THE SYSTEM SHALL "확인된 자료가 없습니다" 대체 문구를 반환하고 LLM 일반지식을 사용하지 말아야 한다. (원칙 2)

### Guardrail

**REQ-GR-01** WHEN 배포 스크립트가 실행되면, THE SYSTEM SHALL Bedrock Guardrail 리소스를 생성하고 다음 정책 6종을 등록해야 한다:
- Denied Topic: `종목 매수·매도 권유`
- Denied Topic: `미래 가격·수익률 보장`
- Word Filter: `리딩방`, `한 방`, `보장`, `무조건 수익`
- Sensitive Info Filter: 주민번호·계좌·카드 번호 마스킹
- Content Filter: Hate/Sexual/Violence 상 수준
- Contextual Grounding: threshold 0.75

**REQ-GR-02** WHEN 모든 Bedrock 호출은 `guardrailIdentifier`와 `guardrailVersion` 파라미터를 반드시 포함해야 한다.

**REQ-GR-03** WHEN Guardrail이 응답을 차단하거나 수정하면, THE SYSTEM SHALL `structlog`에 `guardrail_action`, `blocked_categories` 필드로 기록해야 한다.

**REQ-GR-04** IF Bedrock Guardrail이 차단한 응답이라도, THE SYSTEM SHALL 표준 대체 문구("본 서비스는 종목 추천을 제공하지 않습니다. 판단은 본인에게 있습니다.")를 사용자에게 반환해야 한다.

**REQ-GR-05** THE SYSTEM SHALL 코드 `core/guardrail.py`의 후처리 필터를 유지하여 Bedrock Guardrail과 이중 방어를 이루어야 한다. (원칙 1 이중 방어)

### 환경 격리

**REQ-ENV-01** WHEN `APP_ENV=prod`이고 `BEDROCK_KB_ID` 또는 `BEDROCK_GUARDRAIL_ID`가 빈 값이면, THE SYSTEM SHALL 앱 시작 시점에 `ValueError`를 발생시켜 uvicorn이 뜨지 않아야 한다.

**REQ-ENV-02** WHEN `APP_ENV`가 `local`/`dev`이고 `BEDROCK_KB_ID`가 미설정이면, THE SYSTEM SHALL mock RAG 응답을 반환하되 응답에 `is_mock: true`를 표기해야 한다.

**REQ-ENV-03** THE SYSTEM SHALL `.env.example`에 `HARU_KB_S3_BUCKET`, `HARU_KB_S3_VECTOR_INDEX_ARN`, `BEDROCK_KB_ID`, `BEDROCK_GUARDRAIL_ID`, `BEDROCK_GUARDRAIL_VERSION` 5개 키를 예시 값 없이 추가해야 한다.

### 관측성

**REQ-OBS-01** THE SYSTEM SHALL 모든 KB 호출에 대해 `event=kb_retrieve`, `latency_ms`, `hit_count`, `avg_similarity`를 로그해야 한다.

**REQ-OBS-02** THE SYSTEM SHALL Guardrail 차단 이벤트를 `event=guardrail_blocked`, `category`, `reason`으로 로그해야 한다.

**REQ-OBS-03** THE SYSTEM SHALL `GET /api/v1/admin/kb-status`로 KB 상태와 마지막 동기화 시각을 조회할 수 있게 해야 한다. (관리자 인증은 이 스펙 범위 밖, 향후 스프린트)

---

## Out of Scope (명시)

이 스펙에서 다루지 않는 것:

- 종목 워크북 KB (Sprint 3 이후, 별도 스펙)
- 사용자별 개인 원칙 KB (Sprint 4 이후, 별도 스펙)
- RAGAS 자동 평가 파이프라인 (별도 스펙 `ragas-quality-pipeline` 예정)
- AgentCore Runtime 이관 (M4 이후)
- 관리자 인증 (Sprint 5 이후)
- 프론트엔드 (Sprint 3)

## 성공 기준

이 스펙이 완료됐다고 판단하는 실측 기준:

1. `curl POST /api/v1/glossary/ask -d '{"query":"PER이 뭐야?"}'` → 응답 `answer`에 정의 포함, `citations[]` 최소 1개, `disclaimer` 정확
2. `curl POST /api/v1/glossary/ask -d '{"query":"삼성전자를 지금 매수해도 되나요?"}'` → Guardrail 차단, 표준 대체 문구, `guardrail_action` 로그
3. `APP_ENV=prod uv run uvicorn app.main:app` → KB_ID 미설정 상태에서 앱 시작 실패
4. 회귀 테스트 (`tests/regression/test_guardrail_bedrock.py`) 4개 이상 신설, 모두 통과
5. `pytest` 전체 통과 (Sprint 2의 100개 + 이 스펙 추가 15개 이상)

## 리스크와 완화

| 리스크 | 완화책 |
|---|---|
| S3 Vector Store 신규 GA 기능이라 API 변화 가능 | boto3 최소 버전 `>=1.35.0` 명시, 호출 코드는 단일 파일에 격리 |
| Guardrail Contextual Grounding 오탐 (false positive) | threshold를 config로 노출, prod 모니터링 후 조정 |
| KB 인덱싱 시간 지연 (수 분) | `sync-kb` 명령을 idempotent하게, `--wait` 옵션으로 폴링 |
| Bedrock use case 승인 재확인 필요 | 사용자 계정에서 승인 상태를 사전 확인 (Sprint 2에서 완료) |
