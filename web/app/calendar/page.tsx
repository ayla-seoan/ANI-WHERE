import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getPopupData } from "@/lib/data";
import { dayLabel, todayKST } from "@/lib/popup";
import { posterBg } from "@/components/cards";
import KeepBox, { type KeepItem } from "@/components/member/KeepBox";
import SeasonFx from "@/components/member/SeasonFx";
import { displayName } from "@/lib/server/auth";
import { inbox, myVisited, ruleSettings, whyOf } from "@/lib/server/member";
import { calColor, calStatus, monthWeeks, noticeHistory, upcoming, type CalEvent } from "@/lib/server/mycal";
import { getMe, getMyFavs } from "@/lib/server/session";
import { histId, markId, ntfCookieName, ntfName, ntfRead } from "@/lib/server/ntf";
import NtfHistory, { type HistItem } from "@/components/member/NtfHistory";

// 내 캘린더 (회원만, 앱 render_my_calendar_view): 왼쪽 = 북마크한 팝업 달력 + 곧 있는 팝업,
// 가운데 = 북마크 · 다녀온 팝업 · 최근 본 팝업, 오른쪽 = 알림 받은 내역 (최근 3일).
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "내 캘린더", robots: { index: false } };

type Props = { searchParams: Promise<{ m?: string }> };

