# Claude Code Bootstrap — Haru MVP (v0)

> Claude Code에 이 파일 전체를 그대로 붙여넣으면 됩니다.
> CC는 이 프롬프트만 있으면 프로젝트를 이해하고 첫 3개 스프린트를 순차적으로 진행할 수 있어야 합니다.

---

## 당신의 역할

당신은 **Haru의 시니어 풀스택 개발자**입니다.
- Haru는 개인 투자자의 리서치·의사결정·회고 사이클을 도구화한 SaaS입니다.
- 저는 프로덕트 오너입니다.
- 당신이 코드를 쓰기 전에 반드시 프로젝트 컨텍스트를 파악해야 하고,
  법적/보안 원칙을 지키면서 첫 3개 스프린트를 순차적으로 진행합니다.
- 각 스프린트 완료 시 나에게 검증받고 다음으로 넘어갑니다.

---

## STEP 1 — 첫 15분: 컨텍스트 파악

아래 파일을 이 순서대로 읽고 이해하세요. **읽기만 하고 아직 코드를 쓰지 마세요.**

1. `/Users/westhnu/Agent/Claude/haru_web/README.md` — 프로젝트 개요와 재활용 자산 매핑
2. `/Users/westhnu/Agent/Claude/haru_web/docs/Haru_기획안_v1.1.docx` — 정식 기획서
   - `.docx`는 `python-docx` 또는 `pandoc -f docx -t markdown` 으로 텍스트 추출
   - 특히 다음 섹션을 정독: **§5 MVP 4대 기능, §8 기술스택, §10 법적 리스크, §13 AWS Bedrock 부록 (v1.1 신규)**
3. `/Users/westhnu/Agent/Claude/jutopia_data/README.md` — 재활용할 백엔드 모듈 목록
4. `/Users/westhnu/Agent/Claude/jutopia_data/docs/PROJECT_MODULES_SUMMARY.md` — 모듈 상세 (특히 `dart_client.py`, `HantuStock.py`, `glossary_api.py`, `tavily_search.py`)

읽고 나면 다음을 각 1–2문장으로 요약해서 **"준비 완료" 메시지와 함께** 나에게 보고하세요.
그전에는 파일을 만들거나 수정하지 않습니다.

- Haru의 한 줄 정의
- MVP 4개 핵심 기능 이름과 목적
- 재활용할 jutopia_data 모듈 5개와 각 역할
- 기획안 §13에서 정한 배포 옵션 3단(어떤 시점에 무엇을 쓰는지)

---

## 프로젝트 구조 (이미 만들어져 있음)

```
/Users/westhnu/Agent/Claude/haru_web/
├── README.md
├── docs/               # 기획서 (읽기만, 수정 금지)
│   └── Haru_기획안_v1.1.docx
├── planning/           # 스프린트 로그·의사결정 기록 (당신이 채움)
│   └── claude_code_bootstrap.md  ← 이 파일
├── artifacts/          # 라이브 아티팩트 HTML (Cowork 사이드바 용, 건드리지 말 것)
├── assets/
├── frontend/           # ← Sprint 3 이후 사용, 지금은 비워둠
├── backend/            # ← Sprint 0~2 여기에 코드 작성
└── shared/             # OpenAPI/타입 스키마 공유 (Sprint 4 이후)
```

**재활용 대상 (읽기 전용):** `/Users/westhnu/Agent/Claude/jutopia_data/`

---

## 절대 원칙 (프로덕트 수준의 법적·보안 가드)

### 1. 종목 추천/가격 예측 절대 금지
- AI 응답 어디에서도 "매수하세요", "○○원까지 갑니다", "무조건 수익", "내일 오릅니다" 표현 금지
- 시스템 프롬프트와 응답 후처리 둘 다에서 필터링 (이중 방어)
- 모든 사용자 응답 말미에 다음 문구를 자동 첨부:
  > "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."

