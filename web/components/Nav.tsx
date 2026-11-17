"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "찾기" },
  { href: "/this-week", label: "이번 주" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="nav" aria-label="주요 메뉴">
      {ITEMS.map((it) => (
        <Link key={it.href} href={it.href} aria-current={path === it.href ? "page" : undefined}>
          {it.label}
        </Link>
      ))}
    </nav>
  );
}
