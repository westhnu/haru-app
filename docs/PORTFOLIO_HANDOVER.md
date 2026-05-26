# 하루 HARU — 포트폴리오 자료 핸드오버

> Notion 페이지 작성용으로 이 문서를 그대로 활용하면 됩니다.
> 작업 일자: 2026-05-26
> 작업자: Claude Code (서현우 / @westhnu 의 요청)

---

## 0. 원본 요청 정리

다음 3종이 필요했습니다.

1. **공개 배포 URL** — haru_app/frontend 배포 후 주소
2. **핵심 화면 스크린샷 PNG 4장** — 데이터가 채워진 상태로, 데스크톱 1280px, full-page
   - 홈 `/`
   - 모닝 브리핑 `/brief/morning`
   - 종목 상세 `/stock/005930?name=삼성전자`
   - 이슈·테마 매핑 `/themes`
3. **(선택) 아키텍처 SVG → PNG 변환** — `haru_app/docs/haru_architecture.svg`

추가 요구: 종목 페이지는 **KIS 라이브 모드**(데모 표기 없음)로 캡처. mock 으로 떨어지면 화면 하단 "데이터 안내"의 원인 메시지도 함께 보고.

---

## 1. 결과물 인벤토리

### 1-1. 공개 배포 URL

| 항목 | URL |
| --- | --- |
| **메인 앱 (AWS Amplify SSR)** | https://main.dlz2aim8js0bv.amplifyapp.com |
| **API 헬스체크** | https://main.dlz2aim8js0bv.amplifyapp.com/health |
| **모닝 브리핑** | https://main.dlz2aim8js0bv.amplifyapp.com/brief/morning |
| **이브닝 브리핑** | https://main.dlz2aim8js0bv.amplifyapp.com/brief/evening |
| **테마 매핑** | https://main.dlz2aim8js0bv.amplifyapp.com/themes |
| **종목 상세 (삼성전자 예시)** | https://main.dlz2aim8js0bv.amplifyapp.com/stock/005930?name=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90 |

### 1-2. 스크린샷 4종

| # | 파일 경로 | 화면 |
| --- | --- | --- |
| 1 | `haru_app/screenshots/01_home.png` | 홈 / |
| 2 | `haru_app/screenshots/02_brief_morning.png` | 모닝 브리핑 |
| 3 | `haru_app/screenshots/03_stock_samsung.png` | 종목 상세 (삼성전자, 005930) — **KIS 완전 라이브 모드** |
| 4 | `haru_app/screenshots/04_themes.png` | 이슈·테마 매핑 |

- 해상도: 1280×N (full-page) · device scale factor 2× retina
- 캡처 도구: Playwright + Chromium (headless)
- 캡처 시 데이터: cron 으로 사전 생성된 LLM 라이브 데이터 (mock 아님)

### 1-3. 아키텍처 다이어그램

| 파일 | 비고 |
| --- | --- |
| `haru_app/docs/haru_architecture.svg` | 원본 (벡터) |
| `haru_app/docs/haru_architecture.png` | PNG 변환본 (1600×N, 2× retina) — Playwright/Chromium 렌더링 |

---

## 2. 데이터 검증 — KIS 라이브 모드 확인

### 2-1. 검증 방법

```
curl -s "https://main.dlz2aim8js0bv.amplifyapp.com/api/stock/005930?name=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90"
```

응답 `meta` 필드:

```json
{
  "priceMode": "live",
  "dartMode": "live",
  "indicatorsMode": "live",
  "supplyMode": "live",
  "warnings": []
}
```

**모두 `live`, warnings 빈 배열**. 최종 스크린샷은 이 상태에서 캡처됨.

### 2-2. ⚠️ 캡처 중 마주친 이슈 — KIS 토큰 발급 Rate Limit

**문제**: 첫 캡처 시도에서 종목 페이지가 mock 모드로 떨어졌습니다.

**`/api/stock/005930` 응답 (mock 시 메시지)**:

```json
{
  "priceMode": "mock",
  "dartMode": "live",
  "indicatorsMode": "mock",
  "supplyMode": "mock",
  "warnings": [
    "KIS 일봉 실패: KIS 토큰 발급 실패 (403) → 데모 시세",
    "KIS 현재가 실패: KIS 토큰 발급 실패 (403) → 데모 지표",
    "KIS 수급 실패: KIS 토큰 발급 실패 (403) → 데모 수급",
    "시세·거래량은 데모 데이터입니다",
    "투자 참고지표는 데모 값입니다"
  ]
}
```

**원인**: KIS Open API 는 OAuth 토큰 발급에 약 1분 쿨다운이 있습니다. 짧은 시간 안에 다음이 동시에 발생했을 때 rate limit 에 걸렸습니다.

1. Lambda 가 cron 실행 (브리핑 + 테마 생성 — KIS 호출 다수)
2. 검증용으로 직접 `/api/stock/...` 호출
3. Playwright 가 스크린샷 위해 또 호출

**해결**: 60초 폴링으로 `priceMode/dartMode/indicatorsMode/supplyMode` 모두 `live` 가 될 때까지 대기한 뒤 재캡처 → `03_stock_samsung.png` 는 완전 라이브 상태로 저장됨.

**운영 권장**: 시연 5–10분 전에 종목 페이지를 한 번 열어 토큰을 캐싱해두면 시연 중에 rate limit 안 걸림.

---

## 3. 추가로 잡은 이슈

스크린샷 작업 도중 사용자가 보고한 또 다른 이슈와 함께 처리했습니다.

### `POST /api/brief/generate` 401 / `POST /api/themes` 401

**증상**: 브라우저에서 보고됨.

