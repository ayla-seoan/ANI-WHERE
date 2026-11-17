"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { APP_URL } from "@/lib/popup";
import { ChatIcon } from "./Icons";

const ITEMS = [
  { href: "/", label: "찾기" },
  { href: "/this-week", label: "이번 주" },
];

/** 앱 상단의 '물어보기 · 로그인' 처럼 둥근 테두리 버튼 */
export default function Nav() {
  const path = usePathname();
  return (
    <nav className="nav" aria-label="주요 메뉴">
      {ITEMS.map((it) => (
        <Link key={it.href} href={it.href} aria-current={path === it.href ? "page" : undefined}>
          {it.label}
        </Link>
      ))}
      <a href={`${APP_URL}/ask`} target="_blank" rel="noopener noreferrer">
        <ChatIcon />
        물어보기
      </a>
    </nav>
  );
}
