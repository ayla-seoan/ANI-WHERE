"use client";
import { useEffect, useMemo, useState } from "react";
import { matchQuery, type Item } from "@/lib/popup";

// 리스트로 보기 · 지도로 보기가 함께 쓰는 검색 조건 (앱 page_map 의 검색 · 지역 · 진행여부 · 날짜 + 홈에서 넘어온 작품·사전예약).
// 주소창(?q=&area=&span=&day=&work=&reserve=&sort=)과 맞춰 두어, 상세에서 뒤로 오거나 링크를 공유해도 조건이 남는다.

export const SPANS = ["진행중 + 예정", "예정", "진행중"] as const;
export type Span = (typeof SPANS)[number];
export const SORTS = [
  { key: "new", label: "최신순" },
  { key: "old", label: "등록순" },
  { key: "open", label: "오픈 임박순" },
  { key: "end", label: "종료 임박순" },
] as const;
export type SortKey = (typeof SORTS)[number]["key"];

export type Cond = {
  q: string;
  area: string; // '' = 전체, 여러 곳이면 쉼표로 ('마포,송파') — 11/19 다중 선택
  span: Span;
  day: string; // YYYY-MM-DD 또는 ''
  work: string; // 홈 '특전 있는 작품들' 에서 넘어온 작품 ('' = 전체)
  reserve: boolean; // 홈 '사전예약 팝업' 더보기
  sort: SortKey;
  /** 물어보기 '더보기 · 리스트로 보기': 그 답에서 찾은 팝업만 (다른 조건 대신, 앱 ask_only) */
  ids: string[];
  askLabel: string;
};

export const EMPTY: Cond = {
  q: "",
  area: "",
  span: "진행중 + 예정",
  day: "",
  work: "",
  reserve: false,
  sort: "new",
  ids: [],
  askLabel: "",
};

function fromURL(): Cond {
  const sp = new URLSearchParams(window.location.search);
  const span = sp.get("span");
  const sort = sp.get("sort");
  const day = sp.get("day") || "";
  return {
    q: (sp.get("q") || "").slice(0, 60),
    area: (sp.get("area") || "").slice(0, 200),
    span: (SPANS as readonly string[]).includes(span || "") ? (span as Span) : EMPTY.span,
    day: /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : "",
    work: (sp.get("work") || "").slice(0, 80),
    reserve: sp.get("reserve") === "1",
    sort: SORTS.some((s) => s.key === sort) ? (sort as SortKey) : EMPTY.sort,
    ids: (sp.get("ids") || "")
      .split(",")
      .filter((x) => /^[\w-]{1,64}$/.test(x))
      .slice(0, 400),
    askLabel: (sp.get("ask") || "").slice(0, 40),
  };
}

function toQuery(c: Cond): string {
  const sp = new URLSearchParams();
  if (c.q.trim()) sp.set("q", c.q.trim());
  if (c.area) sp.set("area", c.area);
  if (c.span !== EMPTY.span) sp.set("span", c.span);
  if (c.day) sp.set("day", c.day);
  if (c.work) sp.set("work", c.work);
  if (c.reserve) sp.set("reserve", "1");
  if (c.sort !== EMPTY.sort) sp.set("sort", c.sort);
  if (c.ids.length) {
    sp.set("ids", c.ids.join(","));
    if (c.askLabel) sp.set("ask", c.askLabel);
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function useCond() {
  const [cond, setCond] = useState<Cond>(EMPTY);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    try {
      setCond(fromURL());
    } catch {
      /* 무시 */
    }
    setReady(true);
  }, []);
  useEffect(() => {
    if (!ready) return;
    window.history.replaceState(window.history.state, "", window.location.pathname + toQuery(cond));
  }, [cond, ready]);
  // 검색 조건을 바꾸면 물어보기 결과 보기(ids)는 풀린다 (정렬만 바꿀 때는 그대로)
  const set = (patch: Partial<Cond>) =>
    setCond((c) => {
      const filterChange = Object.keys(patch).some((k) => k !== "sort" && k !== "ids" && k !== "askLabel");
      return { ...c, ...(filterChange ? { ids: [], askLabel: "" } : {}), ...patch };
    });
  const reset = () => setCond((c) => ({ ...EMPTY, sort: c.sort }));
  return { cond, set, reset, ready };
}

