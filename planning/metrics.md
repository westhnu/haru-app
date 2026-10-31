# Haru 실측 지표

> 날짜·명령어·결과 세트로 적립. 재구성 금지.

## 2026-10-31 KB apply — KI-010 사이클
### 1차 시도 (실패, fail-fast)
- 명령: `uv run python scripts/kb/create_or_sync_kb.py --create --sync --apply`
- 결과: ValidationException "Vector index name should not be present with namespace arn"
- 소요: 1초
- 비용: $0 (리소스 미생성)
- 발견: KI-010 (`indexArn` ⊕ `indexName` 상호 배타)
- 하네스가 막은 것: 설계 drift가 운영 환경에 도달
- 수정 커밋: 97ac11d
- 수정 소요: 코드 1줄 + 회귀 테스트 1건 + 문서 3곳

### 2차 시도 (부분 성공, KI-011 발견)
- 명령: `--create --sync --apply`
- 생성 성공: KB=XBBETDQEY4, DS=LPMVBACVJ0 (KI-010 수정 검증됨)
- 실패 지점: sync → `_resolve_ds_id` → `list_data_sources`
- 에러: AccessDeniedException (`bedrock:ListDataSources`)
- 소요: ~1초 (fail-fast at sync; 16:08:11Z→16:08:12Z)
- 비용: $0 (ingestion 전이라 임베딩 발생 없음)
- 발견: KI-011
- 교훈: create가 반환한 ID를 sync에서 버리는 안티패턴 → 최소권한 원칙 위반

### Teardown (KI-011 사이클 종료, KI-012 발견)
- 방식: ad-hoc `delete-knowledge-base` (teardown.py 범위 불일치로 미사용)
- 삭제: KB XBBETDQEY4 (DS LPMVBACVJ0 cascade)
- 보존: vector bucket, vector index, S3 데이터 버킷 (멱등성 재사용 예정)
- 비용: $0
- 발견: KI-012 (teardown all-or-nothing 설계)
- 완료 시각: 2026-10-30T16:21:13Z

### 3차 시도 (KI-011 수정 적용, fresh --apply)
- 명령: `--create --sync --apply`
- 결과: (대기 중)

### 3차 시도 (fresh, KI-010/011 수정 반영)
- 시작: 2026-10-30T16:22:35Z
```
2026-10-31 01:22:36 [info     ] create_step                    dry_run=False resource_id=LEWVDQRRRK resource_type=knowledge_base result=created
2026-10-31 01:22:36 [info     ] create_step                    dry_run=False resource_id=FWRJAYJRK6 resource_type=data_source result=created
KB: LEWVDQRRRK / dataSource: FWRJAYJRK6
→ .env에 추가: BEDROCK_KB_ID=LEWVDQRRRK
2026-10-31 01:22:37 [error    ] kb_sync_start_failed           error_type=ConflictException
Traceback (most recent call last):
  File "/Users/westhnu/Agent/Claude/haru_web/backend/app/services/kb_admin_service.py", line 59, in start_sync
    response = client.start_ingestion_job(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/.venv/lib/python3.12/site-packages/botocore/client.py", line 606, in _api_call
    return self._make_api_call(operation_name, kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/.venv/lib/python3.12/site-packages/botocore/context.py", line 123, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/.venv/lib/python3.12/site-packages/botocore/client.py", line 1094, in _make_api_call
    raise error_class(parsed_response, operation_name)
botocore.errorfactory.ConflictException: An error occurred (ConflictException) when calling the StartIngestionJob operation: You cannot start an ingestion job on a knowledgeBase with status CREATING.

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/westhnu/Agent/Claude/haru_web/backend/scripts/kb/create_or_sync_kb.py", line 256, in <module>
    sys.exit(main())
             ^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/scripts/kb/create_or_sync_kb.py", line 251, in main
    ok = run(dry_run=not args.apply, do_create=args.create, do_sync=args.sync)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/scripts/kb/create_or_sync_kb.py", line 236, in run
    results.append(_do_sync(dry_run, agent, settings, kb_id=created_kb_id, ds_id=created_ds_id))
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/scripts/kb/create_or_sync_kb.py", line 206, in _do_sync
    job_id = admin.start_sync(effective_kb, effective_ds)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/app/services/kb_admin_service.py", line 64, in start_sync
    raise BedrockRetrievalError("KB sync 시작 실패") from exc
app.services.exceptions.BedrockRetrievalError: KB sync 시작 실패
```
- 종료: 2026-10-30T16:22:37Z

