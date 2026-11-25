"use client";
import Link from "next/link";
import { useState } from "react";
import { addDays, byCode, weekday, type Item } from "@/lib/popup";
import { posterBg } from "../cards";
import { ExpandMore } from "../Icons";

const WEEK_MAX = 2; // 요일마다 2곳까지, 나머지는 '+N건 더보기' (앱 WEEK_MAX)
const two = (n: number) => String(n).padStart(2, "0");

// 곧 끝나는 팝업 (11/20 요청): 어제부터 7일 (금요일이면 목 ~ 다음 주 수, 앱 _home_week).
// 그날 끝나는 팝업을 그 날짜 칸에. 모양은 A-Home — 7칸(오늘은 연민트, 지난 날은 흐리게), 칸 안에 작은 포스터 + 이름 줄.
// 모바일(A-Mobile)은 팝업 하나에 한 줄: 날짜 · 포스터 · 이름 · 지역. 끝나는 팝업이 없는 날은 줄이 없다 (CSS).
export default function WeekCalendar({ items, first, today }: { items: Item[]; first: string; today: string }) {
  const [open, setOpen] = useState<Record<number, boolean>>({});
  const days = Array.from({ length: 7 }, (_, i) => {
    const day = addDays(first, i);
    const ends = items.filter((p) => p.end === day && p.start && p.start <= day).sort((a, b) => byCode(a.work, b.work));
    return { day, ends };
  });
  const none = days.every((d) => !d.ends.length);
  return (
    <div className="ah-week-scroll">
      <div className={`ah-week${none ? " none" : ""}`}>
        {days.map(({ day, ends }, i) => {
          const cls = day === today ? "today" : day < today ? "past" : "";
          const shown = open[i] ? ends : ends.slice(0, WEEK_MAX);
          const [, m, d] = day.split("-").map(Number);
          const name = day === today ? "오늘" : day === addDays(today, -1) ? "어제" : weekday(day);
          const date = `${two(m)}.${two(d)}`;
          return (
            <div key={day} className={`ah-wk ${cls}`}>
              <div className="ah-wk-h">
                <span>
                  {name} {date}
                </span>
                {ends.length > 0 && <span className="ah-wk-n">{ends.length}곳</span>}
              </div>
              {shown.map((p) => (
                <Link key={p.id} href={`/popup/${p.id}`} className={`ah-wk-i ${cls}`} prefetch={false}>
                  <span className="ah-wk-d">
                    {name}
                    <br />
                    {date}
                  </span>
                  <span className="ah-wk-p" style={posterBg(p.poster)} />
                  <span className="ah-wk-b">
                    <span className="ah-wk-t">{p.work}</span>
                    <span className="ah-wk-s">{p.area || p.name}</span>
                  </span>
                </Link>
              ))}
              {ends.length > WEEK_MAX && !open[i] && (
                <button type="button" className="ah-wk-more" onClick={() => setOpen((o) => ({ ...o, [i]: true }))}>
                  <ExpandMore />+{ends.length - WEEK_MAX}건 더보기
                </button>
              )}
            </div>
          );
        })}
        {none && <div className="ah-empty ah-wk-none">이번 주에 끝나는 팝업이 없어요.</div>}
      </div>
    </div>
  );
}
