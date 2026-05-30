import type { Config } from "tailwindcss";

/** 디자인 시스템: Tailwind 기본 slate 팔레트를 그대로 사용한다 (M.A.T.E 언어).
 *  별도 커스텀 컬러 없이 slate-950/700/500/100/50 + white 로 구성. */
const config: Config = {
  // 'class' 모드 — layout.tsx 의 인라인 스크립트가 prefers-color-scheme 기반으로
  // html에 .dark 를 토글한다. (mql change 도 listen)
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
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