### 2. 재무 수치는 반드시 출처 인용
- DART, 한투 OpenAPI 등 출처를 응답에 명시 (예: "DART 2025-1Q 기준")
- AI가 만들어낸 수치는 절대 그대로 반환하지 않음 (환각 방지)
- 수치를 인용할 때는 `source` 필드에 원본 URL/문서명 포함

### 3. Secrets는 절대 커밋 금지
- `.env` 파일은 `.gitignore`에 무조건 포함
- API 키·DB 비번은 환경변수로만 주입
- `.env.example` 파일로 필요한 키 목록만 공유 (값은 비워둠)
- 실수로 커밋될 위험이 있는 파일 발견 시 즉시 나에게 보고

### 4. 파일 위치 규칙
- 새 파일은 모두 `/Users/westhnu/Agent/Claude/haru_web/` 하위에만 생성
- `jutopia_data`는 참조만, 절대 수정 금지 (읽기만)
- 임시 스크립트·실험 코드는 `haru_web/planning/tmp/` 아래에
- 세션 임시 파일은 절대 최종 산출물로 남기지 말 것

### 5. 자동매매·주문 실행 코드 전면 금지
- MVP 범위에 실주문 API 호출은 전혀 없음
- 한투 OpenAPI를 쓰더라도 **조회 전용** (잔고·보유·거래내역만)
- 주문 관련 함수는 아예 import 하지 않음

---

## 기술 스택 (기획안 §13 확정)

### Backend (Sprint 0~2)
- **Python 3.11** + **FastAPI** + **Uvicorn**
- **Boto3** (AWS SDK) — Bedrock Runtime 호출용
- **Pydantic v2** — 요청·응답 스키마 검증
- **structlog** — JSON 구조화 로깅
- **Ruff** + **Black** — 린팅/포맷
- **Pytest** — 테스트
- 패키지 매니저: `uv` (없으면 `poetry`, 그것도 없으면 `pip + pip-tools`)

### Frontend (Sprint 3 이후)
- **Next.js 14** (App Router) + **TypeScript**
- **Tailwind CSS** + **shadcn/ui**
- **TanStack Query** + **Zustand**
- 지금은 만들지 마세요.

### AWS (기획안 §13)
- **Bedrock Runtime** — Claude Sonnet 4.5 기본, Haiku 4.5 폴백 (Haiku는 간단한 태깅·판정용)
- **Bedrock Knowledge Base** — S3 벡터스토어 (OpenSearch 비싸서 배제)
- **Bedrock Guardrail** — "종목 매수·매도 권유"를 Denied Topic으로 등록
- **Titan Text Embeddings v2** — 임베딩 통일 (모델 간 벡터 호환 안 됨)
- **Region**: `ap-northeast-2` (서울)
- **배포**: Sprint 3까지는 로컬 개발만. M3 Lambda → M4 AgentCore Runtime → M12+ EKS (기획안 §13.7)

---

## 스프린트 계획 (당신은 순서대로 진행합니다)

### 🏗️ Sprint 0 — 백엔드 스켈레톤 (반나절)

**목표**: FastAPI 서버가 로컬에서 뜨고 `/health` 응답을 준다.

- [ ] `backend/` 하위에 프로젝트 초기화
  - `pyproject.toml` (uv 우선)
  - 폴더: `app/{main.py, config.py, api/v1/, core/, services/, models/, __init__.py}`
- [ ] `app/main.py` — FastAPI 앱, CORS, 라우터 등록
- [ ] `app/config.py` — Pydantic Settings (환경변수 로드)
- [ ] `app/api/v1/health.py` — `GET /health` → `{"status": "ok", "version": "0.1.0"}`
- [ ] `.env.example`:
  ```
  AWS_REGION=ap-northeast-2
  BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-v1:0
  BEDROCK_KB_ID=
  BEDROCK_GUARDRAIL_ID=
  BEDROCK_GUARDRAIL_VERSION=DRAFT
  LOG_LEVEL=INFO
  ```
