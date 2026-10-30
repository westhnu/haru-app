# Haru × Kiro 사용 가이드

> 강의(Spec-Driven Development with Kiro 1.0.2)에서 배운 흐름을 Haru의 `bedrock-kb-and-guardrail` 스펙 실행에 맞춘 실전 가이드.
>
> **원칙**: AI가 작업하고, 사람(나)은 결과를 검증하고 통제한다.

---

## 0 · 사전 준비 (한 번만)

### 0-1. Kiro 열기

1. Kiro를 열고 **New Workspace** → `/Users/westhnu/Agent/Claude/haru-app-mono` 선택
2. 스튜던트 작성자(Trust) 설정 — "I trust the authors of the files in this folder"
3. 터미널 기본 프로필을 운영체제에 맞게 설정 (강의처럼 Command Prompt가 아니라 **Mac이면 zsh**)
4. 테마: 다크 추천 (장시간 작업 시 눈 피로 ↓)

### 0-2. Git 초기화 확인

Sprint 2까지 끝났다면 이미 git 저장소입니다. Kiro 터미널에서:

```bash
cd /Users/westhnu/Agent/Claude/haru-app-mono
git status      # clean 상태 또는 Sprint 2 커밋들 확인
git log --oneline -5
```

### 0-3. 새 브랜치 생성

이 스펙은 별도 브랜치에서 진행합니다 (강의: 되돌릴 수 있어야 함):

```bash
git checkout -b spec/bedrock-kb-and-guardrail
```

### 0-4. 크레딧 상태 확인

Kiro 하단 상태바에 크레딧 잔량이 뜹니다. 이 스펙은 **Phase 1~3 저비용, Phase 4~5 고비용**입니다. 잔량이 낮으면 Phase 1부터 조금씩.

---

## 1 · 스티어링 파일 자동 포함 확인

강의 §스티어링 파일 반영:

### 1-1. 포함 방식 확인

| 파일 | inclusion | Kiro에 자동 포함되는 시점 |
|---|---|---|
| `.kiro/steering/product.md` | `always` | 모든 Kiro 대화 |
| `.kiro/steering/tech.md` | `always` | 모든 Kiro 대화 |
| `.kiro/steering/principles.md` | `always` | 모든 Kiro 대화 |
| `.kiro/steering/structure.md` | `fileMatch: **/*.py` | Python 파일 편집·열람 시 |

### 1-2. 검증

Kiro 좌측 사이드바에서 **Steering** 섹션을 열고, 위 4개 파일이 **녹색 체크**로 활성 상태인지 확인하세요.

### 1-3. 글로벌 vs 워크스페이스

- 다른 프로젝트 가서 Haru 원칙이 섞여 오면 안 됩니다
- 이 4개 파일은 **워크스페이스 스티어링**(이 폴더 안에서만 적용). 글로벌 설정은 건드리지 마세요
- 강의: "글로벌·워크스페이스 충돌 시 워크스페이스 우선"

---

## 2 · Kiro Power — 도구 활성·비활성

강의 §Kiro Power 반영. 컨텍스트 윈도우를 아끼는 핵심.

### 2-1. 활성화할 도구 (bedrock-kb-and-guardrail 스펙 기준)

Kiro 설정 → MCP Servers / Tools:

| 도구 | 왜 켬 |
|---|---|
| **File system** | 코드 편집·생성 (필수) |
| **Terminal / Shell** | `uv run pytest`, `aws` CLI (필수) |
| **boto3 / AWS CLI** | Phase 2·4·5에서 필요 |
| **Python LSP** | 타입 체크·자동 완성 |
| **Git** | 커밋, 브랜치 전환 |

### 2-2. 비활성화할 도구 (지금 이 스펙에서는 불필요)

끄면 컨텍스트 윈도우 절약 → 응답 속도·정확도 ↑:

- Notion
- Canva
- Playwright / 브라우저 자동화
- Figma
- Slack / Discord
- 기타 외부 서비스 MCP

### 2-3. Phase별 재조정

Phase 4(AWS 리소스 생성) 진입 전에 **AWS CLI 도구가 켜져 있는지** 다시 확인하세요.

---

## 3 · 자율성 레벨 설정 (하네스 엔지니어링)

강의 §자율성 단계 조절 + §하네스 엔지니어링 반영.

### 3-1. 기본 모드

Kiro 하단 상태바에서 자율성 레벨을 선택:

