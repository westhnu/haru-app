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
