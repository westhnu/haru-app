# 하루 HARU 배포 + 자동 스케줄링 가이드

> 목표: **배포 → 매일 자동 생성(스케줄) → 종목 데모 없이 라이브.**
> 코드·설정·워크플로우는 전부 준비돼 있어요. 콘솔에서 연결·환경변수·버튼만 누르면 됩니다.

## 0. 공통 준비 (어느 호스팅이든)

1. GitHub에 `haru_app/frontend`를 **레포 루트로** push.
2. 키 준비: `OPENAI_API_KEY`, (`GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`), `TAVILY_API_KEY`, `DART_API_KEY`, `KIS_APP_KEY_PROD`, `KIS_APP_SECRET_PROD`, `CRON_SECRET`(아무 긴 랜덤 문자열).
3. **데모 없음은 자동**: 빌드 시 `npm run build:krx`가 돌아 KRX 전체 종목 매핑(`lib/krx-codes.json`)을 만들어요(빌드 환경은 네트워크 OK). 그래서 배포본은 모든 국내 종목이 KIS 라이브로 뜹니다. (해외 지수는 KIS 대상 아님)

---

## 경로 A — Render / Railway (가장 간단, 권장)

상시 실행 서버라 **파일 저장이 그대로 동작 → S3 불필요.**

1. Render(또는 Railway) → New → Web Service → GitHub repo 연결.
2. Build: `npm ci && npm run build` · Start: `npm run start` · Node 20.
3. 환경변수에 0번 키들 입력. (S3 관련 변수는 불필요)
4. 배포 → 도메인 확인(예: `https://haru.onrender.com`).

> Render 무료 플랜은 idle 시 슬립/디스크 초기화가 있을 수 있어요. 안정 운영은 유료 플랜이나 Railway 볼륨 권장.

---

## 경로 B — AWS Amplify (AWS 네이티브 · 포트폴리오용)

서버리스라 파일이 휘발성 → **S3 스토어 필요.**

1. **S3 버킷** 생성(`ap-northeast-2`). Amplify 서버 런타임 role에 해당 버킷 `GetObject`/`PutObject` 권한 부여.
2. Amplify 콘솔 → Host web app → GitHub 연결. 빌드는 레포의 `amplify.yml` 자동 인식. app root가 `haru_app/frontend`인지 확인.
3. 환경변수: 0번 키들 + `STORAGE=s3`, `S3_BUCKET=<버킷명>`, `AWS_REGION=ap-northeast-2`.
4. 배포 → HTTPS 도메인 확인.

---

## 스케줄링 (두 경로 공통) — GitHub Actions 크론

레포에 `.github/workflows/cron.yml`이 이미 있어요(08:00·17:00 KST에 `/api/cron` 호출 → 브리핑+테마 자동 생성·저장).

1. GitHub repo → **Settings → Secrets and variables → Actions**에 등록:
   - `HARU_URL` = 배포 도메인
   - `CRON_SECRET` = 앱과 동일 값
2. 끝. Actions 탭에서 수동 실행(workflow_dispatch)으로 즉시 테스트 가능.

> AWS 네이티브로 가고 싶으면 EventBridge Scheduler로도 가능해요(아래 "대안" 참고).

### 대안: AWS EventBridge

- `infra/eventbridge-lambda.mjs`를 Lambda(Node 20)로 만들고 env `HARU_URL`/`CRON_SECRET` 설정.
- EventBridge Scheduler 2개: `cron(0 23 * * ? *)` 입력 `{"slot":"morning"}`, `cron(0 8 * * ? *)` 입력 `{"slot":"evening"}`.

---

## 확인

- 수동 트리거: `curl -X POST -H "x-cron-secret: $CRON_SECRET" "<도메인>/api/cron?slot=morning"`
- 응답이 `{ "ok": true, ... }`면 성공. 브리핑·테마 페이지에 생성 내용이 즉시 뜸.
- 종목을 눌렀을 때 "데모" 표기가 없으면(국내 종목) KIS 라이브 정상. 비면 화면 하단 "데이터 안내"에서 원인 확인.

---

## 로컬에서 먼저 점검 (권장)

```bash
cd haru_app/frontend
cp .env.example .env.local      # 키
npm install
npm run build:krx               # 전체 종목 매핑 1회 생성 (데모 제거)
npm run dev
# 새 터미널:
curl -X POST "http://localhost:3000/api/cron?slot=morning"
```