- [ ] `.gitignore` — Python(`__pycache__`, `.venv`, `*.pyc`), AWS(`.aws/`), IDE(`.vscode/`, `.idea/`), `.env`, `dist/`, `.pytest_cache/`
- [ ] `backend/README.md` — 로컬 실행 방법 3줄
- [ ] `pytest` 스모크 테스트 1개 (`test_health.py`)

**완료 기준**:
```
uvicorn app.main:app --reload
curl http://localhost:8000/health
# → {"status":"ok","version":"0.1.0"}
pytest
# → 1 passed
```
위 3줄이 성공하면 나에게 보고하고 Sprint 1로 진행 허가를 받으세요.

---

### 🧪 Sprint 1 — Bedrock 최소 PoC (하루)

**목표**: 실제 Bedrock RetrieveAndGenerate API가 응답을 주고, 응답에 disclaimer가 자동으로 붙는다.

- [ ] `services/bedrock_client.py` — Boto3 `bedrock-runtime`, `bedrock-agent-runtime` 클라이언트 팩토리 (한 번만 생성, 재사용)
- [ ] `services/rag_service.py` — `RetrieveAndGenerate` 호출 래퍼:
  - Input: `query: str`
  - Output: `RagResponse(answer, citations, disclaimer, model_id)`
  - **핵심**: KB ID가 미설정이면 mock 응답 반환 (개발용)
- [ ] `core/prompts.py` — 시스템 프롬프트 상수:
  ```python
  SYSTEM_PROMPT = """당신은 개인 투자자를 돕는 정보 정리 어시스턴트입니다.
  - 특정 종목의 매수·매도를 권유하지 마세요.
  - 미래 가격·수익률 보장 표현을 사용하지 마세요.
  - 재무 수치는 반드시 출처(DART 등)를 함께 표기하세요.
  - 응답 말미에 다음 문구를 반드시 포함하세요:
    "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."
  """
  ```
- [ ] `core/guardrail.py` — 응답 후처리 함수 `enforce_disclaimer(text) -> text`, `has_forbidden_phrase(text) -> bool`
  - 금지 표현 리스트: `["매수하세요", "매도하세요", "무조건 수익", "내일 오릅", "○○원까지"]` 정규식
  - 발견 시 응답을 표준 대체 문구로 교체
- [ ] `api/v1/poc.py` — `POST /api/v1/poc/ask`:
  - Request: `{"query": "PER이 뭐야?"}`
  - Response: `{"answer": "...", "citations": [...], "disclaimer": "..."}`
- [ ] `pytest` 통합 테스트:
  - mock Bedrock 응답으로 정상 경로 1개
  - 금지 표현이 섞인 응답을 강제 주입 → 후처리로 제거되는지 검증 1개

**완료 기준**:
- 환경변수에 `BEDROCK_KB_ID`가 없으면 mock 응답 (disclaimer 포함) 반환
- 환경변수에 KB ID가 설정되면 실제 Bedrock 호출 (내가 나중에 KB를 만들어서 값 넣어줌)
- 모든 응답에 disclaimer가 자동 첨부됨을 테스트로 증명

---

### 🔗 Sprint 2 — 첫 번째 도구 통합 (1~2일)

**목표**: 종목 코드를 넣으면 DART 재무 정보 + AI 요약이 오는데, 반드시 출처와 disclaimer를 포함한다.

- [ ] `services/dart_tool.py` — `jutopia_data/dart_client.py` 얇은 래퍼
  - jutopia_data 임포트 방식: `sys.path.insert(0, ...)` 또는 심볼릭 링크 (판단 후 나에게 근거 보고)
  - 함수: `fetch_dart_financial(stock_code: str) -> DartResult`
  - 오류 시 (종목코드 없음, DART 응답 실패 등) 명확한 예외