```
719-b7f0d33cbdbcdcc6.js:1
POST https://main.dlz2aim8js0bv.amplifyapp.com/api/brief/generate?type=evening 401 (Unauthorized)
```

**원인**: 두 라우트 모두 `CRON_SECRET` 헤더 검증이 있고 UI 의 "지금 생성"/"지금 분석" 버튼이 헤더 없이 호출함.

**아키텍처 맥락**: 오늘 진행 과정에서 cron 을 **AWS Lambda(`haru-cron-worker`) + EventBridge Scheduler** 로 이전 (Amplify SSR Lambda 의 30 초 게이트웨이 타임아웃 회피). UI 의 수동 생성 버튼은 이 구조에서 더 이상 호출할 대상이 없습니다. 브라우저에서 Lambda 를 직접 invoke 하는 건 IAM 자격증명 노출 위험 때문에 비추.

**조치**:
- `frontend/components/BriefView.tsx` · `ThemesView.tsx`: `generate` 함수가 `POST` 호출 대신 `load()` (= `GET /api/brief` 또는 `GET /api/themes`) 만 실행
- 버튼 라벨: `"지금 생성/분석"` → `"새로고침"`
- 빈 화면 안내문에 cron 일정 명시 (`매일 08:00·17:00 KST 자동 갱신`)

**배포**: 커밋 + Amplify 자동 빌드 통해 적용.

---

## 4. 인프라 구조 (재확인용)

cron 아키텍처가 오늘 한 번 바뀌었기 때문에 최신 상태를 정리합니다.

```
EventBridge Scheduler (해당 시각 도래)
        │
        ├── haru-morning  cron(0 23 * * ? *)   UTC = 08:00 KST
        └── haru-evening  cron(0 8  * * ? *)   UTC = 17:00 KST
                │
                ▼
        Lambda: haru-cron-worker (nodejs20.x, 1024MB, 600s)
                │  - Tavily 이슈 수집
                │  - OpenAI gpt-5-mini 브리핑 생성
                │  - Gemini 2.5-flash 교차검증
                │  - 테마 매핑
                ▼
        S3: haru-store-205474063205
            ├── brief-morning.json
            ├── brief-evening.json
            └── themes-latest.json
                │
                ▼
        Amplify SSR (Next.js 14 App Router)
            └── /api/brief, /api/themes, /api/stock/[code] — 페이지 요청 시 S3 읽고 KIS·DART 라이브 호출
```

| 리소스 | 이름 / 식별자 |
| --- | --- |
| Amplify App ID | `dlz2aim8js0bv` |
| Lambda | `haru-cron-worker` (`ap-northeast-2`) |
| S3 Bucket | `haru-store-205474063205` |
| EventBridge | `haru-morning`, `haru-evening` |
| IAM Role (Lambda) | `HaruCronWorkerRole` |
| IAM Role (Amplify Compute) | `HaruAmplifyComputeRole` |
| IAM Role (Scheduler) | `HaruSchedulerRole` |

LLM 모델:
- 메인: `gpt-5-mini` (코드 디폴트, Lambda env 미설정 시 자동 사용)
- 보조/교차검증: `gemini-2.5-flash`

---

## 5. Notion 페이지에 그대로 옮길 때 추천 구조

```
📄 하루 HARU — 포트폴리오 자료
 ├── 1. 라이브 데모
 │    ├── 메인 URL (https://main.dlz2aim8js0bv.amplifyapp.com)
 │    └── 주요 페이지 4종 링크
 ├── 2. 화면 캡처 (4장 임베드)
 │    ├── 01_home.png
 │    ├── 02_brief_morning.png
 │    ├── 03_stock_samsung.png
 │    └── 04_themes.png
 ├── 3. 시스템 아키텍처
 │    └── haru_architecture.png 임베드
 ├── 4. 기술 스택 & 의사결정
 │    ├── Next.js 14 App Router + AWS Amplify SSR
 │    ├── AWS Lambda + EventBridge (cron 분리 — 30s gateway 한계 회피)
 │    ├── S3 (브리핑·테마 영속 저장)
 │    ├── OpenAI gpt-5-mini 메인 / Gemini 2.5-flash 교차검증
 │    └── KIS + DART 실시간 시세·재무 데이터
 └── 5. 시연 시 유의사항
      └── KIS 토큰 발급 쿨다운 — 시연 5분 전 페이지 한 번 열어두기
```

스크린샷은 Notion 에 직접 업로드하면 됩니다 (파일 경로: `/Users/westhnu/Agent/Claude/haru_app/screenshots/`).

---

## 6. 운영·유지보수 메모

| 작업 | 명령어 |
| --- | --- |
| Lambda 수동 호출 (테스트) | `aws lambda invoke --function-name haru-cron-worker --payload '{"slot":"morning"}' --cli-binary-format raw-in-base64-out --region ap-northeast-2 /tmp/out.json` |
| Lambda 로그 확인 | `aws logs tail /aws/lambda/haru-cron-worker --region ap-northeast-2 --since 1h --format short` |
| Lambda 코드 갱신 | `cd frontend && npm run build:lambda && cd dist && zip lambda.zip lambda-handler.mjs package.json && aws lambda update-function-code --function-name haru-cron-worker --zip-file fileb://lambda.zip --region ap-northeast-2` |
| 스케줄 일시 정지 | `aws scheduler update-schedule --name haru-morning --state DISABLED --region ap-northeast-2` |
| 환경변수 변경 | Amplify 콘솔 → App settings → Environment variables → 저장 후 재배포 |

---

**문의/추가 요청은 본 레포 ([github.com/westhnu/haru-app](https://github.com/westhnu/haru-app)) 에 issue 로 남기거나 직접 메시지 주세요.**
