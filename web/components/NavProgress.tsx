"use client";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

// 화면을 옮길 때 맨 위 진행 막대 (11/19 속도 요청). 링크를 누르는 즉시 보이고, 새 화면이 뜨면 사라진다.
// (loading.tsx 는 없는 팝업에 404 대신 200 을 주고 리뷰 저장 뒤 안내가 사라지게 해서 쓰지 않는다)
export default function NavProgress() {
  const path = usePathname();
  const query = useSearchParams()?.toString() ?? "";
  const [on, setOn] = useState(false);

  useEffect(() => setOn(false), [path, query]);

  useEffect(() => {
    const click = (e: MouseEvent) => {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      // 링크 안의 버튼(카드의 북마크 등)은 화면을 옮기지 않는다
      if (el?.closest("button, input, select, textarea, label")) return;
      const a = el?.closest("a");
      if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
      const url = new URL(a.href, location.href);
      if (url.origin !== location.origin) return;
      if (url.pathname === location.pathname && url.search === location.search) return; // 같은 화면 · #이동
      setOn(true);
    };
    // Next 의 <Link> 가 클릭을 먼저 막아서(preventDefault) 캡처 단계에서 본다
    document.addEventListener("click", click, true);
    return () => document.removeEventListener("click", click, true);
  }, []);

  // 혹시 이동이 취소되면 오래 남지 않게
  useEffect(() => {
    if (!on) return;
    const t = setTimeout(() => setOn(false), 10000);
    return () => clearTimeout(t);
  }, [on]);

  return on ? <div className="aw-nav-bar" role="progressbar" aria-label="화면 불러오는 중" /> : null;
}