### 3차 재개 (KI-013 수정 반영, 멱등 재사용)
- 재개 시작: 2026-10-30T16:32:08Z
- 재사용 대상: KB LEWVDQRRRK, DS FWRJAYJRK6

```
2026-10-31 01:32:09 [info     ] create_step                    dry_run=False resource_id=LEWVDQRRRK resource_type=knowledge_base result=already_exists
KB already_exists, reusing: LEWVDQRRRK
2026-10-31 01:32:09 [info     ] kb_wait_active                 elapsed_s=0.1 kb_id=LEWVDQRRRK status=ACTIVE
2026-10-31 01:32:09 [info     ] create_step                    dry_run=False resource_id=FWRJAYJRK6 resource_type=data_source result=already_exists
dataSource already_exists, reusing: FWRJAYJRK6
KB: LEWVDQRRRK / dataSource: FWRJAYJRK6
→ .env에 추가: BEDROCK_KB_ID=LEWVDQRRRK
2026-10-31 01:32:10 [info     ] kb_sync_started                ingestion_job_id=XMUUKHIRZP kb_id=LEWVDQRRRK
2026-10-31 01:32:10 [error    ] kb_sync_poll_failed            error_type=ParamValidationError
Traceback (most recent call last):
  File "/Users/westhnu/Agent/Claude/haru_web/backend/app/services/kb_admin_service.py", line 90, in _fetch_ingestion_status
    response = client.get_ingestion_job(
               ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/.venv/lib/python3.12/site-packages/botocore/client.py", line 606, in _api_call
    return self._make_api_call(operation_name, kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/.venv/lib/python3.12/site-packages/botocore/context.py", line 123, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/.venv/lib/python3.12/site-packages/botocore/client.py", line 1051, in _make_api_call
    request_dict = self._convert_to_request_dict(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/.venv/lib/python3.12/site-packages/botocore/client.py", line 1118, in _convert_to_request_dict
    request_dict = self._serializer.serialize_to_request(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/.venv/lib/python3.12/site-packages/botocore/validate.py", line 424, in serialize_to_request
    raise ParamValidationError(report=report.generate_report())
botocore.exceptions.ParamValidationError: Parameter validation failed:
Missing required parameter in input: "dataSourceId"

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/Users/westhnu/Agent/Claude/haru_web/backend/scripts/kb/create_or_sync_kb.py", line 295, in <module>
    sys.exit(main())
             ^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/scripts/kb/create_or_sync_kb.py", line 290, in main
    ok = run(dry_run=not args.apply, do_create=args.create, do_sync=args.sync)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/scripts/kb/create_or_sync_kb.py", line 275, in run
    results.append(_do_sync(dry_run, agent, settings, kb_id=created_kb_id, ds_id=created_ds_id))
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/scripts/kb/create_or_sync_kb.py", line 246, in _do_sync
    status = admin.poll_sync(effective_kb, job_id)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/app/services/kb_admin_service.py", line 81, in poll_sync
    status = self._fetch_ingestion_status(client, kb_id, ingestion_job_id)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru_web/backend/app/services/kb_admin_service.py", line 95, in _fetch_ingestion_status
    raise BedrockRetrievalError("KB sync 폴링 실패") from exc
app.services.exceptions.BedrockRetrievalError: KB sync 폴링 실패
```
- 재개 종료: 2026-10-30T16:32:10Z
- sync 소요(초): 2

### ad-hoc ingestion job 상태 확인 (get-ingestion-job, read-only)
```json
{
  "ingestionJob": {
    "knowledgeBaseId": "LEWVDQRRRK",
    "dataSourceId": "FWRJAYJRK6",
    "ingestionJobId": "XMUUKHIRZP",
    "status": "FAILED",
    "statistics": {
      "numberOfDocumentsScanned": 1,
      "numberOfNewDocumentsIndexed": 0,
      "numberOfDocumentsFailed": 1
    },
    "failureReasons": [
      "Malformed input request: expected maxLength: 50000, actual: 194198 ... file: glossary/glossary.jsonl"
    ],
    "startedAt": "2026-10-30T16:32:10Z",
    "updatedAt": "2026-10-30T16:32:14Z"
  }
}
```
- status: FAILED
- 실 ingestion 소요: startedAt 16:32:10 → updatedAt 16:32:14 = 4초
- 스캔: 1 document (파일 전체를 1개 문서로 인식), 색인 성공 0, 실패 1
- 원인: single document maxLength 50,000자 초과 (실제 194,198자) — glossary.jsonl 전체가 1개 문서로 처리됨
- 비용: $0 (임베딩 호출 전 입력 검증에서 실패)

