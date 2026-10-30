# Sprint 0 Log — 백엔드 스켈레톤

- **기간**: 2026-09-13
- **브랜치**: `sprint/0-skeleton` (base: `main` 초기 커밋)
- **목표**: FastAPI 서버가 로컬에서 뜨고 `/health`가 응답한다.

---

## 1. 무엇을 만들었고 왜

| 파일 | 내용 | 이유 |
|---|---|---|
| `.gitignore` (루트) | Python·AWS·IDE·`.env*` 제외, `!.env.example`, `planning/tmp/` 제외 | 원칙 3(시크릿) · 원칙 4(임시 파일은 산출물 아님). `.env.local` 같은 변형까지 막으려고 `.env.*` 패턴 사용 |
| `backend/pyproject.toml` + `uv.lock` | uv 프로젝트, `requires-python >=3.11` | PO 결정. lock 파일로 의존성 재현성 확보 |
| `app/main.py` | `create_app()` 팩토리 + 모듈 수준 `app` | 테스트·Lambda 어댑터(M3)에서 설정을 바꿔 앱을 새로 만들 수 있게 팩토리로 둠 |
| `app/config.py` | `Settings(BaseSettings)` + `lru_cache` `get_settings()` | "환경변수는 Settings 하나로" 규칙. `LOG_LEVEL`은 `Literal`로 제한해 오타를 기동 시점에 실패시킴 |
| `app/core/logging.py` | structlog `JSONRenderer(ensure_ascii=False)` | JSON 로그 규칙. 한글 이벤트 값이 `\uXXXX`로 깨지지 않게 함 |
| `app/api/v1/health.py` | `GET /health` → `HealthResponse` | 파일은 `api/v1/`에 두되 경로는 prefix 없는 `/health`. 헬스체크는 API 버전과 무관해야 해서 |
| `app/models/health.py` | `HealthResponse(status: Literal["ok"], version)` | 입출력은 Pydantic 모델로 정의 |
| `tests/test_health.py` | TestClient 스모크 테스트 1개 | 완료 기준 |
| `backend/README.md`, 루트 `README.md` | 실행 방법, 구조, 재활용 자산 매핑 | PO 결정 2 |
| `planning/known-issues.md` | KI-001~004 | PO 결정 5 + 컨텍스트 파악 중 발견한 사항 |

`app/services/`, `app/models/` 등 빈 패키지는 Sprint 1 파일이 들어갈 자리로 미리 만들어 둠.

## 2. 완료 기준 검증 결과

```
$ uv run uvicorn app.main:app --reload
INFO:     Uvicorn running on http://127.0.0.1:8000
{"version": "0.1.0", "event": "app_created", "level": "info", "timestamp": "2026-09-13T08:47:01.725965Z"}
INFO:     127.0.0.1:51519 - "GET /health HTTP/1.1" 200 OK

$ curl http://localhost:8000/health
{"status":"ok","version":"0.1.0"}

$ uv run pytest
1 passed, 1 warning

$ uv run ruff check . && uv run black --check .
All checks passed!  /  12 files would be left unchanged.
```

## 3. Bedrock 모델 ID 확인 (PO 결정 4)

### 절차
2026-09-13, 로컬 AWS CLI(v2.34.32)로 계정 `205474063205`, 리전 `ap-northeast-2`에서 **읽기 전용 조회만** 수행. 모델 호출은 하지 않음(요금 발생 없음).

```bash
aws bedrock list-foundation-models --region ap-northeast-2 --by-provider anthropic
aws bedrock list-inference-profiles --region ap-northeast-2
aws bedrock get-foundation-model-availability --region ap-northeast-2 --model-id <id>
```

