import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { getPopupData } from "@/lib/data";
import { APP_URL } from "@/lib/popup";
import Nav from "@/components/Nav";
import InstallHint from "@/components/InstallHint";
import SWRegister from "@/components/SWRegister";

const siteUrl =
  process.env.SITE_URL ||
  (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "ANI:WHERE — 애니 팝업·콜라보 카페 찾기", template: "%s | ANI:WHERE" },
  description: "지금 열린 애니메이션 팝업스토어·콜라보 카페를 지역·작품으로 찾고, 가기 전에 기간·특전·위치를 확인하세요.",
  applicationName: "ANI:WHERE",
  appleWebApp: { capable: true, title: "ANI:WHERE", statusBarStyle: "default" },
  formatDetection: { telephone: false },
  openGraph: { type: "website", siteName: "ANI:WHERE", locale: "ko_KR", images: ["/icons/icon-512.png"] },
};

export const viewport: Viewport = {
  themeColor: "#56C2A7",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const data = await getPopupData();
  return (
    <html lang="ko">
      <body>
        <header className="header">
          <div className="container header-inner">
            <Link href="/" className="brand" aria-label="ANI:WHERE 처음으로">
              <img src="/logo.png" alt="ANI:WHERE" width={120} height={34} />
            </Link>
            <Nav />
          </div>
        </header>
        <main className="container">{children}</main>
        <footer className="footer">
          <div className="container">
            <p>
              <span className="source-tag">{data.sourceLabel}</span> · 10분마다 새로 고침
              {data.note ? ` · ${data.note}` : ""}
            </p>
            <p>
              리뷰 쓰기·정보 수정·새 팝업 등록은{" "}
              <a href={APP_URL} target="_blank" rel="noopener noreferrer">
                ANI:WHERE 앱
              </a>
              에서 해요. 방문 전 공식 공지를 한 번 더 확인하세요.
            </p>
          </div>
        </footer>
        <InstallHint />
        <SWRegister />
      </body>
    </html>
  );
}