### 3차 재개 ingestion FAILED 분석
- job id: XMUUKHIRZP
- 실 ingestion: 4초 (16:32:10 → 16:32:14, 즉시 실패)
- numberOfDocumentsScanned: 1 (예상 302)
- failureReason: maxLength 50000 초과 (actual 194198)
- 비용: $0 (임베딩 호출 전 검증 실패)
- 발견 KI: KI-014 (폴링 버그, 이번 블록에서 수정), KI-015 (적재 전략, 다음 블록에서 구현)

### 4차 재개 — KI-015 수정 반영, 302 txt 재적재 후 ingestion
- 시작: 2026-10-30T16:58:17Z
```
2026-10-31 01:58:17 [info     ] create_step                    dry_run=False resource_id=LEWVDQRRRK resource_type=knowledge_base result=already_exists
KB already_exists, reusing: LEWVDQRRRK
2026-10-31 01:58:17 [info     ] kb_wait_active                 elapsed_s=0.1 kb_id=LEWVDQRRRK status=ACTIVE
2026-10-31 01:58:17 [info     ] create_step                    dry_run=False resource_id=FWRJAYJRK6 resource_type=data_source result=already_exists
dataSource already_exists, reusing: FWRJAYJRK6
KB: LEWVDQRRRK / dataSource: FWRJAYJRK6
→ .env에 추가: BEDROCK_KB_ID=LEWVDQRRRK
2026-10-31 01:58:18 [info     ] kb_sync_started                ingestion_job_id=R6QMUSL1AU kb_id=LEWVDQRRRK
sync 완료: job=R6QMUSL1AU status=COMPLETE
```
- 종료: 2026-10-30T16:59:49Z

### 5차 재개 — KI-016 수정 반영 (nonFilterableMetadataKeys), index/KB/DS 재생성 후 ingestion
- 시작: 2026-10-30T17:34:23Z
```
2026-10-31 02:34:24 [info     ] create_step                    dry_run=False resource_id=ITEUSMR3IL resource_type=knowledge_base result=created
2026-10-31 02:34:24 [info     ] kb_wait_active                 elapsed_s=0.1 kb_id=ITEUSMR3IL status=CREATING
2026-10-31 02:34:26 [info     ] kb_wait_active                 elapsed_s=2.2 kb_id=ITEUSMR3IL status=ACTIVE
2026-10-31 02:34:26 [info     ] create_step                    dry_run=False resource_id=TICYPXTCJQ resource_type=data_source result=created
KB: ITEUSMR3IL / dataSource: TICYPXTCJQ
→ .env에 추가: BEDROCK_KB_ID=ITEUSMR3IL
2026-10-31 02:34:27 [info     ] kb_sync_started                ingestion_job_id=WUK6SJJHKB kb_id=ITEUSMR3IL
sync 완료: job=WUK6SJJHKB status=COMPLETE
```
- 종료: 2026-10-30T17:35:43Z

### 5차 재개 — 요약 (성공, Phase ⑥ 완결)
- 새 KB id: ITEUSMR3IL
- 새 DS id: TICYPXTCJQ
- Ingestion job: WUK6SJJHKB, status=COMPLETE
- Docs scanned: 302
- Docs indexed: 302
- Docs failed: 0
- 실 ingestion 소요: 65초 (17:34:27 → 17:35:32 UTC)
- 임베딩 비용 실측: 실측 미획득(응답에 토큰 수 없음), 사전 추정 ~$0.0016 (302 docs × Titan v2)
- KI-010 검증: indexName 미전달 ✓
- KI-011 검증: list_data_sources 직접 호출 0회 ✓
- KI-013 검증: kb_wait_active CREATING(0.1s)→ACTIVE(2.2s) ✓
- KI-014 검증: poll_sync에 dataSourceId 포함, 폴링 성공 ✓
- KI-015 검증: numberOfDocumentsScanned=302 (파일=문서 1:1) ✓
- KI-016 검증: indexed=302 / failed=0 (nonFilterableMetadataKeys로 2048B 한도 회피) ✓

### 하네스 ROI 통합 요약 (Phase ⑥ KB 구축 전 사이클)

