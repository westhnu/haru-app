---
inclusion: always
---

# Haru 절대 원칙 (Non-Negotiable)

이 파일에 정의된 원칙은 **어떤 스프린트·기능·리팩토링에서도 예외 없이** 준수한다. 위반하는 코드는 CI에서 자동 실패해야 한다.

## 원칙 1 — 종목 매수·매도 권유 금지, 가격·수익률 예측 금지

- 시스템 프롬프트에 금지 표현 명시 (`core/prompts.py`)
- 응답 후처리에서 금지 표현 감지 시 표준 대체 문구로 교체 (`core/guardrail.py`)
- Bedrock Guardrail Denied Topic으로 **이중 방어** 필수 (이 스펙에서 실물화)
- **회귀 방지 테스트 3종 필수**:
  - `"이 종목을 매수하세요"` → 대체
  - `"내일 오릅니다"` → 대체
  - `"○○원까지 갑니다"` → 대체

## 원칙 2 — 재무 수치는 반드시 출처 인용, AI가 만든 수치 반환 금지

- 모든 재무 응답은 `sources[]` 배열에 최소 1개 (DART URL 등)
- AI 요약에는 코드가 계산한 비율만 전달 (`services/stock_summary_service.py`)
- 요약에 금액이나 근거 없는 % 감지 시 자동 교체 (`summary_source: "template"` 등으로 표기)
- **회귀 방지 테스트**: 3개월치 반환 시 실패하는 케이스 필수 (Sprint 2에서 이미 구축)

## 원칙 3 — Secrets 커밋 금지

- `.env` 파일은 `.gitignore`에 포함
- `.env.example`에는 키 이름만, 값은 빈 문자열
- 커밋 diff에 시크릿 문자열이 있으면 CI 실패 (pre-commit hook)
- 예외 없이 **모든 API 키·토큰**은 환경변수로만 주입
- `jutopia_data/.env`의 다른 12개 변수를 자동 로드하지 않음 (KI-004)

## 원칙 4 — 자동매매·주문 실행 코드 전면 금지

- HantuStock API의 주문 함수 (`bid`, `ask`, `cancel_order`, `send_order` 등) **어떤 파일에서도 import 금지**
- 클래스 상속 대신 명시적 위임(delegation)으로 조회 함수만 노출
- **회귀 방지 테스트**: `hasattr(client, 'bid') is False` 검증 필수
- 매매 스위치 성격의 환경변수(`*_TRADE_ENABLED`, `*_LIVE_ORDER` 등) 자체를 두지 않음
- CI에서 파일명 스캔: `order`·`trade`·`bid`·`ask` 매치 시 실패

## 원칙 5 — 공식 응답 말미 문구

모든 AI 응답 (스트리밍 포함) 말미에 반드시 다음 문구 첨부:

```
본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다.
```

- `core/guardrail.py::enforce_disclaimer(text)` 함수로 강제
- `RagResponse.disclaimer` 필드는 항상 존재, 빈 문자열 금지
- Bedrock Guardrail의 응답 후처리 훅에도 적용

---

## 하네스 (Human-in-the-Loop) 정책

다음 작업은 **반드시 사람의 확인**을 거친다. Kiro의 `Allow Always` 사용 금지 대상:

- AWS 리소스 생성·수정·삭제 (S3, KB, Guardrail, Lambda 등)
- `.env` 편집 또는 시크릿 값 접근
- 프로덕션 배포 스크립트 실행
- 원칙 1~5 관련 코드 변경 (`core/prompts.py`, `core/guardrail.py`, `services/hantu_readonly.py`)
- 외부 API 호출 (실 DART, 실 Bedrock, 실 한투) — 개발 시 mock 우선

## 하네스 (자동 실행 허용) 정책

다음 작업은 `Allow Once` 또는 `Allow Session` 허용 가능:

- pytest 실행
- ruff·black 실행
- 새 파일 생성 (`haru-app-mono/` 하위, 원칙 4 대상 아닌 경우)
- git status·diff (커밋 X)
- structlog 로그 조회

---

## 응답 표현 가이드

### ❌ 금지 표현 (Bedrock Guardrail Denied Topic + core/guardrail.py 이중 필터)

- "이 종목을 매수/매도하세요"
- "○○원까지 오를 것"
- "무조건 수익", "확실한 종목"
- "내일/이번 주 급등", "곧 반등"
- "리딩방", "정보 종목", "한 방"
- 특정 창구를 "스마트머니"로 명시 (§14.7 근거)

### ✅ 허용 표현

- "당신의 체크리스트 7개 중 5개를 충족합니다"
- "DART 2025-1Q 기준 매출은 ○○입니다"
- "결정은 본인의 판단입니다"
- "외국인 투자자가 최근 8영업일 순매수를 유지했습니다" (사실 서술)

---

## 위반 시 조치

1. 원칙 위반 코드 발견 시 **즉시 리버트**
2. `planning/known-issues.md`에 KI 번호 신설, 상세 기록
3. 회귀 방지 테스트 추가 후 다시 커밋
4. 원칙 4 위반은 **main 브랜치에 절대 도달 금지** (CI에서 hard-fail)
