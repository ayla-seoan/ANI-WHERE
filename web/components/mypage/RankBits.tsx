import Link from "next/link";
import { nextTier, tierOf, TIERS, type Tier } from "@/lib/stamp";

// 후기 도장 요약 조각 (A-MVisited · A-MyPage): 진행 막대, 5단계 줄, 60px 도장.
// 서버 · 브라우저 어느 쪽에서나 쓴다 (상태 없음). 스타일은 app/a-member.css (.rkb-*).

export const RANK_HREF = "/mypage/rank";

/** 다음 랭크까지 진행 막대 (가장 높은 랭크면 가득) */
export function RankBar({ stamps }: { stamps: number }) {
  const cur = tierOf(stamps);
  const next = nextTier(stamps);
  const max = next ? next.tier.need : Math.max(stamps, 1);
  const pct = next ? Math.min(100, Math.round((stamps / max) * 100)) : 100;
  return (
    <div
      className="rkb-bar"
      role="progressbar"
      aria-label={next ? `Lv.${next.tier.lv}까지 진행도` : "가장 높은 랭크"}
      aria-valuenow={Math.min(stamps, max)}
      aria-valuemin={0}
      aria-valuemax={max}
    >
      <span style={{ width: `${pct}%`, background: (cur ?? TIERS[0]).ring }} />
    </div>
  );
}

/** '다녀온 후기 4개 · Lv.3 성지순례러까지 6개 남았어요' */
export function RankLine({ stamps, short }: { stamps: number; short?: boolean }) {
  const next = nextTier(stamps);
  return (
    <span className="rkb-line">
      다녀온 후기 <strong>{stamps}개</strong>
      {next ? (
        <>
          {" · "}
          <strong style={{ color: next.tier.fg }}>
            Lv.{next.tier.lv}
            {short ? "" : ` ${next.tier.name}`}
          </strong>
          까지 <strong>{next.left}개</strong> 남았어요
        </>
      ) : (
        " · 가장 높은 랭크예요"
      )}
    </span>
  );
}

/** 테두리 + 마스코트 도장 (크기 자유). 아직 못 받은 단계는 점선 + 흐리게 */
export function TierDot({ tier, size, locked, glow }: { tier: Tier; size: number; locked?: boolean; glow?: boolean }) {
  return (
    <span
      className={`rk-stamp rkb-dot${locked ? " locked" : ""}`}
      aria-hidden
      style={{
        width: size,
        height: size,
        borderWidth: size >= 44 ? 3 : 2.5,
        borderStyle: locked ? "dashed" : "solid",
        borderColor: tier.ring,
        background: tier.fill,
        boxShadow: glow ? `0 0 0 4px ${tier.fill}` : undefined,
      }}
    >
      <img src="/mascot.png" alt="" />
    </span>
  );
}

/** 5단계 한 줄: 받은 단계는 색, 지금 단계는 강조, 나머지는 흐리게. cells = 마이페이지 PC 의 칸 모양 */
export function TierRow({ stamps, cells }: { stamps: number; cells?: boolean }) {
  const cur = tierOf(stamps);
  return (
    <ul className={`rkb-row${cells ? " cells" : ""}`} aria-label="후기 도장 5단계">
      {TIERS.map((t) => {
        const got = stamps >= t.need;
        const now = cur?.lv === t.lv;
        return (
          <li key={t.lv} className={`${got ? "got" : "lock"}${now ? " now" : ""}`} style={now && cells ? { background: t.fill } : undefined}>
            <TierDot tier={t} size={cells ? 48 : 36} locked={!got} glow={now && !cells} />
            <span className="rkb-nm" style={got ? { color: t.fg } : undefined}>
              {!cells && <>Lv.{t.lv}<br /></>}
              {t.name}
            </span>
            {cells && <span className="rkb-need">후기 {t.need}개</span>}
            <span className="sr-only">{now ? " (지금 내 랭크)" : got ? " (받음)" : " (아직)"}</span>
          </li>
        );
      })}
    </ul>
  );
}

/** 60px 도장 + 단계 숫자 (다녀온 팝업 탭 위 요약). 도장이 없으면 Lv.1 을 점선으로 */
export function Stamp60({ stamps }: { stamps: number }) {
  const cur = tierOf(stamps);
  const t = cur ?? TIERS[0];
  return (
    <span className="rkb-s60" role="img" aria-label={cur ? `Lv.${cur.lv} ${cur.name} 도장` : "아직 도장이 없어요"}>
      <span
        className={`rk-stamp${cur ? "" : " rkb-dot locked"}`}
        style={{ width: 60, height: 60, borderWidth: 3, borderStyle: cur ? "solid" : "dashed", borderColor: t.ring, background: t.fill }}
      >
        <img src="/mascot.png" alt="" />
      </span>
      {cur && (
        <span className="rkb-lv" style={{ background: cur.ring }}>
          {cur.lv}
        </span>
      )}
    </span>
  );
}

/** 다녀온 팝업 탭 위 요약 카드 (A-MVisited): 지금 랭크 · 도장 수 · 다음 랭크까지 진행 막대 · 5단계 */
export function RankCard({ stamps, note }: { stamps: number; note?: string }) {
  const cur = tierOf(stamps);
  return (
    <section className="rkb-card" aria-label="내 후기 도장">
      <div className="rkb-top">
        <Stamp60 stamps={stamps} />
        <div className="rkb-txt">
          <span className="rkb-cap">내 후기 도장</span>
          <span className="rkb-name" style={cur ? { color: cur.fg } : undefined}>
            {cur ? `Lv.${cur.lv} ${cur.name}` : "아직 도장이 없어요"}
          </span>
          <RankLine stamps={stamps} short />
        </div>
        <Link href={RANK_HREF} className="rkb-guide">
          랭크 안내
        </Link>
      </div>
      <RankBar stamps={stamps} />
      <TierRow stamps={stamps} />
      {note && <p className="rkb-note">{note}</p>}
    </section>
  );
}
