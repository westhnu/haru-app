from pydantic import BaseModel, ConfigDict, Field

from app.core.guardrail import DISCLAIMER

MAX_QUERY_LENGTH = 1000


class RagRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)


class RagCitation(BaseModel):
    excerpt: str = Field(description="답변 근거로 검색된 원문 발췌")
    source: str = Field(
        description="원본 URL 또는 문서명 (예: s3://haru-kb/dart/005930_2025Q1.pdf)"
    )


class RagResponse(BaseModel):
    answer: str
    # 출처가 없으면 빈 배열로 내려서, 클라이언트가 "출처 없음"을 명시적으로 표시할 수 있게 한다.
    citations: list[RagCitation] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    model_id: str
