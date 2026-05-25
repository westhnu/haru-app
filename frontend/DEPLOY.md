# 하루 HARU 배포 가이드 (AWS Amplify + EventBridge)

> 콘솔에서 진행하는 단계입니다. 코드/설정은 모두 준비돼 있어요.

## 0. 사전 준비

- GitHub 저장소에 `haru_app/frontend`를 **레포 루트로** push (또는 모노레포면 Amplify에서 app root를 `haru_app/frontend`로 지정).
- 키 준비: `OPENAI_API_KEY`, (`GOOGLE_API_KEY` 또는 `GEMINI_API_KEY`), `TAVILY_API_KEY`, `DART_API_KEY`, `KIS_APP_KEY(_PROD)`, `KIS_APP_SECRET(_PROD)`.
- `CRON_SECRET`: 아무 긴 랜덤 문자열 하나 생성(스케줄러와 앱이 공유).

## 1. S3 버킷 (생성 결과 영속화)

Amplify/Lambda는 파일시스템이 휘발성이라, 스케줄 생성 결과를 S3에 저장합니다.

1. S3 버킷 생성: 예 `haru-store-앱이름` (region `ap-northeast-2`).
2. 공개 불필요(비공개 유지). Amplify 앱의 서버 런타임 role에 이 버킷 `GetObject`/`PutObject` 권한 부여.

## 2. Amplify Hosting

1. AWS Amplify 콘솔 → **Host web app** → GitHub 저장소 연결.
2. 빌드 설정: 레포의 `amplify.yml` 자동 인식(Next.js SSR). app root가 `haru_app/frontend`인지 확인.
3. **환경변수** 등록:
   - `OPENAI_API_KEY`, `GEMINI_API_KEY`(또는 `GOOGLE_API_KEY`), `TAVILY_API_KEY`, `DART_API_KEY`
   - `KIS_APP_KEY_PROD`, `KIS_APP_SECRET_PROD` (실전 시세 조회용)
   - `CRON_SECRET`
   - `STORAGE=s3`, `S3_BUCKET=<버킷명>`, `AWS_REGION=ap-northeast-2`
4. 배포 → HTTPS 도메인 확인(예: `https://main.xxxx.amplifyapp.com`).

## 3. 스케줄 Lambda

1. Lambda 함수 생성(Node.js 20.x) → 코드는 `infra/eventbridge-lambda.mjs` 붙여넣기.
2. 함수 환경변수: `HARU_URL=<Amplify 도메인>`, `CRON_SECRET=<위와 동일>`.
3. 타임아웃 2분 권장.

## 4. EventBridge Scheduler (하루 2회)

KST 기준 시각을 UTC로 환산해 두 개의 스케줄을 만들어 위 Lambda를 타깃으로 지정합니다.

| 스케줄 | KST | cron(UTC) | 입력(JSON) |
|---|---|---|---|
| 모닝 | 08:00 | `cron(0 23 * * ? *)` | `{ "slot": "morning" }` |
| 이브닝 | 17:00 | `cron(0 8 * * ? *)` | `{ "slot": "evening" }` |

- 각 스케줄의 "대상 입력"에 위 JSON을 넣으면 Lambda가 `/api/cron?slot=...`을 호출 → 브리핑 + 테마 매핑이 생성·저장됩니다.

## 5. 확인

- 스케줄 수동 실행 또는: `curl -X POST -H "x-cron-secret: $CRON_SECRET" "<HARU_URL>/api/cron?slot=morning"`
- 앱에서 모닝 브리핑·테마 페이지가 생성된 내용으로 즉시 뜨면 성공.

## 참고

- 로컬/단일 서버는 `STORAGE` 미설정(파일 저장) + cron으로 동일하게 운영 가능(README 참고).
- KIS 시세가 비면 화면 하단 "데이터 안내"(`meta.warnings`)에서 원인 확인.
