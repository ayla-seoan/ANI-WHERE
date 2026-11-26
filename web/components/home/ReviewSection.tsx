import { avatarUrl, uploadUrl } from "@/lib/avatar";
import type { Item } from "@/lib/popup";
import type { HomeReview } from "@/lib/server/member";
import { periodShort } from "../browse/BrowseCard";
import ReviewFeed, { type FeedCard, type FeedPop } from "./ReviewFeed";

// 홈 맨 아래 '꿀팁 가득! 실시간 후기' (앱 _home_reviews, 11/18 요청 · 11/26 사용자 시안으로 다시 배치).
// 서버에서 리뷰와 팝업을 묶어 카드 재료만 넘긴다 (팝업 전체 목록을 브라우저로 보내지 않게). 그리는 것은 ReviewFeed.
const POPS = 3;
const kstDay = (stamp: string) => {
  const t = Date.parse(stamp);
  return t ? new Date(t + 9 * 3600_000).toISOString().slice(0, 10) : "";
};

export default function ReviewSection({
  reviews,
  popups,
  kinds,
  today,
  member,
}: {
  reviews: HomeReview[];
  popups: Map<string, Item>;
  /** 리뷰 종류 (lib/server/member.ts KINDS) — 종류 칩 */
  kinds: readonly string[];
  today: string;
  member: boolean;
}) {
  const cards: FeedCard[] = reviews
    .filter((r) => popups.has(r.cafeId))
    .map((rv) => {
      const p = popups.get(rv.cafeId)!;
      return {
        id: rv.id,
        kind: rv.kind,
        name: rv.name,
        avatar: avatarUrl(rv.avatar),
        lv: rv.lv,
        when: rv.when,
        stars: rv.rating ? Math.max(0, Math.min(5, Math.round(rv.rating))) : 0,
        body: rv.body,
        photos: rv.images.map(uploadUrl),
        popupId: p.id,
        popup: p.work || p.name,
        poster: p.poster,
        place: [p.area, periodShort(p, today)].filter(Boolean).join(" · "),
      };
    });

  // 모바일 팝업 칩: 오늘 후기가 많은 작품 3개 (같은 작품의 여러 지점은 한 칩으로 — 누르면 그중 가장 최근 후기의 팝업).
  // 오늘 후기가 없으면 받아 둔 최근 후기로 센다
  const count = (list: FeedCard[]) => {
    const m = new Map<string, { c: FeedCard; n: number }>();
    for (const c of [...list].sort((x, y) => x.when.localeCompare(y.when))) m.set(c.popup, { c, n: (m.get(c.popup)?.n ?? 0) + 1 });
    return [...m.values()].sort((a, b) => b.n - a.n || b.c.when.localeCompare(a.c.when));
  };
  const todays = count(cards.filter((c) => kstDay(c.when) === today));
  const ranked = todays.length ? todays : count(cards);
  const label = todays.length ? "오늘 후기" : "최근 후기";
  const pops: FeedPop[] = ranked.slice(0, POPS).map(({ c, n }) => ({ id: c.popupId, name: c.popup, poster: c.poster, n, label }));

  // 후기 쓰기: 회원은 북마크한 팝업 목록(내 캘린더)에서 골라 리뷰 탭으로, 손님은 로그인부터
  const writeHref = member ? "/calendar?tab=fav#keep" : "/login?next=%2Fcalendar%3Ftab%3Dfav";
  return <ReviewFeed cards={cards} kinds={[...kinds]} pops={pops} writeHref={writeHref} />;
}
