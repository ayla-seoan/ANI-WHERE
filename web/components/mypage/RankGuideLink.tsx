"use client";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import RankGuide from "./RankGuide";

// '랭크 안내 보기' — 누르면 화면을 옮기지 않고 팝업으로 랭크 안내를 보여 준다 (11/26 요청, 앱의 랭크 안내 창과 같게).
// 닫기: × 버튼 · 바깥 누르기 · Esc. 자바스크립트가 꺼져 있으면 /mypage/rank 화면으로 간다 (같은 내용).
export default function RankGuideLink({
  stamps,
  className,
  children,
}: {
  stamps: number | null;
  className?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const openerRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", esc);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden"; // 뒤 화면이 같이 스크롤되지 않게
    closeRef.current?.focus();
    const opener = openerRef.current;
    return () => {
      document.removeEventListener("keydown", esc);
      document.body.style.overflow = prev;
      opener?.focus();
    };
  }, [open]);

  return (
    <>
      <a
        ref={openerRef}
        href="/mypage/rank"
        className={className}
        aria-haspopup="dialog"
        onClick={(e) => {
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return; // 새 탭으로 열기는 그대로
          e.preventDefault();
          setOpen(true);
        }}
      >
        {children}
      </a>
      {open &&
        createPortal(
          <div className="rkd-bg" onClick={() => setOpen(false)}>
            <div className="rkd" role="dialog" aria-modal="true" aria-labelledby="rkp-title" onClick={(e) => e.stopPropagation()}>
              <button ref={closeRef} type="button" className="rkd-x" aria-label="랭크 안내 닫기" onClick={() => setOpen(false)}>
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden>
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
              <RankGuide stamps={stamps} inDialog />
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
