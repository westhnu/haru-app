# Sprint 2 진입 브리핑 — DART 통합 + 운영 안전장치

> Sprint 1 완료(브랜치 `sprint/1-bedrock-poc`, 28 tests passed) 승인 후 Sprint 2 진입 문서.
> Claude Code는 이 파일 전체를 컨텍스트로 삼아 Sprint 2를 시작한다.

---

## ✅ Sprint 1 승인

부트스트랩 프롬프트 체크리스트 전 항목 완료 + 브리핑 추가 지시 3개(PII 마스킹, RagResponse 모델, 회귀 테스트) 모두 이행. 28 tests passed.

**브리핑과 다르게 한 3개 조치, 모두 승인**:
- KI-005로 번호 변경 (KI-002 HantuStock 선점 확인) ✓
- `mask_pii` 실제 호출 직전 적용 (결정 A 반영으로 더 안전) ✓
- 커밋 메시지 사고 정정 (diff 검증 후 브랜치 이동) ✓

---

## 🚦 Sprint 2 전 결정 4개 답변

### 결정 1 — 출처 없는 응답 처리: **컨텍스트 분기 (하이브리드) 채택**

CC 제안이 정확합니다. 요청 카테고리에 따라 분기하세요.

- `RagRequest`에 `context_type: Literal["stock", "glossary", "general"] = "general"` 필드 추가
- **`stock`** (종목 요약, 재무 분석): KB 근거 못 찾으면 **"확인된 자료가 없습니다. DART 공시 데이터가 아직 인덱싱되지 않았을 수 있습니다."** 로 대체. 절대 LLM 일반지식으로 재무 수치 만들지 말 것 (원칙 2 위반)
- **`glossary`** (용어 설명): KB 우선, 없으면 LLM 일반지식 허용. 이때 응답에 `source: "general_knowledge"` 태그 명시
- **`general`** (기타 문의): LLM 일반지식 허용, 단 `disclaimer` 문구는 유지
- 이 분기는 `services/rag_service.py`에서 처리하고, `core/prompts.py`에 컨텍스트별 시스템 프롬프트 3종 상수화

### 결정 2 — APP_ENV=prod 하드 페일: **Sprint 2에 함께 포함 승인**

CC 판단대로 작업량이 작아 지금이 적기입니다.

- `config.py`의 `Settings` 클래스에 Pydantic v2 `model_validator(mode="after")` 로 추가:
  - `APP_ENV=="prod"`인데 `BEDROCK_KB_ID`, `BEDROCK_GUARDRAIL_ID`, `DART_API_KEY` 중 하나라도 빈 문자열/None이면 `ValueError` raise
  - `APP_ENV`는 `Literal["local", "dev", "staging", "prod"] = "local"`
- `main.py` 앱 팩토리에서 Settings 로드 시점에 실패하면 fail-fast (uvicorn 자체가 뜨지 않음)
- 테스트: `test_config_prod_fails_without_required_keys` 케이스 추가

### 결정 3 — DART_API_KEY 확보: **사용자(나)가 직접 발급, 브리핑 시점에 전달**

CC가 대신 할 수 없는 부분입니다. 나(프로덕트 오너)의 액션 아이템:

1. https://opendart.fss.or.kr/ 접속 → 회원가입 → 인증키 신청
2. 개인 무료·즉시 발급 (하루 1만 회 호출 제한)
3. 발급된 키를 로컬 `.env`에 `DART_API_KEY=xxxxxxxx...` 로만 추가 (git에 절대 커밋 X)
4. CC에게 "DART_API_KEY 준비 완료" 메시지로 알림

**CC는 그전까지 Sprint 2 코드를 완성**하되, 실제 DART 호출은 mock 응답으로 개발. 내 키 준비 후 통합 테스트 1회로 검증하는 흐름.

### 결정 4 — `sprint/1-bedrock-poc` → `main` fast-forward 병합: **승인**

커밋 메시지 정정된 상태에서 diff 검증까지 완료했으니 안전합니다. Sprint 2 시작 브랜치는 `sprint/2-dart-integration`.

