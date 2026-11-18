import "server-only";
import { createHash } from "node:crypto";

// 내 캘린더 (common/mycal.py + 앱 _cal_html 규칙): 북마크한 팝업을 달력에 막대로.
// 연속된 날은 한 막대, 주(일~토)를 넘으면 주마다 끊고, 겹치면 아래 줄(lane)로 내린다.

export type CalEvent = {
  cafeId: string;
  work: string;
  cafeName: string;
  start: string;
  end: string;
  poster: string;
  address: string;
};
export type Bar = { e: CalEvent; col: number; span: number; lane: number; cl: boolean; cr: boolean };
export type Week = { days: string[]; bars: Bar[]; lanes: number };

const CAL_COLORS = ["#14b8a6", "#F59E0B", "#8B5CF6", "#EC4899", "#3B82F6", "#22A06B", "#EF6C4D", "#64748B"];
/** 같은 작품은 늘 같은 색 (앱 _cal_color: md5 → 색 8개 중 하나) */
export function calColor(work: string): string {
  const h = createHash("md5").update(work, "utf8").digest("hex");
  return CAL_COLORS[Number(BigInt(`0x${h}`) % BigInt(CAL_COLORS.length))];
}

const toD = (s: string) => new Date(`${s}T00:00:00Z`);
const ymd = (d: Date) => d.toISOString().slice(0, 10);
const addD = (s: string, n: number) => {
  const d = toD(s);
  d.setUTCDate(d.getUTCDate() + n);
  return ymd(d);
};
const diff = (a: string, b: string) => Math.round((toD(b).getTime() - toD(a).getTime()) / 86400000);

/** 그 달의 주들 (일요일 시작, calendar.Calendar(firstweekday=6).monthdatescalendar 와 같음) */
export function monthWeeks(year: number, month: number, events: CalEvent[]): Week[] {
  const first = `${year}-${String(month).padStart(2, "0")}-01`;
  const dow = toD(first).getUTCDay(); // 0=일
  let cur = addD(first, -dow);
  const last = ymd(new Date(Date.UTC(year, month, 0)));
  const weeks: Week[] = [];
  while (cur <= last) {
    const days = Array.from({ length: 7 }, (_, i) => addD(cur, i));
    const [a, z] = [days[0], days[6]];
    const segs = events
      .filter((e) => !(e.end < a || e.start > z))
      .map((e) => {
        const s = e.start > a ? e.start : a;
        const t = e.end < z ? e.end : z;
        return { e, col: diff(a, s), span: diff(s, t) + 1, cl: e.start < a, cr: e.end > z };
      })
      .sort((x, y) => x.col - y.col || y.span - x.span);
    const lanesEnd: number[] = [];
    const bars: Bar[] = [];
    for (const g of segs) {
      let lane = lanesEnd.findIndex((end) => end < g.col);
      if (lane < 0) {
        lane = lanesEnd.length;
        lanesEnd.push(g.col + g.span - 1);
      } else lanesEnd[lane] = g.col + g.span - 1;
      bars.push({ ...g, lane });
    }
    weeks.push({ days, bars, lanes: bars.length ? Math.max(...bars.map((b) => b.lane)) + 1 : 0 });
    cur = addD(cur, 7);
  }
  return weeks;
}

/** 아직 끝나지 않은 일정: 진행 중인 것부터, 그다음 시작일이 가까운 순 (mycal.upcoming) */
export function upcoming(events: CalEvent[], today: string, limit = 10): CalEvent[] {
  return events
    .filter((e) => e.end >= today)
    .sort(
      (x, y) =>
        Number(x.start > today) - Number(y.start > today) ||
        x.start.localeCompare(y.start) ||
        x.end.localeCompare(y.end),
    )
    .slice(0, limit);
}

/** (배지 글자, 색) 진행 중 / 오늘 시작 / D-n / 오늘 종료 / 종료 (mycal.status) */
export function calStatus(e: CalEvent, today: string): [string, string] {
  if (e.end < today) return ["종료", "gray"];
  if (e.start > today) return [`D-${diff(today, e.start)}`, "blue"];
  if (e.start === today) return ["오늘 시작", "green"];
  if (e.end === today) return ["오늘 종료", "red"];
  return ["진행 중", "green"];
}

export type HistItem = { day: string; kind: "open" | "end"; label: string; e: CalEvent };

/** 알림 받은 내역 (앱 _notice_history): 북마크한 팝업마다 오픈·종료 D-n ~ 당일 알림이 생긴 날을 거꾸로, 최근 3일 */
export function noticeHistory(events: CalEvent[], today: string, openDays = 3, endDays = 3, daysBack = 2): HistItem[] {
  const out: HistItem[] = [];
  for (const e of events) {
    if (e.end < today) continue;
    for (const [kind, base, n] of [
      ["open", e.start, openDays],
      ["end", e.end, endDays],
    ] as const) {
      for (let d = n; d >= 0; d--) {
        const day = addD(base, -d);
        if (day > today || diff(day, today) > daysBack) continue;
        if (kind === "end" && day < e.start) continue;
        const label = kind === "open" ? (d === 0 ? "오늘 오픈" : `오픈 D-${d}`) : d === 0 ? "오늘 종료" : `종료 D-${d}`;
        out.push({ day, kind, label, e });
      }
    }
  }
  return out.sort((x, y) => y.day.localeCompare(x.day) || y.kind.localeCompare(x.kind));
}
