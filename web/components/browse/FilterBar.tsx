"use client";
import AreaPicker from "./AreaPicker";
import { useEffect, useRef } from "react";
import { EMPTY, SPANS, type Cond } from "./filters";
import { CloseIcon, SearchIcon } from "../Icons";

// 검색 필터 상자 (A-List 시안): PC 는 메뉴바 검색 아이콘에서 펼쳐지는 말풍선, 모바일은 아래에서 올라오는 시트.
// 칸은 검색 · 지역 · 진행여부 · 날짜 · 초기화. 닫아도 걸어 둔 조건은 그대로 걸리고, 걸린 조건은 목록 위 칩(CondChips)으로 보인다.
export default function FilterBar({
  cond,
  set,
  reset,
  areas,
  open,
  onClose,
  count,
}: {
  cond: Cond;
  set: (p: Partial<Cond>) => void;
  reset: () => void;
  areas: string[];
  open: boolean;
  onClose: () => void;
  count: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  // 말풍선 꼬리를 메뉴바 검색 아이콘 바로 밑에 (앱과 같이 실제 위치를 잰다)
  useEffect(() => {
    if (!open) return;
    const place = () => {
      const ic = document.querySelector(".gnb-search");
      const b = box.current;
      if (!ic || !b) return;
      const a = ic.getBoundingClientRect();
      const r = b.getBoundingClientRect();
      b.style.setProperty("--bubble-tail", `${Math.max(12, r.right - (a.left + a.width / 2) - 8)}px`);
    };
    place();
    window.addEventListener("resize", place);
    return () => window.removeEventListener("resize", place);
  }, [open]);
  return (
    <>
      {open && <div className="filters-bg m-only" onClick={onClose} aria-hidden />}
      <div ref={box} className={`filters${open ? " open" : ""}`} role="search" aria-label="검색 필터">
        <div className="sheet-head m-only">
          <span className="sheet-title">필터</span>
          <button type="button" className="icon-btn" aria-label="필터 닫기" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <div className="frow">
          <label className="fld fq">
            <span className="flabel">검색</span>
            <span className="finput">
              <SearchIcon />
              <input
                type="search"
                inputMode="search"
                enterKeyHint="search"
                placeholder="작품·카페명·캐릭터·주소"
                value={cond.q}
                maxLength={60}
                onChange={(e) => set({ q: e.target.value })}
              />
              {cond.q && (
                <button type="button" className="clear" aria-label="검색어 지우기" onClick={() => set({ q: "" })}>
                  <CloseIcon />
                </button>
              )}
            </span>
          </label>
          <div className="fld">
            <span className="flabel">지역</span>
            <AreaPicker variant="field" value={cond.area} areas={areas} onChange={(v) => set({ area: v })} />
          </div>
          <label className="fld">
            <span className="flabel">진행여부</span>
            <select className={cond.span !== EMPTY.span ? "on" : undefined} value={cond.span} onChange={(e) => set({ span: e.target.value as Cond["span"] })}>
              {SPANS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="fld">
            <span className="flabel">날짜</span>
            <input
              type="date"
              className={cond.day ? "on" : undefined}
              value={cond.day}
              onChange={(e) => set({ day: e.target.value })}
              aria-label="이 날짜에 진행 중인 곳만"
            />
          </label>
          <div className="fld freset">
            <button type="button" className="btn-reset" onClick={reset}>
              초기화
            </button>
          </div>
        </div>
        <div className="sheet-foot m-only">
          <button type="button" className="link-btn" onClick={reset}>
            전체 삭제
          </button>
          <button type="button" className="btn-primary" onClick={onClose}>
            팝업 {count}곳 표시
          </button>
        </div>
      </div>
    </>
  );
}
