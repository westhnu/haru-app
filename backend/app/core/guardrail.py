"""응답 후처리 가드 + PII 마스킹.

시스템 프롬프트(1차 방어)가 뚫렸을 때의 2차 방어선이다. Bedrock Guardrail 리소스가 붙은 뒤에도
유지한다 — 모델·리전·Guardrail 설정과 무관하게 코드 레벨에서 항상 같은 결과를 보장하기 위해서다.
"""

import re

DISCLAIMER = "본 정보는 투자 판단의 보조이며, 최종 결정은 사용자에게 있습니다."
# 기획안 §13.5 위반 시 표준 대체 응답
SAFE_REPLACEMENT = "본 서비스는 종목 추천을 제공하지 않습니다. 판단은 본인에게 있습니다."

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
