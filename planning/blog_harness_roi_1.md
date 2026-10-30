# 하네스 ROI #1 — AWS Bedrock KB + S3 Vectors 통합에서 포획한 7개 설계 결함

> Haru 프로젝트 Phase ⑥ (bedrock-kb-and-guardrail) 회고.
> 작성: 2026-10-31. 블로그·이력서·면접 재료 완성형.

## 제목 후보 (3개 중 택 1)

1. "AWS Bedrock Knowledge Base + S3 Vectors 통합에서 하네스가 막아낸 7개 설계 결함"
2. "운영 비용 $0으로 Bedrock KB 구축하기 — Spec-Driven Development + Human-in-the-Loop 실전"
3. "`--dry-run`/`--apply` 하네스로 AWS Bedrock KB의 숨은 함정 7개를 전부 포획한 과정"

---

## TL;DR

Bedrock Knowledge Base + S3 Vectors + Guardrail을 **Spec-Driven Development + Human-in-the-Loop 하네스**로 구축하면서, 설계 리뷰로는 포착 불가능한 **7건의 아키텍처 drift를 운영 환경 도달 전 전부 포획**했다. 각 drift는 코드 수정 + 회귀 테스트 + known-issues 등재로 재발 차단. 전체 사이클의 **운영 비용 $0, 사용자 체감 장애 0, 데이터 손실 0**.

**최종 수치:**

- 302 docs 전부 색인 완료 (실패 0)
- 임베딩 실 ingestion 65초, 비용 ~$0.0016
- 모든 KI에 회귀 테스트 (단위 테스트 184 passed, 5 skipped)
- 총 7개 drift가 사용자 환경 도달 전 코드로 수렴

---

## 왜 중요한가 — "AI와 함께 짓는 AWS 인프라"의 안전장치

Kiro·Claude Code 같은 AI 에이전트에게 AWS 리소스 생성을 맡기면 가장 큰 리스크는 **"반환됐으니 됐겠지"**로 넘어가는 silent failure다. API는 성공 응답을 돌려줬지만:

- 생성된 리소스가 설계와 미묘하게 다른 상태 (예: `indexName`과 `indexArn`을 **둘 다** 넘기면 reject)
- 비동기 상태라 호출 시점엔 아직 사용 불가 (예: KB status=CREATING)
- 숨은 바이트 한도에 걸려 데이터 일부만 색인 (예: filterable metadata 2048B)

이런 drift는 **설계 리뷰·mock 테스트로는 전혀 안 보인다.** 실 API 호출에서만 드러난다.

그래서 하네스가 필요하다:

- **`--dry-run` 기본, `--apply` 명시** — 모든 생성 스크립트가 기본으론 아무 호출도 하지 않음
- **각 단계 사람 승인 체크포인트** — AI가 혼자 끝까지 질주하지 못하게
- **외부 호출 직전 read-only 재확인** — 상태 변화를 눈으로 1회 더 검증
- **fail-fast + raw 로그 보고** — 자동 재시도·우회 금지

---

## 7개 KI 서사

### KI-010 — `indexArn`과 `indexName` 동시 전달 금지

- Bedrock KB의 `s3VectorsConfiguration`은 둘 중 하나만 받음. 공식 문서엔 상호 배타성 명시 안 됨.
- 1차 `--apply`에서 1초만에 `ValidationException`으로 fail-fast. 리소스 미생성, 비용 $0.
- 수정: kwargs에서 `indexName` 제거, 회귀 테스트로 "indexArn만 있고 indexName은 없음" 영구 단언.

### KI-011 — `sync`가 방금 만든 DS ID를 버리고 다시 조회

- `start_ingestion_job` 전에 `list_data_sources`로 ds_id를 다시 찾는 안티패턴. 운영 IAM에 `bedrock:ListDataSources` 권한이 없으면 즉시 AccessDenied.
- 수정: `create`가 반환한 ds_id를 `sync`에 직접 전달. 결과적으로 **happy path에서 ListDataSources 권한 불필요** → 최소 권한 원칙 준수.