export default async function CalendarPage({ searchParams }: Props) {
  const me = await getMe();
  if (!me) redirect("/login?next=/calendar");
  const sp = await searchParams;
  const today = todayKST();
  const [{ popups }, favIds, rules] = await Promise.all([getPopupData(), getMyFavs(), ruleSettings()]);
  const fav = new Set(favIds);
  const events: CalEvent[] = popups
    .filter((p) => fav.has(p.id) && p.start && p.end && p.end >= today) // 끝난 팝업은 달력에서도 뺀다
    .map((p) => ({
      cafeId: p.id,
      work: p.work,
      cafeName: p.name,
      start: p.start,
      end: p.end,
      poster: p.images[0] || "",
      address: p.address,
    }))
    .sort((a, b) => a.start.localeCompare(b.start) || a.end.localeCompare(b.end) || a.work.localeCompare(b.work));

  const m = /^(\d{4})-(\d{2})$/.exec(sp.m || "");
  const year = m ? Number(m[1]) : Number(today.slice(0, 4));
  const month = m ? Number(m[2]) : Number(today.slice(5, 7));
  const shift = (d: number) => {
    const t = new Date(Date.UTC(year, month - 1 + d, 1));
    return `/calendar?m=${t.toISOString().slice(0, 7)}`;
  };
  const weeks = monthWeeks(year, month, events);
  const [laneH, top, minH] = [23, 32, 86];

  // 가운데 칸: 북마크 · 다녀온(내가 쓴 다녀온 후기) · 최근 본 (최근 본 것은 이 브라우저에 남은 목록으로)
  const live = popups.filter((p) => !p.end || p.end >= today);
  const toKeep = (p: (typeof popups)[number]): KeepItem => ({
    id: p.id,
    work: p.work,
    name: p.name,
    start: p.start,
    end: p.end,
    poster: p.images[0] || "",
  });
  const favItems = live
    .filter((p) => fav.has(p.id))
    .sort((a, b) => a.start.localeCompare(b.start))
    .map(toKeep);
  let visited: { item: KeepItem; reviews: { rating: number; body: string; when: string }[] }[] = [];
  try {
    const mine = await myVisited(displayName(me.row));
    const byCafe = new Map<string, { rating: number; body: string; when: string }[]>();
    for (const r of mine.sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)))) {
      const k = String(r.cafe_id);
      byCafe.set(k, [
        ...(byCafe.get(k) ?? []),
        { rating: Number(r.rating) || 0, body: String(r.body || ""), when: String(r.updated_at) },
      ]);
    }
    visited = [...byCafe.entries()]
      .map(([k, rv]) => ({ p: live.find((p) => p.id === k), rv }))
      .filter((x) => x.p)
      .map((x) => ({ item: toKeep(x.p!), reviews: x.rv }));
  } catch {
    /* 리뷰를 못 읽어도 달력은 보여 준다 */
  }

  const hist = noticeHistory(
    events,
    today,
    rules.open.enabled ? (rules.open.days ?? 3) : -1,
    rules.end.enabled ? (rules.end.days ?? 3) : -1,
  );
  // 받은 알림은 최근 3일만, 20개까지 (앱 _render_notice_history)
  const box = (await inbox(me.key, rules, today))
    .filter((x) => x.when.slice(0, 10) >= new Date(Date.parse(today) - 2 * 86400000).toISOString().slice(0, 10))
    .slice(0, 20)
    .map(({ id, title, body, why }) => ({ id, title, body, why }));
  // 오늘 알림은 종과 같은 번호(읽음 공유), 지난 날 알림은 'h' 번호로 '지난 알림'
  let lastDay = "";
  const histItems: HistItem[] = hist.slice(0, 40).map((h) => {
    const head =
      h.day !== lastDay ? (h.day === today ? "오늘" : `${Number(h.day.slice(5, 7))}월 ${Number(h.day.slice(8, 10))}일`) : "";
    lastDay = h.day;
    const why = whyOf(h.kind, rules);
    return {
      id: h.day === today ? markId(today, h.e.cafeId, h.label, ntfName(h.e.work, h.e.cafeName), why) : histId(h.day, h.e.cafeId, h.label),
      head,
      past: h.day !== today,
      label: h.label,
      work: h.e.work,
      cafe: h.e.cafeName,
      cafeId: h.e.cafeId,
      poster: h.e.poster,
      why,
    };
  });

  return (
    <div className="mycal">
      {/* 내 캘린더에서만 계절 배경 (꽃잎 · 잎사귀 · 단풍 · 눈) — 다른 화면으로 가면 이 칸과 함께 사라진다 */}
      <SeasonFx />
      <section className="mc-box mycal-box">
        <div className="cal-nav">
          <span className="cal-title">
            <span className="cal-label">내 캘린더</span>
            <span className="cal-month">
              {year}년 {month}월
            </span>
            <span className="help" tabIndex={0}>
              ?
              <span className="tip">
                내가 북마크한 팝업만 달력에 보여요. 리스트나 상세의 북마크 아이콘을 누르면 여기에 추가돼요.
              </span>
            </span>
          </span>
          <Link href={shift(-1)} className="cal-arrow" aria-label="지난달">
            ‹
          </Link>
          <Link href={shift(1)} className="cal-arrow" aria-label="다음 달">
            ›
          </Link>
          <Link href="/calendar" className="cal-now">
            이번달
          </Link>
        </div>
        <div className="cal-nick">{String(me.row.nickname || "")}</div>
        {!events.length && (
          <div className="cal-empty">아직 북마크한 팝업이 없어요. 리스트에서 북마크하면 달력에 일정이 채워져요.</div>
        )}
        <div className="cal">
          <div className="cal-dow">
            {"일월화수목금토".split("").map((d) => (
              <div key={d}>{d}</div>
            ))}
          </div>
          {weeks.map((w) => {
            const h = Math.max(minH, top + w.lanes * laneH + 8);
            return (
              <div className="cal-week" key={w.days[0]}>
                {w.days.map((d, i) => (
                  <div
                    key={d}
                    className={`cal-day${Number(d.slice(5, 7)) !== month ? " out" : ""}${i === 0 ? " sun" : i === 6 ? " sat" : ""}${d === today ? " today" : ""}`}
                    style={{ minHeight: h }}
                  >
                    <span>{Number(d.slice(8, 10))}</span>
                  </div>
                ))}
                {w.bars.map((b) => (
                  <Link
                    key={`${b.e.cafeId}-${b.col}`}
                    href={`/popup/${b.e.cafeId}`}
                    className={`cal-bar${b.cl ? " cl" : ""}${b.cr ? " cr" : ""}`}
                    style={{
                      left: `calc(${b.col} * 100% / 7 + 3px)`,
                      width: `calc(${b.span} * 100% / 7 - 6px)`,
                      top: top + b.lane * laneH,
                      background: calColor(b.e.work),
                    }}
                  >
                    {b.e.work}
                  </Link>
                ))}
              </div>
            );
          })}
        </div>
        <div className="up-head">
          <b>곧 있는 팝업</b>
          <i />
        </div>
        {upcoming(events, today).map((e) => {
          const [label, color] = calStatus(e, today);
          const when = dayLabel(e.start, false) + (e.start === e.end ? "" : ` - ${dayLabel(e.end, false)}`);
          return (
            <Link key={e.cafeId} className="up-item" href={`/popup/${e.cafeId}`}>
              <span className="up-bar" style={{ background: calColor(e.work) }} />
              <span className="up-thumb" style={posterBg(e.poster)} />
              <span className="up-text">
                <span className="up-name">
                  {e.work} · {e.cafeName}
                </span>
                <span className="up-when">{when}</span>
              </span>
              <span className={`up-state ${color}`}>{label}</span>
            </Link>
          );
        })}
        {!events.length && <div className="up-empty">곧 있는 북마크한 팝업이 없어요. 리스트에서 북마크해 보세요.</div>}
      </section>

      <section className="mc-box keep-box">
        <KeepBox favs={favItems} visited={visited} all={live.map(toKeep)} today={today} />
      </section>

      <section className="mc-box ntf-box">
        <div className="mc-title">
          알림 받은 내역
          <span className="help" tabIndex={0}>
            ?
            <span className="tip">
              북마크한 팝업의 오픈 {rules.open.days}일 전, 종료 {rules.end.days}일 전부터 당일까지 알려 드려요. 최근 3일
              알림만 보여요. 관리자 공지와 삭제 요청 결과도 여기에 와요.
            </span>
          </span>
        </div>
        <NtfHistory
          cookie={ntfCookieName(me.key)}
          initial={await ntfRead(me.key)}
          inbox={box}
          hist={histItems}
          nearKm={20}
        />
      </section>
    </div>
  );
}
