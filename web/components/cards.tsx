import Link from "next/link";
import type { CSSProperties } from "react";
import { PLACEHOLDER_POSTER, periodDot, periodLong, periodSlash, regionColor, stateOf, type Item } from "@/lib/popup";
import { StoreIcon } from "./Icons";
import BookmarkButton from "./member/BookmarkButton";

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

/** 지역 칩 (홈 · 내 캘린더 · 물어보기, 11/20 요청 '지역마다 색'): 시 색을 옅게(20%) 깐 바탕 + 시 색 글자 (앱 _area_chip 과 같게) */
export function areaFill(city: string): CSSProperties {
  const c = regionColor(city);
  // 흰 바탕 위에 옅은 시 색을 겹친다 — 포스터 · 어두운 배너 위에서도 비치지 않고 읽힌다
  return { background: `linear-gradient(${c}33, ${c}33), #fff`, color: c, borderColor: `${c}33`, fontWeight: 700 };
}

/** 지역 고르기 알약: 평소엔 시 색 테두리 · 글자, 고르면 진한 시 색 바탕 + 흰 글자 (11/20 요청) */
export function areaPill(city: string, on: boolean, color?: string): CSSProperties {
  const c = color || regionColor(city); // '전체' 는 포인트 색 (--accent #14b8a6)
  return on ? { background: c, color: "#fff", borderColor: c } : { borderColor: c, color: c };
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
    <div className="pcard-wrap">
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
      <BookmarkButton cafeId={p.id} />
    </div>
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
    <div className={`hc-wrap${tall ? " tall" : ""}`}>
      <Link href={`/popup/${p.id}`} className={`hc${tall ? " tall" : ""}`} prefetch={false}>
        <div className="hcp" style={posterBg(p.poster)}>
          {badge && <span className={`hcbadge${badge.startsWith("사전예약") ? " res" : badge === "오늘 종료" ? " today" : ""}`}>{badge}</span>}
          {rank ? <span className="hcrank">{rank}</span> : null}
        </div>
        <div className="hct">{p.work}</div>
        <div className="hcd">{periodDot(p)}</div>
        <div className="hcchips">
          {p.area && <span style={areaFill(p.city)}>{p.area}</span>}
          <span className={`st ${s.color}`}>{s.label}</span>
        </div>
      </Link>
      <BookmarkButton cafeId={p.id} variant="row" />
    </div>
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
