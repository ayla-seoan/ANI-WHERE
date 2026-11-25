// 후기 도장 랭크 (11/25 새 기능, docs/design/handoff/README.md 4절 · A-Rank 시안). 앱 common/stamp.py 와 같은 표 · 같은 규칙.
// 도장 수 = 내가 쓴 '다녀온 후기'가 있는 팝업 수 (같은 팝업은 1개, 기대평 · 답글 · 지운 후기 제외, 별점만 남겨도 1개).
// 새 표를 만들지 않고 리뷰 기록에서 그때그때 센다 (DB 는 건드리지 않는다). 이름 · 기준은 시안의 제안값이다.

export type Tier = {
  lv: number;
  name: string;
  en: string; // 96px 도장 둘레 글자
  need: number; // 이 랭크가 되는 도장 수
  ring: string; // 테두리
  fill: string; // 바탕
  fg: string; // 글자
  perk: string;
};

export const TIERS: Tier[] = [
  { lv: 1, name: "새싹 팬", en: "SPROUT", need: 1, ring: "#5fbf9f", fill: "#f0faf6", fg: "#0f6b5c", perk: "첫 후기 기념 도장 · 리뷰 닉네임 옆에 도장 표시" },
  { lv: 2, name: "단골 팬", en: "REGULAR", need: 3, ring: "#21b287", fill: "#e9f7f2", fg: "#0f6b5c", perk: "도장이 진한 초록으로" },
  { lv: 3, name: "성지순례러", en: "PILGRIM", need: 10, ring: "#2c5bc5", fill: "#eaf0fc", fg: "#2c5bc5", perk: "파란 도장" },
  { lv: 4, name: "덕질 마스터", en: "MASTER", need: 25, ring: "#7656c4", fill: "#f1ecff", fg: "#5b3fae", perk: "보라 도장" },
  { lv: 5, name: "전설의 덕후", en: "LEGEND", need: 50, ring: "#c99a00", fill: "#fff6d6", fg: "#7a5a00", perk: "금색 도장" },
];

/** 도장 수 → 랭크 (0개면 null = 아직 도장 없음) */
export function tierOf(stamps: number): Tier | null {
  let cur: Tier | null = null;
  for (const t of TIERS) if (stamps >= t.need) cur = t;
  return cur;
}

export const tierByLv = (lv: number): Tier | null => TIERS.find((t) => t.lv === lv) ?? null;

/** 다음 랭크와 남은 도장 수 (가장 높은 랭크면 null) */
export function nextTier(stamps: number): { tier: Tier; left: number } | null {
  const next = TIERS.find((t) => stamps < t.need);
  return next ? { tier: next, left: next.need - stamps } : null;
}

export const STAMP_RULES = [
  "별점만 남긴 다녀온 후기도 1개로 세요",
  "같은 팝업에는 도장 1개만 (여러 번 써도 1개)",
  "기대평 · 답글은 세지 않아요",
  "지운 후기, 관리자가 지운 후기는 빼고 세요",
  "탈퇴하면 도장도 함께 지워져요",
];
