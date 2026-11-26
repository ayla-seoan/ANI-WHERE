import Link from "next/link";
import { nextTier, STAMP_RULES, tierOf, TIERS } from "@/lib/stamp";
import { RankStampBig } from "@/components/RankStamp";

// 후기 도장 랭크 안내 내용 (A-Rank). /mypage/rank 화면과 '랭크 안내 보기' 팝업(RankGuideLink)이 같이 쓴다.
// stamps = 내 도장 수, 손님이면 null. 시안 카드의 '혜택' 글은 아직 없는 기능이라 쓰지 않는다 (lib/stamp.ts 의 perk 만).
export default function RankGuide({ stamps, inDialog }: { stamps: number | null; inDialog?: boolean }) {
  const member = stamps !== null;
  const n = stamps ?? 0;
  const cur = member ? tierOf(n) : null;
  const next = member ? nextTier(n) : null;
  const H = inDialog ? "h2" : "h1";
  return (
    <div className={`rkp${inDialog ? " in-dlg" : ""}`}>
      <div className="rkp-head">
        <div>
          <H id="rkp-title">후기 도장 랭크</H>
          <p>다녀온 후기를 남기면 도장이 하나씩 쌓이고, 쌓인 도장 수만큼 랭크가 올라가요.</p>
        </div>
        <span className="rkp-chip">다녀온 후기 1개 = 도장 1개</span>
      </div>

      {member ? (
        <p className="rkp-me">
          지금 내 도장 <strong>{n}개</strong>
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
          {!inDialog && <Link href="/mypage">마이페이지로</Link>}
        </p>
      ) : (
        <p className="rkp-me">
          로그인하고 다녀온 후기를 쓰면 내 도장이 쌓여요.
          <Link href="/login?next=/mypage">로그인</Link>
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
              <RankStampBig tier={t} size={inDialog ? 104 : 116} idPrefix={inDialog ? "dlg" : "pg"} />
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

      <section className="rkp-rules" aria-labelledby={inDialog ? "rkp-rules-d" : "rkp-rules-h"}>
        {inDialog ? <h3 id="rkp-rules-d">세는 규칙</h3> : <h2 id="rkp-rules-h">세는 규칙</h2>}
        <ul>
          {STAMP_RULES.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
