// 차트 공통 테마 (Phase F4). 모든 색은 CSS 변수 참조라 .dark 전환 시 자동으로 바뀐다.
// SVG 표현 속성(stroke="...")의 var() 지원은 브라우저마다 달라, 컴포넌트에서는 style로 넘긴다.
const v = (name: string, alpha?: number) =>
  alpha === undefined ? `hsl(var(--color-${name}))` : `hsl(var(--color-${name}) / ${alpha})`;

export const chartTheme = {
  up: v("chart-up"),
  down: v("chart-down"),
  grid: v("chart-grid"),
  axis: v("fg-subtle"),
  areaOpacity: 0.18,
  // HTML 툴팁(div)은 Tailwind 토큰 클래스로 맞춘다
  tooltipClass: "bg-fg text-surface",
  tooltipMutedClass: "text-surface/60",
} as const;

export function lineColor(up: boolean): string {
  return up ? chartTheme.up : chartTheme.down;
}
