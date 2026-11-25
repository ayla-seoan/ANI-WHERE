"use client";
import { useMemo, useState } from "react";
import { addDays, darken, regionColor, stateOf, weekday, type Item } from "@/lib/popup";
import { posterBg } from "../cards";
import { periodShort } from "./BrowseCard";
import { HelpIcon } from "../Icons";
import { areasByDistance, type LatLng } from "@/lib/locate";

// 데일리 팝업 노트 (앱 render_daily): 고른 날(처음엔 오늘) 열려 있는 팝업을 지역별로. ‹ › 로 날짜·지역을 넘긴다.
// 위치를 허용하면 내 위치에서 가까운 지역부터 (앱과 같게, 11/19 요청), 아니면 그날 팝업이 많은 지역부터.
export default function DailyNote({
  items,
  today,
  onPick,
  me = null,
  picked = "",
}: {
  items: Item[];
  today: string;
  onPick: (id: string) => void;
  me?: LatLng | null;
  /** 지도에서 미리보기가 열려 있는 팝업 (그 줄을 민트 테두리로) */
  picked?: string;
}) {
  const [off, setOff] = useState(0);
  const [ai, setAi] = useState(0);
  const day = addDays(today, off);
  const open = useMemo(() => items.filter((p) => p.start && p.end && p.start <= day && day <= p.end), [items, day]);
  const order = useMemo(() => {
    const cnt = new Map<string, number>();
    for (const p of open) cnt.set(p.area || "기타", (cnt.get(p.area || "기타") ?? 0) + 1);
    const byCount = [...cnt.entries()].sort((a, b) => b[1] - a[1]);
    if (!me) return byCount;
    const near = areasByDistance(
      me,
      open
        .filter((p) => p.lat !== null && p.lng !== null)
        .map((p) => ({ area: p.area || "기타", lat: p.lat as number, lng: p.lng as number })),
    );
    const rank = new Map(near.map((a, i) => [a, i]));
    return byCount.sort((a, b) => (rank.get(a[0]) ?? 999) - (rank.get(b[0]) ?? 999));
  }, [open, me]);
  const choices = [...order.map(([a]) => a), "전체"];
  const area = choices[((ai % choices.length) + choices.length) % choices.length];
  const count = area === "전체" ? open.length : (order.find(([a]) => a === area)?.[1] ?? 0);
  const rows = (area === "전체" ? open : open.filter((p) => (p.area || "기타") === area)).sort((a, b) =>
    a.start.localeCompare(b.start),
  );
  const [y, m, d] = day.split("-").map(Number);
  const yy = String(y) === today.slice(0, 4) ? "" : `${y}년 `;
  const first = order[0]?.[0];

  return (
    <div className="daily">
      <div className="daily-head">
        <h2 className="dn-title">
          데일리 팝업 노트
          <span className="help" tabIndex={0}>
            <HelpIcon />
            <span className="tip">
              고른 날 열려 있는 팝업이에요.{" "}
              {me ? "내 위치에서 가까운 지역부터 보여 줘요." : "그날 팝업이 많은 지역부터 보여 줘요 (위치를 허용하면 가까운 지역부터)."}
            </span>
          </span>
        </h2>
        <div className="dn-nav dn-day">
          <button type="button" aria-label="전날" onClick={() => setOff((k) => k - 1)}>
            <Chev back />
          </button>
          <span className="dn-date">
            {off === 0 && <span className="dn-today">오늘</span>}
            <span className="pc-only">
              {yy}
              {m}월 {d}일 ({weekday(day)})
            </span>
            <span className="m-only">
              {m}.{d} ({weekday(day)})
            </span>
          </span>
          <button type="button" aria-label="다음 날" onClick={() => setOff((k) => k + 1)}>
            <Chev />
          </button>
        </div>
        <div className="dn-nav dn-areanav">
          <button
            type="button"
            aria-label="이전 지역"
            disabled={choices.length < 2}
            onClick={() => setAi((k) => k - 1)}
          >
            <Chev back />
          </button>
          <span className="dn-area">
            {area}
            <span>{count}</span>
          </span>
          <button
            type="button"
            aria-label="다음 지역"
            disabled={choices.length < 2}
            onClick={() => setAi((k) => k + 1)}
          >
            <Chev />
          </button>
        </div>
        {first && (
          <div className="dn-hint">
            {me ? "내 위치에서 가까운 " : "팝업이 많은 "}
            <b>{first}</b>부터
          </div>
        )}
      </div>
      {rows.length ? (
        <ul className="dn-list">
          {rows.map((p) => {
            const s = stateOf(p, today);
            return (
              <li key={p.id}>
                <button
                  type="button"
                  className={`dn-item${p.id === picked ? " on" : ""}`}
                  aria-current={p.id === picked ? "true" : undefined}
                  onClick={() => onPick(p.id)}
                >
                  <span className="dn-thumb" style={posterBg(p.poster)} />
                  <span className="dn-body">
                    <span className="dn-name">{p.work}</span>
                    <span className="dn-place">
                      {p.area && <b style={{ color: darken(regionColor(p.city), 0.62) }}>{p.area}</b>}
                      {p.area ? " · " : ""}
                      {periodShort(p, today)}
                    </span>
                  </span>
                  <span className={`dn-state ${s.color}`}>{s.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="dn-empty">이날 열려 있는 팝업이 없어요.</div>
      )}
    </div>
  );
}

function Chev({ back = false }: { back?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={back ? "M15 6l-6 6 6 6" : "M9 6l6 6-6 6"} />
    </svg>
  );
}
