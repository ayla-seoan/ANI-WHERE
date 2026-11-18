"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { APP_URL } from "@/lib/popup";
import { CloseIcon, SearchIcon } from "./Icons";

// 앱(Streamlit) 상단 메뉴바와 같은 모양: 연민트 바탕 + 아래 둥근 모서리, 왼쪽 로고, 가운데 탭 (홈 · 지도로 보기 · 리스트로 보기).
// 알림·관리자는 이 공개 웹에 두지 않는다 (읽기 전용). '로그인' 은 앱(Streamlit)의 로그인 화면으로 가는 링크.
// 지도·리스트 화면에서는 앱처럼 검색 아이콘이 보이고, 누르면 검색 필터 상자가 열린다 (window 이벤트 'aw:filters').
const TABS = [
  { href: "/", label: "홈" },
  { href: "/map", label: "지도로 보기" },
  { href: "/list", label: "리스트로 보기" },
];

function activeTab(path: string): string {
  if (path.startsWith("/map")) return "/map";
  if (path.startsWith("/list")) return "/list";
  if (path === "/") return "/";
  return "";
}

export default function Gnb() {
  const path = usePathname() || "/";
  const on = activeTab(path);
  // null = 이 화면에 필터 상자가 없음, true/false = 열림 여부
  const [filters, setFilters] = useState<boolean | null>(null);
  useEffect(() => {
    const f = (e: Event) => setFilters((e as CustomEvent<boolean | null>).detail);
    window.addEventListener("aw:filters-state", f);
    const now = document.documentElement.dataset.filters;
    if (now) setFilters(now === "1");
    return () => window.removeEventListener("aw:filters-state", f);
  }, []);

  return (
    <header className="gnb-wrap">
      <div className="gnb">
        <Link href="/" className="gnb-logo" aria-label="ANI:WHERE 홈">
          <img src="/logo_mint_sm.webp" alt="ANI:WHERE — ANIME POP-UP · CAFE · GOODS" width={155} height={47} />
        </Link>
        <nav className="gnb-tabs" aria-label="주요 메뉴">
          {TABS.map((t) => (
            <Link
              key={t.href}
              href={t.href}
              className={on === t.href ? "on" : undefined}
              aria-current={on === t.href ? "page" : undefined}
            >
              {t.label}
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
          {/* 앱 손님 메뉴바의 '로그인' 과 같은 자리·글꼴. 로그인은 Streamlit 앱에서 (이 웹은 읽기 전용, 인증 없음) */}
          <a href={`${APP_URL}/login`} className="gnb-login">
            로그인
          </a>
        </div>
      </div>
    </header>
  );
}
