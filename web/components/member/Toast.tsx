"use client";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

// 화면 가운데 잠깐 떴다 사라지는 알림 (앱 _toast 와 같은 모양, 최신 것만 보인다).
// 서버가 남긴 한 번짜리 안내(쿠키 aw_flash, 로그인·로그아웃 뒤)도 여기서 보여 주고 지운다.
type Kind = "ok" | "error" | "bookmark" | "unbookmark" | "wave";
type T = { msg: string; kind: Kind; n: number };

export function toast(msg: string, kind: Kind = "ok") {
  window.dispatchEvent(new CustomEvent("aw:toast", { detail: { msg, kind } }));
}

const ICON: Record<Kind, React.ReactNode> = {
  ok: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  error: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5.5M12 16.5v.1" />
    </>
  ),
  bookmark: <path d="M6 4h12v16l-6-4-6 4V4zM9 10l2 2 4-4" />,
  unbookmark: <path d="M6 4h12v16l-6-4-6 4V4zM9.5 10h5" />,
  wave: <path d="M7 12l3-7 2 6 2-4 3 9H7z" />,
};

export default function Toast() {
  const [t, setT] = useState<T | null>(null);
  const path = usePathname();
  useEffect(() => {
    const on = (e: Event) => {
      const d = (e as CustomEvent<{ msg: string; kind: Kind }>).detail;
      setT({ msg: d.msg, kind: d.kind, n: Date.now() });
    };
    window.addEventListener("aw:toast", on);
    return () => window.removeEventListener("aw:toast", on);
  }, []);
  useEffect(() => {
    const m = document.cookie.match(/(?:^|; )aw_flash=([^;]*)/);
    if (!m) return;
    document.cookie = "aw_flash=; path=/; max-age=0";
    try {
      const msg = decodeURIComponent(m[1]);
      if (msg) setT({ msg, kind: /환영|가입/.test(msg) ? "wave" : "ok", n: Date.now() });
    } catch {
      /* 무시 */
    }
  }, [path]);
  useEffect(() => {
    if (!t) return;
    const id = setTimeout(() => setT(null), 2600);
    return () => clearTimeout(id);
  }, [t]);
  if (!t) return null;
  return (
    <div className="ani-toast show" role="status" key={t.n}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        {ICON[t.kind]}
      </svg>
      <span className="tx">{t.msg}</span>
    </div>
  );
}
