# Haru Backend

FastAPI 기반 Haru API 서버. 로컬 실행 (`backend/` 에서):

```bash
uv sync && cp .env.example .env                 # 의존성 설치 + 환경변수 템플릿 복사
uv run uvicorn app.main:app --reload            # → http://localhost:8000/health
uv run pytest                                   # 테스트
```

린트/포맷: `uv run ruff check . && uv run black --check .`

## 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/health` | 헬스체크 |
| POST | `/api/v1/poc/ask` | Bedrock KB RetrieveAndGenerate PoC. `BEDROCK_KB_ID`가 비어 있으면 mock 응답 |

```bash
curl -X POST localhost:8000/api/v1/poc/ask -H 'Content-Type: application/json' -d '{"query":"PER이 뭐야?"}'
```

`BEDROCK_KB_ID`를 채우면 실제 Bedrock을 호출합니다(요금 발생). AWS 자격증명은 boto3 기본 체인을 사용합니다.
