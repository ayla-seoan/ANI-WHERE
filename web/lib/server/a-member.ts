import "server-only";
import { tagOf } from "./member";
import { calColor } from "./mycal";
import { current, rows } from "./store";

// A안 내 캘린더 · 마이페이지에서만 쓰는 읽기 함수 (11/25). 쓰기는 없다 — 기존 서버 액션(app/actions.ts)을 그대로 쓴다.

export type MyReview = {
  id: string;
  cafeId: string;
  kind: string;
  rating: number; // 0 = 별점 없음
  body: string;
  when: string;
  photos: number;
};

/** 내가 쓴 원글 리뷰 전부 (답글 · 지운 글 제외), 최신 순. myName = '닉네임#m1a2b' */
export async function myReviews(myName: string): Promise<MyReview[]> {
  const tag = tagOf(myName);
  if (!tag) return [];
  return current(await rows("reviews"))
    .filter((r) => !String(r.parent_id || "") && tagOf(String(r.nickname || "")) === tag)
    .map((r) => {
      const n = Number(r.rating);
      return {
        id: String(r.entry_id),
        cafeId: String(r.cafe_id),
        kind: String(r.kind || ""),
        rating: n >= 1 && n <= 5 ? n : 0,
        body: String(r.body || ""),
        when: String(r.updated_at || ""),
        photos: String(r.images || "")
          .split(",")
          .filter((x) => x.trim()).length,
      };
    })
    .sort((a, b) => b.when.localeCompare(a.when));
}

// 달력 막대 색 (A-Cal 은 옅은 바탕 + 진한 글자, A-MCal 은 6px 진한 줄). 작품마다 늘 같은 색인 것은 calColor 그대로.
const TONE: Record<string, [string, string]> = {
  "#14b8a6": ["#c8eedd", "#6fd0aa"],
  "#F59E0B": ["#ffdcae", "#ffb866"],
  "#8B5CF6": ["#e4d6ff", "#b99cf5"],
  "#EC4899": ["#ffc9d2", "#ff9fb0"],
  "#3B82F6": ["#cddcff", "#8fb0ff"],
  "#22A06B": ["#d3efc9", "#8fd27c"],
  "#EF6C4D": ["#ffd3c4", "#ff9d82"],
  "#64748B": ["#dde3ea", "#a3b0c0"],
};
/** [옅은 색 (PC 막대 바탕), 진한 색 (모바일 줄 · 범례)] */
export function calTone(work: string): [string, string] {
  return TONE[calColor(work)] ?? ["#c8eedd", "#6fd0aa"];
}
