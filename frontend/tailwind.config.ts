import type { Config } from "tailwindcss";

/** 디자인 시스템 (Phase F2): 색은 globals.css의 CSS 변수(HSL)를 참조하는 의미 토큰만 쓴다.
 *  라이트/다크는 변수 값만 바뀌므로 컴포넌트에서 dark: 색 접두가 필요 없다.
 *  `hsl(var(--x) / <alpha-value>)` 형식이라 bg-surface/85 같은 투명도 수식어도 동작한다. */
const token = (name: string) => `hsl(var(--color-${name}) / <alpha-value>)`;

const config: Config = {
  // 'class' 모드 — layout.tsx 의 인라인 스크립트가 prefers-color-scheme 기반으로
  // html에 .dark 를 토글한다. (mql change 도 listen)
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: token("brand"), foreground: token("brand-foreground") },
        surface: {
          DEFAULT: token("surface"),
          muted: token("surface-muted"),
          elevated: token("surface-elevated"),
        },
        fg: { DEFAULT: token("fg"), muted: token("fg-muted"), subtle: token("fg-subtle") },
        border: { DEFAULT: token("border"), subtle: token("border-subtle") },
        // 체크리스트 상태: 충족=success, 판단 보류=warning, 미충족=danger
        success: token("success"),
        warning: token("warning"),
        danger: token("danger"),
      },
      // 의미 spacing. Tailwind 3.4 maxWidth는 spacing을 먼저 펼치고 xs~7xl을 뒤에 정의하므로
      // max-w-sm/md 등 기존 폭 유틸은 덮어쓰지 않는다.
      spacing: {
        xs: "0.5rem",
        sm: "0.75rem",
        md: "1rem",
        lg: "1.5rem",
        xl: "2rem",
        "2xl": "3rem",
      },
      maxWidth: {
        "container-sm": "28rem",
        "container-md": "42rem",
        "container-lg": "56rem",
      },
      fontFamily: {
        sans: [
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Text",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        // 수치 강조(체크리스트 N/M, 가상 단가)용. tabular-nums와 함께 쓴다.
        mono: ["var(--font-mono)"],
      },
      boxShadow: {
        card: "0 18px 54px -42px rgba(15,23,42,0.55)",
        soft: "0 10px 30px -20px rgba(15,23,42,0.45)",
      },
      borderRadius: {
        "4xl": "28px",
        "5xl": "32px",
      },
    },
  },
  plugins: [],
};

export default config;