### 결과
| 모델 | 기반 모델 ID | 서울 리전 호출 방식 | 서울에서 쓸 수 있는 프로파일 |
|---|---|---|---|
| Claude Sonnet 4.5 | `anthropic.claude-sonnet-4-5-20250929-v1:0` | `INFERENCE_PROFILE` 전용 (ON_DEMAND 불가) | `global.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Claude Haiku 4.5 | `anthropic.claude-haiku-4-5-20251001-v1:0` | `INFERENCE_PROFILE` 전용 | `global.anthropic.claude-haiku-4-5-20251001-v1:0` |

- 부트스트랩 초안의 `anthropic.claude-sonnet-4-5-v1:0`은 **존재하지 않는 ID**. 날짜 스탬프가 빠져 있음.
- 서울 리전에 `apac.` 프로파일은 Claude 3.x ~ Sonnet 4(2025-05)까지만 있음. **4.5 이상은 `global.` 프로파일만 제공**.
- 두 모델 모두 `authorizationStatus: AUTHORIZED`, `entitlementAvailability: AVAILABLE`, `regionAvailability: AVAILABLE`.
  단 `agreementAvailability.status`는 `NOT_AVAILABLE`로 나옴. **실제 호출 성공 여부는 Sprint 1에서 1회 호출로 확인 필요.**
- 같은 조회에서 신규 모델도 서울 `global.` 프로파일로 제공 중임을 확인: Sonnet 5, Opus 5, Opus 4.8 등.

### 반영
- `.env.example`, `Settings.bedrock_model_id` 기본값 → `global.anthropic.claude-sonnet-4-5-20250929-v1:0`

## 4. 이후 리팩토링 후보

- **버전 문자열 중복**: `pyproject.toml`과 `app/__init__.py`에 `0.1.0`이 두 번 있음. 패키지로 설치하는 시점(M3 Lambda 번들)에 `importlib.metadata`로 단일화.
- **`.env` 경로가 CWD 기준**: `backend/` 밖에서 실행하면 `.env`를 못 읽음. `__file__` 기준 절대경로로 변경 검토.
- **모델 ID 기본값 중복**: `config.py` 기본값과 `.env.example` 두 곳. 기본값을 없애 필수값으로 만들지 Sprint 1에서 결정 (mock 모드와의 관계 고려).
- **라우터 집계**: v1 라우터가 늘어나면 `api/v1/__init__.py`에 `api_router`를 모아 `prefix="/api/v1"`로 한 번에 등록.
- **CORS `allow_headers=["*"]`**: 인증 도입(Sprint 5) 시 필요한 헤더만 허용하도록 좁히기.

## 5. 알려진 이슈 · 기술 부채

- **pytest 경고 1건 (upstream)**: `starlette.testclient`가 쓰는 `anyio.abc.BlockingPortal` alias deprecation. 우리 코드와 무관, starlette 업데이트 시 해소 예정.
  - 원래 2건이었는데 `httpx` → `httpx2`로 교체해 `StarletteDeprecationWarning` 1건은 해소.
- **Python 버전**: PO 결정은 "3.14로 개발"이었지만 `uv sync`가 venv 인터프리터로 **3.12.13**을 선택함. `.python-version`은 아직 고정하지 않음. M3 Lambda 배포 전에 Lambda Python 런타임 지원 버전에 맞춰 고정 필요.
- **Bedrock agreement 상태 미확인**: §3 참고.
- 기타 기획안·자산 불일치는 [`known-issues.md`](known-issues.md) 참고 (KI-001~004).

## 6. Sprint 1 전 PO 결정 요청

1. **`global.` 추론 프로파일 사용 승인**: 서울 리전에서 Sonnet/Haiku 4.5를 쓰려면 전 세계 리전으로 라우팅되는 `global.` 프로파일밖에 없음. 요청 데이터가 한국 밖에서 처리될 수 있음. MVP 입력은 공개 정보(DART·용어)이고 PII는 Guardrail로 마스킹할 예정이라 승인을 권장.
2. **기본 모델 유지 여부**: 기획안 §13.2대로 Sonnet 4.5로 진행할지, 서울에서 이미 제공 중인 Sonnet 5(`global.anthropic.claude-sonnet-5`)로 올릴지. 환경변수만 바꾸면 되므로 Sprint 1은 4.5로 진행하고, 이후 RAGAS 비교로 결정해도 됨.
3. **`sprint/0-skeleton` → `main` 병합 방식**: 검증 후 fast-forward merge로 할지, 브랜치를 유지할지.
