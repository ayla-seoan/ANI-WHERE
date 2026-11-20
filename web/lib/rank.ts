// 홈 '실시간 인기 급상승 랭킹' 규칙 — 앱 common/rank.py 와 한 글자도 다르지 않게 (11/20: 두 사이트 결과를 맞춤).
// 바꾸면 두 곳을 같이 바꾸고 samples/rank_cases.json 으로 둘 다 돌린다 (npm run test:rank · pytest tests/test_rank.py).
//   ① 최근 7일 점수 = 최근 7일 북마크 수 × 2 + 최근 7일 리뷰 · 답글 수
//   ② 같으면 전체 기간의 같은 점수
//   ③ 같으면 오픈이 빠른 순 (점수 0인 팝업도 이 순서로 채움)
//   ④ 같으면 팝업 번호(entry_id) 순 — 같은 날 여는 팝업끼리 두 사이트 순서가 달라지지 않게
// 북마크 · 리뷰는 지금 살아 있는 기록(current)만 받는다. 리뷰는 보이는 것만(전체 기록으로 판단한 뒤 7일을 거름).
// 시간대가 없는 시각은 UTC 로 본다. 이 파일은 서버 전용 모듈을 부르지 않는다 (시험 스크립트가 바로 돌림).
export const RANK_DAYS = 7;
export const TOP_N = 5;

type Row = Record<string, unknown>;
export type Score = { week: number; all: number };

function ts(v: unknown): number {
  const s = String(v ?? "")
    .trim()
    .replace(/^(\d{4}-\d{2}-\d{2}) /, "$1T");
  if (!s) return NaN;
  // 시간대 표시(Z · +09:00)가 없으면 UTC (파이썬 쪽과 같게)
  return Date.parse(/(Z|[+-]\d{2}:?\d{2})$/i.test(s) || !s.includes("T") ? s : `${s}Z`);
}

/** 화면에 보이는 리뷰만: 원글이거나, 답글을 따라 올라가 원글에 닿는 것 (앱 review.threads) */
export function visibleReviews(all: Row[]): Row[] {
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

function countBy(list: Row[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const r of list) {
    const k = String(r.cafe_id || "");
    if (k) m.set(k, (m.get(k) ?? 0) + 1);
  }
  return m;
}

/** 팝업 id → { week: 최근 7일 점수, all: 전체 기간 점수 } */
export function scoreRows(favs: Row[], reviews: Row[], now: number = Date.now()): Map<string, Score> {
  const since = now - RANK_DAYS * 86_400_000;
  const revs = visibleReviews(reviews);
  const recent = (list: Row[]) => list.filter((x) => ts(x.updated_at) >= since);
  const [f7, r7, fa, ra] = [countBy(recent(favs)), countBy(recent(revs)), countBy(favs), countBy(revs)];
  const out = new Map<string, Score>();
  for (const id of new Set([...fa.keys(), ...ra.keys()])) {
    out.set(id, {
      week: (f7.get(id) ?? 0) * 2 + (r7.get(id) ?? 0),
      all: (fa.get(id) ?? 0) * 2 + (ra.get(id) ?? 0),
    });
  }
  return out;
}

const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

/** 진행 중 · 오픈 예정 팝업을 랭킹 순서로 (전부 돌려준다. 화면은 앞 TOP_N 개). start 는 YYYY-MM-DD */
export function rankOrder<T extends { id: string; start: string }>(live: T[], scores: Map<string, Score>): T[] {
  const sc = (p: T) => scores.get(p.id) ?? { week: 0, all: 0 };
  return [...live].sort(
    (a, b) => sc(b).week - sc(a).week || sc(b).all - sc(a).all || cmp(a.start, b.start) || cmp(a.id, b.id),
  );
}
