# Haru Backend

FastAPI 기반 Haru API 서버. 로컬 실행 (`backend/` 에서):

```bash
uv sync && cp .env.example .env                 # 의존성 설치 + 환경변수 템플릿 복사
uv run uvicorn app.main:app --reload            # → http://localhost:8000/health
uv run pytest                                   # 테스트
```

린트/포맷: `uv run ruff check . && uv run black --check .`
