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
