---
inclusion: always
---

# 말투 가이드 (Phase F1)

사용자에게 보이는 모든 문구(AI reasoning, message, label, placeholder, 빈 상태, error)는
`planning/tone_guide.md` 가이드를 통과해야 한다.

- 명사형·단문 종결. "~해요", "~입니다", "~보여요" 금지
- 모호어(아직·조금·곧·거의·다소)·수동태·과공손("주세요")·사용자 호명("당신") 금지
- 수치는 단위 포함, 근거 없으면 "데이터 없음"
- 예외: 원칙 5 `DISCLAIMER` 고정 문구, `AI_EVAL_NOTICE`, "(본인 기록)" 라벨
- 백엔드 문구는 `app/core/guardrail.py::has_tone_violation` 테스트로 고정한다