- **Supervised** (추천 시작): 모든 명령 전에 `Allow / Deny` 묻기
- **Semi-Autopilot**: 안전한 명령(read-only)만 자동, 쓰기는 묻기
- **Autopilot**: 전부 자동 ← **이 스펙에서는 사용 금지**

### 3-2. 명령별 승인 정책 (`steering/principles.md`에 이미 명시)

| 명령 유형 | 승인 방식 |
|---|---|
| `pytest`, `ruff`, `black` | Allow Session |
| 파일 생성·편집 (`haru-app-mono/` 하위) | Allow Once |
| `aws` read-only (`list*`, `get*`, `describe*`) | Allow Once |
| `aws` write (`create*`, `update*`, `delete*`) | **필수 승인** · Allow Always 금지 |
| `.env` 편집 | **필수 승인** · 값 노출 금지 |
| `git commit`, `git push` | Allow Once |
| 외부 네트워크 호출 | Allow Once · 로그 확인 |

### 3-3. 승인 프롬프트 체크 포인트

Kiro가 "Allow this command?" 창을 띄우면:

1. 명령 전문을 읽는다
2. **대상 파일/리소스**가 `haru-app-mono/` 하위인지 확인
3. **파괴적 작업**(rm, DROP, DELETE)인지 확인
4. **시크릿 노출**이 없는지 확인
5. 괜찮으면 `Allow Once`, 아니면 `Deny` + 나에게 보고

---

## 4 · 스펙 실행 흐름 (강의 §스펙 모드)

### 4-1. 스펙 로드

Kiro 좌측 **Specs** 섹션 → `bedrock-kb-and-guardrail`을 클릭하면 3개 파일이 열립니다:

- `requirements.md` (REQ-* 20개 이상)
- `design.md` (아키텍처, 시퀀스, 데이터 모델)
- `tasks.md` (Phase 6개, 태스크 30여 개)

### 4-2. 세 문서 다 읽기 (Kiro에게 시킴)

Kiro 채팅에 다음 한 줄만:

```
.kiro/specs/bedrock-kb-and-guardrail/의 requirements.md, design.md, tasks.md를 순서대로 읽고 한 문장씩 요약해줘. 그리고 아직 코드는 쓰지 마.
```

이 단계가 중요합니다. Kiro가 전체 그림을 머리에 담은 뒤 실행에 들어가야 품질이 높아집니다. 강의: "구현 전에 무엇을 만들지 지정한다."

### 4-3. 요약이 맞으면 Phase 1 시작

```
tasks.md의 Phase 1 (T-101 ~ T-105)을 순서대로 실행해줘. 각 태스크의 DoD(완료 기준)를 통과한 뒤에만 다음으로 넘어가. 실패하면 즉시 멈추고 보고해.
```

### 4-4. 태스크 체크박스

Phase 1이 끝나면 `tasks.md`의 각 체크박스가 `[x]`로 바뀝니다. Kiro가 자동 수정합니다 — 당신은 **git diff로 확인만** 하세요:

```bash
git diff .kiro/specs/bedrock-kb-and-guardrail/tasks.md
```

---

## 5 · Phase별 실행 전략

### Phase 1 — 스키마 확장 (저비용) 🟢

- 코드만, AWS 리소스 X
- 자율성: Semi-Autopilot OK
- 완료 후 커밋: `feat: expand config for Bedrock KB and Guardrail`

### Phase 2 — Bedrock Client Fake 모드 (저비용) 🟢

- Mock 응답 중심, 실호출 없음
- 자율성: Semi-Autopilot
- pytest 통과 확인

### Phase 3 — API 라우터 (저비용) 🟢

- `/api/v1/glossary/ask`, `/api/v1/admin/kb-status`
- 자율성: Semi-Autopilot
- `curl` 테스트 후 커밋

### Phase 4 — AWS 리소스 생성 (고위험) 🔴 ⚠️ **반드시 Supervised**

- S3 버킷, Bedrock KB, Guardrail 생성
- 자율성: **Supervised** 강제
- 각 태스크 Kiro가 명령 실행 전에 반드시 `Allow Once` 프롬프트 뜨는지 확인
- **AWS 비용**: KB 생성 자체는 저렴, 임베딩 호출 시 Titan v2 요금 발생 (73개 용어 × 평균 100 tokens ≈ 몇 센트)
- Guardrail 생성 비용 무료, 호출당 과금

### Phase 5 — 실호출·회귀 통과 (중비용) 🟡

