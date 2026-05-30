import type { Metadata } from "next";
import "./globals.css";
import BottomNav from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "하루 HARU · 마켓 브리핑",
  description:
    "개인 투자자가 본인 증권사에서 직접 결정할 때 필요한 정보를 하루 2회 자동 브리핑으로.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          as="style"
          crossOrigin="anonymous"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
        />
        {/* prefers-color-scheme 기반 다크모드 자동 적용을 위한 html.dark 토글 */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{const m=window.matchMedia('(prefers-color-scheme: dark)');const apply=()=>document.documentElement.classList.toggle('dark',m.matches);apply();m.addEventListener('change',apply);}catch(e){}`,
          }}
        />
      </head>
      <body className="bg-white font-sans text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        {children}
        <BottomNav />
      </body>
    </html>
  );
}