---

## 🎯 Sprint 2 목표 (부트스트랩 프롬프트 원문 + v1.2 반영 확장)

부트스트랩 프롬프트의 Sprint 2 원문은 그대로 유지되고, 다음 사항을 추가/조정합니다.

### 부트스트랩 원문 (요약)
- `services/dart_tool.py` — `jutopia_data/dart_client.py` 얇은 래퍼
- `services/stock_summary_service.py` — DART 결과 + Bedrock 요약 오케스트레이션
- `api/v1/stock.py` — `GET /api/v1/stock/{code}/summary`
- 완료 기준: `curl /api/v1/stock/005930/summary` → 삼성전자 재무 요약 + DART 출처 + disclaimer

### v1.2 추가 지시

**A. jutopia_data 임포트 방식 결정 후 근거 보고**
- 후보: (1) `sys.path.insert` (2) 심볼릭 링크 `haru_web/vendor/jutopia_data` (3) 패키지 설치(`pip install -e ../jutopia_data`)
- 판단해서 선택하고 `planning/sprint-2-log.md`에 근거 기록
- 개인 추천: **(2) 심볼릭 링크** — 프로젝트 루트에서 관계 명시적, git 추적 없음

**B. 컨텍스트 분기 시스템 프롬프트 3종 (결정 1)**
- `core/prompts.py`에 `SYSTEM_PROMPT_STOCK`, `SYSTEM_PROMPT_GLOSSARY`, `SYSTEM_PROMPT_GENERAL` 상수
- `services/rag_service.py`에서 `context_type` 파라미터로 분기
- 각 프롬프트에 원칙 2(재무 수치 출처 인용) 명시

**C. APP_ENV 하드 페일 (결정 2)**
- `config.py`에 model_validator 추가
- `test_config.py` 신설 (prod 미설정 실패, local 통과 케이스)

**D. DART 응답 캐싱**
- DART API는 1만 회/일 제한. `functools.lru_cache` 또는 인메모리 dict TTL 캐시 30분
- 재무제표 캐시 키: `(corp_code, year, reprt_code)`
- 캐시 히트/미스는 structlog에 기록

**E. 스토크 요약 응답 스키마**
- `models/stock.py`: `StockSummaryResponse` — `code, name, financials, summary, sources[], disclaimer`
- `sources[]`는 반드시 최소 1개 이상. DART 원본 접근 URL(`https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}`) 포함

### 지금은 하지 말 것
- HantuStock 통합 (Sprint 2.5 예정)
- 키움 통합 (Sprint 2.5 예정)
- 프론트엔드 (Sprint 3)
- 실제 KB 생성 (내가 별도로 진행 예정)

---

## 📋 완료 시 보고 형식

1. ✅ 체크리스트 (부트스트랩 원문 + v1.2 A~E)
2. 🖥 실행 예시:
   ```
   curl http://localhost:8000/api/v1/stock/005930/summary
   ```
   응답에 `sources[]`, `disclaimer` 포함 확인
3. 🧪 pytest 결과 (Sprint 1의 28개 + Sprint 2 추가 예상 10개 이상)
4. 📝 `planning/sprint-2-log.md`:
   - jutopia_data 임포트 방식 결정 근거
   - DART 응답 형태 검증 결과 (예상과 차이 있으면 기록)
   - 캐시 히트율 대략치 (개발 중 관찰)
   - Sprint 2.5 진입 전 결정받고 싶은 것

## ⏳ 사용자 액션 아이템 (내가 할 일)

- [ ] `DART_API_KEY` 발급 후 CC에게 전달
- [ ] Sprint 2 완료 후 Sprint 2.5 브리핑 작성 (v1.2 §14.3 근거)
- [ ] 실제 Bedrock KB 생성 (별도 진행, Sprint 2 이후)

---

준비되면 **"Sprint 2 시작"** 이라고 알려주세요. `DART_API_KEY`는 아직 없어도 됩니다 (mock 응답으로 개발).
