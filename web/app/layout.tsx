import Link from "next/link";
import type { Metadata, Viewport } from "next";
import "./globals.css";
import "./member.css";
import "./admin.css";
import "./edit.css";
import "./pages.css";
import { getPopupData } from "@/lib/data";
import Gnb from "@/components/Gnb";
import Footer from "@/components/Footer";
import InstallHint from "@/components/InstallHint";
import SWRegister from "@/components/SWRegister";
import ScrollTop from "@/components/ScrollTop";
import Toast from "@/components/member/Toast";
import { MemberProvider, type MeLite } from "@/components/member/MemberContext";
import type { BellData } from "@/components/member/Bell";
import { bookmarkMarks, inbox, ruleSettings, whyOf } from "@/lib/server/member";
import { ntfCookieName, ntfRead } from "@/lib/server/ntf";
import { getMe, getMyFavs } from "@/lib/server/session";
import { todayKST } from "@/lib/popup";

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
  // 로그인한 회원 (쿠키 aw_session). 회원이면 북마크 · 종 알림도 서버에서 읽어 넘긴다
  const me = await getMe();
  const favIds = await getMyFavs();
  let bell: BellData | null = null;
  if (me) {
    const today = todayKST();
    const rules = await ruleSettings();
    bell = {
      inbox: (await inbox(me.key, rules, today)).slice(0, 10),
      marks: bookmarkMarks(data.popups, new Set(favIds), rules, today),
      cookie: ntfCookieName(me.key),
      read: await ntfRead(me.key),
      near: { on: rules.near.enabled, why: whyOf("near", rules) },
    };
  }
  const meLite: MeLite = me
    ? {
        nick: String(me.row.nickname || ""),
        avatar: String(me.row.avatar || ""),
        admin: me.admin,
        key4: `m${me.key.slice(0, 4)}`,
      }
    : null;
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
      <body className={me ? "member" : undefined}>
        <MemberProvider me={meLite} favIds={favIds}>
          <div className="page">
            <Gnb bell={bell} />
            <main className="main">{children}</main>
            <Footer />
          </div>
          {me && (
            // 오른쪽 아래 코랄색 + (등록하기 /add, 회원에게만 보인다, 앱과 같게)
            <Link className="add-fab" href="/add" aria-label="새 팝업 등록">
              <svg viewBox="0 0 24 24" aria-hidden>
                <path d="M12 5v14M5 12h14" />
              </svg>
            </Link>
          )}
          <Toast />
        </MemberProvider>
        <ScrollTop />
        <InstallHint />
        <SWRegister />
      </body>
    </html>
  );
}
