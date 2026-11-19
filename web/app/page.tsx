import Link from "next/link";
import { getPopupData } from "@/lib/data";
import {
  addDays,
  byCode,
  daysBetween,
  mondayOf,
  periodDot,
  stateOf,
  todayKST,
  toItem,
  type Item,
  type Popup,
} from "@/lib/popup";
import BookmarkPicker from "@/components/member/BookmarkPicker";
import { HomeCard, posterBg } from "@/components/cards";
import HScroll from "@/components/HScroll";
import RankBanner from "@/components/home/RankBanner";
import NewSection from "@/components/home/NewSection";
import WeekCalendar from "@/components/home/WeekCalendar";
import EmptyState from "@/components/EmptyState";
import { getMe, getMyFavs } from "@/lib/server/session";
import { rankScores, type Score } from "@/lib/server/rank";
import { EventIcon, HelpIcon, HourglassIcon, NewIcon } from "@/components/Icons";

export const revalidate = 600;

const STORY_MAX = 12;

/**
 * 실시간 인기 급상승 랭킹 (5위까지) — 앱 _home_rank 와 같은 기준 (11/19 요청, lib/server/rank.ts):
 *   ① 최근 7일 점수 = 북마크 수 × 2 + 리뷰 · 답글 수  ② 같으면 전체 기간 점수  ③ 같으면 오픈이 빠른 순
 */
function rankTop(live: Popup[], scores: Map<string, Score>): Popup[] {
  const sc = (p: Popup) => scores.get(p.id) ?? { week: 0, all: 0 };
  return [...live]
    .sort((a, b) => sc(b).week - sc(a).week || sc(b).all - sc(a).all || a.start.localeCompare(b.start))
    .slice(0, 5);
}

/** 팝업이 많은 지역 n 곳 (앱 _home_areas) */
function topAreas(rows: Item[], n = 3): string[] {
  const cnt = new Map<string, number>();
  for (const r of rows) if (r.area) cnt.set(r.area, (cnt.get(r.area) ?? 0) + 1);
  return [...cnt.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([a]) => a);
}

function HomeHead({ title, icon, more }: { title: string; icon: React.ReactNode; more?: string }) {
  return (
    <div className="home-hh">
      <h2 className="home-h">
        {icon}
        {title}
      </h2>
      {more && (
        <Link href={more} className="home-more">
          더보기
        </Link>
      )}
    </div>
  );
}

