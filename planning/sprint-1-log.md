# Sprint 1 Log — Bedrock RAG 최소 PoC

- **기간**: 2026-09-13
- **브랜치**: `sprint/1-bedrock-poc` (base: `main` = `sprint/0-skeleton` fast-forward)
- **목표**: RetrieveAndGenerate 래퍼 + `POST /api/v1/poc/ask`. KB가 없으면 mock으로 응답하고, 모든 응답에 면책 문구가 자동으로 붙는다.

---

## 1. 무엇을 만들었고 왜

### 요청 흐름

```
POST /api/v1/poc/ask {"query": ...}
  │  RagRequest 검증 (앞뒤 공백 제거, 1~1000자) ── 실패 시 422
  ▼
RagService.ask
  │  mask_pii(query)                  ← 결정 A: Bedrock·로그로 나가기 전에 PII 치환
  ├─ BEDROCK_KB_ID 없음 → mock 응답 (Bedrock 호출 없음, citations = [])
  └─ BEDROCK_KB_ID 있음 → RetrieveAndGenerate
  │                         (시스템 프롬프트 템플릿 + Guardrail ID가 있으면 guardrailConfiguration)
  ▼
apply_output_guard(answer)            ← 금지 표현이면 통째로 교체 + 면책 문구를 말미에 정확히 1회
  ▼
RagResponse {answer, citations[], disclaimer, model_id}   ── Bedrock 실패 시 502 (내부 정보 비노출)
```

### 파일별

| 파일 | 내용 | 이유 |
|---|---|---|
| `core/guardrail.py` | `DISCLAIMER`, `SAFE_REPLACEMENT`, `FORBIDDEN_PATTERNS`, `has_forbidden_phrase`, `enforce_disclaimer`, `apply_output_guard`, `mask_pii` | 원칙 1 이중 방어의 2차(코드) 방어선. 모델·리전·Guardrail 설정과 무관하게 항상 같은 결과를 보장 |
| `core/prompts.py` | `SYSTEM_PROMPT`(부트스트랩 원문), `RAG_PROMPT_TEMPLATE` | 1차 방어. 면책 문구는 `DISCLAIMER` 상수를 f-string으로 참조해 두 곳 문구가 어긋나지 않게 함 |
| `models/rag.py` | `RagRequest`, `RagCitation(excerpt, source)`, `RagResponse` | 브리핑 지시. `citations`는 `default_factory=list`로 항상 배열, `disclaimer`는 기본값으로 항상 존재 |
| `services/bedrock_client.py` | `bedrock-runtime` / `bedrock-agent-runtime` 클라이언트를 `lru_cache`로 1회 생성 | 부트스트랩 지시. 타임아웃(connect 5s / read 120s), adaptive 재시도 3회 |
| `services/rag_service.py` | `RagService`(클라이언트 주입), `parse_citations`, `get_rag_service` | 테스트에서 Fake 클라이언트를 주입해 AWS를 한 번도 호출하지 않기 위해 클래스 + 생성자 주입 |
| `api/v1/poc.py` | `POST /api/v1/poc/ask`, `Depends(get_rag_service)` | 동기 `def` 엔드포인트 → FastAPI 스레드풀에서 blocking boto3 호출 |

### 3중 방어 구조 (원칙 1)
1. **시스템 프롬프트**: 권유·예측 금지, 출처 표기, 면책 문구 지시, 근거 밖 수치 생성 금지
2. **코드 후처리** (`apply_output_guard`): 정규식으로 금지 표현을 감지하면 **부분 삭제 없이 통째로 교체**. 문장 일부만 지우면 권유 맥락이 남을 수 있기 때문
3. **Bedrock Guardrail 리소스**: `BEDROCK_GUARDRAIL_ID`만 채우면 요청에 자동으로 포함됨. 리소스 생성은 PO 몫

### Sprint 2.5(키움)를 수용하기 위한 설계
- `services/`는 벤더별로 파일 하나 (`bedrock_client.py`, 향후 `dart_tool.py`, `hantu_readonly.py`, `kiwoom_readonly.py`)
- 서비스는 **동기 메서드 + Pydantic 반환 타입**이고, 외부 클라이언트는 **생성자 주입**. Sprint 2의 `@tool` 래핑과 테스트 Fake 주입이 같은 패턴으로 가능
- 외부 호출은 `try/except` → structlog 에러 로그 → 도메인 예외(`RagServiceError`) → 라우터에서 HTTP 코드로 변환

