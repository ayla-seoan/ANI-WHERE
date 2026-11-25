import type { CSSProperties } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getPopupData } from "@/lib/data";
import { daysBetween, todayKST, weekday } from "@/lib/popup";
import { tierOf } from "@/lib/stamp";
import KeepBox, { type KeepItem, type KeepTab } from "@/components/member/KeepBox";
import SeasonFx from "@/components/member/SeasonFx";
import { displayName } from "@/lib/server/auth";
import { calTone } from "@/lib/server/a-member";
import { inbox, myVisited, ruleSettings, whyOf } from "@/lib/server/member";
import { monthWeeks, noticeHistory, upcoming, type CalEvent } from "@/lib/server/mycal";
import { getMe, getMyFavs } from "@/lib/server/session";
import { myStamps } from "@/lib/server/stamp";
import { histId, markId, ntfCookieName, ntfName, ntfRead } from "@/lib/server/ntf";
import NtfHistory, { type HistItem } from "@/components/member/NtfHistory";

// 내 캘린더 (회원만, A-Cal · A-MCal · A-MVisited / 앱 render_my_calendar_view):
// 왼쪽 400px = 북마크한 팝업 달력 + 곧 있는 팝업, 가운데(넓게) = 북마크 · 다녀온 팝업(후기 도장) · 최근 본,
// 오른쪽 = 알림 받은 내역 (최근 3일) + 내 주변 추천. 모바일은 달력 → 목록 → 알림 순으로 한 줄.
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "내 캘린더", robots: { index: false } };

type Props = { searchParams: Promise<{ m?: string; tab?: string }> };

const md = (s: string) => `${Number(s.slice(5, 7))}.${Number(s.slice(8, 10))}`;

/** 곧 있는 팝업 배지 (A-Cal): 열리기 전 = 'D-3 오픈'(파랑), 진행 중 = '종료 D-5'(7일 안이면 빨강) */
function upBadge(e: CalEvent, today: string): [string, string, string] {
  if (e.start > today) return [`D-${daysBetween(today, e.start)} 오픈`, "blue", e.start];
  if (e.start === today && e.end !== today) return ["오늘 오픈", "green", e.start];
  const left = daysBetween(today, e.end);
  if (left === 0) return ["오늘 종료", "red", e.end];
  return [`종료 D-${left}`, left <= 7 ? "red" : "gray", e.end];
}

