"use client";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

// 화면 가운데 잠깐 떴다 사라지는 알림 (앱 _toast 와 같은 모양: 아이콘 + 굵은 글자, 닫기 버튼 없음, 최신 것만 보인다).
// 서버가 남긴 한 번짜리 안내(쿠키 aw_flash = "<종류>|<문구>", 로그인·로그아웃 뒤)도 여기서 보여 주고 지운다.
export type ToastKind = "ok" | "error" | "bookmark" | "unbookmark" | "wave" | "login" | "logout" | "restore";
type T = { msg: string; kind: ToastKind; n: number };

export function toast(msg: string, kind: ToastKind = "ok") {
  if (!msg) return;
  window.dispatchEvent(new CustomEvent("aw:toast", { detail: { msg, kind } }));
}

// 앱이 쓰는 material 아이콘(check_circle · error · bookmark_added · bookmark_remove · waving_hand · login · logout · restore)과
// 같은 뜻의 선 그림. 글꼴 아이콘은 글꼴을 받기 전 'check_circle' 같은 글자가 보여서 SVG 로 그린다
const ICON: Record<ToastKind, React.ReactNode> = {
  ok: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.3l2.8 2.8L16.2 9.6" />
    </>
  ),
  error: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v5.5M12 16.4v.1" />
    </>
  ),
  bookmark: <path d="M6.5 4h11v16l-5.5-3.8L6.5 20V4zM9.3 10.2l1.9 1.9 3.6-3.6" />,
  unbookmark: <path d="M6.5 4h11v16l-5.5-3.8L6.5 20V4zM9.5 10.5h5" />,
  wave: (
    <path d="M8.5 11.5V6.2a1.3 1.3 0 012.6 0v4.8M11.1 10.6V4.9a1.3 1.3 0 012.6 0v5.7M13.7 10.6V6a1.3 1.3 0 012.6 0v7.2c0 3.8-2.4 6.8-6 6.8-2.3 0-3.7-1-5-3l-2-3.2a1.3 1.3 0 012.1-1.5l1.6 1.9V8.6a1.3 1.3 0 012.6 0" />
  ),
  login: <path d="M14 4h4a2 2 0 012 2v12a2 2 0 01-2 2h-4M10 16l4-4-4-4M14 12H4" />,
  logout: <path d="M10 20H6a2 2 0 01-2-2V6a2 2 0 012-2h4M16 16l4-4-4-4M20 12H9" />,
  restore: <path d="M4 12a8 8 0 108-8 8 8 0 00-5.7 2.3L4 8.6M4 4v4.6h4.6M12 8v4.2l2.8 1.8" />,
};
const KINDS = new Set(Object.keys(ICON));

export default function Toast() {
  const [t, setT] = useState<T | null>(null);
  const [shown, setShown] = useState(false);
  const path = usePathname();
  useEffect(() => {
    const on = (e: Event) => {
      const d = (e as CustomEvent<{ msg: string; kind: ToastKind }>).detail;
      setT({ msg: d.msg, kind: KINDS.has(d.kind) ? d.kind : "ok", n: Date.now() + Math.random() });
    };
    window.addEventListener("aw:toast", on);
    return () => window.removeEventListener("aw:toast", on);
  }, []);
  useEffect(() => {
    const check = () => {
      const m = document.cookie.match(/(?:^|; )aw_flash=([^;]*)/);
      if (!m) return;
      document.cookie = "aw_flash=; path=/; max-age=0";
      let raw = "";
      try {
        raw = decodeURIComponent(m[1]);
      } catch {
        return;
      }
      // "<종류>|<문구>" (예전 모양: 문구만)
      const bar = raw.indexOf("|");
      const head = bar > 0 ? raw.slice(0, bar) : "";
      const kind = (KINDS.has(head) ? head : "ok") as ToastKind;
      const msg = KINDS.has(head) ? raw.slice(bar + 1) : raw;
      if (msg) toast(msg, kind);
    };
    check();
    // 같은 주소로 돌아오는 서버 액션(로그인 화면에서 로그아웃 등)은 주소가 안 바뀌어서 잠깐씩 다시 본다
    const id = setInterval(check, 400);
    return () => clearInterval(id);
  }, [path]);
  useEffect(() => {
    if (!t) return;
    // 앱과 같은 시간: 2.8초 보이고 0.3초 동안 사라진다
    const raf = requestAnimationFrame(() => setShown(true));
    const hide = setTimeout(() => setShown(false), 2800);
    const drop = setTimeout(() => setT(null), 3100);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(hide);
      clearTimeout(drop);
      setShown(false);
    };
  }, [t]);
  if (!t) return null;
  return (
    <div className={`ani-toast${shown ? " show" : ""}`} role="status" aria-live="polite" key={t.n}>
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
