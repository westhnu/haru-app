# 하루 HARU — 포트폴리오용 기술 팩트 시트

> 측정된 수치·코드 위치·결정 근거만 정리. 마케팅 표현 X.
> 데이터 수집 일자: 2026-06-09 (최초 작성 2026-05-28)
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
| `GET /api/brief?type=morning` (S3 read-only) | **0.146 s** | **0.106 s** | **0.101 s** |
| `GET /api/stock/005930` (KIS 라이브 + DART 라이브) | **0.686 s** | **0.185 s** | **0.162 s** |

페이지 조회 시 LLM 을 호출하지 않는 **생성·조회 분리** 설계 덕에 사용자 응답은 100~200 ms 대 유지. 종목 페이지는 KIS + DART 실시간이지만 S3 토큰 캐시 적중 후 < 200 ms.

---

## 3. LLM 교차검증 (LLM-as-judge) — 단일 vendor · 다른 모델 family

| 단계 | 모델 | 역할 |
| --- | --- | --- |
| 생성 | OpenAI `gpt-5-mini` | 브리핑 작성 |
| 검증 | OpenAI `gpt-4o-mini` | hallucination·원본 불일치·투자권유 표현 cross-check (다른 model family로 confirmation bias 완화) |
| 메인 일과성 장애 대비 | retry × 2 (1.5 s, 4 s exponential backoff) | rate-limit/timeout/일과성 503 회복 |
| 최종 fallback | mock + S3 skip 패턴 | 3회 재시도 모두 실패 시. 다음 cron 까지 직전 라이브 유지 (§13) |

**왜 멀티 vendor (Gemini) 가 아니라 단일 vendor (OpenAI) + 모델 family 다양화?**

- 운영 단순화 — API key/SDK/응답 schema 1개. 1인 운영에 fit.
- Vendor 자체 outage 는 드물고 짧음. 일과성 rate-limit/timeout 이 압도적으로 흔하며 — 같은 vendor 안의 retry + backoff 가 가성비 좋음.
- 모델 family 다양화(gpt-5-mini ↔ gpt-4o-mini) 만으로도 LLM-as-judge confirmation bias 가 상당 부분 완화.
- Vendor 자체 outage 가 발생하면 어차피 mock-skip 패턴(§13)이 사용자에겐 직전 라이브 노출.
- 실측: 어제 OpenAI quota 초과 + Gemini 503 동시 장애도 mock-skip 으로 정상 처리. 멀티 vendor 의 장점이 실전에선 잘 드러나지 않았음.

코드: [frontend/lib/pipeline.ts](frontend/lib/pipeline.ts), [frontend/lib/llm.ts](frontend/lib/llm.ts), [frontend/lib/thememap.ts](frontend/lib/thememap.ts)

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

## 5. 외부 API 통합 — 5종 직접 연결

| API | 용도 | 특이사항 |
| --- | --- | --- |
| KIS Open API | 한국 시세·일봉·수급 | tr_id 3종 (`FHKST01010100`, `FHKST03010100`, `FHKST01010900`) 직접 호출, OAuth 토큰 직접 관리 |
| DART | 재무제표 (fnlttSinglAcntAll) | `corp_code` 매핑 직접 (`lib/corpcodes.ts`) |
| TwelveData | 해외 시세·일봉 | NASDAQ/NYSE 등 |
| Tavily | 이슈 수집 (브리핑 입력) | LLM zero-shot 검색 |
| OpenAI | 브리핑 생성(`gpt-5-mini`) + 교차검증(`gpt-4o-mini`) | 단일 vendor / 모델 family 다양화 (§3) |

총 20개 라이브러리 모듈 ([frontend/lib/](frontend/lib/)).

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

- TS/TSX 파일: **41 개**
- 총 라인 수: **4,746** (lib + components + app/api + scripts)
- API route handlers: **4 개** (brief / brief/generate / themes / stock/[code])
- lib 모듈: **20 개** (cache · pipeline · kis · dart · twelvedata · llm · tavily · store · themestore · s3 · corpcodes · glossary · usePullToRefresh 등)
- React 컴포넌트: **9 개** (BriefView · ThemesView · StockDetail · PriceChart · SectionCard · BottomNav · SearchDialog · VerifyBadge · GlossaryText)

