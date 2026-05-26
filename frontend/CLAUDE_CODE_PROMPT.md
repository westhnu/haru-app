# Claude Code 작업 지시 (복붙용)

아래 내용을 그대로 로컬 Claude Code에 붙여넣으세요.

---

너는 `haru_app/frontend`(Next.js 14 App Router + Tailwind) 프로젝트를 **배포하고, 매일 자동 업데이트되도록 스케줄링하고, 종목 페이지에서 데모 없이 실데이터(KIS/DART)가 뜨게** 만드는 일을 맡았어. 코드는 이미 거의 완성돼 있고, 너는 (1) 로컬 검증·실연동 디버깅 → (2) 배포 → (3) 스케줄 연결 순서로 끝내면 돼.

## 프로젝트 개요 (이미 구현돼 있음)

- 화면: 홈(`/`, 시간대별 모닝/이브닝), 브리핑(`/brief/morning`,`/brief/evening`), 이슈·테마 매핑(`/themes`), 종목 상세(`/stock/[code]`).
- 생성/조회 분리: `GET /api/brief?type=`·`GET /api/themes`는 저장본 즉시 반환, `POST /api/brief/generate`·`POST /api/themes`·통합 `POST /api/cron?slot=morning|evening`이 생성·저장.
- LLM: 메인 OpenAI(`OPENAI_API_KEY`, `OPENAI_MODEL` 기본 gpt-5-mini), 보조 Gemini(`GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`, `GEMINI_MODEL` 기본 gemini-2.5-flash) 교차검증/fallback. 이슈수집 Tavily.
- 종목: `lib/kis.ts`(KIS 현재가 FHKST01010100 / 일봉 inquire-daily-itemchartprice FHKST03010100 / 수급 inquire-investor FHKST01010900), `lib/dart.ts`(재무 fnlttSinglAcntAll). 실패 시 mock 폴백.
- 이름→코드: `lib/corpcodes.ts` + `lib/krx-codes.json`(현재 비어 있음). `scripts/build-krx.mjs`가 KRX 전체 매핑 생성.
- 스토어: `lib/store.ts`/`lib/themestore.ts` — 기본 파일(`data/`), `STORAGE=s3`면 `lib/s3.ts`로 S3.
- 배포 보조: `amplify.yml`, `.github/workflows/cron.yml`, `infra/eventbridge-lambda.mjs`, `DEPLOY.md`, `README.md`. 키는 `.env.example`에 있음(이미 .gitignore 처리됨 — 절대 커밋 금지).

## 1단계 — 로컬 검증 & 실연동 디버깅 (가장 중요)

이전 작업은 외부망이 막힌 환경에서 진행돼 **실제 KIS/DART/LLM 호출은 검증되지 않았다.** 네 환경은 네트워크가 되니 반드시 실제로 돌려보고 응답 형식이 다르면 코드를 고쳐라.

```bash
cd haru_app/frontend
cp .env.example .env.local
npm install
npm run build:krx     # lib/krx-codes.json 채워짐(전체 종목). 0개면 KRX 페이지 형식 변경 → 파서 수정
npm run dev
```

다른 터미널에서:
```bash
# 생성(브리핑+테마) — 응답에 ok:true, mode:live 확인
curl -s -X POST "http://localhost:3000/api/cron?slot=morning" | jq .
# 종목 실데이터 — meta.priceMode/indicatorsMode/supplyMode 가 "live" 여야 함
curl -s "http://localhost:3000/api/stock/005930?name=삼성전자" | jq '.profile, .meta'
```

체크 & 수정 포인트:
- KIS 토큰/현재가/일봉/수급이 `live`로 오는지. 안 오면 `lib/kis.ts`의 도메인(`baseUrl`)·tr_id·필드명(`stck_prpr`, `prdy_ctrt`, `per`, `acml_vol`, `stck_bsop_date`, `frgn_ntby_qty` 등)을 실제 응답과 대조해 고쳐라. KIS는 시세조회를 실전 도메인+PROD 키로 하는 게 정석(코드도 그렇게 돼 있음). `meta.warnings`에 원인이 찍힌다.
- DART 재무가 `dartMode:"live"`인지(삼성전자 등 corp_code 매핑 종목). 안 되면 `lib/dart.ts` 연도/계정명 매핑 확인.
- 브리핑이 `mode:"live"`이고 한국어로 자연스러운지. 모델 ID(`gpt-5-mini`/`gemini-2.5-flash`)가 실제와 다르면 `.env.local`의 `OPENAI_MODEL`/`GEMINI_MODEL`로 교정.
- 브라우저에서 브리핑 종목 클릭 → 종목 페이지에 "데모" 표기 없이(국내 종목) 차트·지표·수급·재무가 뜨는지 확인. 해외 지수(S&P500 등)는 KIS 대상 아님(정상).
- 타입체크: `npm run typecheck` (또는 `npx tsc --noEmit`) 0건 유지.

여기서 실연동이 깨끗하게 통과할 때까지 고친 뒤 다음 단계로.

## 2단계 — 배포

호스팅은 둘 중 하나. 사용자에게 물어보고 정해(기본 추천은 A):

- **A. Render/Railway (간단·권장)**: 상시 서버라 파일 저장 그대로 동작(S3 불필요). repo 연결 → Build `npm ci && npm run build`, Start `npm run start`, Node 20 → 환경변수(.env.local의 키들) 입력.
- **B. AWS Amplify (AWS 네이티브)**: 서버리스라 S3 필요. S3 버킷 생성 + 런타임 role에 Get/PutObject 권한 → 환경변수에 위 키들 + `STORAGE=s3`, `S3_BUCKET`, `AWS_REGION=ap-northeast-2`. `amplify.yml` 그대로 사용.

`DEPLOY.md`에 상세 단계가 있으니 참고. 가능하면 `gh` CLI로 repo 생성/푸시까지 자동화하되 **시크릿·`.env*`는 커밋하지 마라.** 배포 도메인을 확보해.

## 3단계 — 자동 스케줄링

`.github/workflows/cron.yml`이 매일 08:00·17:00(KST)에 `/api/cron`을 호출하도록 이미 작성돼 있다. GitHub repo Secrets에 `HARU_URL`(배포 도메인), `CRON_SECRET`(앱 환경변수와 동일 값) 등록만 하면 된다. `gh secret set`로 처리 가능. 등록 후 Actions에서 workflow_dispatch로 1회 수동 실행해 동작 확인.

## 완료 기준 (acceptance)

1. 공개 URL 접속 시 홈/브리핑/테마/종목 페이지 정상.
2. `/api/cron?slot=morning` 수동 호출 → 브리핑·테마가 갱신되고 페이지에 즉시 반영(LLM 대기 없음).
3. 국내 종목 상세에 "데모" 표기 없이 KIS 시세·지표·수급 + DART 재무가 뜸.
4. GitHub Actions 크론이 스케줄로 동작(수동 트리거로 검증).
5. 시크릿이 레포에 커밋되지 않음.

막히면 `README.md`·`DEPLOY.md`를 먼저 읽고, 실패 원인은 `meta.warnings`에서 확인해라.
