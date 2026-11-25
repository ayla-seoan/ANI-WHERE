import { avatarUrl, uploadUrl } from "@/lib/avatar";
import { stateOf, type Item } from "@/lib/popup";
import type { HomeReview } from "@/lib/server/member";
import ReviewWall, { type WallCard } from "./ReviewWall";

// 홈 맨 아래 '꿀팁 가득! 실시간 후기 모음' (앱 _home_reviews, 11/18 요청 · 웹은 11/20 추가 · 11/25 A안 모양).
// 서버에서 리뷰와 팝업을 묶어 카드 재료만 넘긴다 (팝업 전체 목록을 브라우저로 보내지 않게). 그리는 것은 ReviewWall.
export default function ReviewSection({
  reviews,
  popups,
  kinds,
  today,
}: {
  reviews: HomeReview[];
  popups: Map<string, Item>;
  /** 리뷰 종류 (lib/server/member.ts KINDS) — 제목 오른쪽 칩 */
  kinds: readonly string[];
  today: string;
}) {
  const cards: WallCard[] = reviews
    .filter((r) => popups.has(r.cafeId))
    .map((rv) => {
      const p = popups.get(rv.cafeId)!;
      const s = stateOf(p, today);
      return {
        id: rv.id,
        kind: rv.kind,
        name: rv.name,
        avatar: avatarUrl(rv.avatar),
        lv: rv.lv,
        when: rv.when,
        stars: rv.rating ? Math.max(0, Math.min(5, Math.round(rv.rating))) : 0,
        body: rv.body,
        photo: rv.images[0] ? uploadUrl(rv.images[0]) : "",
        more: Math.max(0, rv.images.length - 1),
        popupId: p.id,
        popup: p.work || p.name,
        poster: p.poster,
        state: s.label,
        stateColor: s.color,
      };
    });
  return <ReviewWall cards={cards} kinds={[...kinds]} />;
}
