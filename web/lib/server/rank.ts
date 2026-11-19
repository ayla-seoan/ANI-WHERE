import "server-only";
import { current, mode, rows, type Row } from "./store";

// 홈 '실시간 인기 급상승 랭킹' 점수 (앱 _home_rank 와 같은 규칙, 11/19 요청: 두 사이트 기준을 맞춤).
//   ① 최근 7일 점수 = 북마크 수 × 2 + 리뷰 · 답글 수
//   ② 같으면 전체 기간의 같은 점수
//   ③ 같으면 오픈이 빠른 순 (점수 0인 팝업도 이 순서로 채움)
// 북마크 · 리뷰 표에서 팝업별 '개수'만 센다 (누가 했는지는 쓰지 않는다).
export const RANK_DAYS = 7;

export type Score = { week: number; all: number };

function countBy(list: Row[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const r of list) {
    const k = String(r.cafe_id || "");
    if (k) m.set(k, (m.get(k) ?? 0) + 1);
  }
  return m;
}

/** 화면에 보이는 리뷰만 (원글이 지워져 함께 숨겨진 답글은 빼고, 앱 review.counts) */
function visibleReviews(all: Row[]): Row[] {
  const byId = new Map(all.map((r) => [String(r.entry_id), r]));
  const alive = (r: Row): boolean => {
    const seen = new Set<string>();
    let cur: Row | undefined = r;
    while (cur && String(cur.parent_id || "")) {
      if (seen.has(String(cur.entry_id))) return false;
      seen.add(String(cur.entry_id));
      cur = byId.get(String(cur.parent_id));
    }
    return Boolean(cur);
  };
  return all.filter(alive);
}

/** 팝업 id → { week: 최근 7일 점수, all: 전체 기간 점수 }. 저장소가 없거나 못 읽으면 빈 표 (오픈 순으로만 줄 세움) */
export async function rankScores(): Promise<Map<string, Score>> {
  const out = new Map<string, Score>();
  if (mode() === "none") return out;
  let favs: Row[] = [];
  let revs: Row[] = [];
  try {
    [favs, revs] = await Promise.all([rows("favorites"), rows("reviews")]);
  } catch {
    return out;
  }
  const f = current(favs);
  const r = visibleReviews(current(revs));
  const since = Date.now() - RANK_DAYS * 86_400_000;
  const recent = (list: Row[]) =>
    list.filter((x) => {
      const t = Date.parse(String(x.updated_at || ""));
      return !Number.isNaN(t) && t >= since;
    });
  const [f7, r7, fa, ra] = [countBy(recent(f)), countBy(recent(r)), countBy(f), countBy(r)];
  for (const id of new Set([...fa.keys(), ...ra.keys()])) {
    out.set(id, {
      week: (f7.get(id) ?? 0) * 2 + (r7.get(id) ?? 0),
      all: (fa.get(id) ?? 0) * 2 + (ra.get(id) ?? 0),
    });
  }
  return out;
}
