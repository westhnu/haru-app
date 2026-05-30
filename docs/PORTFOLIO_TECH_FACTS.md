# 하루 HARU — 포트폴리오용 기술 팩트 시트

> 측정된 수치·코드 위치·결정 근거만 정리. 마케팅 표현 X.
> 데이터 수집 일자: 2026-05-28
> 라이브: https://main.dlz2aim8js0bv.amplifyapp.com

---

## 1. 아키텍처 결정 — Amplify SSR ↔ Lambda 분리

| 항목 | 값 |
| --- | --- |
| 페이지 조회 (`/api/brief`, `/api/themes`, `/api/stock`) | AWS Amplify SSR (Next.js 14 App Router) |
| 무거운 LLM 작업 (브리핑·테마 생성) | AWS Lambda (`haru-cron-worker`) — `nodejs20.x`, 1024 MB, 600 s timeout, 178 KB zip |
| 스케줄링 | AWS EventBridge Scheduler — `cron(0 23 * * ? *)` UTC = 08:00 KST / `cron(0 8 * * ? *)` UTC = 17:00 KST |
| 영속 저장 | S3 `haru-store-205474063205` (brief/themes/cache 분리 prefix) |

**왜 분리?** Amplify Hosting Compute 의 게이트웨이 응답 한계가 ~30 초. 브리핑 생성은 LLM·외부 API 가 길어 분리가 강제됨.

**측정** — Lambda 브리핑+테마 생성 1회 소요 (CloudWatch REPORT, 최근 8회):
`74.6 s · 94.6 s · 104.8 s · 109.0 s · 115.8 s · 129.5 s · 134.0 s · 169.2 s` (평균 약 116 s, 게이트웨이 한계의 4배)

**관련 코드**: [frontend/scripts/lambda-handler.ts](frontend/scripts/lambda-handler.ts), [package.json `build:lambda`](frontend/package.json) (esbuild → 838 KB JS → ZIP 178 KB)

---

## 2. 응답 시간 (실측, 라이브 URL)

| 엔드포인트 | 1회차 (cold) | 2회차 | 3회차 |
| --- | --- | --- | --- |
| `GET /api/brief?type=morning` (S3 read-only) | **0.297 s** | **0.194 s** | **0.136 s** |
| `GET /api/stock/005930` (KIS 라이브 + DART 라이브) | **0.934 s** | **0.203 s** | **0.230 s** |

페이지 조회 시 LLM 을 호출하지 않는 **생성·조회 분리** 설계 덕에 사용자 응답은 200 ms 대 유지. 종목 페이지는 KIS + DART 실시간이지만 S3 토큰 캐시 적중 후 200 ms.

---

## 3. 이중 LLM 교차검증 (LLM-as-judge)

| 단계 | 모델 | 역할 |
| --- | --- | --- |
| 생성 | OpenAI `gpt-5-mini` | 브리핑 작성 |
| 검증 | Google `gemini-2.5-flash` | hallucination·원본 불일치·투자권유 표현 cross-check |
| Fallback | Gemini 단독 생성 | GPT 호출 실패 시 |
| 최종 fallback | mock | 두 LLM 모두 실패 시 graceful degradation |

코드: [frontend/lib/pipeline.ts](frontend/lib/pipeline.ts), [frontend/lib/llm.ts](frontend/lib/llm.ts)

---

## 4. 캐싱 전략 — 다중 사용자 / 콜드스타트 대응

자체 구현한 **2-tier 캐시** (`lib/cache.ts`): 모듈 메모리 (warm) + S3 (cold/cross-instance)

| 키 | TTL | 효과 |
| --- | --- | --- |
| `cache/kis-token.json` | KIS 응답의 `expires_in` (~24 h) | KIS OAuth 발급 1 분 cooldown 위반 회피. 모든 Lambda 인스턴스가 토큰 1개 공유 |
| `cache/dart-financials-<corp>.json` | 24 h | DART 호출 절감 (재무는 분기 갱신) |
| `cache/td-quote-<sym>.json` | 5 분 | TwelveData free tier 800 req/day 절약 |
| `cache/td-daily-<sym>-<days>.json` | 30 분 | 동일 |

**라이브 검증** — `cache/kis-token.json` 422 B, 만료까지 24.0 h. 모든 사용자 같은 토큰 공유 중.

**관련 코드**: [frontend/lib/cache.ts](frontend/lib/cache.ts), [frontend/lib/kis.ts:33-58](frontend/lib/kis.ts), [frontend/lib/dart.ts:44-64](frontend/lib/dart.ts), [frontend/lib/twelvedata.ts](frontend/lib/twelvedata.ts)

---

## 5. 외부 API 통합 — 6종 직접 연결

| API | 용도 | 특이사항 |
| --- | --- | --- |
| KIS Open API | 한국 시세·일봉·수급 | tr_id 3종 (`FHKST01010100`, `FHKST03010100`, `FHKST01010900`) 직접 호출, OAuth 토큰 직접 관리 |
| DART | 재무제표 (fnlttSinglAcntAll) | `corp_code` 매핑 직접 (`lib/corpcodes.ts`) |
| TwelveData | 해외 시세·일봉 | NASDAQ/NYSE 등 |
| Tavily | 이슈 수집 (브리핑 입력) | LLM zero-shot 검색 |
| OpenAI | 브리핑 본문 생성 | gpt-5-mini |
| Google Gemini | 교차검증 / Fallback | gemini-2.5-flash |

