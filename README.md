# Haru (가제) — Personal Investment Workflow OS

> 리서치 · 의사결정 · 회고를 한 곳에서 설계하고 자동화하는 개인 투자자의 워크플로우 OS — *Notion for Investors*.

MTS는 매매에, 증권사 앱·커뮤니티는 정보 소비에 머뭅니다. Haru는 그 사이에 비어 있는 **"왜 사는가"를 정리하는 도구**입니다.
사용자가 만든 워크북·체크리스트·저널로 종목을 검토하고, AI는 **정리·요약·해석만** 담당합니다.
**종목을 추천하지 않으며, 최종 결정은 언제나 사용자에게 있습니다.**

## MVP 4대 기능

| 기능 | 목적 |
|---|---|
| 종목 워크북 | DART 재무·한투 시세·뉴스를 블록으로 모으고 AI 사이드패널로 요약 (Capture · Curate) |
| AI 체크리스트 | 사용자 원칙을 항목별로 충족/미충족/판단 어려움 채점 + 근거 표시 (Decide) |
| 투자 저널 + 가상 포트폴리오 | 결정과 근거를 기록하고 실매매 없이 추적, 월간 회고 (Reflect) |
| 용어 도우미 | 73개 용어 사전 hover 카드 |

## 프로젝트 구조

```
haru_web/
├── README.md
├── docs/                 # 기획서 (읽기 전용)
│   └── Haru_기획안_v1.1.docx
├── planning/             # 스프린트 로그 · 의사결정 · known-issues
│   └── tmp/              # 실험 스크립트 (git 제외)
├── backend/              # FastAPI (Python ≥3.11) — Sprint 0~2
│   ├── app/
│   │   ├── main.py       # 앱 팩토리, CORS, 라우터 등록
│   │   ├── config.py     # Pydantic Settings (환경변수 단일 진입점)
│   │   ├── api/v1/       # 라우터
│   │   ├── core/         # 로깅, 프롬프트, 가드레일
│   │   ├── services/     # Bedrock · DART 등 외부 연동
│   │   └── models/       # Pydantic 입출력 스키마
│   └── tests/
├── frontend/             # (예정) Next.js 14 — Sprint 3
└── shared/               # (예정) OpenAPI / 타입 스키마 — Sprint 4
```

## 로컬 실행

```bash
cd backend && uv sync && cp .env.example .env
uv run uvicorn app.main:app --reload        # → http://localhost:8000/health
uv run pytest
```

## 재활용 자산 매핑 (`/Users/westhnu/Agent/Claude/jutopia_data`, 읽기 전용)

| 모듈 | Haru에서의 역할 |
|---|---|
| `dart_client.py` | 종목코드 → DART 고유번호, 공시·재무제표 조회 (워크북 재무) |
| `HantuStock.py` | 한투 OpenAPI 잔고·보유·거래내역·분봉 — **조회 전용 래퍼(`hantu_readonly.py`)로만 사용** |
| `tavily_search.py` | 종목 뉴스·시장 반응 검색 (워크북 뉴스) |
| `glossary_api.py` + `data/glossary.json` | 73개 용어 사전 (용어 도우미) |
| `stock_chart_data.py` | 일봉·분봉 차트 데이터 (워크북 차트) |

**부재 모듈** — 기획안 §12에 적혀 있지만 실제로는 없는 파일입니다. 지표 계산기 v2에서 자체 구현합니다 ([known-issues KI-001](planning/known-issues.md)).
`dart_financial_loader.py` · `metrics_calculator.py` · `financial_analyzer.py`

## 절대 원칙 (요약)

1. 종목 매수·매도 권유, 가격·수익률 예측 표현 금지 — 시스템 프롬프트 + 응답 후처리 이중 방어
2. 재무 수치는 반드시 출처(DART 등) 인용, AI가 만든 수치는 반환 금지
3. Secrets 커밋 금지 — `.env.example`로 키 목록만 공유
4. 자동매매·주문 실행 코드 전면 금지 — 한투 API는 조회 전용

모든 AI 응답 말미: *"본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."*

## 문서

- 기획안: [`docs/Haru_기획안_v1.1.docx`](docs/Haru_기획안_v1.1.docx) — 특히 §5 MVP, §10 법적 리스크, §13 AWS Bedrock 부록
- 개발 부트스트랩: [`planning/claude_code_bootstrap.md`](planning/claude_code_bootstrap.md)
- 알려진 이슈: [`planning/known-issues.md`](planning/known-issues.md)
- 스프린트 로그: `planning/sprint-{N}-log.md`
