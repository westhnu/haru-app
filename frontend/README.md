# 하루(Haru) · Daily 2-Brief PoC

개인 투자자가 본인 증권사에서 직접 결정할 때 필요한 **"무엇에 왜 투자할지"의 정보**를
하루 두 번(아침·저녁) 자동 브리핑으로 받아보는 서비스의 PoC.

> 메인 LLM(gpt-5-mini)이 브리핑을 생성하면, 다른 모델 family의 검증 LLM(gpt-4o-mini)이 hallucination·원본 불일치·
> 투자권유 표현을 **교차검증(LLM-as-judge)** 한다. 데이터 결측 시 "없음"을 명시하고
> disclaimer를 자동 노출해 금융 AI의 평가 책임을 시스템이 지도록 설계했다.

---

## 핵심 설계 — 생성과 조회의 분리

페이지를 열 때마다 LLM을 돌리면 느리다. 그래서 **무거운 생성은 스케줄로 미리 돌려
저장**하고, 사용자 페이지는 저장된 결과만 즉시 읽는다.

```
[스케줄러] ──(매일 08:00 / 17:00 KST)──▶ POST /api/brief/generate?type=morning|evening
                                              │  (Tavily 수집 → gpt-5-mini 생성 → gpt-4o-mini 교차검증)
                                              ▼
                                        저장 (lib/store.ts)
                                              ▲
[사용자] ──▶ GET /api/brief?type=...  ────────┘   ← LLM 호출 없음, 즉시 반환
```

- `GET /api/brief` : 저장된 최신 브리핑을 그대로 반환(빠름). 없으면 `empty: true`.
- `POST /api/brief/generate` : 실제 생성·저장. 스케줄러 또는 화면의 "지금 생성" 버튼이 호출.
- 모든 생성 단계는 **graceful degradation** — 어느 단계가 실패해도 모킹으로 폴백.

---

## 화면 구성

| 경로 | 내용 |
|---|---|
| `/` | 홈 — 슬로건 히어로 + 기능 선택. **현재 KST 시각**에 따라 CTA·Today 카드가 모닝/이브닝으로 자동 전환(14시 기준) |
| `/brief/morning` | 모닝 브리핑 (간밤 글로벌 → 오늘 국내 장) |
| `/brief/evening` | 이브닝 브리핑 (오늘 국내 마감 → 밤 미국 장 대비) |
| `/themes` | 이슈·테마 매핑 — 오늘 이슈를 LLM zero-shot으로 테마·종목에 연결 (신뢰도·동인 키워드·관련 종목) |
| `/stock/[code]` | 종목 상세 — 가격 차트 + 종목정보(시세 요약·투자 지표) + 재무제표(DART). 브리핑·테마의 종목 태그에서 진입 |

디자인: 슬레이트 기반 + 아침→저녁 warm→cool 시그니처 액센트(lucide 아이콘), 이모지 없음, Pretendard.

### 가독성·이해 보조
- 본문 타이포 대비·행간 강화로 장문도 편하게.
- **용어 사전 툴팁**: 브리핑 텍스트의 어려운 용어(PER·골든크로스·공매도 등 302개)에 점선 밑줄 → 호버/탭 시 쉬운 설명. 데이터 출처: `jutopia_data/data/glossary.json`.
- **근거 뉴스**: 클릭 시 새 탭으로 외부 기사 이동.
- **종목 태그**: 클릭 시 종목 상세 페이지로 이동.

### 종목 상세 (`/stock/[code]`)
- 가격 차트(인라인 SVG, 호버 시 날짜·가격 툴팁, 1·3개월·전체), 시세 요약, 투자 참고 지표(양호/보통/주의 평가), 재무제표.
- **시세·지표·수급: KIS(한국투자증권) 라이브** — 국내 6자리 코드는 일봉(`inquire-daily-itemchartprice`)·현재가(`FHKST01010100`)로 실데이터. PER/PBR/EPS/BPS/시총/52주는 현재가 응답에서 추출하고 PER·PBR은 기준 대비 평가. **외국인·기관·개인 순매수(수급 동향)**는 `inquire-investor`(FHKST01010900).
- **재무: DART 라이브** — corp_code 매핑 종목(`lib/corpcodes.ts`)은 실데이터, 그 외 데모.
- 키·호출 실패, 해외 심볼(NVDA 등)·비표준 코드는 자동으로 데모 데이터로 폴백(화면에 "데모" 표기).

---

## 빠른 실행

```bash
cd haru_app/frontend
cp .env.example .env.local     # 키 입력 (아래 참고)
npm install
npm run dev                    # http://localhost:3000
```

처음엔 저장된 브리핑이 없으므로 각 브리핑 화면의 **"지금 생성하기"** 버튼을 누르거나:

```bash
curl -X POST "http://localhost:3000/api/brief/generate?type=morning"
curl -X POST "http://localhost:3000/api/brief/generate?type=evening"
```

> 키가 하나도 없어도 **모킹(DEMO) 데이터로 동작**합니다(구조 확인용).
> 키를 넣으면 실제 LLM 호출(LIVE)로 전환됩니다.

### 환경변수 (`.env.local`)

