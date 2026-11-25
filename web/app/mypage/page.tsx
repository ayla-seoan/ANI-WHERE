import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getPopupData } from "@/lib/data";
import { todayKST } from "@/lib/popup";
import { tierOf, TIERS } from "@/lib/stamp";
import { avatarUrl } from "@/lib/avatar";
import { RankStamp, RankStampBig } from "@/components/RankStamp";
import { RANK_HREF, RankBar, RankLine, TierRow } from "@/components/mypage/RankBits";
import MyReviews, { type MyReviewItem } from "@/components/mypage/MyReviews";
import Settings from "@/components/mypage/Settings";
import { myReviews } from "@/lib/server/a-member";
import { displayName, PROVIDER_LABEL, suggestNick } from "@/lib/server/auth";
import { RATED_KIND, ruleSettings } from "@/lib/server/member";
import { getMe, getMyFavs } from "@/lib/server/session";
import { myStamps } from "@/lib/server/stamp";

// 마이페이지 (회원만, A-MyPage · A-MMyPage): 프로필 + 랭크 도장, 숫자 3개, 내 후기 도장, 내가 쓴 후기, 설정.
// 예전에 /login 이 회원에게 보여 주던 '내 계정' 기능은 모두 여기 '설정' 으로 옮겼다.
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "마이페이지", robots: { index: false } };

export default async function MyPage() {
  const me = await getMe();
  if (!me) redirect("/login?next=/mypage");
  const today = todayKST();
  const myName = displayName(me.row);
  const [{ popups }, favIds, stamps, rules] = await Promise.all([getPopupData(), getMyFavs(), myStamps(myName), ruleSettings()]);
  let suggest = "졸린 고양이";
  try {
    suggest = await suggestNick();
  } catch {
    /* 회원 목록을 못 읽어도 화면은 그린다 */
  }
  const byId = new Map(popups.map((p) => [p.id, p]));
  // 북마크 수는 내 캘린더와 같게: 아직 끝나지 않은 팝업만
  const fav = new Set(favIds);
  const nFav = popups.filter((p) => fav.has(p.id) && (!p.end || p.end >= today)).length;
  let reviews: MyReviewItem[] = [];
  try {
    const stamped = new Set<string>(); // 팝업마다 가장 최근 다녀온 후기 하나에만 도장
    reviews = (await myReviews(myName))
      .filter((r) => byId.has(r.cafeId)) // 내린 팝업의 후기는 갈 곳이 없어 뺀다
      .map((r) => {
        const p = byId.get(r.cafeId)!;
        const stamp = r.kind === RATED_KIND && !stamped.has(r.cafeId);
        if (stamp) stamped.add(r.cafeId);
        return {
          id: r.id,
          cafeId: r.cafeId,
          title: p.work ? `${p.work} · ${p.name}` : p.name,
          poster: p.images[0] || "",
          kind: r.kind || "리뷰",
          rating: r.rating,
          body: r.body,
          date: r.when ? `${Number(r.when.slice(5, 7))}.${Number(r.when.slice(8, 10))}` : "",
          photos: r.photos,
          stamp,
        };
      });
  } catch {
    /* 리뷰를 못 읽어도 프로필 · 설정은 보여 준다 */
  }

  const cur = tierOf(stamps);
  const nick = String(me.row.nickname || "");
  const avatar = String(me.row.avatar || "");
  const provider = String(me.row.provider || "");
  const label = PROVIDER_LABEL[provider] || "";
  const agreed = String(me.row.agreed_at || "").slice(0, 10).replaceAll("-", ".");
  const od = rules.open.enabled ? rules.open.days : null;
  const ed = rules.end.enabled ? rules.end.days : null;
  const notice =
    od === null && ed === null
      ? "지금은 운영자가 오픈 · 종료 알림을 꺼 두었어요"
      : `북마크한 팝업, ${[od !== null ? `오픈 ${od}일 전` : "", ed !== null ? `종료 ${ed}일 전` : ""].filter(Boolean).join(" · ")}부터 종과 내 캘린더로`;

  return (
    <div className="mp">
      <h1 className="mp-h">마이페이지</h1>

      <div className="mp-top">
        <section className="mp-prof" aria-label="내 프로필">
          <span className="mp-av">
            {/* 사진이 깨지면 기본 그림이 보이게 배경으로 한 겹 더 깐다 (서버 컴포넌트라 onError 를 못 쓴다) */}
            <span className="mp-av-img" style={{ backgroundImage: `url("${avatarUrl("")}")` }}>
              <img className="me-avimg" src={avatarUrl(avatar)} alt="" width={104} height={104} referrerPolicy="no-referrer" />
            </span>
            {cur && (
              <span className="mp-av-stamp">
                <RankStamp lv={cur.lv} size={40} />
              </span>
            )}
          </span>
          <div className="mp-who">
            <span className="mp-nickname">{nick}</span>
            <span className="mp-lv" style={cur ? { color: cur.fg, background: cur.fill } : undefined}>
              {cur ? `Lv.${cur.lv} ${cur.name}` : "아직 도장이 없어요"}
            </span>
            <span className="mp-meta">
              {label ? `${label}로 로그인` : "로그인 중"}
              {agreed ? ` · ${agreed} 가입` : ""}
            </span>
            <span className="mp-meta small">
              회원 번호 <code>{me.key}</code>
              {me.admin ? " · 관리자" : ""}
            </span>
          </div>
          <a href="#mp-set" className="mp-edit">
            <span className="pc-only">프로필 수정</span>
            <span className="m-only">수정</span>
          </a>
          <div className="mp-nums">
            <Link href="/calendar?tab=fav#keep">
              <strong>{nFav}</strong>
              <span>북마크</span>
            </Link>
            <Link href="/calendar?tab=visited#keep">
              <strong>{stamps}</strong>
              <span>후기 도장</span>
            </Link>
            <a href="#my-reviews">
              <strong>{reviews.length}</strong>
              <span>쓴 후기</span>
            </a>
          </div>
        </section>

        <section className="mp-rank" aria-labelledby="mp-rank-h">
          <div className="mp-rank-top">
            <RankStampBig tier={cur ?? TIERS[0]} size={96} dim={!cur} />
            <div className="mp-rank-txt">
              <h2 id="mp-rank-h">내 후기 도장</h2>
              <span className="mp-rank-name" style={cur ? { color: cur.fg } : undefined}>
                {cur ? `Lv.${cur.lv} ${cur.name}` : "첫 도장을 받아 보세요"}
              </span>
              <RankLine stamps={stamps} />
              <RankBar stamps={stamps} />
            </div>
            <Link href={RANK_HREF} className="mp-rank-link">
              랭크 안내 보기
            </Link>
          </div>
          <TierRow stamps={stamps} cells />
        </section>
      </div>

      <div className="mp-bottom">
        <section className="mp-rvs" id="my-reviews" aria-labelledby="mp-rv-h">
          <h2 id="mp-rv-h">
            내가 쓴 후기 <em>{reviews.length}</em>
          </h2>
          <MyReviews items={reviews} lv={cur?.lv ?? 0} />
        </section>

        <Settings a={{ nick, hasPhoto: !!avatar && avatar !== "none", provider, providerLabel: label }} suggest={suggest} notice={notice} />
      </div>
    </div>
  );
}
