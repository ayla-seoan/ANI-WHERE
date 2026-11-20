import "server-only";
import { current, mode, rows } from "./store";
import { scoreRows, type Score } from "../rank";

// 홈 '실시간 인기 급상승 랭킹' 점수. 규칙은 lib/rank.ts (앱 common/rank.py 와 같음, 11/20).
// 여기는 북마크 · 리뷰 표를 읽어 넘기기만 한다 (누가 했는지는 쓰지 않는다).
export type { Score };

/** 팝업 id → { week: 최근 7일 점수, all: 전체 기간 점수 }. 저장소가 없거나 못 읽으면 빈 표 (오픈 순으로만 줄 세움) */
export async function rankScores(): Promise<Map<string, Score>> {
  if (mode() === "none") return new Map();
  try {
    const [favs, revs] = await Promise.all([rows("favorites"), rows("reviews")]);
    return scoreRows(current(favs), current(revs));
  } catch {
    return new Map();
  }
}