## 2. Bedrock 실제 호출 결과

| 항목 | 결과 |
|---|---|
| 모델 접근 (Converse 1회, `global.anthropic.claude-sonnet-4-5-20250929-v1:0`, maxTokens 10) | ✅ **성공**: 응답 `ok`, 입력 24 / 출력 4 토큰, `end_turn`. Sprint 0의 `agreementAvailability: NOT_AVAILABLE`은 실제 호출에 영향 없음 |
| RetrieveAndGenerate | ⏸ **미호출**: KB가 아직 없음. **mock 모드로 동작 확인** (아래 curl) |
| 과금 | Converse 1회, 28토큰 (1센트 미만) |

```bash
$ curl -X POST localhost:8000/api/v1/poc/ask -H 'Content-Type: application/json' -d '{"query":"PER이 뭐야?"}'
{"answer":"[MOCK] Knowledge Base가 설정되지 않아 개발용 응답을 반환합니다. 질문: PER이 뭐야?\n\n본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다.",
 "citations":[],"disclaimer":"본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다.","model_id":"mock"}

# 금지 표현이 섞인 질의 → mock 응답에 질의가 에코되므로 출력 가드가 통째로 교체
$ curl ... -d '{"query":"주민번호 900101-1234567인데 이 종목 매수하세요?"}'
{"answer":"본 서비스는 종목 추천을 제공하지 않습니다. 판단은 본인에게 있습니다.\n\n본 정보는 ...","citations":[],...}

# 공백만 있는 질의 → 422
```

### KB 생성 후 첫 실호출에서 확인할 것
API 형태는 추측하지 않고 아래 근거로 맞췄다. 다만 실제 KB 호출은 아직 한 번도 하지 않았다.
- 요청·응답 필드: botocore 1.43.93 서비스 모델 `bedrock-agent-runtime.RetrieveAndGenerate`에서 직접 확인
- `modelArn`에 프로파일 ID 사용: AWS 문서 "Use an inference profile in model invocation"에 *"If you're using a cross-Region (system-defined) inference profile, you can use either the ARN or the ID"*라고 명시됨
- `$output_format_instructions$`: AWS 문서 "Knowledge base prompt templates"에 *"required field for citations to be displayed in the response"*라고 명시됨
- `$query$`: 문서에서 확인되지 않아 템플릿에서 **제외**. 문서상 템플릿은 시스템 프롬프트이고 질의는 Bedrock이 따로 결합함 → **첫 실호출에서 모델이 질의를 제대로 받는지 확인 필요**

## 3. PII 마스킹 인터페이스 설계 의도

```python
mask_pii(text: str) -> str
```

- **어디서 쓰나**: `RagService.ask` 첫 줄. Bedrock 요청과 로그로 나가기 **전에** 적용. 로그에는 질의 원문 대신 `query_length`만 기록
  - 브리핑은 "Sprint 1에서 실제 사용은 없어도 인터페이스 준비"였지만, 결정 A가 "PII는 절대 프롬프트에 포함되지 않도록"이어서 호출 지점에 바로 연결함. 테스트 `test_pii_is_masked_before_reaching_bedrock`로 보장
- **값 대신 라벨 토큰** (`[주민등록번호]`, `[카드번호]`, `[전화번호]`, `[계좌번호]`): 모델이 "계좌번호가 언급됐다"는 맥락은 이해하되 값은 모르게 하기 위해. `***`보다 응답 품질이 덜 떨어짐
- **적용 순서 = 긴 패턴 먼저**: 주민번호(13자리) → 카드(16) → 휴대전화 → 계좌. 짧은 패턴이 긴 번호의 일부를 먼저 먹지 않게 함
- **계좌번호 판정**: 금융기관마다 자리 구분이 달라(3-2-6, 3-3-6, 6-2-6, 한투 8-2 …) "하이픈으로 묶인 숫자 그룹 + 총 10~14자리"로 판정. 날짜(`2025-09-13`, 8자리)나 `2024-2025`는 범위 밖이라 보존
- **순수 함수 · 무상태**: Sprint 2.5 키움/한투 래퍼 응답이나 저널 본문에도 그대로 재사용 가능. 규칙을 바꾸면 `test_guardrail.py`의 PII 테스트 7건이 회귀 검증
- **한계**: 하이픈 없는 계좌번호(`110123456789`), 유선전화, 이메일, 이름은 마스킹하지 않음 → Bedrock Guardrail Sensitive Information 필터로 보완 예정 (KI-005)

