import type { Metadata, Viewport } from "next";
import "./globals.css";
import { getPopupData } from "@/lib/data";
import Gnb from "@/components/Gnb";
import Footer from "@/components/Footer";
import InstallHint from "@/components/InstallHint";
import SWRegister from "@/components/SWRegister";
import ScrollTop from "@/components/ScrollTop";

const siteUrl =
  process.env.SITE_URL ||
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "ANI:WHERE — 애니 팝업·콜라보 카페 찾기", template: "%s | ANI:WHERE" },
  description:
    "지금 열린 애니메이션 팝업스토어·콜라보 카페를 지역·작품으로 찾고, 가기 전에 기간·특전·위치를 확인하세요.",
  applicationName: "ANI:WHERE",
  appleWebApp: { capable: true, title: "ANI:WHERE", statusBarStyle: "default" },
  formatDetection: { telephone: false },
  openGraph: { type: "website", siteName: "ANI:WHERE", locale: "ko_KR", images: ["/icons/icon-512.png"] },
};

export const viewport: Viewport = {
  themeColor: "#E9F7F2",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const data = await getPopupData();
  return (
    <html lang="ko">
      <head>
        {/* 앱(Streamlit)과 같은 글꼴: 제목 Jua, 본문 나눔스퀘어라운드 → Pretendard */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link href="https://fonts.googleapis.com/css2?family=Jua&display=swap" rel="stylesheet" />
        <link
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
          rel="stylesheet"
        />
        <link
          href="https://cdn.jsdelivr.net/gh/moonspam/NanumSquareRound@1.0/nanumsquareround.min.css"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="page">
          <Gnb />
          <main className="main">{children}</main>
          <Footer sourceLabel={data.sourceLabel} note={data.note} />
        </div>
        <ScrollTop />
        <InstallHint />
        <SWRegister />
      </body>
    </html>
  );
}