| 시도 | 결과 | 소요 | 비용 | 발견 KI | 수정 방식 |
|---|---|---|---|---|---|
| 1차 --apply | ValidationException | 1s | $0 | KI-010 (indexArn⊕indexName) | 코드 1줄 + 회귀 테스트 |
| 2차 --apply | AccessDenied | 1s | $0 | KI-011 (sync가 list_data_sources 재호출) | 리팩토링 + 회귀 테스트 |
| Teardown #1 | KB cascade | ~2m | $0 | KI-012 (teardown all-or-nothing) | Phase 6 리팩토링 예약 |
| 3차 --apply | ConflictException | <5s | $0 | KI-013 (KB ACTIVE 대기 누락) | _wait_kb_active + 테스트 3건 |
| 3차 재개 | ingestion FAILED (50KB) | 4s | $0 | KI-014 (poll dataSourceId 누락), KI-015 (JSONL blob 50KB) | 폴링 수정 + 302 txt 재설계 |
| 4차 재개 | 부분 성공 (144/302) | 76s | ~$0.001 | KI-016 (2048B filterable) | nonFilterableMetadataKeys 지정 |
| Teardown #2 + Rebuild | index/KB/DS 재생성 | ~3m | $0 | — | — |
| 5차 재개 | 302/302 COMPLETE | 65s | ~$0.0016 | — | — |
| Phase ⑦ 1차 --apply | ValidationException | 1s | $0 | KI-017 (KR_RRN enum 미지원) | regexesConfig 전환 + 회귀 테스트 |
| Phase ⑦ 재 apply | 성공 | ~1s | $0 | — | — |

- 총 발견 drift: **8건** (KI-010 ~ KI-017)
- 모든 drift가 운영 환경 도달 전 포획 (사용자 체감 장애 0, 데이터 손실 0)
- 전체 사이클 운영 롤백 비용: $0 (임베딩 실측 총합 < $0.01)
- 하네스 설계 요소: --dry-run 기본 / --apply 명시 / --confirm teardown / 각 단계 사람 승인 체크포인트 / 외부 호출 전 read-only 재확인 / fail-fast with raw 로그
- 수정 방식: 8건 중 7건 코드 수정 + 회귀 테스트 + known-issues 등재. KI-012는 Phase 6 리팩토링(T-603) 예약.

### Phase ⑥ 완료 후 .env 반영 필요 (사용자 직접)
- BEDROCK_KB_ID=ITEUSMR3IL
- HARU_KB_S3_VECTOR_INDEX_ARN: 변경 없음 (재생성 후 ARN 동일)

## 2026-10-31 Phase ⑦ Guardrail 생성
- 시작: 2026-10-31T02:17:21Z
```
Traceback (most recent call last):
  File "/Users/westhnu/Agent/Claude/haru-app-mono/backend/scripts/guardrail/create_guardrail.py", line 118, in <module>
    sys.exit(main())
             ^^^^^^
  File "/Users/westhnu/Agent/Claude/haru-app-mono/backend/scripts/guardrail/create_guardrail.py", line 114, in main
    return 0 if run(dry_run=dry_run) else 1
                ^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru-app-mono/backend/scripts/guardrail/create_guardrail.py", line 97, in run
    resp = bedrock.create_guardrail(**_build_kwargs())
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru-app-mono/backend/.venv/lib/python3.12/site-packages/botocore/client.py", line 606, in _api_call
    return self._make_api_call(operation_name, kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru-app-mono/backend/.venv/lib/python3.12/site-packages/botocore/context.py", line 123, in wrapper
    return func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "/Users/westhnu/Agent/Claude/haru-app-mono/backend/.venv/lib/python3.12/site-packages/botocore/client.py", line 1094, in _make_api_call
    raise error_class(parsed_response, operation_name)
botocore.errorfactory.ValidationException: An error occurred (ValidationException) when calling the CreateGuardrail operation: 1 validation error detected: Value at 'sensitiveInformationPolicyConfig.piiEntitiesConfig.1.member.type' failed to satisfy constraint: Member must satisfy enum value set: [US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER, US_BANK_ROUTING_NUMBER, MAC_ADDRESS, AWS_ACCESS_KEY, VEHICLE_IDENTIFICATION_NUMBER, CREDIT_DEBIT_CARD_EXPIRY, NAME, CA_HEALTH_NUMBER, UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER, INTERNATIONAL_BANK_ACCOUNT_NUMBER, CREDIT_DEBIT_CARD_CVV, PHONE, URL, UK_NATIONAL_INSURANCE_NUMBER, UK_NATIONAL_HEALTH_SERVICE_NUMBER, DRIVER_ID, AWS_SECRET_KEY, ADDRESS, US_PASSPORT_NUMBER, PIN, USERNAME, US_SOCIAL_SECURITY_NUMBER, LICENSE_PLATE, SWIFT_CODE, PASSWORD, IP_ADDRESS, EMAIL, US_BANK_ACCOUNT_NUMBER, CREDIT_DEBIT_CARD_NUMBER, CA_SOCIAL_INSURANCE_NUMBER, AGE]
```
- 종료: 2026-10-31T02:17:22Z

