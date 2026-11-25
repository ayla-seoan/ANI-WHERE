"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { avatarUrl } from "@/lib/avatar";
import { CloseIcon, SearchIcon } from "./Icons";
import Bell, { type BellData } from "./member/Bell";
import { useMember } from "./member/MemberContext";
import GnbMotion from "./GnbMotion";

// 앱(Streamlit) 상단 메뉴바와 같은 모양: 연민트 바탕 + 아래 둥근 모서리, 왼쪽 로고, 가운데 탭 (홈 · 지도로 보기 · 리스트로 보기
// · 회원이면 내 캘린더). 오른쪽: 검색(지도·리스트) · 알림(회원) · 관리자(관리자 회원, 앱의 관리자 화면으로) · 로그인 / 프로필 사진.
const TABS = [
  { href: "/", label: "홈", short: "홈" },
  { href: "/map", label: "지도로 보기", short: "지도" },
  { href: "/list", label: "리스트로 보기", short: "리스트" },
];

function activeTab(path: string): string {
  if (path.startsWith("/map")) return "/map";
  if (path.startsWith("/list")) return "/list";
  if (path.startsWith("/calendar")) return "/calendar";
  if (path === "/") return "/";
  return "";
}

export default function Gnb({ bell }: { bell: BellData | null }) {
  const path = usePathname() || "/";
  const on = activeTab(path);
  const { me } = useMember();
  // null = 이 화면에 필터 상자가 없음, true/false = 열림 여부
  const [filters, setFilters] = useState<boolean | null>(null);
  useEffect(() => {
    const f = (e: Event) => setFilters((e as CustomEvent<boolean | null>).detail);
    window.addEventListener("aw:filters-state", f);
    const now = document.documentElement.dataset.filters;
    if (now) setFilters(now === "1");
    return () => window.removeEventListener("aw:filters-state", f);
  }, []);
  const tabs = me ? [...TABS, { href: "/calendar", label: "내 캘린더", short: "캘린더" }] : TABS;

  return (
    <header className="gnb-wrap">
      <GnbMotion />
      <div className="gnb">
        <Link href="/" className="gnb-logo" aria-label="ANI:WHERE 홈">
          <img src="/logo_sm.webp" alt="ANI:WHERE" width={186} height={52} />
        </Link>
        <nav className={`gnb-tabs${me ? " four" : ""}`} aria-label="주요 메뉴">
          {tabs.map((t) => (
            <Link
              key={t.href}
              href={t.href}
              className={on === t.href ? "on" : undefined}
              aria-current={on === t.href ? "page" : undefined}
            >
              {/* 모바일은 짧은 이름 (A-Mobile: 홈 · 지도 · 리스트 · 캘린더) */}
              <span className="pc-only">{t.label}</span>
              <span className="m-only" aria-hidden>
                {t.short}
              </span>
            </Link>
          ))}
        </nav>
        <div className="gnb-right">
          {filters !== null && (on === "/map" || on === "/list") && (
            <button
              type="button"
              className="gnb-search"
              aria-label={filters ? "검색 필터 닫기" : "검색 필터 열기"}
              aria-expanded={filters}
              onClick={() => window.dispatchEvent(new Event("aw:filters"))}
            >
              {filters ? <CloseIcon /> : <SearchIcon />}
            </button>
          )}
          {me && bell && <Bell data={bell} />}
          {me?.admin && (
            <Link href="/data" className="gnb-admin">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" />
                <path d="M9 12l2 2 4-4" />
              </svg>
              관리자
            </Link>
          )}
          {me ? (
            // 회원: 닉네임 글자 대신 프로필 사진 동그라미 → 마이페이지 (앱과 같게)
            <Link href="/mypage" className="gnb-me" aria-label={`${me.nick} 마이페이지`}>
              <img
                src={avatarUrl(me.avatar)}
                alt=""
                width={36}
                height={36}
                referrerPolicy="no-referrer"
                onError={(e) => {
                  e.currentTarget.src = avatarUrl("");
                }}
              />
            </Link>
          ) : (
            <Link
              href={`/login${path !== "/" && path !== "/login" ? `?next=${encodeURIComponent(path)}` : ""}`}
              className="gnb-login"
            >
              로그인
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
