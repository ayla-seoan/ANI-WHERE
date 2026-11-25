import Link from "next/link";
import { periodDot, regionColor, stateOf, type Item } from "@/lib/popup";
import { posterBg } from "../cards";
import BookmarkButton from "../member/BookmarkButton";

// 리스트로 보기 · 이번 주 팝업의 포스터 카드 (A-List / A-MList 시안).
// 포스터(3:4, 민트 테두리 2.5px · 모서리 12px) 위에 상태 · 지역 · 칩 · 북마크, 아래에 작품(Jua) · 매장 · 기간.
// PC 에서 마우스를 올리면 캐릭터 · 주소 · 특전이 포스터 아래쪽에 겹쳐 보인다 (터치 기기에는 hover 가 없어 겹침 판을 띄우지 않는다).
// 예전 카드(cards.tsx PosterCard)와 같은 바깥 클래스(pcard-wrap · t · bm)를 남겨 시험 스크립트가 그대로 돈다.

/** '~ 12.15' (열린 뒤) · '11.28 ~' (열리기 전) — 모바일 카드의 짧은 기간 */
export function periodShort(p: Pick<Item, "start" | "end">, today: string): string {
  if (!p.start) return "기간 확인 필요";
  const f = (s: string) => `${s.slice(5, 7)}.${s.slice(8, 10)}`;
  if (p.start > today) return `${f(p.start)} ~`;
  return p.end ? `~ ${f(p.end)}` : "상시";
}

const one = (s: string) => s.replace(/\s+/g, " ").trim();

export default function BrowseCard({ p, today }: { p: Item; today: string }) {
  const s = stateOf(p, today);
  const over = [
    ["캐릭터", one(p.characters)],
    ["주소", one(p.address)],
    ["특전", one(p.perks)],
  ].filter(([, v]) => v);
  return (
    <div className="pcard-wrap bc" data-card={p.id}>
      <div className="bc-pwrap">
        <Link href={`/popup/${p.id}`} className="bc-poster" style={posterBg(p.poster)} aria-label={`${p.work} ${p.name}`} prefetch={false}>
          <span className={`bc-state ${s.color}`}>{s.label}</span>
          {p.area && (
            <span className="bc-area" style={{ background: regionColor(p.city) }}>
              {p.area}
            </span>
          )}
          {over.length > 0 && (
            <span className="bc-over" aria-hidden>
              {over.map(([k, v]) => (
                <span key={k}>
                  {k} · {v}
                </span>
              ))}
            </span>
          )}
          {p.chip && <span className={`bc-chip${p.chipTag ? " tag" : ""}`}>{p.chip}</span>}
        </Link>
        <BookmarkButton cafeId={p.id} />
      </div>
      <Link href={`/popup/${p.id}`} className="bc-text" tabIndex={-1} prefetch={false}>
        <span className="t bc-title">{p.work}</span>
        <span className="bc-sub">
          <span className="bc-name">{p.name}</span>
          <span className="bc-date pc-only"> · {periodDot(p)}</span>
          <span className="bc-date m-only"> · {periodShort(p, today)}</span>
        </span>
      </Link>
    </div>
  );
}
