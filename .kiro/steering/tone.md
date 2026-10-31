---
inclusion: always
---

# 말투 가이드 (Phase F1.5 — 레이어 분리)

상세: `planning/tone_guide.md`. 새 문구를 쓰기 전에 레이어를 먼저 정한다.

| 레이어 | 대상 | 톤 | 검사 |
|---|---|---|---|
| L1 엄격 | AI 생성 텍스트 (AI 평가 reasoning, Bedrock KB 답변·fallback) | 명사형·단문 | `has_tone_violation_l1` |
| L2 서비스 | 안내·빈 상태·에러·히어로·사용법·placeholder·메시지 템플릿·API error detail | 자연스러운 ~요/~세요 | `has_tone_violation_l2` |
| L3 액션 | 버튼·탭·상태 라벨·배지 | 명사·짧은 동사 | L1 규칙 |

- L2 금지: 과공손(~바랍니다, ~주시면 감사), 수동태, 모호어(아직·조금·곧·거의·다소·대략·약간), 호명(당신·여러분), 자기 지칭 과잉(저희 Haru, Haru는), 감탄사
- whitelist: 원칙 5 `DISCLAIMER`, `AI_EVAL_NOTICE`, `SAFE_REPLACEMENT`
- 결정 라벨 "(본인 기록)", 상태 라벨 "판단 보류"는 유지
