# Sprint 1 진입 브리핑 — v1.2 반영 후

> 이 파일은 Sprint 0 완료 검토 결과, Sprint 1 결정 답변, 그리고 v1.2 §14(키움 통합) 반영에 따른 후속 계획을 담는다.
> Claude Code는 이 파일 전체를 컨텍스트로 삼아 Sprint 1을 시작한다.

---

## ✅ Sprint 0 승인

Sprint 0 완료 보고(첫 커밋 `e0d8b89`, 브랜치 `sprint/0-skeleton`) 승인. 3개 완료 기준 모두 통과.

**변경된 결정 사항 승인**:
- 모델 ID `global.anthropic.claude-sonnet-4-5-...` 채택 승인. 서울 리전에 native 4.5가 없고 `apac.` 프로파일도 없음이 확인됨.
- Python 3.12 고정 승인 (uv sync 기본). M3 Lambda 배포 시 런타임 버전에 맞춰 재확인.
- httpx → httpx2 교체 승인. 남은 starlette 경고 1건은 무시.
- HantuStock 조회 래퍼 구현은 Sprint 2 한투 연동 시점으로 이월(known-issues 기록 확인).

---

## 🚦 Sprint 1 결정 답변 (3가지)

### 결정 A — `global.` 프로파일 승인 ✅

- MVP는 공개 정보만 다루고, PII는 Guardrail로 마스킹되므로 리스크 낮음.
- 데이터 처리가 해외 리전에서 이루어질 수 있음을 `planning/known-issues.md`에 `KI-002 · 데이터 처리 리전 이슈`로 반드시 기록.
- 개인 계좌·주민번호·전화번호 등 PII는 절대 프롬프트에 포함되지 않도록 `core/guardrail.py`에 PII 마스킹 함수 사전 배치.

### 결정 B — Sonnet 4.5로 Sprint 1 진행 ✅

- 일단 4.5로 완료. Sonnet 5 비교는 §13.6 RAGAS 파이프라인(M6) 도입 후 수행.
- 모델 ID는 `.env`에서 한 줄 교체로 바꿀 수 있게 `config.py`에서만 참조.

### 결정 C — `sprint/0-skeleton` → `main` fast-forward 병합 ✅

- Sprint 1 시작 전에 병합 완료할 것.
- 병합 후 새 브랜치: `sprint/1-bedrock-poc`

---

## 📘 v1.2 기획안 변경 요약 (Sprint 1에는 참조만)

`docs/Haru_기획안_v1.2.docx`가 갱신됨. 특히 §14 부록 C가 신설됨.

- **§14.1**: 키움 차별화 자산 8개 매트릭스 (개인/외국인/기관 매매동향, 조건검색식, 창구 색깔 등)
- **§14.2**: 톱픽 3개 상세 설계
- **§14.3**: **Sprint 2.5 신설** — 국내 시장 데이터 확장 스프린트 (5개 서브 태스크)
- **§14.5**: 원칙 5(주문 함수 격리) 를 키움 API에도 예외 없이 적용 — 회귀 방지 4단(파일/스코프/문자열/환경변수)
- **§11 로드맵 변경**: M2.5 신설, M4·M6·M9-12에 키움 도구 편입

**Sprint 1에는 키움 통합을 시작하지 않는다.** Sprint 1은 부트스트랩 프롬프트대로 Bedrock RetrieveAndGenerate PoC만 완료한다. 단, Sprint 1에서 만들 파일 구조·인터페이스가 Sprint 2.5 키움 래퍼도 자연스럽게 수용할 수 있게 다음을 미리 고려한다:

- `services/` 폴더 하위에 벤더별 파일 컨벤션 (`bedrock_client.py`, `dart_tool.py`, 향후 `hantu_readonly.py`, `kiwoom_readonly.py`)
- `@tool` 형태의 함수 인터페이스는 Sprint 2에서 도입 예정이지만, 시그니처를 미리 예상해 서비스 함수는 동기 함수 + Pydantic 반환 타입 통일

---

## 🧪 Sprint 1 시작 지시

부트스트랩 프롬프트의 **Sprint 1** 섹션을 그대로 따르세요. 요약:

- `services/bedrock_client.py` — Boto3 팩토리
- `services/rag_service.py` — RetrieveAndGenerate 래퍼 (KB ID 미설정 시 mock 응답)
- `api/v1/poc.py` — `POST /api/v1/poc/ask`
- `core/prompts.py` — 시스템 프롬프트 상수
- `core/guardrail.py` — 응답 후처리 + PII 마스킹 (v1.2 결정 A 반영)
- `pytest` 통합 테스트 2개 (정상 + 금지 표현 필터링)

**추가 지시 (v1.2 반영)**:
- `core/guardrail.py`에 PII 마스킹 함수(`mask_pii(text) -> text`)를 함께 배치. 정규식 기반으로 한국 주민번호(6자리-7자리), 계좌번호(3-2-6 등), 휴대전화(010-xxxx-xxxx)를 마스킹. Sprint 1에서 실제 사용은 없어도 인터페이스는 준비.
- `models/rag.py`에 `RagResponse`, `RagCitation`, `RagRequest` Pydantic 모델을 정의. `citations` 필드는 항상 배열(비어있을 수 있음), `disclaimer`는 항상 존재.
- `test_guardrail.py`에 다음 회귀 방지 테스트 추가:
  - `"이 종목을 매수하세요"` → 대체 문구로 교체
  - `"내일 오릅니다"` → 대체 문구로 교체
  - `"주민번호는 900101-1234567입니다"` → 마스킹 확인

---

## 🚧 Sprint 2 이후 미리 알림

- **Sprint 2** (DART 통합): 부트스트랩 프롬프트대로. 
- **Sprint 2.5** (v1.2 §14.3 신설): 5개 서브 태스크(2.5-A~E). Sprint 2 완료 시점에 별도 브리핑 예정.
  - 필요 크리덴셜: 사용자 본인 키움 앱키/앱시크릿 (Sprint 2.5 진입 전 제공 예정)
- **Sprint 3** (프론트엔드): Sprint 2.5 완료 후 진입.

---

## 📋 완료 시 보고 형식

Sprint 1 완료 시 다음을 보고:
1. ✅ 부트스트랩 프롬프트 체크리스트
2. 🖥 실행 예시: `curl -X POST localhost:8000/api/v1/poc/ask -d '{"query":"PER이 뭐야?"}'` 응답
3. 🧪 pytest 결과 (통합 테스트 2개 + 회귀 테스트 3개 통과)
4. 📝 `planning/sprint-1-log.md`에 다음 기록:
   - Bedrock 실제 호출 성공 여부 (KB 없는 상태에서 mock 모드 확인)
   - PII 마스킹 인터페이스 설계 의도
   - Sprint 2 진입 전 결정받고 싶은 것 (있으면)
5. Git: `sprint/1-bedrock-poc` 브랜치 커밋 로그

준비되면 **"Sprint 1 시작"** 이라고 알려주세요.
