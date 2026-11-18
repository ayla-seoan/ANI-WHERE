"use client";
import { useEffect, useState } from "react";
import type { Item } from "@/lib/popup";
import { ChatIcon, CloseIcon } from "../Icons";
import AskChat from "./AskChat";

// 모바일(폭 640px 이하) 오른쪽 아래 동그란 물어보기 버튼 (앱 .st-key-ask_fab) → 아래에서 올라오는 대화 시트
export default function AskFab({
  items,
  today,
  onShowAll,
}: {
  items: Item[];
  today: string;
  onShowAll?: (ids: string[], label: string) => void;
}) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden"; // 시트 뒤 화면이 같이 스크롤되지 않게
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);
  return (
    <>
      <button type="button" className="ask-fab" aria-label="ANI:WHERE에게 물어보기" onClick={() => setOpen(true)}>
        <ChatIcon />
      </button>
      {open && (
        <div className="ask-sheet-bg" onClick={() => setOpen(false)}>
          <div
            className="ask-sheet"
            role="dialog"
            aria-label="ANI:WHERE에게 물어보기"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="ask-sheet-head">
              <span className="apn-title">ANI:WHERE에게 물어보기</span>
              <button type="button" className="icon-btn" aria-label="닫기" onClick={() => setOpen(false)}>
                <CloseIcon />
              </button>
            </div>
            <AskChat
              items={items}
              today={today}
              onOpen={() => setOpen(false)}
              onShowAll={
                onShowAll
                  ? (ids, label) => {
                      setOpen(false);
                      onShowAll(ids, label);
                    }
                  : undefined
              }
            />
          </div>
        </div>
      )}
    </>
  );
}
