"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { fetchNear, useNtfRead, type Near } from "./ntfRead";

// 종 알림 (앱 _gnb 의 알림 popover): 모두 읽음 · 받은 알림(관리자 공지·삭제 요청 결과·리뷰 삭제) ·
// 북마크한 팝업(오픈 D-n ~ 당일, 종료 D-n ~ 당일) · 내 주변 추천(위치를 허용했을 때, 지금 열려 있는 가까운 곳).
// 읽음 표시는 앱과 같은 쿠키(aw_ntf_read_<회원 해시>)에 남긴다. 안 읽은 게 있으면 종에 빨간 점.

export type BellMark = { id: string; label: string; name: string; why: string; cafeId: string };
export type BellInbox = { id: string; title: string; body: string; why: string };
export type BellData = {
  inbox: BellInbox[];
  marks: BellMark[];
  /** 읽음 쿠키 이름 · 서버가 읽어 둔 값 */
  cookie: string;
  read: string;
  /** 알림 규칙 '내 주변 추천' 이 켜져 있는지 + 그 안내 한 줄 */
  near: { on: boolean; why: string };
};

export default function Bell({ data }: { data: BellData }) {
  const [open, setOpen] = useState(false);
  const { read, mark } = useNtfRead(data.cookie, data.read);
  const [near, setNear] = useState<Near>({ state: "idle", items: [] });
  const box = useRef<HTMLDivElement>(null);

  // 위치 권한이 이미 허용돼 있으면 묻지 않고 가까운 팝업을 받아 둔다 (빨간 점에도 들어간다)
  useEffect(() => {
    if (!data.near.on) return;
    let live = true;
    fetchNear("bell", false).then((n) => live && n.state !== "idle" && setNear(n));
    return () => {
      live = false;
    };
  }, [data.near.on]);
  // 종을 열었는데 아직 위치를 모르면 그때 물어본다 (앱은 메뉴바가 위치를 묻는다)
  useEffect(() => {
    if (!open || !data.near.on || near.state !== "idle") return;
    let live = true;
    setNear({ state: "asking", items: [] });
    fetchNear("bell", true).then((n) => live && setNear(n));
    return () => {
      live = false;
    };
  }, [open, data.near.on, near.state]);
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

  const ids = [...data.inbox.map((x) => x.id), ...data.marks.map((x) => x.id), ...near.items.map((x) => x.id)];
  const unread = ids.filter((id) => !read.has(id));
  const state = (id: string) => (read.has(id) ? "읽음" : "새 알림");
  const go = (id: string) => {
    mark([id]);
    setOpen(false);
  };

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
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
                <path d="M2 12.5l4.5 4.5L15 8.5M10.5 16l1 1L22 6.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
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
              onClick={() => go(x.id)}
            >
              <span className="ntf-st">{state(x.id)}</span>
              <b>{x.label}</b> · {x.name}
              <div className="ntf-why">{x.why}</div>
            </Link>
          ))}
          <b className="ntf-h">내 주변 추천</b>
          {(!data.near.on || near.state === "idle" || near.state === "denied") && (
            <div className="ntf-empty">
              위치를 허용하면 지금 열려 있는 가까운 팝업을 추천해 드려요. 브라우저 주소창의 위치 권한을 허용해 주세요.
            </div>
          )}
          {data.near.on && near.state === "asking" && <div className="ntf-empty">내 위치를 확인하는 중이에요…</div>}
          {data.near.on && near.state === "done" && near.items.length === 0 && (
            <div className="ntf-empty">지금 주변에 열려 있는 팝업이 없어요.</div>
          )}
          {data.near.on &&
            near.items.map((x) => (
              <Link
                key={x.id}
                href={`/popup/${x.cafeId}`}
                className={`ntf-item${read.has(x.id) ? " read" : ""}`}
                onClick={() => go(x.id)}
              >
                <span className="ntf-st">{state(x.id)}</span>
                <b>내 주변 {x.dist}</b> · {[x.work, x.cafe].filter(Boolean).join(" · ")}
                <div className="ntf-why">{data.near.why}</div>
              </Link>
            ))}
        </div>
      )}
    </div>
  );
}
