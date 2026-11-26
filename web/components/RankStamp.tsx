import { tierByLv, type Tier } from "@/lib/stamp";

// 후기 도장 (A-Rank 시안). 어디서나 같은 도장, 크기만 다르게:
//   96px 마이페이지 대표 (둘레 글자 + 단계 숫자) · 40px 다녀온 팝업 카드 · 32px 리뷰 작성칸 · 20px 리뷰 닉네임 옆
//   40px 이하는 색 테두리 + 마스코트만. 스타일은 app/a-shell.css (.rk-*).

const BORDER: Record<number, number> = { 20: 2, 32: 2.5, 40: 3 };

/** 작은 도장 (40px 이하): 테두리 + 마스코트 */
export function RankStamp({ lv, size = 20 }: { lv: number; size?: 20 | 32 | 40 }) {
  const t = tierByLv(lv);
  if (!t) return null;
  return (
    <span
      className="rk-stamp"
      role="img"
      aria-label={`Lv.${t.lv} ${t.name} 도장`}
      style={{ width: size, height: size, borderWidth: BORDER[size], borderColor: t.ring, background: size === 20 ? "#fff" : t.fill }}
    >
      <img src="/mascot.png" alt="" />
    </span>
  );
}

/** 리뷰 닉네임 옆: 20px 도장 + 'Lv.2' 알약 */
export function RankChip({ lv }: { lv: number }) {
  const t = tierByLv(lv);
  if (!t) return null;
  return (
    <span className="rk-chip" style={{ background: t.fill }} aria-label={`Lv.${t.lv} ${t.name}`}>
      <RankStamp lv={lv} size={20} />
      <span style={{ color: t.fg }}>Lv.{t.lv}</span>
    </span>
  );
}

/** 큰 도장 (마이페이지 96px · 랭크 안내 116px): 둘레 글자 + 단계 숫자 */
export function RankStampBig({ tier, size = 96, dim, idPrefix = "" }: { tier: Tier; size?: number; dim?: boolean; idPrefix?: string }) {
  // 같은 화면에 같은 도장이 두 번 나와도(화면 + 팝업) SVG id 가 겹치지 않게
  const id = `rk-ring-${idPrefix}${tier.lv}-${size}`;
  return (
    <span className={`rk-big${dim ? " dim" : ""}`} style={{ width: size, height: size }} role="img" aria-label={`Lv.${tier.lv} ${tier.name} 도장`}>
      <svg width={size} height={size} viewBox="0 0 80 80" aria-hidden>
        <defs>
          <path id={id} d="M40 40 m-29.5 0 a29.5 29.5 0 1 1 59 0 a29.5 29.5 0 1 1 -59 0" />
        </defs>
        <circle cx="40" cy="40" r="38" fill={tier.fill} />
        <circle cx="40" cy="40" r="38" fill="none" stroke={tier.ring} strokeWidth="3.5" />
        <circle cx="40" cy="40" r="22.5" fill="#ffffff" stroke={tier.ring} strokeWidth="1.2" />
        <text className="rk-ring-t" fontSize="7.2" fill={tier.fg} textLength="172" lengthAdjust="spacingAndGlyphs">
          <textPath href={`#${id}`} textLength="172" lengthAdjust="spacingAndGlyphs">
            ANI:WHERE ✦ LV.{tier.lv} {tier.en} ✦
          </textPath>
        </text>
      </svg>
      <img src="/mascot.png" alt="" />
      <span className="rk-lv" style={{ background: tier.ring }}>
        {tier.lv}
      </span>
    </span>
  );
}
