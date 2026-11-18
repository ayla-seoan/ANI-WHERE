"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { periodDot, stateOf, type Item } from "@/lib/popup";
import { AreaBadge, posterBg } from "../cards";
import { CalendarIcon, ExpandMore, PinIcon, StoreIcon, TuneIcon } from "../Icons";
import FilterBar from "./FilterBar";
import DailyNote from "./DailyNote";
import MapCanvas, { type Bounds } from "./MapCanvas";
import NoResult from "./NoResult";
import AskPanel from "../ask/AskPanel";
import BookmarkButton from "../member/BookmarkButton";
import AskFab from "../ask/AskFab";
import { activeCount, applyCond, sortItems, useAreas, useCond, useFilterToggle } from "./filters";

/** 지도 처음 화면: 팝업이 가장 많은 시의 점들을 감싸는 범위 (앱 _busiest_area). 너무 확대되지 않게 최소 폭 */
function busiest(pts: Item[]): Bounds | null {
  if (!pts.length) return null;
  const cnt = new Map<string, number>();
  for (const p of pts) cnt.set(p.city || "?", (cnt.get(p.city || "?") ?? 0) + 1);
  const top = [...cnt.entries()].sort((a, b) => b[1] - a[1])[0][0];
  const sel = pts.filter((p) => (p.city || "?") === top);
  const lats = sel.map((p) => p.lat as number);
  const lngs = sel.map((p) => p.lng as number);
  const [s, n, w, e] = [Math.min(...lats), Math.max(...lats), Math.min(...lngs), Math.max(...lngs)];
  const padLat = Math.max((n - s) * 0.15, 0.02);
  const padLng = Math.max((e - w) * 0.15, 0.025);
  return { south: s - padLat, north: n + padLat, west: w - padLng, east: e + padLng };
}

export default function MapView({ items, today }: { items: Item[]; today: string }) {
  const router = useRouter();
  const { cond, set, reset, ready } = useCond();
  const [sheet, setSheet] = useFilterToggle(cond, ready);
  const [focus, setFocus] = useState<{ id: string; n: number } | null>(null);
  const areas = useAreas(items);
  const view = useMemo(() => sortItems(applyCond(items, cond, today), cond.sort, today), [items, cond, today]);
  const mapped = useMemo(() => view.filter((p) => p.lat !== null && p.lng !== null), [view]);
  // 처음 화면 범위는 전체 팝업 기준으로 한 번만 (조건을 바꿀 때마다 지도가 튀지 않게)
  const home = useMemo(
    () => busiest(items.filter((p) => p.lat !== null && p.lng !== null && p.end >= today)),
    [items, today],
  );
  const act = activeCount(cond);
  // 목록은 24곳씩 (모바일에서 지도 아래로 116장이 한꺼번에 길게 늘어지지 않게, 리스트로 보기와 같은 '더보기')
  const [n, setN] = useState(24);
  const sig = view.map((p) => p.id).join(",");
  useEffect(() => setN(24), [sig]);

  const pick = (id: string) => {
    if (mapped.some((p) => p.id === id)) {
      setFocus((f) => ({ id, n: (f?.n ?? 0) + 1 }));
      // 모바일: 지도가 화면 위에 보이게
      if (window.matchMedia("(max-width: 640px)").matches) {
        document.querySelector(".map-col")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } else {
      router.push(`/popup/${id}`); // 지도에 없는 팝업(좌표 없음·조건 밖)은 바로 상세로
    }
  };

  return (
    <div className="map-page">
      <FilterBar
        cond={cond}
        set={set}
        reset={reset}
        areas={areas}
        open={sheet}
        onClose={() => setSheet(false)}
        count={view.length}
      />
      <div className="map-tools m-only">
        <span className="map-count">
          지도에 <b>{mapped.length}</b>곳
        </span>
        <button type="button" className="m-filter" aria-label="필터 열기" onClick={() => setSheet((o) => !o)}>
          <TuneIcon />
          {act ? <span>{act}</span> : null}
        </button>
      </div>
      {/* 앱 지도로 보기와 같은 칸: 왼쪽 큰 칸(데일리 팝업 노트 · 지도, 그 아래 팝업 목록) | 오른쪽 물어보기 */}
      <div className="map-layout">
        <div className="map-left">
          <div className="map-row">
            <div className="daily-col">
              <DailyNote items={view} today={today} onPick={pick} />
            </div>
            <div className="map-col">
              {mapped.length || view.length ? (
                <MapCanvas points={mapped} home={home} focus={focus} />
              ) : (
                <NoResult items={items} cond={cond} set={set} reset={reset} today={today} />
              )}
            </div>
          </div>
          <section className="maplist" aria-label="팝업 목록">
            <div className="maplist-head">
              팝업 카페 <b>{view.length}</b>곳
              {view.length > mapped.length && <small> · 지도에 표시 {mapped.length}곳</small>}
            </div>
            <div className="maplist-body">
              {view.slice(0, n).map((p) => {
                const s = stateOf(p, today);
                return (
                  <div key={p.id} className="scard">
                    <Link href={`/popup/${p.id}`} className="scard-link" prefetch={false}>
                      <span className="thumb" style={posterBg(p.poster)} />
                      <span className="scard-info">
                        <AreaBadge area={p.area} city={p.city} />
                        <span className="ctitle">
                          <strong>{p.work}</strong> <span className={`cstate ${s.color}`}>{s.label}</span>
                        </span>
                        <span className="ccafe">
                          <StoreIcon />
                          {p.name}
                        </span>
                        <span className="cmeta">
                          <CalendarIcon />
                          {periodDot(p)}
                        </span>
                      </span>
                    </Link>
                    <BookmarkButton cafeId={p.id} variant="row" />
                    {p.lat !== null && (
                      <button
                        type="button"
                        className="scard-pin"
                        aria-label={`${p.work} 지도에서 보기`}
                        onClick={() => pick(p.id)}
                      >
                        <PinIcon />
                      </button>
                    )}
                  </div>
                );
              })}
              {view.length > n && (
                <div className="list-more">
                  <button type="button" onClick={() => setN((k) => k + 24)}>
                    <ExpandMore />
                    {view.length - n}건 더보기
                  </button>
                </div>
              )}
              {!view.length && <div className="dn-empty">조건에 맞는 팝업이 없어요.</div>}
            </div>
          </section>
        </div>
        <div className="map-right pc-only">
          <AskPanel items={items} today={today} />
        </div>
      </div>
      <div className="m-only">
        <AskFab items={items} today={today} />
      </div>
    </div>
  );
}
