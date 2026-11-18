"use client";
import { useMemo, useState } from "react";
import { addDays, weekday, type Item } from "@/lib/popup";
import { AreaBadge, posterBg } from "../cards";
import { HelpIcon } from "../Icons";

// 데일리 팝업 노트 (앱 render_daily): 고른 날(처음엔 오늘) 열려 있는 팝업을 지역별로. ‹ › 로 날짜·지역을 넘긴다.
// 앱은 내 위치에서 가까운 지역부터 보여 주지만, 이 웹은 위치를 묻지 않고 그날 팝업이 많은 지역부터 보여 준다.
export default function DailyNote({
  items,
  today,
  onPick,
}: {
  items: Item[];
  today: string;
  onPick: (id: string) => void;
}) {
  const [off, setOff] = useState(0);
  const [ai, setAi] = useState(0);
  const day = addDays(today, off);
  const open = useMemo(() => items.filter((p) => p.start && p.end && p.start <= day && day <= p.end), [items, day]);
  const order = useMemo(() => {
    const cnt = new Map<string, number>();
    for (const p of open) cnt.set(p.area || "기타", (cnt.get(p.area || "기타") ?? 0) + 1);
    return [...cnt.entries()].sort((a, b) => b[1] - a[1]);
  }, [open]);
  const choices = [...order.map(([a]) => a), "전체"];
  const area = choices[((ai % choices.length) + choices.length) % choices.length];
  const count = area === "전체" ? open.length : (order.find(([a]) => a === area)?.[1] ?? 0);
  const rows = (area === "전체" ? open : open.filter((p) => (p.area || "기타") === area)).sort((a, b) =>
    a.start.localeCompare(b.start),
  );
  const [y, m, d] = day.split("-");

  return (
    <div className="daily">
      <div className="daily-head">
        <div className="dn-title">
          데일리 팝업 노트
          <span className="help" tabIndex={0}>
            <HelpIcon />
            <span className="tip">고른 날 열려 있는 팝업이에요. 그날 팝업이 많은 지역부터 보여 줘요.</span>
          </span>
        </div>
        <div className="dn-nav">
          <button type="button" aria-label="전날" onClick={() => setOff((k) => k - 1)}>
            ‹
          </button>
          <span>
            {off === 0 && <span className="dn-today">오늘</span>}
            <span className="dn-date">
              {y.slice(2)}. {m}. {d}. {weekday(day)}
            </span>
          </span>
          <button type="button" aria-label="다음 날" onClick={() => setOff((k) => k + 1)}>
            ›
          </button>
        </div>
        <div className="dn-nav">
          <button
            type="button"
            aria-label="이전 지역"
            disabled={choices.length < 2}
            onClick={() => setAi((k) => k - 1)}
          >
            ‹
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
            ›
          </button>
        </div>
      </div>
      {rows.length ? (
        <div className="dn-list">
          {rows.map((p) => (
            <button key={p.id} type="button" className="dn-item" onClick={() => onPick(p.id)}>
              <span className="dn-thumb" style={posterBg(p.poster)} />
              <span className="dn-body">
                <AreaBadge area={p.area} city={p.city} />
                <span className="dn-name">{p.work}</span>
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="dn-empty">이날 열려 있는 팝업이 없어요.</div>
      )}
    </div>
  );
}