- 실제 Bedrock KB·Guardrail 호출
- 자율성: Supervised
- 실측 curl 2회 → 비용 10센트 미만
- 전체 pytest 통과 후 main 병합

### Phase 6 — Agent Hooks (저비용) 🟢

- 저장 시 자동 테스트 훅 설정
- 자율성: Semi-Autopilot

---

## 6 · Agent Hooks 설정 (강의 §Agent Hooks)

Phase 6에서 설정합니다. Kiro 좌측 **Hooks** 섹션:

### 6-1. 저장 시 회귀 테스트 자동

**Hook 이름**: `guardrail-regression-on-save`

**트리거**: `core/guardrail.py` 저장

**액션**:
```bash
cd backend && uv run pytest tests/regression/test_guardrail_bedrock.py -q
```

**실패 시**: 에디터에 빨간 배너 표시

### 6-2. 원칙 4 (주문 함수) 회귀 자동

**Hook 이름**: `principle-4-check`

**트리거**: `services/hantu_readonly.py` 저장

**액션**:
```bash
cd backend && uv run pytest tests/regression/test_no_order_functions.py -q
```

### 6-3. pre-commit

Phase 6의 T-601을 Kiro가 처리합니다. `pre-commit install` 자동.

---

## 7 · HITL (Human-in-the-Loop) 체크포인트

강의 §휴먼 인 더 루프 반영. 각 체크포인트에서 **반드시 사람이 확인**:

| 체크포인트 | 확인할 것 |
|---|---|
| Phase 1 끝 | `pytest tests/unit/` 통과? `.env.example` 올바른 키? |
| Phase 2 끝 | Fake Bedrock 응답 파싱 정확? 통합 테스트 Green? |
| Phase 3 끝 | `curl /api/v1/glossary/ask` mock 응답 OK? |
| Phase 4 시작 전 | AWS 비용 예상·승인. 콘솔에서 잘못 생성된 리소스 없는지 사전 체크 |
| Phase 4 각 리소스 생성 후 | AWS 콘솔에서 리소스 ID·속성 확인 |
| Phase 5 실호출 전 | Bedrock use case 승인 여전히 유효? 모델 ID 올바름? |
| Phase 5 실측 후 | 응답에 금지 표현 없음? disclaimer 정확? citations 1개+? |
| 병합 전 | 전체 pytest Green? known-issues 업데이트? |

### 사람의 역할 (강의 요지 그대로)

> "AI가 코드를 만들었다고 해서 설계 의도와 일치한다고 단정할 수 없다. 생성된 코드가 기존 지식 기반을 사용하는지, 아니면 문서를 다시 만들고 임베딩·벡터 저장·검색을 새로 수행하는지 확인해야 한다."

Kiro가 Phase 4에서 혹시 "새로 KB를 하나 더 만든다"고 하면 **멈추세요**. 이 스펙은 기존 KB 하나만 사용합니다.

---

## 8 · 크레딧 관리

강의: "크레딧은 작업량에 따라 빠르게 소진된다." Haru 스펙 기준 추정:

| Phase | 예상 크레딧 소모 (Kiro Pro 기준) |
|---|---|
| Phase 1 | 매우 적음 (스키마 확장만) |
| Phase 2 | 적음 (Fake 모드) |
| Phase 3 | 적음 (라우터) |
| Phase 4 | **중간** (AWS CLI 호출 많음, 재시도 가능성) |
| Phase 5 | **중간** (실호출 디버깅 포함) |
| Phase 6 | 적음 |

### 크레딧 아끼는 7가지 팁

1. **스티어링 파일이 짧게 유지되는지** 확인 (`always`인 3개 파일이 너무 길면 매 호출마다 비용 ↑)
2. **Kiro Power에서 불필요 도구 끄기** (§2 참고)
3. **Phase 단위로 세션 분리** — 세션 하나에 Phase 전부 돌리면 컨텍스트 누적 커짐
4. **"코드 안 쓰고 요약만"** 지시로 사전 이해 → 본격 작업 분리
5. **실패하면 즉시 멈추기** — 재시도 루프 돌면 크레딧 폭증
6. **같은 질문 반복 금지** — 모르면 명확한 추가 정보로 한 번에
7. **중간 커밋 자주** — 롤백 가능 상태 유지해서 재작업 방지

---

## 9 · 바이브 모드 vs 스펙 모드

강의: "같은 작업을 다시 재현하기 어렵고, 왜 특정 설계를 선택했는지 이력이 남지 않는다"는 바이브 코딩의 한계.

