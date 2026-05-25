import type { Metadata } from "next";
import "./globals.css";

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
      </head>
      <body className="font-sans">{children}</body>
    </html>
  );
}
