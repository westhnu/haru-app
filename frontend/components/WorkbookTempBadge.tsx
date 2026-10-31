/** 백엔드 워크북 저장소가 in-memory라 서버 재시작 시 사라진다는 안내 (SQLite 승격 전까지). */
export default function WorkbookTempBadge() {
  return (
    <span
      title="백엔드가 메모리에 저장합니다. 서버를 재시작하면 추가한 내용이 사라지고 샘플만 남아요."
      className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
    >
      임시 저장
    </span>
  );
}
