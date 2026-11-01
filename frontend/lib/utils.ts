/** className 합치기 (falsy 무시). 외부 의존성(clsx·tailwind-merge) 없이 최소 구현 —
 *  충돌 클래스 병합은 하지 않으므로, 덮어쓸 클래스는 호출부에서 겹치지 않게 넘긴다. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
