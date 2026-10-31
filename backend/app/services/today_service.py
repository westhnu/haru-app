"""홈 '오늘의 흐름' 카드 조립 (Phase E).

원칙 1: 결정은 '본인 기록'으로만 표기한다 (AI 권유처럼 읽히지 않게).
날짜·공시 일정·"N일 뒤" 같은 근거 없는 행동 문구는 만들지 않는다 — 데이터에 있는 사실(최근 기록,
체크리스트 미판단 수)만으로 다음 행동을 고른다.
"""

from urllib.parse import quote

from sqlalchemy.orm import Session

from app.db.repositories import checklist_repo, journal_repo, workbook_repo
from app.models.checklist import Checklist
from app.models.journal import Decision, JournalEntry
from app.models.today import NextAction, TodayCard
from app.models.workbook import Workbook

DECISION_LABELS: dict[Decision, str] = {
    "buy": "매수 결정",
    "sell": "매도 결정",
    "hold": "보유",
    "watch": "관망",
}
SELF_RECORD = "본인 기록"


def decision_label(decision: Decision) -> str:
    """예: "buy" → "매수 결정 (본인 기록)"."""
    return f"{DECISION_LABELS[decision]} ({SELF_RECORD})"


def workbook_tab_href(stock_code: str, stock_name: str) -> str:
    return f"/stock/{quote(stock_code)}?name={quote(stock_name)}&tab=workbook"


def _score(cl: Checklist) -> tuple[int, int, int]:
    total = len(cl.items)
    satisfied = sum(1 for i in cl.items if i.status == "satisfied")
    uncertain = sum(1 for i in cl.items if i.status == "uncertain")
    return satisfied, uncertain, total


class TodayService:
    def build_today_card(self, session: Session) -> TodayCard:
        entry = journal_repo.latest_entry(session)
        workbook = workbook_repo.latest_workbook(session)
        if entry is None and workbook is None:
            return TodayCard(
                next_action=NextAction.EMPTY,
                message="오늘 종목 하나를 열어 체크리스트를 채워 보세요.",
                cta_label="종목 검색",
            )
        if entry is not None:
            return self._from_entry(session, entry)
        assert workbook is not None
        return self._from_workbook(workbook)

    def _from_entry(self, session: Session, entry: JournalEntry) -> TodayCard:
        base = f"최근 결정: {entry.stock_name} {decision_label(entry.decision)}."
        context: dict[str, str | int] = {
            "stock_code": entry.stock_code,
            "stock_name": entry.stock_name,
            "decision": entry.decision,
        }
        checklist = (
            checklist_repo.get_checklist(session, entry.checklist_id)
            if entry.checklist_id
            else None
        )
        if checklist is not None:
            satisfied, uncertain, total = _score(checklist)
            context |= {"score_satisfied": satisfied, "score_total": total}
            if uncertain > 0:
                return TodayCard(
                    next_action=NextAction.CHECKLIST_INCOMPLETE,
                    message=(
                        f"{base} 체크리스트 {total}개 중 {satisfied}개 충족, "
                        f"{uncertain}개는 아직 판단하지 않았어요."
                    ),
                    cta_label="체크리스트 이어서 채우기",
                    cta_href=workbook_tab_href(entry.stock_code, entry.stock_name),
                    context=context | {"score_uncertain": uncertain},
                )
        return TodayCard(
            next_action=NextAction.REVIEW_DECISION,
            message=f"{base} 저널에서 결정 근거를 다시 보고 회고를 이어가세요.",
            cta_label="저널 보기",
            cta_href="/journal",
            context=context,
        )

    def _from_workbook(self, workbook: Workbook) -> TodayCard:
        return TodayCard(
            next_action=NextAction.START_NEW,
            message=(
                f"최근 분석: {workbook.stock_name} 워크북. "
                "체크리스트를 채운 뒤 결정을 기록해 보세요."
            ),
            cta_label="체크리스트 열기",
            cta_href=workbook_tab_href(workbook.stock_code, workbook.stock_name),
            context={"stock_code": workbook.stock_code, "stock_name": workbook.stock_name},
        )


def get_today_service() -> TodayService:
    return TodayService()