- 재시작: 2026-10-31T02:33:59Z (KI-017 수정 반영)
```
2026-10-31 11:34:00 [info     ] create_step                    dry_run=False resource_id=gtulvril25hb resource_type=guardrail result=created
Guardrail: gtulvril25hb
→ .env에 추가: BEDROCK_GUARDRAIL_ID=gtulvril25hb, BEDROCK_GUARDRAIL_VERSION=DRAFT
```
- 종료: 2026-10-31T02:34:00Z exit=

### Phase ⑦ Guardrail — 요약 (성공, KI-017 수정 반영)
- Guardrail id: gtulvril25hb
- Guardrail ARN: arn:aws:bedrock:ap-northeast-2:205474063205:guardrail/gtulvril25hb
- Version: DRAFT (status READY)
- 6종 정책 전부 반영 확인:
  - Denied Topic x2 ✓ (investment-advice, future-price-guarantee)
  - Word Filter 4개 ✓ (리딩방, 한 방, 무조건 수익, 보장)
  - Sensitive Info — regexesConfig(KR_RRN, `\d{6}-[1-8]\d{6}`, ANONYMIZE) ✓ (KI-017 수정 검증, piiEntities 빈 배열)
  - Content HIGH x3 ✓ (Hate/Sexual/Violence input+output)
  - Contextual Grounding 0.75 ✓ (BLOCK)
- 차단 메시지: input "본 서비스는 종목 추천을 제공하지 않습니다." / output "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."
- 소요: ~1s
- 비용: $0 (생성 자체는 무료, invoke 시만 과금)
- 발견 KI: KI-017 (piiEntitiesConfig의 KR_RRN 미지원 → regexesConfig 커스텀 패턴)

### Phase ⑦ 완료 후 .env 반영 필요 (사용자 직접)
- BEDROCK_GUARDRAIL_ID=gtulvril25hb
- BEDROCK_GUARDRAIL_VERSION=DRAFT

## 2026-10-31 Phase 5a — 1차 실행 (오염됨, KI-020 발견)

> ⚠️ Guardrail 과잉 차단(KI-020)으로 성공 76건 중 상당수가 '면책 문구만' 반환.
> block rate 49%는 과잉 차단 포함이므로 포폴 수치로 사용 금지. KI-020 수정 후 재측정 예정.
> 에러 24건은 KI-007 재발(Anthropic use case 미승인 응답). source 분포·latency·비용은 유효.

- CSV: `run_20261031T033640Z.csv`
- 실행 구간(UTC): 2026-10-31T03:36:40+00:00 ~ 2026-10-31T03:50:40+00:00
- 구성: 50 KB sample + 30 투자용어 + 10 가짜 + 10 Guardrail
- 성공/에러: 76/24
- Source 분포:
  - general_knowledge: 54 (54%)
  - BedrockRetrievalError: 24 (24%)
  - knowledge_base: 22 (22%)
- Latency(성공): p50 9652ms, p95 13338ms, p99 36995ms
- Guardrail INTERVENED: 원칙 테스트셋 9/10, 전체 49/100
- Mock 응답: 0/100
- disclaimer 누락: 0/76
- 평균 answer 길이: 153자
- 비용 실측 (CloudWatch, Sonnet 차원만 — KI-021 수정 후):
  - 토큰: input 79,187 / output 14,153 → 모델 비용 합계 $0.45
  - 쿼리당: **$0.0055~0.0069** (호출 100건 기준 $0.0045 / 성공 76건 기준 $0.0059, Guardrail 가정 +$0.001)
  - 사전 추정 $0.013의 약 절반. 수정 전 스크립트는 차원 중복 합산으로 $0.0129를 냈음(KI-021)
  - 월 비용(실측 기준): 혼자 테스트 20회/일 ≈ $4.15, 활성 100명 × 5회/일 ≈ $104
- 그룹별 INTERVENED (성공 건 기준): 원칙 테스트 9/9, 투자용어 21/28, KB 샘플 16/31, 가짜 3/8
  - 정상 용어 질문(투자용어+KB 샘플) 37/59 = 63% 차단 → KI-020