---

## 13. 외부 의존성 장애 회복 패턴 (resilience)

LLM·외부 API 가 일과성 장애를 일으켜도 사용자 화면이 mock 으로 떨어지지 않게 설계.

**케이스 1 — 메인 모델 일과성 장애 → retry × 2 with exponential backoff**

가장 흔한 케이스 — 같은 vendor 안의 rate-limit / timeout / 일과성 503. `lib/llm.ts` 의 `generateBriefWithGPT` 와 `lib/thememap.ts` 의 `genGPTWithRetry` 가 즉시 → 1.5 s → 4 s 간격으로 3번 시도. retry 가 발생했는지는 `meta.fallbackUsed` 로 응답에 노출.

**케이스 2 — LLM 3회 재시도 모두 실패 시 직전 라이브 유지**

이전: cron → 메인 모델 실패 → mock 결과를 S3 에 덮어쓰기 → 사용자 12시간 동안 mock 화면.
현재: `lambda-handler.ts` 가 `brief.meta.mode === "mock"` 이면 S3 의 직전 객체를 읽어보고, **이전 라이브가 있으면 덮어쓰기 skip**. 첫 실행이라 S3 가 비어있을 때만 mock 저장. 사용자에겐 stale 한 직전 라이브가 그대로 보임. 다음 cron 또는 수동 invoke 에서 회복. (테마도 동일 패턴)

**케이스 3 — KIS 토큰 발급 cooldown** (§4 참조)

**케이스 4 — KIS 장중 수급 0주** (§6 참조)

**케이스 5 — KRX 컬럼 변경** (§6 참조)

코드: [frontend/lib/llm.ts](frontend/lib/llm.ts), [frontend/scripts/lambda-handler.ts](frontend/scripts/lambda-handler.ts)

---

## 14. 모바일 UX 패턴 (4종)

| 패턴 | 구현 | 위치 |
| --- | --- | --- |
| **Bottom navigation** | 4탭 (홈/브리핑/테마/검색), 현재 시각으로 브리핑 destination 결정, `env(safe-area-inset-bottom)` 대응 | [components/BottomNav.tsx](frontend/components/BottomNav.tsx) |
| **Pull-to-refresh** | 자체 hook. `scrollY === 0` 에서 아래로 당기면 √-resistance 적용 → 60 px 임계 → 콜백. 떠 있는 회전 인디케이터 | [lib/usePullToRefresh.ts](frontend/lib/usePullToRefresh.ts) |
| **Sticky mini-header** | `IntersectionObserver` 로 h1 추적, 사라지면 `backdrop-blur` 상단 바에 mini 타이틀 fade-in. -56px rootMargin | BriefView + StockDetail |
| **Page transitions** | `app/template.tsx` — 라우트 마다 remount → CSS `animate-fade-up` 재실행. Chrome View Transitions API rule 도 함께 정의 | [app/template.tsx](frontend/app/template.tsx) + [globals.css](frontend/app/globals.css) |

---

## 15. 다크 모드 (system pref auto-sync)

- `tailwind.config.darkMode: 'class'`
- `layout.tsx` 의 inline script 가 SSR 출력 직전 `prefers-color-scheme` 매칭 → `html.dark` 토글. `change` 이벤트도 listen → OS 다크모드 변경 실시간 반응. 토글 UI 불필요.
- **288 개 `dark:` 변형 적용** (10 컴포넌트). Python 스크립트로 일괄 적용 + 후처리 (중복 dark: 제거, `hover:X dark:Y` → `hover:X dark:hover:Y` 정정).
- 외부 컨테이너 `slate-950`, 내부 컨테이너 `slate-900` 으로 톤 분리.

---

## 16. 종목 검색 (KRX 2,765 + 미국 주요 15)

- `lib/krx-codes.json` (빌드 시 KRX 스크레이핑으로 생성) + 하드코딩 US 티커 리스트 (NVDA, AAPL, MSFT, GOOGL, TSLA, …)
- 검색 매칭: 이름 substring + 코드/심볼 prefix
- 다이얼로그 — backdrop 클릭 / ESC 닫힘, body scroll lock, auto-focus, 키보드/터치 인터랙션
- 검색 결과 클릭 → `/stock/[code]?name=…` 이동
- 코드: [components/SearchDialog.tsx](frontend/components/SearchDialog.tsx)

