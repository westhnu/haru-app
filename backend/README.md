# Haru Backend

FastAPI 기반 Haru API 서버. AWS Bedrock Knowledge Base + Guardrail로 투자 용어 RAG를 제공하고, 워크북·체크리스트·저널 API를 둔다.

## 로컬 실행 (`backend/`에서)

```bash
uv sync && cp .env.example .env                              # 의존성 + 환경변수 템플릿
PYTHONPATH=. uv run uvicorn app.main:app --reload --port 8000  # → http://localhost:8000/docs
PYTHONPATH=. uv run pytest tests/ -q                         # 239 passed, 5 skipped
uv run ruff check . && uv run black --check .                # 린트/포맷
```

- `BEDROCK_KB_ID`가 비어 있으면 RAG 엔드포인트는 mock 응답, `DART_API_KEY`가 비어 있으면 mock 재무 데이터를 돌려준다.
- `BEDROCK_KB_ID`·`BEDROCK_GUARDRAIL_ID`를 채우면 실제 Bedrock을 호출한다(요금 발생). AWS 자격증명은 boto3 기본 체인을 쓴다.
- 환경변수는 `app/config.py` 단일 진입점에서 읽는다. 키 목록은 `.env.example` 참고(값은 비어 있음).

## 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| POST | `/api/v1/glossary/ask` | 투자 용어 질의. Bedrock KB RetrieveAndGenerate + Guardrail. 응답에 `source`(knowledge_base / general_knowledge / guardrail_blocked / mock), `citations`, `disclaimer` 포함 |
| POST | `/api/v1/poc/ask` | RAG PoC. `context_type`: `stock` / `glossary` / `general` |
| GET | `/api/v1/stock/{code}/summary` | DART 재무 + 코드 계산 비율 기반 AI 요약 + DART 원문 출처 |
| GET | `/api/v1/admin/kb-status` | KB 상태 조회 |
| GET·POST | `/api/v1/workbooks`, `/api/v1/workbooks/{id}` | 종목 워크북 (in-memory) |
| GET | `/api/v1/checklists`, `/{id}`, `/{id}/score` | AI 체크리스트 채점 (in-memory) |
| GET·POST | `/api/v1/journal/entries`, GET `/api/v1/journal/portfolio` | 투자 저널 + 가상 포트폴리오 (in-memory) |

```bash
curl -X POST localhost:8000/api/v1/glossary/ask -H 'Content-Type: application/json' -d '{"query":"PER이 뭐야?"}'
```

## 안전 설계 (원칙 1·2·5)

- **질의**: `mask_pii`(주민번호·카드·휴대폰·계좌)를 거친 뒤에만 외부로 나간다.
- **Guardrail** (`scripts/guardrail/create_guardrail.py`): Denied Topic 2종, word 필터 4종, KR_RRN 정규식(KI-017), content 필터, contextual grounding 0.50. topic·content는 Standard tier + cross-Region `apac.guardrail.v1:0`(KI-023).
- **코드 후처리** (`app/core/guardrail.py`): `apply_output_guard`가 금지 표현을 감지하면 답변 전체를 표준 문구로 교체하고, `enforce_disclaimer`가 면책 문구를 말미에 정확히 한 번 붙인다.
- **차단 응답**: Guardrail이 개입하면 `source="guardrail_blocked"`와 "근거 자료를 찾지 못했습니다" 안내를 돌려준다(KI-020).
- 한계: 우회 표현 5건은 Guardrail INPUT을 통과한다(KI-024). 3층 방어와 측정치는 `planning/known-issues.md` 참고.

## 운영 스크립트

모든 스크립트는 `--dry-run`이 기본이고, 실제 AWS 호출은 `--apply`를 명시해야 한다.

| 경로 | 용도 |
|---|---|
| `scripts/kb/` | glossary 변환·업로드, KB 생성·sync, teardown |
| `scripts/guardrail/` | Guardrail 생성·갱신(`update_guardrail.py`는 정책 전체 재전송), teardown, topic 후보 |
| `scripts/bench/query_cost.py` | 100건 쿼리 벤치마크 (500ms 간격, 1·2·4초 백오프 재시도) |
| `scripts/bench/estimate_cost.py` | CloudWatch 토큰 실측 기반 비용 산정 (모델 차원만, KI-021) |
| `scripts/bench/topic_eval.py` | 50건 원칙 테스트셋 ApplyGuardrail 평가 (temp Guardrail 생성·삭제) |
| `scripts/bench/grounding_investigate.py`, `hallucination_check.py` | grounding score 재획득, threshold 완화 환각 체크 (T-514) |

벤치·평가 스크립트의 원 답변은 `/tmp`에만 저장하고 커밋하지 않는다.

## Phase 5a 벤치마크 요약 (100건, 2026-10-31)

| 지표 | 1차 (Classic, 0.75) | 2차 (Standard, 0.75) | 3차 (Standard, 0.50) |
|---|---|---|---|
| 성공률 | 76% | 100% | 100% |
| 쿼리당 비용 | $0.0069 | $0.0088 | $0.0103 |
| p50 / p95 | 9.65s / 13.34s | 9.64s / 13.56s | 9.82s / 13.43s |
| KB 보유 용어 차단 (품질 지표) | 47% | 38% | 22% |
| KB 미보유 용어 거절 (원칙 2 작동) | 90% | 82% | 86% |

- 측정 기준: 정상 질문을 KB 보유 용어(58건)와 미보유 용어(22건)로 나눈다. 미보유 용어 거절은 "근거 없는 내용 반환 금지"(원칙 2)가 작동한 결과라 결함으로 세지 않는다.
- 50건 원칙 테스트셋 INPUT 차단: Classic 2/35 → Standard 30/35, 최종 판정 35/35.
- 상세: [`planning/metrics.md`](../planning/metrics.md), [`planning/blog_harness_roi_1.md`](../planning/blog_harness_roi_1.md)
