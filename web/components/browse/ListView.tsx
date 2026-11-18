"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Item } from "@/lib/popup";
import { PosterCard } from "../cards";
import { ChatIcon, CloseIcon, ExpandMore, HelpIcon, TuneIcon } from "../Icons";
import FilterBar from "./FilterBar";
import AskPanel from "../ask/AskPanel";
import AskFab from "../ask/AskFab";
import NoResult from "./NoResult";
import {
  EMPTY,
  SORTS,
  activeCount,
  applyCond,
  sortItems,
  useAreas,
  useCond,
  useFilterToggle,
  type SortKey,
} from "./filters";

const LIST_PAGE = 24; // 앱 LIST_PAGE: 처음 24장(4열 × 6줄), '더보기' 마다 24장씩

export default function ListView({ items, today }: { items: Item[]; today: string }) {
  const { cond, set, reset, ready } = useCond();
  const [sheet, setSheet] = useFilterToggle(cond, ready);
  const [n, setN] = useState(LIST_PAGE);
  const firstNew = useRef<string | null>(null);
  const areas = useAreas(items);

  const view = useMemo(() => sortItems(applyCond(items, cond, today), cond.sort, today), [items, cond, today]);

  // 조건이 바뀌면 다시 처음 장수로
  const sig = view.map((p) => p.id).join(",");
  useEffect(() => setN(LIST_PAGE), [sig]);

  // '더보기' 로 불러왔으면 새로 나온 첫 카드가 화면 위쪽에 오게 (앱과 같게)
  useEffect(() => {
    const id = firstNew.current;
    if (!id) return;
    firstNew.current = null;
    const el = document.querySelector(`[data-card="${id}"]`);
    if (el) window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - 110, behavior: "smooth" });
  }, [n]);

  const more = () => {
    firstNew.current = view[n]?.id ?? null;
    setN((k) => k + LIST_PAGE);
  };
  const act = activeCount(cond);
  // 물어보기 '+N건 더보기 · 리스트로 보기': 다른 조건은 풀고 그 답의 팝업만 (앱 _ask_show_all)
  const showAll = (ids: string[], label: string) => {
    set({ ...EMPTY, sort: cond.sort, ids, askLabel: label });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <>
      <FilterBar
        cond={cond}
        set={set}
        reset={reset}
        areas={areas}
        open={sheet}
        onClose={() => setSheet(false)}
        count={view.length}
      />
      <div className="list-layout">
        <div className="list-main">
          {cond.ids.length > 0 && (
            <div className="ask-only-bar">
              <div className="ask-only">
                <ChatIcon />
                물어보기 결과 · <b>{cond.askLabel || "질문"}</b> <span>{view.length}건</span>
              </div>
              <button type="button" className="ask-only-clear" onClick={() => set({ ids: [], askLabel: "" })}>
                <CloseIcon />
                전체 팝업 보기
              </button>
            </div>
          )}
          <div className="listtools">
            <h1 className="listbar">
              팝업 카페 <b>{view.length}</b>곳
              <span className="help" tabIndex={0}>
                <HelpIcon />
                <span className="tip">조건에 맞는 팝업 {view.length}곳 · 카드를 누르면 상세를 볼 수 있어요.</span>
              </span>
            </h1>
            <button
              type="button"
              className="m-filter m-only"
              aria-label="필터 열기"
              onClick={() => setSheet((o) => !o)}
            >
              <TuneIcon />
              {act ? <span>{act}</span> : null}
            </button>
            {/* 앱 목록 위 '지역 고르기' 칸 (PC). 필터 상자의 지역과 같은 값 */}
            <select
              className="region-pick pc-only"
              value={cond.area}
              aria-label="지역 고르기"
              onChange={(e) => set({ area: e.target.value })}
            >
              <option value="">지역 고르기 (전체)</option>
              {areas.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <select
              className="sort"
              value={cond.sort}
              aria-label="정렬"
              onChange={(e) => set({ sort: e.target.value as SortKey })}
            >
              {SORTS.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          {view.length ? (
            <>
              <div className="wide-grid">
                {view.slice(0, n).map((p) => (
                  <div key={p.id} data-card={p.id}>
                    <PosterCard p={p} today={today} />
                  </div>
                ))}
              </div>
              {view.length > n && (
                <div className="list-more">
                  <button type="button" onClick={more}>
                    <ExpandMore />
                    {view.length - n}건 더보기
                  </button>
                </div>
              )}
            </>
          ) : (
            <NoResult items={items} cond={cond} set={set} reset={reset} today={today} />
          )}
        </div>
        <div className="list-side pc-only">
          <AskPanel items={items} today={today} onShowAll={showAll} />
        </div>
      </div>
      <div className="m-only">
        <AskFab items={items} today={today} onShowAll={showAll} />
      </div>
    </>
  );
}
