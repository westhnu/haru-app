---
inclusion: always
---

# Haru 기술 스택 (확정)

## Backend (Sprint 0~2 완료, 이 스펙에서 확장)

| 레이어 | 선택 | 근거 |
|---|---|---|
| 언어 | Python 3.12 (`requires-python = ">=3.11"`) | uv sync 기본 |
| 프레임워크 | FastAPI + Uvicorn | 비동기·타입힌트·자동 스키마 |
| 검증 | Pydantic v2 | Settings·요청·응답 통일 |
| AWS SDK | Boto3 | bedrock-runtime, bedrock-agent-runtime, bedrock-agent |
| 로깅 | structlog (JSON) | 관측성 |
| 린트/포맷 | Ruff + Black | pre-commit hook |
| 테스트 | pytest | 통합·회귀·유닛 |
| 패키지 매니저 | uv | pyproject.toml 우선 |

## Frontend (Sprint 3 이후, 지금은 건드리지 않음)

- Next.js 14 (App Router) + TypeScript
- 스타일: Tailwind 3.4 (shadcn/ui는 UI 완성도 보강 필요 시 세션 4-5에서 도입)
- 데이터 패칭: fetch 직접 호출 (세션 4-5에서 TanStack Query 승격 예정)
- 상태: React useState (상태 복잡해지면 Zustand 승격 예정)
- 백엔드 연결: `next.config.mjs` rewrites로 `/backend/*` → `http://localhost:8000/api/v1/*` 프록시
- Node: 20 (Lambda 빌드 대상), 로컬 24

## AWS Bedrock 스택 (이 스펙의 주 대상)

| 리소스 | 선택 | 근거 |
|---|---|---|
| 리전 | `ap-northeast-2` (서울) | 지연 최소화 |
| 추론 프로파일 | Cross-Region Inference (`global.` 접두) | 서울 native 4.5 없음, fallback 자동 |
| 기본 모델 | `global.anthropic.claude-sonnet-4-5-v1:0` | 종목 요약·워크북 |
| 보조 모델 | `global.anthropic.claude-haiku-4-5-v1:0` | 저비용 판정·태깅 |
| 임베딩 모델 | `amazon.titan-embed-text-v2:0` | 벡터 저장소 호환 통일 |
| 벡터 저장소 | **S3 Vector Store** | OpenSearch는 고정비 커서 배제 |
| Guardrail | Bedrock Guardrail 리소스 | 코드 후처리 위 상위 방어 |
| Knowledge Base | Bedrock Knowledge Base | RetrieveAndGenerate API |

## 배포 옵션 (로드맵)

- **M3 알파**: Lambda + Bedrock 직접 호출
- **M4-M6 베타~런칭**: AgentCore Runtime + Strands SDK
- **M12+**: 필요 시 EKS 컨테이너

## 재활용 자산 (`/Users/westhnu/Agent/Claude/jutopia_data`, 읽기 전용, 로더 방식)

- `dart_client.py` — DART 재무·공시 (Sprint 2에서 HTTP만 새로 짜고 계산 로직 참고)
- `HantuStock.py` — 조회 전용 래퍼 필수 (bid/ask/cancel_order 절대 노출 금지)
- `glossary_api.py` + `data/glossary.json` — 73개 용어 사전 (이 스펙의 KB 첫 데이터)
- `tavily_search.py`, `stock_chart_data.py` — 향후 Sprint

## 부재 모듈 (기획안 §12에 있지만 실제 없음)

- `dart_financial_loader.py`, `metrics_calculator.py`, `financial_analyzer.py` — 자체 구현
- KI-001에 기록됨

## 환경 변수 (config.py 단일 진입점)

필수(prod)::

- `APP_ENV` (`local`/`dev`/`staging`/`prod`)
- `AWS_REGION=ap-northeast-2`
- `BEDROCK_MODEL_ID`
- `BEDROCK_HAIKU_MODEL_ID`
- `BEDROCK_EMBEDDING_MODEL_ID`
- `BEDROCK_KB_ID` — 이 스펙에서 신설
- `BEDROCK_GUARDRAIL_ID` — 이 스펙에서 신설
- `BEDROCK_GUARDRAIL_VERSION=DRAFT` (초기)
- `DART_API_KEY`
- `JUTOPIA_DATA_DIR`
- `HARU_KB_S3_BUCKET` — 이 스펙에서 신설
- `HARU_KB_S3_VECTOR_INDEX_ARN` — 이 스펙에서 신설

## 관측성

- structlog JSON 포맷
- Bedrock 호출 지연·토큰·모델 ID 로그 필수
- Guardrail 차단 이벤트 로그 필수 (`guardrail_action`, `blocked_categories`)
- KB 검색 hit/miss 로그