총 19개 라이브러리 모듈 ([frontend/lib/](frontend/lib/)).

---

## 6. KIS 실시간 데이터 — 발견·해결한 버그 3건

**버그 1: 토큰 발급 cooldown** — 다중 인스턴스 동시 Lambda 콜드스타트 시 KIS 1분 rate limit 직격. → **S3 공유 토큰 캐시** (위 §4)로 해결.

**버그 2: 장중 수급 0주 반환** — KIS `inquire-investor` 가 09:00–15:30 KST 중 당일 누적 0,0,0 응답을 줌. → output 배열에서 **첫 비영(非零) 행** 사용 (직전 마감일 fallback). [lib/kis.ts:204-213](frontend/lib/kis.ts)

**버그 3: KRX 종목코드 스크레이퍼** — KRX가 컬럼 1개 추가하면서 종목코드가 `tds[1]` → `tds[2]`로 밀려 2,765개 매핑이 0개로 됨. → 위치 의존 제거, **모든 td 스캔해서 6자리 숫자인 첫 행** 사용. [scripts/build-krx.mjs:48-55](frontend/scripts/build-krx.mjs)

---

## 7. 다중 통화·다중 시장 UI

| 시장 | 가격 표시 | 데이터 소스 |
| --- | --- | --- |
| KOSPI / KOSDAQ | `"307,000원"` | KIS 라이브 |
| NASDAQ / NYSE | `"$310.85"` | TwelveData 라이브 |
| 기타 | `"123.45 EUR"` 형태 fallback | TwelveData |

해외 종목엔 KIS 수급·DART 재무 탭 **자동 숨김** (의미 없는 빈 카드 제거). 한국 종목엔 그대로 노출. [components/StockDetail.tsx](frontend/components/StockDetail.tsx)

---

## 8. UI 디테일

| 항목 | 구현 |
| --- | --- |
| 글로서리 툴팁 | 302개 용어, viewport-aware positioning (호버 시 단어 위치 측정 후 좌/중/우 자동 정렬) |
| 홈 카드 시간대 전환 | KST 시각 기반 — `08:00–16:59` 모닝 / 그 외 이브닝 표시 |
| 뒤로가기 | `window.history.length > 1` 확인 후 `router.back()` / 직접 URL 진입 시 `/` fallback |
| 모바일 max-width | 480 px 일관 |

---

## 9. 빌드·배포 파이프라인

| 항목 | 값 |
| --- | --- |
| Amplify 자동 빌드 | 평균 **117 초** (최근 10회: 116–129 s 범위) |
| Lambda 번들링 | esbuild — TS + 모든 lib 의존성 → 단일 `.mjs` 838 KB → ZIP **178 KB** |
| Lambda 코드 갱신 | `npm run build:lambda && zip && aws lambda update-function-code` (1 command line) |
| TypeScript 타입체크 | 0 errors |

---

## 10. 보안·격리

| 리소스 | 권한 |
| --- | --- |
| `HaruCronWorkerRole` (Lambda) | S3 R/W on `haru-store-205474063205/*` only + CloudWatch Logs |
| `HaruAmplifyComputeRole` (Amplify SSR) | 동일 S3 prefix 한정 |
| `HaruSchedulerRole` (EventBridge) | `lambda:InvokeFunction` on `haru-cron-worker` ARN only |
| Git 히스토리 secret 노출 | **0건** (별도 audit 결과) |

`CRON_SECRET` 헤더 검증으로 cron HTTP 엔드포인트 보호 — 다만 현재 cron 자체는 EventBridge → Lambda 직접 호출이라 우회됨.

---

## 11. 인프라 자동화

| 작업 | 자동 |
| --- | --- |
| EventBridge → Lambda → S3 → Amplify 페이지 | 매일 2회, 사용자 액션 0 |
| 토큰 발급 | 첫 인스턴스 1회 → 24 h 모든 인스턴스 공유 |
| KRX 종목 매핑 갱신 | 빌드 시 자동 (`npm run build:krx`) |
| 환경변수 baking | next.config.mjs `env` (Amplify SSR 런타임 한계 회피) |

---

## 12. 코드 규모

- TS/TSX 파일: **37 개**
- 총 라인 수: **4,078** (lib + components + app/api + scripts)
- API route handlers: **4 개** (brief / brief/generate / themes / stock/[code])
- lib 모듈: **19 개**

---

## 포트폴리오 후크 (각 항목 1줄로 쓸 때)

> 한국 + 해외 시장 멀티 소스 (KIS · DART · TwelveData · Tavily · OpenAI · Gemini) 를 통합한 Next.js + AWS Lambda 풀스택. KIS OAuth 토큰을 S3 에 공유 캐싱해 다중 인스턴스 환경의 1분 cooldown 위반을 회피했고, Amplify SSR 의 30초 게이트웨이 한계는 EventBridge → Lambda 분리로 해소함. 평균 116초 걸리는 LLM 작업을 백엔드로 옮긴 결과, 사용자 페이지 응답은 200ms 대 유지.

---

**팩트 출처**

- CloudWatch Logs (`/aws/lambda/haru-cron-worker`) — Lambda duration
- AWS Amplify Console — build time
- `curl -w "%{time_total}"` 측정 (3회) — 응답 시간
- 코드: 본 레포 HEAD (`https://github.com/westhnu/haru-app` main)
- S3 직접 확인 — 캐시 객체 / 만료
