"""응답 후처리 가드 + PII 마스킹.

시스템 프롬프트(1차 방어)가 뚫렸을 때의 2차 방어선이다. Bedrock Guardrail 리소스가 붙은 뒤에도
유지한다 — 모델·리전·Guardrail 설정과 무관하게 코드 레벨에서 항상 같은 결과를 보장하기 위해서다.
"""

import re

DISCLAIMER = "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."
# 기획안 §13.5 위반 시 표준 대체 응답 (말투 가이드 G-4: 명사형)
SAFE_REPLACEMENT = "종목 추천 미제공. 최종 판단은 본인 책임."
# AI 평가 화면 안내 (G-4). 원칙 5의 DISCLAIMER를 대신하지 않는다 — 함께 쓴다.
AI_EVAL_NOTICE = "AI 평가는 참고용. 최종 판단은 본인 책임."
# 결정 1: 종목·재무 질의에서 KB 근거를 못 찾았을 때의 고정 응답
NO_EVIDENCE_STOCK_ANSWER = "확인된 자료 없음. DART 공시 데이터 미색인 가능성."
# KI-020: Bedrock Guardrail이 출력을 막았을 때의 안내. 면책 문구와 달라야 한다.
# 말투 가이드(F1) 미적용: AWS Guardrail 리소스의 blockedOutputsMessaging과 같은 값이어야 해서,
# 바꾸려면 update_guardrail.py --apply(AWS 변경, 사람 승인)를 함께 해야 한다.
# 같으면 enforce_disclaimer가 중복 제거하면서 본문이 비고 사용자는 면책 문구만 본다.
# Guardrail 리소스의 blockedOutputsMessaging도 이 상수로 설정한다 (단일 소스).
GUARDRAIL_BLOCKED_ANSWER = (
    "현재 질문에 대해 신뢰할 수 있는 근거 자료를 찾지 못했습니다. "
    "다른 용어나 더 구체적인 질문으로 시도해 보세요."
)

# 기획안 §10.4 금지 표현 + §13.5 Denied Topic 예시.
# "수익을 보장하지 않습니다", "52주 최고가 8만원까지 상승했습니다" 같은 허용 표현을 오탐하지 않도록
# 권유형 어미·미래형 어미까지 묶어서 매칭한다.
FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r"(매수|매도)\s*하세요",
        r"(매수|매도)\s*(를|을)?\s*(추천|권유|권장)합니다",
        r"(지금|당장)\s*(사|파)세요",
        r"팔아야\s*합니다",
        r"무조건\s*수익",
        r"수익\s*(을|이)?\s*보장(합니다|됩니다|해\s*드립니다)",
        r"내일\s*(오릅니다|오를\s*(것|거)|올라갑니다|급등|상승합니다|상승할\s*(것|거))",
        r"원\s*까지\s*(갑니다|갈\s*(것|거)|간다|오를\s*(것|거)|올라갈|상승할)",
    )
)

_RRN = re.compile(r"(?<!\d)\d{6}\s*-\s*[1-8]\d{6}(?!\d)")
_CARD = re.compile(r"(?<!\d)\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}(?!\d)")
_MOBILE = re.compile(r"(?<!\d)01[016789][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)")
# 은행·증권사마다 자리 구분이 달라(3-2-6, 3-3-6, 6-2-6, 8-2 …) 하이픈 묶음 + 총 자릿수로 판정한다.
# 날짜(2025-09-13, 8자리)는 자릿수 범위 밖이라 마스킹되지 않는다.
_ACCOUNT = re.compile(r"(?<!\d)\d{2,8}(?:-\d{2,8}){1,3}(?!\d)")
ACCOUNT_DIGIT_RANGE = range(10, 15)


def has_forbidden_phrase(text: str) -> bool:
    return any(pattern.search(text) for pattern in FORBIDDEN_PATTERNS)


def enforce_disclaimer(text: str) -> str:
    """면책 문구를 말미에 정확히 한 번만 둔다. 모델이 중간에 넣은 문구는 걷어내고 끝으로 옮긴다."""
    body = text.replace(DISCLAIMER, "").rstrip()
    return f"{body}\n\n{DISCLAIMER}" if body else DISCLAIMER


def apply_output_guard(text: str) -> str:
    """모델 응답을 사용자 응답으로 바꾼다.

    금지 표현이 하나라도 있으면 부분 삭제 없이 통째로 교체한다. 문장 일부만 지우면
    권유 맥락("삼성전자는 지금이 기회")이 남을 수 있기 때문이다.
    """
    safe = SAFE_REPLACEMENT if has_forbidden_phrase(text) else text
    return enforce_disclaimer(safe)