### KI-012 — Teardown 스크립트가 all-or-nothing 설계

- 운영에서는 "KB만 롤백"처럼 부분 롤백 요구가 더 흔한데, teardown이 전체 스택을 지우도록 돼 있었다. dry-run이 사전에 포획해서 실제 삭제는 ad-hoc `delete-knowledge-base`로 대체.
- 근본 해결은 `--scope {kb-only, vector-only, s3-only, all}` 플래그 리팩토링으로 Phase 6에 예약 등재.
- 교훈: **IaC의 "되돌리기"는 생성과 대칭적이면 좋지만, 운영에선 비대칭적 부분 롤백이 필요하다.**

### KI-013 — KB가 ACTIVE 되기 전에 ingestion 시작 → ConflictException

- `create_knowledge_base`는 비동기. 반환 즉시 `CREATING` 상태라 `start_ingestion_job`이 거부됨.
- 수정: `_wait_kb_active(timeout=120s, interval=2s)` 폴링. CREATING→ACTIVE 대기, FAILED→즉시 RuntimeError.
- 교훈: **AWS 비동기 리소스에서 "반환 == 사용 가능"이 아니다.** 상태 폴링은 선택이 아니라 필수.

### KI-014 — 폴링에 `dataSourceId` 누락 → ParamValidationError

- `start_ingestion_job`은 `knowledgeBaseId + dataSourceId`를 받는데, `get_ingestion_job`도 둘 다 필수인 걸 Phase 2 Fake 테스트에선 몰랐다.
- 수정: `poll_sync(kb_id, job_id, *, data_source_id)` keyword-only 필수 추가.
- 교훈: **Mock은 메서드 존재 여부만 검증한다. 실 API 파라미터 스키마는 contract test나 실호출로만 검증 가능.**

### KI-015 — JSONL blob 1개 = KB 문서 1개 → 50KB 초과

- 302줄 JSONL을 하나의 파일로 올렸더니, Bedrock KB는 "파일 1개 = 문서 1개"로 취급. 194KB 단일 문서가 되어 50KB 한도 거부.
- 수정: 302개 개별 `.txt`로 재설계 (`term_001.txt`~`term_302.txt`). 각 용어 최대 ~3KB.
- 설계 승격: chunking=NONE이 "용어 경계 보존"이라는 원래 설계 의도와 1:1로 맞음. Citation granularity 302배 개선.

### KI-016 — S3 Vectors의 filterable metadata 2048B 한도

- 50KB 통과했지만 두 번째 숨은 한도 발견. filterable metadata는 2048B/벡터, non-filterable은 40KB/벡터.
- 302개 중 158개(> 2048B) 색인 실패.
- 수정: `metadataConfiguration.nonFilterableMetadataKeys=["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"]`로 index 재생성. AWS 공식 kb-chunking 가이드와 일치.
- 교훈: **벡터 스토어마다 metadata 모델이 다르다. "검색 가능 필드"에 숨은 바이트 한도가 있을 수 있다.**

---

## 하네스 ROI 수치

| 시도 | 결과 | 소요 | 비용 | 발견 |
|---|---|---|---|---|
| 1차 | fail-fast | 1s | $0 | KI-010 |
| 2차 | 부분 성공 | 1s | $0 | KI-011 |
| Teardown #1 | 성공 | 2m | $0 | KI-012 |
| 3차 | 부분 성공 | 5s | $0 | KI-013 |
| 3차 재개 | FAILED (50KB) | 4s | $0 | KI-014, KI-015 |
| 4차 재개 | 144/302 | 76s | ~$0.001 | KI-016 |
| Teardown #2 + Rebuild | 성공 | 3m | $0 | — |
| **5차 재개** | **302/302 COMPLETE** | **65s** | **~$0.0016** | — |

