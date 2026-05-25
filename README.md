# Haru (가제)

> **Personal Investment Workflow OS — 투자자를 위한 두 번째 뇌**
> 작성일: 2026-05-04 · 단계: 기획 (Planning)

---

## 한 줄 정의

> "리서치 → 의사결정 → 회고까지의 투자 사이클을 한 곳에서 설계·자동화하는 SaaS"

기존 MTS는 매매 중심, 정보 앱은 소비 중심이지만, **'투자 의사결정의 과정'** 자체를 도구화한 한국 서비스는 부재. Haru는 그 빈 공간을 채운다.

---

## 프로젝트 구조

```
haru_web/
├── docs/                # 정식 기획·명세 문서 (.docx, .md)
│   └── Haru_기획안_v1.docx
├── planning/            # 워크인프로그레스 메모, 의사결정 로그
├── artifacts/           # 라이브 아티팩트(HTML) 백업본
├── assets/              # 이미지, 다이어그램, 로고 후보
├── frontend/            # (예정) Next.js 14 + TS + Tailwind
├── backend/             # (예정) FastAPI — jutopia_data 모듈 import
└── shared/              # 타입·스키마 공유 (OpenAPI / Zod)
```

## 기술 스택 (확정)

| 레이어 | 선택 | 이유 |
|---|---|---|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui | SSR/SEO, 차트 인터랙션, 커뮤니티/생태계 |
| State / Data | TanStack Query + Zustand | 서버 상태와 클라 상태 분리 |
| Backend | FastAPI (Python) | `/jutopia_data`의 모듈을 그대로 import 가능 |
| DB | PostgreSQL (Supabase) + Redis | 관계형 + 캐시 |
| AI | Anthropic Claude (메인) | 워크북 요약, 체크리스트 검토 |
| 인프라 | Vercel (FE) · Railway (BE) · Supabase (DB) | 1인 운영 가능한 비용 구조 |
| 외부 연동 | PlayMCP · Notion API · Canva API · 한투 OpenAPI(조회한정) | 사용자 워크플로우 확장 |

## 재활용 자산 (`/jutopia_data`에서)

| Haru 기능 | 재활용 모듈 |
|---|---|
| 종목 리서치 워크북 | `dart_client.py`, `dart_financial_loader.py`, `metrics_calculator.py`, `stock_chart_data.py` |
| 용어 도우미 | `glossary_api.py`, `data/glossary.json` |
| 외부 정보 수집 | `tavily_search.py`, `stock_news_data.py` |
| 시뮬레이터 | `averaging_calculator.py` |
| (선택) 계좌 조회 | `HantuStock.py` *— 매매는 v2에서 검토* |

## 문서

- **메인 기획안**: [docs/Haru_기획안_v1.docx](./docs/Haru_기획안_v1.docx)
- **라이브 아티팩트**: 우측 사이드바에서 `Haru 기획 비주얼 보드` 열기

## 법적 가이드라인 (요약)

1. **종목 직접 추천 금지** — 모든 출력은 "당신의 체크리스트에 따른 정보 정리"로 명시
2. 수익률 보장·미래 가격 예측 표현 금지
3. AI 응답에 표준 면책 텍스트 동봉
4. 자세한 내용은 기획안 §11 법적 리스크 매트릭스 참조
