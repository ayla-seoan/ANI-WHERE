import Link from "next/link";
import { getPopupData } from "@/lib/data";
import {
  addDays,
  byCode,
  periodDot,
  stateOf,
  todayKST,
  toItem,
  type Item,
} from "@/lib/popup";
import BookmarkPicker from "@/components/member/BookmarkPicker";
import { areaFill, posterBg } from "@/components/cards";
import HScroll from "@/components/HScroll";
import RankBanner from "@/components/home/RankBanner";
import NewSection from "@/components/home/NewSection";
import WeekCalendar from "@/components/home/WeekCalendar";
import ReviewSection from "@/components/home/ReviewSection";
import ReserveSection from "@/components/home/ReserveSection";
import SecHead from "@/components/home/SecHead";
import { ClockLine } from "@/components/home/Icons2";
import EmptyState from "@/components/EmptyState";
import { getMe, getMyFavs } from "@/lib/server/session";
import { rankScores } from "@/lib/server/rank";
import { homeReviews, KINDS } from "@/lib/server/member";
import { rankOrder, TOP_N } from "@/lib/rank";
import { HelpIcon } from "@/components/Icons";

export const revalidate = 600;

const STORY_MAX = 12;
const REVIEW_MAX = 30; // 후기 모음: 처음 6개, '후기 더보기'로 6개씩 여기까지

/** 팝업이 많은 지역 n 곳 (앱 _home_areas) */
function topAreas(rows: Item[], n = 3): string[] {
  const cnt = new Map<string, number>();
  for (const r of rows) if (r.area) cnt.set(r.area, (cnt.get(r.area) ?? 0) + 1);
  return [...cnt.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([a]) => a);
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

  // 특전 있는 작품들 (11/20 요청, 예전 이름 '요즘 일정 많은 작품'): 진행 중·예정 팝업 중 특전이 적힌 팝업이 많은 작품 순.
  // 숫자 = 그 작품의 특전 있는 팝업 수. 대표 포스터는 진행 중인 것 먼저 (앱 _guest_stories)
  const perkLive = live.filter((p) => p.perks.length > 0);
  const count = new Map<string, number>();
  for (const p of perkLive) if (p.work.trim()) count.set(p.work.trim(), (count.get(p.work.trim()) ?? 0) + 1);
  const works = [...count.keys()].sort((a, b) => count.get(b)! - count.get(a)! || byCode(a, b)).slice(0, STORY_MAX);
  const posterOf = new Map<string, string>();
  // 포스터는 그 작품의 진행 중·예정 팝업 아무거나 (특전 팝업에 포스터가 없을 수 있음)
  for (const p of [...live].sort((a, b) => stateOf(a, today).rank - stateOf(b, today).rank)) {
    const w = p.work.trim();
    if (w && !posterOf.has(w) && p.images[0]) posterOf.set(w, p.images[0]);
  }

  const me = await getMe();
  const favs = new Set(await getMyFavs());
  const marked = live
    .filter((p) => favs.has(p.id))
    .sort((a, b) => stateOf(a, today).rank - stateOf(b, today).rank || a.end.localeCompare(b.end));
  // 실시간 인기 급상승 랭킹 (5위까지): 규칙은 lib/rank.ts — 앱 common/rank.py 와 같은 시험(samples/rank_cases.json)을 통과 (11/20)
  const [scores, reviews] = await Promise.all([rankScores(), homeReviews(new Set(popups.map((p) => p.id)), REVIEW_MAX)]);
  const top = rankOrder(live, scores).slice(0, TOP_N).map(toItem);
  const fresh = [...liveItems].sort((a, b) => b.created.localeCompare(a.created));
  // 곧 끝나는 팝업: 어제부터 7일 (11/20 요청 — 금요일이면 목 ~ 다음 주 수, 앱 _home_week)
  const first = addDays(today, -1);
  const weekItems = popups.filter((p) => p.end && p.end >= first && p.end <= addDays(first, 6)).map(toItem);
  // 사전예약 팝업: 아직 열기 전(오픈 예정)인 것만, 빨리 여는 순
  const reserve = liveItems
    .filter((p) => p.reserve && stateOf(p, today).rank === 1)
    .sort((a, b) => a.start.localeCompare(b.start));

  return (
    <div className="home ah">
      <h1 className="sr-only">ANI:WHERE 홈 — 애니 팝업·콜라보 카페</h1>

      {me ? (
        // 회원: '북마크 팝업' — 사용자 요청(11/25)으로 A안 이전 모양 그대로 (a-home.css 의 동그라미 규칙은 손님 줄에만).
        // 회원: '북마크 팝업' — 내가 북마크한 (진행 중 · 예정) 팝업 하나에 동그라미 하나, 위에 지역, 아래 작품 (앱 render_stories)
        <section className="stories stories-old" aria-labelledby="story-h">
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
                  {p.area && (
                    <span className="rg" style={areaFill(p.city)}>
                      {p.area}
                    </span>
                  )}
                  <span className="pic" style={posterBg(p.images[0] ?? "")} />
                </span>
                <span className="nm">{p.work}</span>
              </Link>
            ))}
          </HScroll>
        </section>
      ) : (
        // 손님: '특전 있는 작품들' — 사용자 요청(11/26)으로 A안 이전 모양 그대로 (북마크 줄과 같은 동그라미, 오른쪽 아래 숫자)
        <section className="stories stories-old" aria-labelledby="story-h">
          <div className="story-head" id="story-h">
            특전 있는 작품들
            <span
              className="help"
              tabIndex={0}
              aria-label="지금 진행 중이거나 곧 열리는 팝업 중 특전을 주는 팝업이 많은 작품이에요. 숫자는 특전 있는 팝업 수예요."
            >
              <HelpIcon />
              <span className="tip">
                지금 진행 중이거나 곧 열리는 팝업 중 특전을 주는 팝업이 많은 작품이에요. 숫자는 특전 있는 팝업 수예요.
              </span>
            </span>
          </div>
          <HScroll className="story-row" label="특전 있는 작품들">
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

      {/* 실시간 인기 급상승 랭킹: 사용자 요청으로 예전 모양 · 동작 그대로 (RankBanner 와 그 CSS 는 고치지 않는다) */}
      {top.length > 0 && <RankBanner items={top} today={today} />}

      <NewSection items={fresh} areas={topAreas(liveItems)} today={today} />

      <section className="ah-sec ah-end" aria-labelledby="ah-end-h">
        <SecHead id="ah-end-h" title="곧 끝나는 팝업" icon={<ClockLine />}>
          <Link href="/list?sort=end" className="ah-more" prefetch={false}>
            더보기
          </Link>
        </SecHead>
        <WeekCalendar items={weekItems} first={first} today={today} />
      </section>

      <ReserveSection items={reserve} today={today} />

      {/* 꿀팁 가득! 실시간 후기 모음 (앱 _home_reviews, 11/20 웹에 추가) */}
      <ReviewSection reviews={reviews} popups={new Map(popups.map((p) => [p.id, toItem(p)]))} kinds={KINDS} today={today} />
    </div>
  );
}