- **총 drift: 7건**, 전부 운영 환경 도달 전 포획
- **총 운영 비용: < $0.01** (임베딩 실측 합)
- **사용자 체감 장애: 0**, **데이터 손실: 0**
- 각 drift에 회귀 테스트 추가 (184 passed, 재발 영구 차단)

---

## 교훈 3가지

1. **"반환 성공" ≠ "작업 완료"** — AWS의 비동기 리소스, 숨은 한도, 상호 배타적 파라미터는 설계 리뷰로 안 잡힌다. 실 API 호출에서만 드러난다.
2. **최소 권한은 돈이 아니라 설계 품질 지표다** — "방금 만든 ID를 다시 조회하는 코드"는 안티패턴이면서 동시에 불필요한 IAM 권한을 요구한다. 코드 품질이 올라가면 권한도 줄어든다.
3. **하네스는 생산성 저하가 아니다** — 매 단계 사람 승인·`--dry-run`·raw 로그 보고가 "느려 보여도", 7건 drift를 전부 사용자 환경 도달 전에 잡아서 **운영 롤백 비용을 $0으로 만들었다**. 하네스는 **ROI 양의 보험**이다.

---

## 다음 단계

- Phase ⑦ Guardrail 생성 (6종 정책, 비슷한 하네스 패턴)
- Phase 5 실측·회귀·RAGAS 세팅 (**이번 블로그의 7개 수치가 다음 블로그 7개 품질 수치로 이어짐**: Faithfulness, Context Precision, Guardrail block rate 등)
- KI-012 teardown `--scope` 리팩토링 (Phase 6)

---

## 이력서 bullet 완성형

### 한 줄 버전

> AWS Bedrock Knowledge Base + S3 Vectors + Guardrail을 Spec-Driven Development 기반으로 구축. `--dry-run`/`--apply`/`--confirm` 비대칭 하네스로 **7건의 설계 drift를 운영 환경 도달 전 전부 포획**, 각 drift에 회귀 테스트 영구 등재. 302 docs 색인 완료, **운영 롤백 비용 $0 / 사용자 체감 장애 0**, 전체 비용 < $0.01.

### 3줄 버전

> **AI 에이전트와 AWS 인프라 공동 구축** — Kiro(Spec-Driven Development) + Claude Code 환경에서 Bedrock KB(S3 Vectors) + Guardrail 백엔드 설계·구현.
> **하네스 엔지니어링** — `--dry-run`/`--apply`/`--confirm` 비대칭 플래그 + 사람 승인 체크포인트 + fail-fast raw 보고로 7건 아키텍처 drift(KI-010~016)를 운영 도달 전 전부 포획.
> **품질 지표** — 302 docs 100% 색인 (실패 0), 임베딩 ~65초/$0.0016, 전체 운영 롤백 비용 $0, 회귀 테스트 184 passed로 재발 영구 차단.

---

## 면접 스토리 (STAR 포맷)

**Q: "AI 에이전트와 함께 작업할 때 가장 신경 쓴 안전장치는?"**

- **Situation**: Kiro·Claude Code에게 AWS Bedrock KB 생성을 맡겨야 하는데, API 성공 응답과 실제 설계 일치를 구분할 방법이 없었다.
- **Task**: AI가 혼자 끝까지 질주하지 못하도록 하면서, 설계 리뷰로 못 잡는 drift를 조기 포획하는 하네스 설계.
- **Action**: `--dry-run` 기본 + `--apply` 명시 + `--confirm` teardown 비대칭 플래그, 각 외부 호출 전 read-only 재확인, fail-fast + raw 로그 보고. AI에게는 "자동 재시도 금지, 각 단계 멈춤 지점에서 사람 승인 받기"를 지시서에 명시.
- **Result**: KB 구축 중 7건 drift(KI-010~016)를 전부 운영 환경 도달 전 포획. 각 drift에 회귀 테스트 영구 등재. 전체 운영 롤백 비용 $0, 사용자 체감 장애 0.
