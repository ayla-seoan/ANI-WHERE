"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { goLogin, useMember } from "../member/MemberContext";
import type { Item } from "@/lib/popup";
import { PosterCard } from "../cards";
import { BookmarkIcon, ChatIcon, CloseIcon, ExpandMore, HelpIcon, TuneIcon } from "../Icons";
import FilterBar from "./FilterBar";
import AreaPicker from "./AreaPicker";
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
  // '북마크' 버튼 (앱 _follow_switch · fav_only): 내가 북마크한 팝업만. 검색 조건이 아니라서 필터 숫자에는 세지 않는다 (11/19)
  const { me, favs } = useMember();
  const router = useRouter();
  const path = usePathname() || "/list";
  const [favOnly, setFavOnly] = useState(false);
  const toggleFavOnly = () => {
    if (!me) {
      goLogin(router, "북마크는 로그인하면 쓸 수 있어요.", path);
      return;
    }
    setFavOnly((v) => !v);
  };

  const view = useMemo(() => {
    const hit = applyCond(items, cond, today);
    return sortItems(favOnly ? hit.filter((p) => favs.has(p.id)) : hit, cond.sort, today);
  }, [items, cond, today, favOnly, favs]);

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
            <button
              type="button"
              className={`fav-only${favOnly ? " on" : ""}`}
              aria-pressed={favOnly}
              onClick={toggleFavOnly}
            >
              <BookmarkIcon />
              북마크
            </button>
            {/* 앱 목록 위 '지역 고르기' 칸 (PC). 필터 상자의 지역과 같은 값 */}
            <AreaPicker className="pc-only" value={cond.area} areas={areas} onChange={(v) => set({ area: v })} />
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
            favOnly && applyCond(items, cond, today).length ? (
              <div className="bx-empty fav-empty">
                <h4>{favs.size ? "이 조건에 북마크한 팝업이 없어요" : "아직 북마크한 팝업이 없어요"}</h4>
                <p>카드 오른쪽 아래 북마크 아이콘을 누르면 여기에 모여요.</p>
                <div className="list-more">
                  <button type="button" onClick={() => setFavOnly(false)}>
                    북마크만 보기 끄기
                  </button>
                </div>
              </div>
            ) : (
              <NoResult items={items} cond={cond} set={set} reset={reset} today={today} />
            )
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