export default async function CalendarPage({ searchParams }: Props) {
  const me = await getMe();
  if (!me) redirect("/login?next=/calendar");
  const sp = await searchParams;
  const today = todayKST();
  const myName = displayName(me.row);
  const [{ popups }, favIds, rules, stamps] = await Promise.all([getPopupData(), getMyFavs(), ruleSettings(), myStamps(myName)]);
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
  // 모바일 달력 아래 범례: 이 달에 보이는 팝업 (작품마다 한 번)
  const legend = [...new Map(weeks.flatMap((w) => w.bars).map((b) => [b.e.work || b.e.cafeName, calTone(b.e.work)[1]])).entries()];

  // 가운데 칸: 북마크 · 다녀온(내가 쓴 다녀온 후기) · 최근 본 (최근 본 것은 이 브라우저에 남은 목록으로)
  const byId = new Map(popups.map((p) => [p.id, p])); // 알림 내역의 지역 칩 (11/20)
  const live = popups.filter((p) => !p.end || p.end >= today);
  const toKeep = (p: (typeof popups)[number]): KeepItem => ({
    id: p.id,
    work: p.work,
    name: p.name,
    start: p.start,
    end: p.end,
    poster: p.images[0] || "",
    area: p.area,
    city: p.city,
    perk: p.perks[0] || "",
  });
  const favItems = live
    .filter((p) => fav.has(p.id))
    .sort((a, b) => a.start.localeCompare(b.start))
    .map(toKeep);
  let visited: { item: KeepItem; reviews: { rating: number; body: string; when: string }[] }[] = [];
  try {
    const mine = await myVisited(myName);
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
  const dayText = (d: string) => (d === today ? "오늘" : md(d));
  // 받은 알림은 최근 3일만, 20개까지 (앱 _render_notice_history)
  const box = (await inbox(me.key, rules, today))
    .filter((x) => x.when.slice(0, 10) >= new Date(Date.parse(today) - 2 * 86400000).toISOString().slice(0, 10))
    .slice(0, 20)
    .map(({ id, title, body, why, when }) => ({ id, title, body, why, day: dayText(when.slice(0, 10)) }));
  // 오늘 알림은 종과 같은 번호(읽음 공유), 지난 날 알림은 'h' 번호로 '지난 알림'
  const histItems: HistItem[] = hist.slice(0, 40).map((h) => {
    const why = whyOf(h.kind, rules);
    return {
      id: h.day === today ? markId(today, h.e.cafeId, h.label, ntfName(h.e.work, h.e.cafeName), why) : histId(h.day, h.e.cafeId, h.label),
      day: dayText(h.day),
      past: h.day !== today,
      label: h.label,
      work: h.e.work,
      cafe: h.e.cafeName,
      cafeId: h.e.cafeId,
      poster: h.e.poster,
      area: byId.get(h.e.cafeId)?.area || "",
      city: byId.get(h.e.cafeId)?.city || "",
      why,
    };
  });
  const od = rules.open.enabled ? rules.open.days : null;
  const ed = rules.end.enabled ? rules.end.days : null;
  const tip =
    od !== null && ed !== null
      ? od === ed
        ? `북마크한 팝업은 오픈·종료 ${od}일 전부터 알려 드려요.`
        : `북마크한 팝업은 오픈 ${od}일 전 · 종료 ${ed}일 전부터 알려 드려요.`
      : od !== null
        ? `북마크한 팝업은 오픈 ${od}일 전부터 알려 드려요.`
        : ed !== null
          ? `북마크한 팝업은 종료 ${ed}일 전부터 알려 드려요.`
          : "";
  const tab: KeepTab = sp.tab === "visited" || sp.tab === "recent" ? sp.tab : "fav";
  const up = upcoming(events, today);

  return (
    <div className="mycal">
      {/* 내 캘린더에서만 계절 배경 (꽃잎 · 잎사귀 · 단풍 · 눈) — 다른 화면으로 가면 이 칸과 함께 사라진다 */}
      <SeasonFx />
      <div className="amc-left">
        <section className="amc-box" aria-labelledby="amc-h">
          <div className="amc-head">
            <div className="amc-title">
              <h1 id="amc-h">
                내 캘린더
                <span className="help" tabIndex={0}>
                  ?
                  <span className="tip">
                    내가 북마크한 팝업만 달력에 보여요. 리스트나 상세의 북마크 아이콘을 누르면 여기에 추가돼요.
                  </span>
                </span>
              </h1>
              <span className="amc-nick">
                {String(me.row.nickname || "")} · 북마크한 팝업 {favItems.length}곳
              </span>
            </div>
            <div className="amc-nav">
              <Link href={shift(-1)} className="amc-arrow prev" aria-label="지난달">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" aria-hidden>
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </Link>
              <span className="amc-month">
                {year}년 {month}월
              </span>
              <Link href={shift(1)} className="amc-arrow" aria-label="다음 달">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" aria-hidden>
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </Link>
              <Link href="/calendar" className="amc-now">
                이번달
              </Link>
            </div>
          </div>
          {!events.length && (
            <div className="amc-empty">아직 북마크한 팝업이 없어요. 리스트에서 북마크하면 달력에 일정이 채워져요.</div>
          )}
          <div className="amc-dow" aria-hidden>
            {"일월화수목금토".split("").map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>
          <div className="amc-weeks">
            {weeks.map((w) => (
              <div className="amc-week" key={w.days[0]} style={{ "--lanes": w.lanes } as CSSProperties}>
                <div className="amc-days">
                  {w.days.map((d, i) => (
                    <div
                      key={d}
                      className={`amc-day${Number(d.slice(5, 7)) !== month ? " out" : ""}${i === 0 ? " sun" : ""}${d === today ? " today" : ""}`}
                    >
                      <span>{Number(d.slice(8, 10))}</span>
                    </div>
                  ))}
                </div>
                {w.bars.map((b) => {
                  const [soft, strong] = calTone(b.e.work);
                  return (
                    <Link
                      key={`${b.e.cafeId}-${b.col}`}
                      href={`/popup/${b.e.cafeId}`}
                      className={`amc-bar${b.cl ? " cl" : ""}${b.cr ? " cr" : ""}`}
                      aria-label={`${b.e.work || b.e.cafeName} ${md(b.e.start)} ~ ${md(b.e.end)}`}
                      style={
                        {
                          left: `${(b.col / 7) * 100}%`,
                          width: `${(b.span / 7) * 100}%`,
                          "--lane": b.lane,
                          "--soft": soft,
                          "--strong": strong,
                        } as CSSProperties
                      }
                    >
                      <span>{b.e.work || b.e.cafeName}</span>
                    </Link>
                  );
                })}
              </div>
            ))}
          </div>
          <p className="amc-foot pc-only">막대 = 북마크한 팝업 기간 · 둥근 끝 = 시작·종료일</p>
          {legend.length > 0 && (
            <div className="m-only">
              <ul className="amc-legend" aria-label="달력 색">
                {legend.map(([name, c]) => (
                  <li key={name}>
                    <i style={{ background: c }} />
                    {name}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="amc-up" aria-labelledby="amc-up-h">
          <h2 id="amc-up-h">곧 있는 팝업</h2>
          {up.map((e) => {
            const [label, color, when] = upBadge(e, today);
            return (
              <Link key={e.cafeId} className="am-up" href={`/popup/${e.cafeId}`}>
                <span className={`am-st ${color}`}>{label}</span>
                <span className="am-up-t">{e.work ? `${e.work} · ${e.cafeName}` : e.cafeName}</span>
                <span className="am-up-when">
                  {md(when)} ({weekday(when)})
                </span>
              </Link>
            );
          })}
          {!up.length && <div className="am-up-empty">곧 있는 북마크한 팝업이 없어요. 리스트에서 북마크해 보세요.</div>}
        </section>
      </div>

      <section className="amc-mid" id="keep">
        <KeepBox
          favs={favItems}
          visited={visited}
          all={live.map(toKeep)}
          today={today}
          stamps={stamps}
          lv={tierOf(stamps)?.lv ?? 0}
          initialTab={tab}
        />
      </section>

      <aside className="amc-side ntf-box">
        <NtfHistory
          cookie={ntfCookieName(me.key)}
          initial={await ntfRead(me.key)}
          inbox={box}
          hist={histItems}
          nearKm={20}
          help={`북마크한 팝업의 오픈 ${rules.open.days}일 전, 종료 ${rules.end.days}일 전부터 당일까지 알려 드려요. 최근 3일 알림만 보여요. 관리자 공지와 삭제 요청 결과도 여기에 와요.`}
          tip={tip}
        />
      </aside>
    </div>
  );
}