| 변수 | 용도 | 없을 때 |
|---|---|---|
| `TAVILY_API_KEY` | 이슈 수집 검색 | 모킹 소스 |
| `OPENAI_API_KEY` | 메인 LLM(생성)·교차검증 | 모킹 브리핑, 교차검증 생략 |
| `OPENAI_MODEL` | 모델 ID (기본 `gpt-5-mini`) | 기본값 |
| `VERIFY_MODEL` | 교차검증 모델 ID (기본 `gpt-4o-mini`) | 기본값 |
| `DART_API_KEY` | 종목 재무제표(DART) | 재무 데모 |
| `KIS_APP_KEY_PROD` / `KIS_APP_SECRET_PROD` | KIS 실시간 시세·지표·수급 | 시세·지표·수급 데모 |
| `CRON_SECRET` | 생성 엔드포인트 보호 토큰 | 미설정 시 누구나 호출 가능(운영 시 필수) |
| `STORAGE` / `S3_BUCKET` / `AWS_REGION` | 운영 영속 스토어(S3). `STORAGE=s3`일 때 사용 | 로컬 파일 저장 |

> ⚠️ 실제 키는 `.env.local`(gitignore됨)에만 두세요. `.env.example`은 빈 템플릿으로
> 유지해야 GitHub 노출 사고를 막을 수 있습니다.
> 모델 ID(`gpt-5-mini` / `gpt-4o-mini`)는 공식 문서에서 확인 후 갱신하세요.
> 2026-06-09 `a70a3cf`에서 Gemini 교차검증을 단일 vendor(OpenAI) 모델 family 분리로 교체했다 (KI-025).

---

## 스케줄링 (정해진 시각 자동 생성)

**통합 엔드포인트** `POST /api/cron?slot=morning|evening` 가 해당 시간대의
**브리핑 + 이슈·테마 매핑을 한 번에** 생성·저장한다. 하루 2회 호출하면 전체가 갱신된다.

- `slot=morning` → 모닝 브리핑 + 테마 매핑
- `slot=evening` → 이브닝 브리핑 + 테마 매핑

> 개별 생성도 가능: `POST /api/brief/generate?type=...`, `POST /api/themes`.

### 로컬 / 단일 서버 — cron

```cron
# 서버가 떠 있는 상태에서 (next start)
0 8 * * *  curl -s -X POST -H "x-cron-secret: $CRON_SECRET" "http://localhost:3000/api/cron?slot=morning"
0 17 * * * curl -s -X POST -H "x-cron-secret: $CRON_SECRET" "http://localhost:3000/api/cron?slot=evening"
```

### 배포 — AWS EventBridge Scheduler

1. AWS Amplify Hosting에 배포 → 환경변수(TAVILY/OPENAI/GOOGLE/CRON_SECRET) 등록.
2. EventBridge Scheduler에서 두 스케줄 생성(cron: `0 23 * * ? *`=08:00 KST, `0 8 * * ? *`=17:00 KST, UTC 기준 환산).
3. 타깃: 배포된 `/api/cron?slot=morning|evening` 를 호출하는 Lambda(헤더 `x-cron-secret` 포함).

> ⚠️ Amplify/Lambda는 파일시스템이 휘발성이므로, 운영에서는 `lib/store.ts`·`lib/themestore.ts`
> 의 파일 저장을 **S3 또는 DynamoDB로 교체**해야 결과가 유지된다.

> ⚠️ Amplify/Lambda는 파일시스템이 휘발성이므로, 운영에서는 `lib/store.ts` 의
> 파일 저장을 **S3 또는 DynamoDB로 교체**해야 결과가 유지된다. 인터페이스는 그대로.

---

## 파일 구조

```
frontend/
├── app/
│   ├── page.tsx                  # 홈 (슬로건 + 기능 선택)
│   ├── brief/morning/page.tsx    # 모닝 브리핑 라우트
│   ├── brief/evening/page.tsx    # 이브닝 브리핑 라우트
│   └── api/brief/
│       ├── route.ts              # GET — 저장본 즉시 반환
│       └── generate/route.ts     # POST — 생성·저장 (스케줄러용)
├── components/
│   ├── BriefView.tsx             # 브리핑 화면 공용 (morning/evening)
│   ├── SectionCard.tsx
│   └── VerifyBadge.tsx
├── lib/
│   ├── pipeline.ts               # 수집→생성→검증 오케스트레이션
│   ├── store.ts                  # 저장/조회 (PoC: 파일 / 운영: S3·DDB)
│   ├── tavily.ts · llm.ts · prompts.ts · mock.ts · types.ts
└── data/                         # 생성 결과 저장 위치 (gitignore)
```

## AI 품질 설계 (카뱅 직무 어필 포인트)

- **교차검증 가시화**: 화면 배지로 "교차검증 통과" / "검증 불일치 N건" 표시.
- **Hallucination 방지**: 소스에 없는 내용은 `dataGaps`에 "정보 없음"으로 분리 표기.
- **투자권유 차단**: 프롬프트에서 매수·매도 권유 금지 + 검증 단계에서 `advice_violations` 적발.
- **책임 명시**: 모든 화면 하단에 자본시장법 의식 disclaimer 자동 노출.

## 한계 / TODO

- 실시간 지수·환율·등락률 미연동 (KIS / yfinance 시세는 V2).
- 운영 저장소(S3/DynamoDB) 미연결 — 현재 PoC는 로컬 파일 저장.
- 평가 케이스(TC-A~J) 자동 회귀 테스트 미연결.