---

## 17. 가독성 디테일 (typography pass)

| 항목 | 변경 |
| --- | --- |
| 본문 contrast | `text-slate-500` → `text-slate-600~800` (한글 본문 가독성 ↑) |
| 위계 (weight) | 작은 라벨·칩의 `font-black` → `bold/semibold`. 헤딩만 black 유지 |
| 행간 | `leading-6 (1.5)` → `leading-7 / leading-[1.85]`. 한글 본문 호흡 |
| 숫자 정렬 | 가격·등락률·수급·지표·52주 등 모든 수치에 `tabular-nums` (세로 정렬) |
| Glossary 툴팁 | 본문 12 → 13 px, contrast slate-600 → 700, leading 1.7 |
| Viewport-aware 툴팁 | 단어 위치 측정 후 좌/중/우 자동 정렬 + `max-w-[calc(100vw-32px)]` |

---

## 18. 시각 polish (디테일)

| 항목 | 구현 |
| --- | --- |
| **테마 색조 태그** | 6색 팔레트 (sky/emerald/violet/amber/rose/indigo). theme name 해시 → 색상. 같은 테마는 항상 같은 색 유지. 카드 좌측 3px strip + 제목 옆 dot |
| **수치 magnitude 압축** | 시가총액 표기 `"1,748조 373억"` → `"1,748조"` (100조 이상 정수, 미만 1소수점) |
| **Currency-aware 차트 hover** | PriceChart 가 currency prop 받음. 툴팁: KRW `"원"` / USD `"$xx.xx"` / 기타 `"n EUR"` 자동 |
| **Skeleton screens** | 실제 카드 형태와 일치 — BriefView 는 hero + 3 섹션 (아이콘 칩 + 4줄), ThemesView 는 테마 헤더 + 종목 칩 2개, StockDetail 은 헤더 + 차트 + 탭 + 2x2 grid. stagger 100ms |
| **Editorial Home Today 카드** | 정적 PREVIEW 제거 → S3 직접 읽기. oneLine + verifyPassed 배지 + 업데이트 시간. 시간대별 Sunrise/Sunset 아이콘, 좌측 그라데이션 quote line |
| **Non-stock 메타 항목** | 브리핑 본문의 ticker 영역에서 "미국 실적(예시)" 같은 비-종목 항목은 strict 검증 (KR 6자리 또는 US 티커 패턴 매칭) 실패 시 클릭 비활성 정보 카드로 렌더 |

---

## 포트폴리오 후크 (각 항목 1줄로 쓸 때)

> 한국 + 해외 시장 5종 API (KIS · DART · TwelveData · Tavily · OpenAI) 를 통합한 Next.js + AWS Lambda 풀스택. **OpenAI 단일 vendor 안에서 모델 family 다양화** (gpt-5-mini 생성 ↔ gpt-4o-mini 교차검증) 로 LLM-as-judge confirmation bias 를 완화하면서 운영 단순도(키·SDK·schema 1개)도 유지. 일과성 장애는 메인 모델 retry × 2 (exponential backoff) + S3 mock-skip 패턴으로 흡수. KIS OAuth 토큰 S3 공유 캐시로 다중 인스턴스 1분 cooldown 위반 회피. Amplify SSR 30초 게이트웨이 한계는 EventBridge → Lambda 분리로 해소 (평균 116 초 LLM 작업이 가능해짐). 사용자 페이지 응답은 100~200 ms 유지. 다크 모드(system pref auto-sync), 풀-투-리프레시, 종목 검색(2,780+ 티커), sticky mini-header 등 모바일 UX 패턴 적용.

---

**팩트 출처**

- CloudWatch Logs (`/aws/lambda/haru-cron-worker`) — Lambda duration
- AWS Amplify Console — build time
- `curl -w "%{time_total}"` 측정 (3회) — 응답 시간
- 코드: 본 레포 HEAD (`https://github.com/westhnu/haru-app` main)
- S3 직접 확인 — 캐시 객체 / 만료
