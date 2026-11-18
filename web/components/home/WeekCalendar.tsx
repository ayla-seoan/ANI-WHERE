"use client";
import { useState } from "react";
import { addDays, byCode, daysBetween, type Item } from "@/lib/popup";
import { HomeCard } from "../cards";
import { ExpandMore } from "../Icons";

const WEEKDAYS = "월화수목금토일";
const WEEK_MAX = 2; // 요일마다 2곳까지, 나머지는 '+N건 더보기' (앱 WEEK_MAX)

// 이번 주에 끝나는 팝업: 월~일 일곱 칸 (앱 _home_week). 그날 끝나는 팝업을 그 요일 칸에, 오늘 칸은 강조, 지난 요일은 흐리게.
// 모바일에서는 요일을 위에서 아래로 한 줄씩 쌓는다 (CSS).
export default function WeekCalendar({ items, monday, today }: { items: Item[]; monday: string; today: string }) {
  const [open, setOpen] = useState<Record<number, boolean>>({});
  return (
    <div className="home-week">
      {Array.from({ length: 7 }, (_, i) => {
        const day = addDays(monday, i);
        const ends = items
          .filter((p) => p.end === day && p.start && p.start <= day)
          .sort((a, b) => byCode(a.work, b.work));
        const cls = day === today ? "today" : day < today ? "past" : "";
        const shown = open[i] ? ends : ends.slice(0, WEEK_MAX);
        const [, m, d] = day.split("-").map(Number);
        return (
          <div key={day} className={`wk ${cls}`}>
            <div className={`wkh ${cls}`}>
              <b>
                {WEEKDAYS[i]}
                {day === today ? " · 오늘" : ""}
              </b>
              <span className="wkd">
                {m}.{d}
              </span>
              <span className="wkn">{ends.length}</span>
            </div>
            {shown.map((p) => {
              const left = daysBetween(today, day);
              return (
                <HomeCard
                  key={p.id}
                  p={p}
                  today={today}
                  tall
                  badge={left === 0 ? "오늘 종료" : left < 0 ? "종료" : `D-${left}`}
                />
              );
            })}
            {ends.length > WEEK_MAX && !open[i] && (
              <button type="button" className="wk-more" onClick={() => setOpen((o) => ({ ...o, [i]: true }))}>
                <ExpandMore />+{ends.length - WEEK_MAX}건 더보기
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