- [ ] `services/stock_summary_service.py` — DART 결과 + Bedrock 요약 오케스트레이션
- [ ] `api/v1/stock.py` — `GET /api/v1/stock/{code}/summary`:
  - Response: `{"code": "005930", "name": "삼성전자", "summary": "...", "financials": {...}, "sources": [{"name":"DART", "url":"..."}], "disclaimer": "..."}`
- [ ] 통합 테스트: mock DART + mock Bedrock으로 스모크 테스트 1개
- [ ] 실제 호출은 테스트에 넣지 말 것 (요금·flakiness 방지)

**완료 기준**:
```
curl http://localhost:8000/api/v1/stock/005930/summary
# → 삼성전자 재무 요약이 오는데:
#   1. sources 배열에 DART 출처 명시
#   2. disclaimer 자동 첨부
#   3. 금지 표현 없음
```

---

## 코드 스타일 규칙

- **타입 힌트 필수** (Python 3.11 문법: `list[str]`, `dict[str, Any]`, `X | None`)
- **Pydantic 모델**로 API 입출력 정의 (`BaseModel`)
- 함수는 20줄 이내 유지 (초과 시 분리)
- 주석은 "왜"만, "무엇"은 코드가 말하게
- 외부 호출(Bedrock, DART, HTTP)은 반드시 try/except + structlog 로깅
- 로그는 JSON 포맷 (`structlog.processors.JSONRenderer`)
- 상수는 대문자 스네이크 (`SYSTEM_PROMPT`, `MAX_TOKENS`)
- 환경변수는 `Settings` 클래스 하나로 관리, 직접 `os.getenv` 금지

---

## 커밋 규칙

- **Conventional Commits** prefix (영문): `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`
- 메시지 본문은 한국어 OK
- Sprint 단위 브랜치: `sprint/0-skeleton`, `sprint/1-bedrock-poc`, `sprint/2-dart-tool`
- 한 커밋 = 한 논리 단위 (여러 스프린트가 한 커밋에 섞이면 안 됨)

---

## 매 스프린트 종료 시 나에게 보고할 것

1. ✅ 완료된 체크박스 목록
2. 🖥 실행 방법 한 줄 (`curl` 예시)
3. 🔍 다음 스프린트 전 나에게 결정받고 싶은 사항 (있으면)
4. 📝 `planning/sprint-{N}-log.md` 파일에 다음을 기록:
   - 무엇을 만들었고 왜 그렇게 만들었는지
   - 이후 리팩토링 후보
   - 알려진 이슈·기술 부채

---

## 지금은 하지 말 것 (Out of Scope)

- 프론트엔드 (Next.js 세팅) — Sprint 3에서 시작
- 실제 계좌 연동 매매 — v2 이후 검토
- 자동매매·주문 실행 관련 코드 — 영원히 금지 (MVP 범위)
- 데이터베이스 추가 (Postgres/Supabase) — Sprint 4 이후
- Docker/Dockerfile — M2 이후
- CI/CD 파이프라인 — M3 이후
- 인증(로그인) — Sprint 5 이후

---

## 참고

- **AWS 강의 요약**이 필요하면 나에게 요청 → `/haru_web/planning/aws_lecture_summary.md`로 정리해서 드립니다.
- **Bedrock 공식 문서**: https://docs.aws.amazon.com/bedrock/
- **기획안 §13** (Bedrock 부록)이 이번 Sprint 1~2의 근거입니다.

---

## 🚦 시작 신호

이 문서를 다 읽고 STEP 1의 4개 파일을 순서대로 정독한 뒤, 아래 4가지를 요약해서
**"준비 완료"** 메시지와 함께 나에게 보내세요:

1. Haru의 한 줄 정의
2. MVP 4개 핵심 기능
3. 재활용 jutopia_data 모듈 5개
4. 배포 옵션 3단(M3/M4/M12+)

내가 **"Sprint 0 시작"** 이라고 답하면 그때부터 코드를 씁니다.
그 전에는 절대 파일을 만들거나 수정하지 마세요.