export default async function Home() {
  const { popups } = await getPopupData();
  const today = todayKST();
  if (!popups.length) {
    return <EmptyState title="지금은 팝업 정보를 불러오지 못했어요" hint="잠시 뒤 새로 고침해 보세요." />;
  }

  // 진행 중·오픈 예정만 (끝난 건 뺌, 앱 _live_rows)
  const live = popups.filter((p) => stateOf(p, today).rank < 2 && p.start && p.end);
  const liveItems = live.map(toItem);

  // 요즘 일정 많은 작품: 진행 중·예정 팝업이 많은 작품 순. 숫자 = 그 작품 팝업 수. 대표 포스터는 진행 중인 것 먼저
  const count = new Map<string, number>();
  for (const p of live) if (p.work.trim()) count.set(p.work.trim(), (count.get(p.work.trim()) ?? 0) + 1);
  const works = [...count.keys()].sort((a, b) => count.get(b)! - count.get(a)! || byCode(a, b)).slice(0, STORY_MAX);
  const posterOf = new Map<string, string>();
  for (const p of [...live].sort((a, b) => stateOf(a, today).rank - stateOf(b, today).rank)) {
    const w = p.work.trim();
    if (w && !posterOf.has(w) && p.images[0]) posterOf.set(w, p.images[0]);
  }

  const me = await getMe();
  const favs = new Set(await getMyFavs());
  const marked = live
    .filter((p) => favs.has(p.id))
    .sort((a, b) => stateOf(a, today).rank - stateOf(b, today).rank || a.end.localeCompare(b.end));
  const top = rankTop(live, await rankScores()).map(toItem);
  const fresh = [...liveItems].sort((a, b) => b.created.localeCompare(a.created));
  const monday = mondayOf(today);
  const weekItems = popups.filter((p) => p.end && p.end >= monday && p.end <= addDays(monday, 6)).map(toItem);
  // 사전예약 팝업: 아직 열기 전(오픈 예정)인 것만, 빨리 여는 순
  const reserve = liveItems
    .filter((p) => p.reserve && stateOf(p, today).rank === 1)
    .sort((a, b) => a.start.localeCompare(b.start));

  return (
    <div className="home">
      <h1 className="sr-only">ANI:WHERE 홈 — 애니 팝업·콜라보 카페</h1>

      {me ? (
        // 회원: '북마크 팝업' — 내가 북마크한 (진행 중 · 예정) 팝업 하나에 동그라미 하나, 위에 지역, 아래 작품 (앱 render_stories)
        <section className="stories" aria-labelledby="story-h">
          <div className="story-head" id="story-h">
            북마크 팝업
            <span className="help" tabIndex={0}>
              <HelpIcon />
              <span className="tip">
                내가 북마크한 팝업(진행 중 · 오픈 예정)이 여기에 모여요. 동그라미를 누르면 그 팝업으로 가고, &apos;최애
                추가하기&apos; 로 팝업을 골라 한 번에 북마크할 수 있어요.
              </span>
            </span>
          </div>
          <HScroll className="story-row" label="북마크 팝업">
            <BookmarkPicker
              items={live.map((p) => ({
                id: p.id,
                work: p.work,
                name: p.name,
                chars: p.characters,
                poster: p.images[0] ?? "",
                period: periodDot(p),
                rank: stateOf(p, today).rank,
                start: p.start,
              }))}
            />
            {!marked.length && <span className="story-empty">팝업을 북마크하면 여기에 모여요.</span>}
            {marked.map((p) => (
              <Link key={p.id} href={`/popup/${p.id}`} className="story mark" prefetch={false}>
                <span className="ring">
                  {p.area && <span className="rg">{p.area}</span>}
                  <span className="pic" style={posterBg(p.images[0] ?? "")} />
                </span>
                <span className="nm">{p.work}</span>
              </Link>
            ))}
          </HScroll>
        </section>
      ) : (
        <section className="stories" aria-labelledby="story-h">
          <div className="story-head" id="story-h">
            요즘 일정 많은 작품
            <span
              className="help"
              tabIndex={0}
              aria-label="지금 진행 중이거나 곧 열리는 팝업이 많은 작품이에요. 숫자는 그 작품의 팝업 수예요."
            >
              <HelpIcon />
              <span className="tip">
                지금 진행 중이거나 곧 열리는 팝업이 많은 작품이에요. 숫자는 그 작품의 팝업 수예요.
              </span>
            </span>
          </div>
          <HScroll className="story-row" label="요즘 일정 많은 작품">
            {works.map((w) => (
              <Link key={w} href={`/list?work=${encodeURIComponent(w)}`} className="story hot" prefetch={false}>
                <span className="ring">
                  <span className="pic" style={posterBg(posterOf.get(w) ?? "")} />
                  <span className="cnt">{count.get(w)}</span>
                </span>
                <span className="nm">{w}</span>
              </Link>
            ))}
          </HScroll>
        </section>
      )}

      {top.length > 0 && <RankBanner items={top} today={today} />}

      <HomeHead title="따끈따끈 신규 등록 팝업" icon={<NewIcon />} more="/list?sort=new" />
      <NewSection items={fresh} areas={topAreas(liveItems)} today={today} />

      <HomeHead title="이번 주에 끝나는 팝업" icon={<HourglassIcon />} more="/list?sort=end" />
      <WeekCalendar items={weekItems} monday={monday} today={today} />

      <HomeHead title="사전예약 팝업" icon={<EventIcon />} more="/list?reserve=1&sort=open" />
      {reserve.length ? (
        <HScroll className="home-row" label="사전예약 팝업">
          {reserve.map((p) => (
            <HomeCard key={p.id} p={p} today={today} badge={`사전예약 D-${daysBetween(today, p.start)}`} />
          ))}
        </HScroll>
      ) : (
        <div className="home-empty">곧 열리는 팝업 중 사전예약을 받는 곳이 없어요.</div>
      )}
    </div>
  );
}