def _mask_account(match: re.Match[str]) -> str:
    digits = sum(char.isdigit() for char in match.group())
    return "[계좌번호]" if digits in ACCOUNT_DIGIT_RANGE else match.group()


def mask_pii(text: str) -> str:
    """LLM 프롬프트·로그로 나가기 전에 한국형 PII를 라벨 토큰으로 치환한다.

    값 대신 라벨을 남기는 이유: 모델이 "계좌번호가 언급됐다"는 맥락은 이해하되
    값은 모르게 하기 위해.
    자릿수가 긴 패턴부터 적용해야 짧은 패턴이 긴 번호의 일부를 먼저 먹지 않는다.
    """
    masked = _RRN.sub("[주민등록번호]", text)
    masked = _CARD.sub("[카드번호]", masked)
    masked = _MOBILE.sub("[전화번호]", masked)
    return _ACCOUNT.sub(_mask_account, masked)


# --- 말투 가이드 (Phase F1.5, planning/tone_guide.md) -------------------------------------
# L1 엄격: AI 생성 텍스트(평가 reasoning·KB 답변 fallback). 명사형·단문 — 환각·사족 방지.
# L2 서비스: 사용자 안내·빈 상태·에러·메시지 템플릿. 자연스러운 평서문·제안형(~요, ~세요) 허용.
# L3 액션: 버튼·탭·상태 라벨·배지. 명사·짧은 동사 — L1 규칙으로 검사한다.
# 원칙 5 면책 문구(DISCLAIMER)·AI_EVAL_NOTICE·SAFE_REPLACEMENT는 고정 문구라 검사 전에 걷어낸다.
TONE_WHITELIST: tuple[str, ...] = (DISCLAIMER, AI_EVAL_NOTICE, SAFE_REPLACEMENT)
# "필요"·"개요"·"중요"처럼 '요'로 끝나는 명사를 오탐하지 않도록 어미를 나열한다.
_POLITE_ENDING = re.compile(
    r"(해요|에요|예요|이야|어요|아요|여요|워요|네요|군요|죠|세요|까요|게요|래요|대요|"
    r"보여요|니다|바랍니다)$"
)
_PASSIVE = re.compile(r"되지\s*않았|처리되었|확인되었|판단되지")
_VAGUE = re.compile(r"아직|조금|곧|거의|다소|대략|약간")
_ADDRESS = re.compile(r"당신|여러분|사용자님")
_L1_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("passive", _PASSIVE),
    ("vague", _VAGUE),
    ("address", _ADDRESS),
    ("over_polite", re.compile(r"주세요|바랍니다")),
)
# L2: "~해 주세요"는 자연스러운 안내라 허용하고, "~바랍니다"·"~주시면 감사"만 과공손으로 본다.
_L2_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("over_polite", re.compile(r"바랍니다|주시면\s*감사")),
    ("passive", _PASSIVE),
    ("vague", _VAGUE),
    ("address", _ADDRESS),
    ("self_reference", re.compile(r"저희\s*Haru|Haru는\s+")),
    # "투자!"처럼 단어 안의 '자!'를 오탐하지 않게 앞이 공백·문두일 때만 본다.
    ("exclamation", re.compile(r"(?:^|[\s\"'(])(?:자|오|좋아요)!")),
)
_SENTENCE_SPLIT = re.compile(r"[.!?。\n]+")
_TRAILING = " \t\"'”’)]»"


def _strip_whitelist(text: str) -> str:
    for fixed in TONE_WHITELIST:
        text = text.replace(fixed, " ")
    return text


def find_tone_violations_l1(text: str) -> list[str]:
    """L1(엄격) 위반 종류 목록. 빈 목록이면 통과. (예: ["ending:보여요", "vague:아직"])"""
    text = _strip_whitelist(text)
    found: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(text):
        m = _POLITE_ENDING.search(sentence.rstrip(_TRAILING))
        if m:
            found.append(f"ending:{m.group(1)}")
    for kind, pattern in _L1_PATTERNS:
        found += [f"{kind}:{m.group(0)}" for m in pattern.finditer(text)]
    return found


def has_tone_violation_l1(text: str) -> bool:
    return bool(find_tone_violations_l1(text))


def find_tone_violations_l2(text: str) -> list[str]:
    """L2(서비스) 위반 종류 목록. 종결 어미(~요·~세요)는 허용한다."""
    text = _strip_whitelist(text)
    found: list[str] = []
    for kind, pattern in _L2_PATTERNS:
        found += [f"{kind}:{m.group(0).strip()}" for m in pattern.finditer(text)]
    return found


def has_tone_violation_l2(text: str) -> bool:
    return bool(find_tone_violations_l2(text))