## 4. 테스트

```
$ uv run pytest
28 passed, 1 warning
```

| 파일 | 테스트 | 수 |
|---|---|---|
| `test_health.py` | 헬스체크 | 1 |
| `test_poc.py` (통합) | mock 모드 + 면책 문구 / **정상 경로**(Fake RetrieveAndGenerate, 인용 파싱·중복 제거) / **금지 표현 강제 주입 → 교체** / PII가 Bedrock 요청 전에 마스킹됨 / Bedrock 실패 → 502 + ARN 비노출 | 5 |
| `test_guardrail.py` | **회귀 필수 3종**(`매수하세요`, `내일 오릅니다`, 주민번호 마스킹) + 금지 변형 6 + 허용 표현 오탐 방지 5 + 면책 문구 1회 보장 1 + PII 4 + 비PII 보존 3 | 22 |

- 모든 테스트는 `Settings(_env_file=None, bedrock_kb_id=...)`로 값을 명시함 → 로컬 `.env`에 실제 KB ID가 있어도 실호출하지 않음
- 남은 경고 1건: starlette 내부의 anyio deprecation (Sprint 0에서 무시하기로 승인)

## 5. 이후 리팩토링 후보

- **라우터 집계**: 라우터가 2개가 됐고 `/api/v1` prefix가 라우터 파일마다 반복됨 → Sprint 2에서 `stock.py`를 추가할 때 `api/v1/__init__.py`에서 `api_router`로 묶기
- **금지 표현 목록 외부화**: 정규식이 코드 상수라 PO가 표현을 추가하려면 코드를 고쳐야 함. Guardrail Denied Topic과 함께 관리할 수 있게 YAML이나 Prompt Management로 이관 검토
- **`MAX_TOKENS` 설정화**: 모듈 상수 → 작업별 모델 매트릭스(§13.2) 도입 시 `Settings`로
- **스트리밍**: `RetrieveAndGenerateStream`으로 체감 지연 개선 (프론트엔드 Sprint 3과 함께)
- **mock 응답이 질의를 에코함**: 질의에 금지 표현이 있으면 mock 전체가 대체 문구로 바뀜. 개발용이라 무해하지만 혼동 소지가 있음

## 6. 알려진 이슈 · 기술 부채

- **정규식 필터는 우회 가능**: "매수 추천드려요", 영어, 초성, 띄어쓰기 변형 등. 2차 방어선일 뿐이며 Bedrock Guardrail Denied Topic(§13.5)이 필수
- **오탐 시 응답 전체가 교체됨**: 허용 표현 5종은 테스트로 고정했지만 새로운 오탐이 나오면 정상 답변이 통째로 사라짐. 운영 로그로 오탐을 모니터링해야 함
- **원칙 2 "AI가 만든 수치 반환 금지"를 코드 레벨에서 검증하지 않음**: Sprint 1은 프롬프트 지시 + citations 파싱까지만. Contextual Grounding(§13.5 threshold 0.75) 또는 Sprint 2의 DART 원본 수치 대조로 보완
- **citations가 비어 있는 KB 응답도 그대로 반환됨**: 아래 결정 요청 1
- **mock 모드가 조용히 200을 반환**: 배포 환경에서 `BEDROCK_KB_ID`가 빠지면 사용자가 mock 응답을 받게 됨. M3 배포 전에 환경 구분 필요 (결정 요청 2)
- 데이터 처리 리전: [`known-issues.md` KI-005](known-issues.md)

## 7. Sprint 2 진입 전 PO 결정 요청

1. **출처 없는 응답 처리 (원칙 2 엄격도)**: KB가 근거를 못 찾아 `citations`가 빈 응답을 ① 그대로 반환할지, ② "확인된 자료가 없습니다"로 대체할지. Sprint 2 종목 요약은 재무 수치가 핵심이라 **②를 권장**하고, 용어 설명 같은 일반 질의는 ①로 두는 것을 제안
2. **mock 모드 운영 가드**: `APP_ENV=prod`에서는 KB·DART 키가 비어 있으면 **기동 자체를 실패**시킬지. 지금 넣어도 비용이 작아서 Sprint 2에 함께 넣는 것을 권장
3. **Sprint 2 준비물**: `DART_API_KEY` 제공 필요 (로컬 `backend/.env`에 직접 넣어 주세요). jutopia_data import 방식(`sys.path` vs 복사 vs 로컬 패키지)은 부트스트랩 지시대로 Sprint 2에서 근거와 함께 보고
