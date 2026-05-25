// ── 국내(KRX) 개장일·날짜 유틸 ──────────────────────────────
// 주말 감지는 정확하고, 공휴일은 연 1회 갱신이 필요한 근사 목록이다.
// ⚠️ 음력·대체공휴일은 매년 확인해 갱신할 것. 누락돼도 주말 처리는 항상 동작한다.

const HOLIDAYS: Record<string, string> = {
  // 2026 (best-effort, 검증 후 갱신 권장)
  "2026-01-01": "신정",
  "2026-02-16": "설날 연휴",
  "2026-02-17": "설날",
  "2026-02-18": "설날 연휴",
  "2026-03-01": "삼일절",
  "2026-03-02": "삼일절 대체휴일",
  "2026-05-05": "어린이날",
  "2026-05-24": "부처님오신날",
  "2026-05-25": "부처님오신날 대체휴일",
  "2026-06-06": "현충일",
  "2026-08-15": "광복절",
  "2026-08-17": "광복절 대체휴일",
  "2026-09-24": "추석 연휴",
  "2026-09-25": "추석",
  "2026-09-26": "추석 연휴",
  "2026-10-03": "개천절",
  "2026-10-05": "개천절 대체휴일",
  "2026-10-09": "한글날",
  "2026-12-25": "성탄절",
};

const WEEKDAY_KO = ["일", "월", "화", "수", "목", "금", "토"];

export interface MarketDateInfo {
  date: string; // YYYY-MM-DD (KST)
  label: string; // "2026년 5월 25일 (월)"
  weekday: string; // 월~일
  isWeekend: boolean;
  holiday?: string; // 휴일명 (있으면 휴장)
  isOpen: boolean; // 국내 증시 개장 여부
  note?: string; // 휴장 안내 문구
}

function kstYmd(d: Date): { y: number; m: number; day: number; wdShort: string } {
  const date = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d); // "2026-05-25"
  const wd = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Seoul",
    weekday: "short",
  }).format(d); // "Mon"
  const [y, m, day] = date.split("-").map(Number);
  return { y, m, day, wdShort: wd };
}

const WD_MAP: Record<string, number> = {
  Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6,
};

export function getMarketDateInfo(d: Date = new Date()): MarketDateInfo {
  const { y, m, day, wdShort } = kstYmd(d);
  const dow = WD_MAP[wdShort] ?? new Date(y, m - 1, day).getDay();
  const dateStr = `${y}-${String(m).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  const weekday = WEEKDAY_KO[dow];
  const isWeekend = dow === 0 || dow === 6;
  const holiday = HOLIDAYS[dateStr];
  const isOpen = !isWeekend && !holiday;

  let note: string | undefined;
  if (holiday) note = `오늘은 ${holiday}로 국내 증시가 휴장합니다.`;
  else if (isWeekend) note = "주말에는 국내 증시가 열리지 않아요.";

  return {
    date: dateStr,
    label: `${y}년 ${m}월 ${day}일 (${weekday})`,
    weekday,
    isWeekend,
    holiday,
    isOpen,
    note,
  };
}
