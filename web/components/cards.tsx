import Link from "next/link";
import type { CSSProperties } from "react";
import { PLACEHOLDER_POSTER, periodDot, periodLong, periodSlash, regionColor, stateOf, type Item } from "@/lib/popup";
import { StoreIcon } from "./Icons";

// 포스터는 CSS 배경 두 겹으로 그린다 (앱과 같은 방법): 포스터가 깨지거나 없으면 아래 겹의 기본 포스터가 보인다.
// 그래서 서버 컴포넌트에서도 JS 없이 깨진 그림 아이콘이 안 보인다.
function cssUrl(u: string): string {
  return `url("${u.replace(/["\\\n\r]/g, (c) => encodeURIComponent(c))}")`;
}

export function posterBg(url: string, extra?: CSSProperties): CSSProperties {
  const layers = url ? `${cssUrl(url)}, ${cssUrl(PLACEHOLDER_POSTER)}` : cssUrl(PLACEHOLDER_POSTER);
  return { backgroundImage: layers, ...extra };
}

/** 포스터 위 지역 배지: 시 색을 진하게 채우고 흰 테두리·그림자 (앱 _area_badge cls="area") */
export function AreaOnPoster({ area, city, className = "area" }: { area: string; city: string; className?: string }) {
  if (!area) return null;
  const c = regionColor(city);
  return (
    <span className={className} style={{ background: `${c}E6` }}>
      {area}
    </span>
  );
}

/** 흰 바탕 위 지역 배지: 시 색 테두리·글자, 옅은 바탕 (앱 .abadge) */
export function AreaBadge({ area, city }: { area: string; city: string }) {
  if (!area) return null;
  const c = regionColor(city);
  return (
    <span className="abadge" style={{ background: `${c}1A`, borderColor: c, color: c }}>
      {area}
    </span>
  );
}

/** 리스트로 보기 카드 (앱 .pcard): 포스터를 꽉 채우고 아래 그라데이션 위에 작품 · 매장 · 기간 · 칩 */
export function PosterCard({ p, today }: { p: Item; today: string }) {
  const s = stateOf(p, today);
  return (
    <Link href={`/popup/${p.id}`} className="pcard-link" aria-label={`${p.work} ${p.name}`} prefetch={false}>
      <div className="pcard" style={posterBg(p.poster)}>
        <AreaOnPoster area={p.area} city={p.city} />
        <span className={`state ${s.color}`}>{s.label}</span>
        <div className="info">
          <div className="t">{p.work}</div>
          <div className="s">
            <StoreIcon />
            <span>{p.name}</span>
          </div>
          <div className="d">
            <span className="d-long">{periodLong(p)}</span>
            <span className="d-short">{periodSlash(p)}</span>
          </div>
          {p.chip && (
            <div className="chips short">
              <span className={`chip${p.chipTag ? " tag" : ""}`}>{p.chip}</span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

/** 홈 포스터 카드 (앱 .hc): 포스터(순위 숫자 · 배지) · 작품 · 기간 · 지역/상태 칩 */
export function HomeCard({
  p,
  today,
  rank,
  badge,
  tall = false,
}: {
  p: Item;
  today: string;
  rank?: number;
  badge?: string;
  tall?: boolean;
}) {
  const s = stateOf(p, today);
  return (
    <Link href={`/popup/${p.id}`} className={`hc${tall ? " tall" : ""}`} prefetch={false}>
      <div className="hcp" style={posterBg(p.poster)}>
        {badge && <span className={`hcbadge${badge.startsWith("사전예약") ? " res" : ""}`}>{badge}</span>}
        {rank ? <span className="hcrank">{rank}</span> : null}
      </div>
      <div className="hct">{p.work}</div>
      <div className="hcd">{periodDot(p)}</div>
      <div className="hcchips">
        {p.area && <span>{p.area}</span>}
        <span className={`st ${s.color}`}>{s.label}</span>
      </div>
    </Link>
  );
}

/** 상세 아래 '비슷한 팝업' 카드 (앱 .simc) */
export function SimCard({ p, today, title, meta }: { p: Item; today: string; title: string; meta?: string }) {
  const s = stateOf(p, today);
  return (
    <Link href={`/popup/${p.id}`} className="simc" prefetch={false}>
      <div className="simp" style={posterBg(p.poster)}>
        <span className={`sims ${s.color}`}>{s.label}</span>
        <span className="simr">
          <AreaOnPoster area={p.area} city={p.city} />
        </span>
      </div>
      <div className="simt">{title}</div>
      <div className="simm">{periodDot(p)}</div>
      {meta ? <div className="simm">{meta}</div> : null}
    </Link>
  );
}
