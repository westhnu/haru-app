from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.guardrail import DISCLAIMER

MAX_QUERY_LENGTH = 1000

ContextType = Literal["stock", "glossary", "general"]
# knowledge_base    KB 근거를 인용한 답변
# general_knowledge 근거 없이 모델 일반 지식으로 답변 (glossary·general만 허용)
# no_evidence       근거가 없어 답변하지 않음 (stock)
# mock              KB 미설정 개발 모드
# guardrail_blocked Bedrock Guardrail이 응답을 차단함 (KI-020)
AnswerSource = Literal[
    "knowledge_base", "general_knowledge", "no_evidence", "mock", "guardrail_blocked"
]
# Bedrock Guardrail이 응답에 개입했는지. None은 Guardrail 리소스 미연결(Phase 4 이전) 상태.
GuardrailAction = Literal["none", "intervened"]
# summary_source는 source(AnswerSource)와 다른 레이어의 메타데이터다 (결정 B, 분리).
#   source          : 근거가 어디서 왔는가 (knowledge_base/general_knowledge/no_evidence/mock)
#   summary_source  : 응답이 어떻게 생성됐는가 (bedrock/template/cached_bedrock/general_knowledge)
# 겹치는 값은 general_knowledge 하나뿐이고 나머지는 서로 다른 질문에 답한다.
SummarySource = Literal["bedrock", "template", "cached_bedrock", "general_knowledge"]


class RagRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=MAX_QUERY_LENGTH)
    context_type: ContextType = "general"


class RagCitation(BaseModel):
    excerpt: str = Field(description="답변 근거로 검색된 원문 발췌")
    source: str = Field(
        description="원본 URL 또는 문서명 (예: s3://haru-kb/dart/005930_2025Q1.pdf)"
    )
    # Phase 5의 유사도 임계 판정(REQ-RAG-03/04)에 쓴다. 구버전 경로는 생략 가능하도록 옵션.
    similarity: float | None = Field(default=None, ge=0.0, le=1.0)


class RagResponse(BaseModel):
    answer: str
    # 출처가 없으면 빈 배열로 내려서, 클라이언트가 "출처 없음"을 명시적으로 표시할 수 있게 한다.
    citations: list[RagCitation] = Field(default_factory=list)
    source: AnswerSource
    disclaimer: str = DISCLAIMER
    model_id: str
    # 신규 필드는 전부 default를 둬 기존 생성 지점(rag_service, 테스트)을 깨지 않는다.
    context_type: ContextType = "general"
    guardrail_action: GuardrailAction | None = None
    is_mock: bool = False
    # default=template: mock·거절 등 비(非)Bedrock 생성 경로의 기본값. 기존 생성 지점을 깨지 않는다.
    summary_source: SummarySource = "template"

    @field_validator("disclaimer")
    @classmethod
    def _disclaimer_not_empty(cls, value: str) -> str:
        # 원칙 5: 면책 문구는 어떤 경로로도 빈 문자열이 될 수 없다.
        if not value.strip():
            raise ValueError("disclaimer는 빈 문자열일 수 없습니다")
        return value
