"use client";
import Link from "next/link";

// 바닥글 링크 (11/19 요청): 튜토리얼 · 디자인 시스템 · 처리방침을 누르면 그 화면 맨 위부터 보이게.
// 바닥글은 레이아웃에 있어서 Next 가 스크롤을 옮기지 않고 아래쪽(누른 자리)에서 새 화면이 열렸다.
export default function FootLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} onClick={() => window.scrollTo({ top: 0, left: 0, behavior: "instant" })}>
      {children}
    </Link>
  );
}