/** 걸린 조건 수 (모바일 필터 버튼 옆 숫자) */
export function activeCount(c: Cond): number {
  return [!!c.q.trim(), !!c.area, c.span !== EMPTY.span, !!c.day, !!c.work, c.reserve].filter(Boolean).length;
}

/** 앱 _filter_view 와 같은 규칙 */
export function applyCond(items: Item[], c: Cond, today: string, opts: { area?: boolean } = {}): Item[] {
  if (c.ids.length) {
    // 물어보기 결과: 그 답의 팝업 전부 (검색 조건 대신)
    const keep = new Set(c.ids);
    return items.filter((p) => keep.has(p.id));
  }
  return items.filter((p) => {
    if (!p.start || !p.end) return false;
    if (c.span === "진행중 + 예정" && p.end < today) return false;
    if (c.span === "예정" && !(p.start > today)) return false;
    if (c.span === "진행중" && !(p.start <= today && p.end >= today)) return false;
    if (c.day && !(p.start <= c.day && c.day <= p.end)) return false;
    if (c.work && p.work !== c.work) return false;
    if (c.reserve && !(p.reserve && p.start > today)) return false;
    if (opts.area !== false && c.area && !c.area.split(",").includes(p.area)) return false;
    return matchQuery(p.text, c.q);
  });
}

/** 앱 _sort_view (인기순·리뷰 많은 순은 북마크·리뷰 수를 읽지 않아 뺐다) */
export function sortItems(items: Item[], sort: SortKey, today: string): Item[] {
  const v = [...items];
  const byCreated = (a: Item, b: Item) => b.created.localeCompare(a.created);
  if (sort === "new") v.sort(byCreated);
  if (sort === "old") v.sort((a, b) => a.created.localeCompare(b.created));
  if (sort === "open")
    v.sort(
      (a, b) =>
        Number(a.start <= today) - Number(b.start <= today) || a.start.localeCompare(b.start) || byCreated(a, b),
    );
  if (sort === "end")
    v.sort((a, b) => Number(a.end < today) - Number(b.end < today) || a.end.localeCompare(b.end) || byCreated(a, b));
  return v;
}

/** 지역 고르기 목록: 지금 있는 팝업의 지역, 많은 순 */
export function useAreas(items: Item[]): string[] {
  return useMemo(() => {
    const cnt = new Map<string, number>();
    for (const p of items) if (p.area) cnt.set(p.area, (cnt.get(p.area) ?? 0) + 1);
    return [...cnt.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "ko")).map(([a]) => a);
  }, [items]);
}

/**
 * 검색 필터 상자 열기·닫기. 앱처럼 PC 는 메뉴바의 검색 아이콘, 모바일은 목록 위 필터 아이콘으로 연다.
 * 메뉴바(Gnb)와는 window 이벤트로 주고받는다: 'aw:filters' (열기/닫기 요청) · 'aw:filters-state' (지금 열림 여부).
 */
export function useFilterToggle(cond: Cond, ready: boolean) {
  const [open, setOpen] = useState(false);
  // 주소창으로 검색·지역·날짜·진행여부 조건을 받아 들어왔으면 PC 에서는 처음부터 열어 둔다
  useEffect(() => {
    if (!ready) return;
    const has = !!cond.q.trim() || !!cond.area || !!cond.day || cond.span !== EMPTY.span;
    if (has && window.matchMedia("(min-width: 641px)").matches) setOpen(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);
  useEffect(() => {
    const onToggle = () => setOpen((o) => !o);
    window.addEventListener("aw:filters", onToggle);
    return () => window.removeEventListener("aw:filters", onToggle);
  }, []);
  // 메뉴바가 나중에 그려져도 알 수 있게 <html data-filters> 에도 적어 둔다
  useEffect(() => {
    document.documentElement.dataset.filters = open ? "1" : "0";
    window.dispatchEvent(new CustomEvent("aw:filters-state", { detail: open }));
  }, [open]);
  useEffect(
    () => () => {
      delete document.documentElement.dataset.filters;
      window.dispatchEvent(new CustomEvent("aw:filters-state", { detail: null }));
    },
    [],
  );
  return [open, setOpen] as const;
}