**이 스펙은 전적으로 스펙 모드**로 진행합니다. Kiro UI에서 모드 전환할 때:

- ✅ **Spec**: `.kiro/specs/*` 사용 — 이 스펙 전체
- ❌ **Vibe**: 즉흥 지시 — 지금 쓰지 않음

중간에 "작은 유틸 함수 하나만 추가" 같은 vibe 유혹이 오면 **참으세요**. 요구사항·설계가 바뀌면 먼저 문서에 반영한 뒤 태스크로 추가합니다.

---

## 10 · 실행 중 흔한 문제와 대응

### 10-1. "Not authorized to perform" (AWS)

강의 §권한 오류 반영.

- Kiro가 띄우는 에러 메시지를 그대로 저에게 공유해주세요
- IAM에서 해당 액션 권한 추가 필요한지, 아니면 역할 신뢰 관계 문제인지 판단

### 10-2. Bedrock 호출이 다시 막힘

Sprint 2에서 겪은 use case 승인 재검증:

```bash
aws bedrock-runtime converse --model-id global.anthropic.claude-sonnet-4-5-v1:0 \
  --messages '[{"role":"user","content":[{"text":"hi"}]}]' --region ap-northeast-2
```

성공 응답이 오면 OK. 다시 `ResourceNotFoundException`이면 콘솔에서 use case 상태 재확인.

### 10-3. KB 동기화가 끝없이 pending

- `aws bedrock-agent get-ingestion-job --knowledge-base-id ... --data-source-id ... --ingestion-job-id ...`로 상세 상태 확인
- 10분 넘으면 멈추고 저에게 보고

### 10-4. Guardrail이 정상 응답까지 차단 (false positive)

- `scripts/guardrail/create_guardrail.py`에서 `contextualGroundingPolicyConfig.threshold`를 0.75 → 0.6으로 낮춰 재배포
- `planning/known-issues.md`에 KI 신설

### 10-5. Kiro가 스티어링을 안 따름

- Kiro 재시작
- Steering 사이드바에서 파일이 녹색 체크인지 확인
- 그래도 안 되면: 채팅에 `.kiro/steering/principles.md를 다시 읽고 요약해줘` 로 강제 재참조

---

## 11 · 완료 후

### 11-1. 커밋 & 머지

```bash
git log --oneline spec/bedrock-kb-and-guardrail
git checkout main
git merge --ff-only spec/bedrock-kb-and-guardrail
git tag spec-kb-and-guardrail-v1
```

### 11-2. 기록

- `planning/spec-kb-guardrail-log.md` 작성 (실측 값, 실제 비용, KI 추가)
- `README.md`의 **진행 상태 문구** 업데이트 (Sprint 2 → Sprint 2 + KB·Guardrail 실물화 완료)

### 11-3. 다음 스펙

- Sprint 2.5: 한투 조회 전용 래퍼 → 새 스펙 `hantu-readonly-wrapper`
- 또는 Sprint 3: 프론트엔드 → 새 스펙 `frontend-nextjs-skeleton`
- 저와 상의해서 결정

---

## 12 · 저(Claude)와의 협업 방법

Kiro가 작업하는 동안 저에게 올려야 할 것:

| 시점 | 공유 |
|---|---|
| Phase 끝날 때마다 | `pytest` 결과·git diff 요약 |
| 승인 프롬프트 애매할 때 | 명령 전문 복사 |
| AWS 콘솔 에러 | 에러 메시지 전문 |
| 설계 변경이 떠오를 때 | 대화 메시지 (파일 수정 전에) |
| 완료 시 | `planning/spec-kb-guardrail-log.md` 초안 |

저는:
- Kiro가 못 보는 큰 그림 (기획안, 다른 Sprint, 비즈니스 관점) 검증
- EARS 요구사항 추가·수정 안 작성
- 실측 데이터 해석
- known-issues·log 작성 가이드

---

## 체크리스트 — 지금 Kiro 열기 전에

- [ ] `git status` clean, `spec/bedrock-kb-and-guardrail` 브랜치 생성
- [ ] Kiro Power에서 불필요 도구 끔
- [ ] 자율성 Supervised 또는 Semi-Autopilot
- [ ] Steering 4개 파일 녹색 체크 확인
- [ ] 크레딧 잔량 확인
- [ ] 저와 Phase 1 시작 전 짧은 사전 공유 (옵션)

준비되면 Kiro 채팅에 §4-2의 요약 지시부터 넣어보세요. 결과를 보고 Phase 1 시작합니다.
