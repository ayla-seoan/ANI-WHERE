import type { Metadata } from "next";
import Link from "next/link";
import { nextTier, STAMP_RULES, tierOf, TIERS } from "@/lib/stamp";
import { RankStampBig } from "@/components/RankStamp";
import { displayName } from "@/lib/server/auth";
import { getMe } from "@/lib/server/session";
import { myStamps } from "@/lib/server/stamp";

// 후기 도장 랭크 안내 (A-Rank). 누구나 볼 수 있고, 회원이면 내 지금 랭크를 강조한다.
// 시안 카드의 '혜택' 글은 아직 없는 기능이라 쓰지 않는다 — lib/stamp.ts 의 perk(도장 색이 바뀐다는 사실)만 보여 준다.
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "후기 도장 랭크", robots: { index: false } };

export default async function RankPage() {
  const me = await getMe();
  const stamps = me ? await myStamps(displayName(me.row)) : 0;
  const cur = me ? tierOf(stamps) : null;
  const next = me ? nextTier(stamps) : null;
  return (
    <div className="rkp">
      <div className="rkp-head">
        <div>
          <h1>후기 도장 랭크</h1>
          <p>다녀온 후기를 남기면 도장이 하나씩 쌓이고, 쌓인 도장 수만큼 랭크가 올라가요.</p>
        </div>
        <span className="rkp-chip">다녀온 후기 1개 = 도장 1개</span>
      </div>

      {me ? (
        <p className="rkp-me">
          지금 내 도장 <strong>{stamps}개</strong>
          {cur ? (
            <>
              {" · "}
              <strong style={{ color: cur.fg }}>
                Lv.{cur.lv} {cur.name}
              </strong>
            </>
          ) : (
            " · 아직 랭크가 없어요"
          )}
          {next ? ` · Lv.${next.tier.lv} ${next.tier.name}까지 ${next.left}개 남았어요` : " · 가장 높은 랭크예요"}
          <Link href="/mypage">마이페이지로</Link>
        </p>
      ) : (
        <p className="rkp-me">
          로그인하고 다녀온 후기를 쓰면 내 도장이 쌓여요.
          <Link href="/login?next=/mypage/rank">로그인</Link>
        </p>
      )}

      <ol className="rkp-grid">
        {TIERS.map((t) => {
          const now = cur?.lv === t.lv;
          return (
            <li key={t.lv} className={now ? "now" : undefined} style={now ? { borderColor: t.ring } : undefined} aria-current={now ? "true" : undefined}>
              {now && (
                <span className="rkp-now" style={{ background: t.ring }}>
                  지금 내 랭크
                </span>
              )}
              <RankStampBig tier={t} size={116} />
              <div className="rkp-txt">
                <span className="rkp-name" style={{ color: t.fg }}>
                  {t.name}
                </span>
                <span className="rkp-need" style={{ background: t.fill, color: t.fg }}>
                  다녀온 후기 {t.need}개
                </span>
                <span className="rkp-perk">{t.perk}</span>
              </div>
            </li>
          );
        })}
      </ol>

      <section className="rkp-rules" aria-labelledby="rkp-rules-h">
        <h2 id="rkp-rules-h">세는 규칙</h2>
        <ul>
          {STAMP_RULES.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
