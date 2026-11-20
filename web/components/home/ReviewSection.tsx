import Link from "next/link";
import HScroll from "@/components/HScroll";
import { posterBg } from "@/components/cards";
import { avatarUrl, uploadUrl } from "@/lib/avatar";
import { stateOf, type Item } from "@/lib/popup";
import type { HomeReview } from "@/lib/server/member";

// 홈 맨 아래 '꿀팁 가득! 실시간 후기 모음' (앱 _home_reviews, 11/18 요청 · 웹은 11/20 추가).
// 카드: 팝업(포스터 · 작품 · 상태 · 지역) + 리뷰(프로필 사진 · 닉네임 · 별점 · 날짜 · 종류 · 본문 · 사진 2장). 누르면 그 팝업 상세.
const KIND_CLASS: Record<string, string> = { "다녀온 후기": "visit", 기대평: "hope", 기타: "etc" };

function whenText(stamp: string): string {
  const t = Date.parse(stamp);
  if (!t) return "";
  const k = new Date(t + 9 * 3600_000); // 한국 시간
  const two = (n: number) => String(n).padStart(2, "0");
  return `${two(k.getUTCMonth() + 1)}/${two(k.getUTCDate())} ${two(k.getUTCHours())}:${two(k.getUTCMinutes())}`;
}

export default function ReviewSection({
  reviews,
  popups,
  today,
}: {
  reviews: HomeReview[];
  popups: Map<string, Item>;
  today: string;
}) {
  const list = reviews.filter((r) => popups.has(r.cafeId));
  if (!list.length) {
    return <div className="home-empty">아직 후기가 없어요. 다녀온 팝업에 첫 후기를 남겨 보세요.</div>;
  }
  return (
    <HScroll className="home-row rv-row" label="실시간 후기 모음">
      {list.map((rv) => {
        const p = popups.get(rv.cafeId)!;
        const s = stateOf(p, today);
        const n = rv.rating ? Math.max(0, Math.min(5, Math.round(rv.rating))) : 0;
        return (
          <Link key={rv.id} href={`/popup/${p.id}`} className="rvc" prefetch={false}>
            <div className="rvtop">
              <div className="rvth" style={posterBg(p.poster)} />
              <div className="rvtt">
                <div className="rvw">{p.work}</div>
                <div className="rvchips">
                  <span className={`st ${s.color}`}>{s.label}</span>
                  {p.area && <span>{p.area}</span>}
                </div>
              </div>
            </div>
            <div className="rvbox">
              <div className="rvme">
                <img
                  className="rv-av"
                  src={avatarUrl(rv.avatar)}
                  alt=""
                  width={34}
                  height={34}
                  referrerPolicy="no-referrer"
                  loading="lazy"
                />
                <div className="rvwho">
                  <b>{rv.name}</b>
                  {n > 0 && (
                    <div className="rvs" aria-label={`5점 만점에 ${n}점`}>
                      {"★".repeat(n)}
                      <span className="off">{"★".repeat(5 - n)}</span>
                      <b>{n.toFixed(1)}</b>
                      <span className="of"> / 5.0</span>
                    </div>
                  )}
                </div>
                <span className="rvdate">{whenText(rv.when)}</span>
              </div>
              {rv.kind && <span className={`rvkind ${KIND_CLASS[rv.kind] ?? "etc"}`}>{rv.kind}</span>}
              <div className="rvbody">{rv.body}</div>
              {rv.images.length > 0 && (
                <div className="rvpics">
                  {rv.images.slice(0, 2).map((x) => (
                    <div key={x} className="rvp" style={{ backgroundImage: `url("${uploadUrl(x)}")` }} />
                  ))}
                </div>
              )}
            </div>
          </Link>
        );
      })}
    </HScroll>
  );
}
