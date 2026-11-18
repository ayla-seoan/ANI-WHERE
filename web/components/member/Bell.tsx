"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

// 종 알림 (앱 메뉴바의 알림): 받은 알림(관리자 공지·삭제 요청 결과) · 북마크한 팝업(오픈 D-3 ~ 당일, 종료 D-3 ~ 당일).
// 읽음 표시는 이 브라우저에만 남긴다 (회원마다 따로). 안 읽은 게 있으면 종에 빨간 점.

export type BellMark = { id: string; label: string; name: string; why: string; cafeId: string };
export type BellInbox = { id: string; title: string; body: string; why: string };
export type BellData = { inbox: BellInbox[]; marks: BellMark[] };

const storeKey = (owner: string) => `aw_ntf_read_${owner}`;

function loadRead(owner: string): Set<string> {
  try {
    return new Set((localStorage.getItem(storeKey(owner)) || "").split("|").filter(Boolean));
  } catch {
    return new Set();
  }
}

export default function Bell({ data, owner }: { data: BellData; owner: string }) {
  const [open, setOpen] = useState(false);
  const [read, setRead] = useState<Set<string>>(new Set());
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => setRead(loadRead(owner)), [owner]);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    window.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      window.removeEventListener("keydown", esc);
    };
  }, [open]);

  const ids = [...data.inbox.map((x) => x.id), ...data.marks.map((x) => x.id)];
  const unread = ids.filter((id) => !read.has(id));
  const mark = (more: string[]) => {
    const n = new Set([...read, ...more]);
    setRead(n);
    try {
      localStorage.setItem(storeKey(owner), [...n].slice(-200).join("|"));
    } catch {
      /* 저장이 막혀도 이번 화면에서는 읽음 */
    }
  };
  const state = (id: string) => (read.has(id) ? "읽음" : "새 알림");

  return (
    <div className="bell" ref={box}>
      <button
        type="button"
        className={`gnb-bell${unread.length ? " dot" : ""}`}
        aria-label={unread.length ? `알림 ${unread.length}개 새로 옴` : "알림"}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2.2}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M6.3 16.4V11.2a5.7 5.7 0 0 1 11.4 0v5.2" />
          <path d="M4.6 16.6c0 .3.3.5.6.5h13.6c.3 0 .6-.2.6-.5" />
          <path d="M10.2 19.6a1.9 1.9 0 0 0 3.6 0" />
        </svg>
      </button>
      {open && (
        <div className="bell-pop" role="dialog" aria-label="알림">
          {unread.length > 0 && (
            <button type="button" className="ntf-all" onClick={() => mark(unread)}>
              모두 읽음
            </button>
          )}
          {data.inbox.length > 0 && (
            <>
              <b className="ntf-h">받은 알림</b>
              {data.inbox.map((x) => (
                <div key={x.id} className={`ntf-item plain${read.has(x.id) ? " read" : ""}`}>
                  <span className="ntf-st">{state(x.id)}</span>
                  <b>{x.title}</b>
                  <br />
                  {x.body}
                  <div className="ntf-why">{x.why}</div>
                </div>
              ))}
            </>
          )}
          <b className="ntf-h">북마크한 팝업</b>
          {data.marks.length === 0 && (
            <div className="ntf-empty">
              오픈 3일 전부터 당일까지, 그리고 끝나기 3일 전부터 알려 드려요. 팝업을 북마크해 보세요.
            </div>
          )}
          {data.marks.map((x) => (
            <Link
              key={x.id}
              href={`/popup/${x.cafeId}`}
              className={`ntf-item${read.has(x.id) ? " read" : ""}`}
              onClick={() => {
                mark([x.id]);
                setOpen(false);
              }}
            >
              <span className="ntf-st">{state(x.id)}</span>
              <b>{x.label}</b> · {x.name}
              <div className="ntf-why">{x.why}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
