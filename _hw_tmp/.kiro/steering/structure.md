---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# Haru 파일 구조 · Python 코드 스타일

이 파일은 Python 코드를 편집·생성할 때 자동으로 컨텍스트에 포함된다.

## 파일 위치 규칙

- 새 파일은 모두 `/Users/westhnu/Agent/Claude/haru_web/` 하위에만 생성
- `jutopia_data`는 참조 전용, **절대 수정 금지**
- 임시 스크립트는 `planning/tmp/` (git에 포함하지 않음)
- 세션 임시 파일은 최종 산출물로 남기지 않음

## backend 디렉터리 구조 (Sprint 0에서 확정)

```
backend/
├── pyproject.toml           # uv, ruff, black, pytest 설정
├── .env.example             # 키 목록만, 값 없음
├── app/
│   ├── main.py              # 앱 팩토리, CORS, 라우터 등록
│   ├── config.py            # Pydantic Settings 단일 진입점
│   ├── api/
│   │   └── v1/              # 버전별 라우터
│   ├── core/                # 로깅·프롬프트·가드레일
│   ├── services/            # 외부 연동 (bedrock, dart, hantu)
│   └── models/              # Pydantic 스키마
└── tests/
    ├── conftest.py          # Fake 클라이언트 fixture
    ├── unit/
    ├── integration/
    └── regression/          # 원칙 회귀 방지 전용
```

## Python 코드 스타일

- **타입 힌트 필수** — Python 3.11+ 문법 (`list[str]`, `dict[str, Any]`, `X | None`)
- Pydantic v2 모델로 API 입출력 정의 (`BaseModel`)
- 함수는 20줄 이내 유지, 초과 시 분리
- 클래스보다 함수 선호 (단, 클라이언트 팩토리는 클래스 OK)
- **주석은 "왜"만**, "무엇"은 코드가 말하게
- 상수는 대문자 스네이크 (`SYSTEM_PROMPT`, `MAX_TOKENS`)
- 환경변수는 `Settings` 클래스 하나로만, 직접 `os.getenv` 금지
- 매직 넘버 금지 — 상수화

## 명명 규칙

- 모듈: 소문자 스네이크 (`rag_service.py`)
- 클래스: PascalCase (`RagService`, `BedrockClient`)
- 함수: 소문자 스네이크 (`fetch_dart_financial`, `enforce_disclaimer`)
- 상수: 대문자 스네이크 (`SYSTEM_PROMPT_STOCK`)
- 프라이빗: `_` 접두 (`_strip_pii`)

## 외부 호출 필수 패턴

모든 외부 호출(Bedrock, DART, Kiwoom, HTTP)은 다음 6가지 필수:

1. `try/except` 감싸기 (구체 예외 포먼트)
2. `structlog.get_logger().info/warn/error` 로깅
3. 재시도 정책 명시 (횟수, backoff)
4. 타임아웃 명시 (초 단위)
5. 실패 시 fallback 동작 정의 (mock 또는 명시적 502)
6. **PII·secrets 로그 유출 금지** (`hide_input_in_errors` 등)

## 로깅

- `structlog.processors.JSONRenderer` 필수
- 필드: `event`, `service`, `latency_ms`, `model_id`, `cache_hit`, `guardrail_action`, `bedrock_status`
- API 키·토큰·인증정보는 절대 로그하지 않음
- 사용자 프롬프트는 마스킹 후 로그

## 커밋 규칙

- **Conventional Commits** prefix (영문): `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`
- 메시지 본문은 한국어 OK
- 스프린트/스펙 단위 브랜치: `sprint/N-name`, `spec/kb-and-guardrail`
- 한 커밋 = 한 논리 단위

## 테스트

- 실제 AWS·DART 호출 절대 금지 (Fake 클라이언트 주입)
- `pytest.fixture`로 `.env` 격리
- 회귀 테스트는 `tests/regression/` 아래, 원칙 위반 감지가 목적
- 통합 테스트는 `tests/integration/`
- 최소 커버리지 목표: `services/`, `core/`, `api/` 각 80%+

## Import 순서

1. 표준 라이브러리
2. 서드파티 (boto3, fastapi, pydantic, structlog)
3. Haru 내부 (`from app.core...`, `from app.services...`)
4. jutopia 로더 (한정된 파일만)

## 절대 하지 말 것

- `import *` 사용
- print()로 디버깅 (structlog만)
- 매직 넘버·문자열 (상수화 필수)
- 전역 뮤터블 상태 (Settings 제외)
- 원칙 4 대상 함수를 파일 스코프에 노출
- 20줄 초과 함수 방치
- 커밋 메시지 없이 push
