// 홈 랭킹 규칙 시험: samples/rank_cases.json 의 답을 web/lib/rank.ts 가 그대로 내는지 (앱 tests/test_rank.py 와 같은 문제).
//   cd web && npm run test:rank
import * as fs from "fs";
import * as path from "path";
import { rankOrder, scoreRows } from "../lib/rank";

type Case = {
  name: string;
  now: string;
  favorites: Record<string, unknown>[];
  reviews: Record<string, unknown>[];
  popups: { id: string; start: string }[];
  scores: Record<string, [number, number]>;
  expected: string[];
};

// 웹은 팝업 날짜를 lib/data.ts ymd 로 YYYY-MM-DD 로 맞춰 둔다 — 시험도 같은 모양으로
function ymd(v: string): string {
  const m = v.match(/(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})/);
  return m ? `${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}` : "";
}

const file = path.resolve(__dirname, "..", "..", "..", "samples", "rank_cases.json");
const { cases } = JSON.parse(fs.readFileSync(file, "utf-8")) as { cases: Case[] };
let bad = 0;
for (const c of cases) {
  const sc = scoreRows(c.favorites, c.reviews, Date.parse(c.now));
  const got = Object.fromEntries([...sc].map(([k, v]) => [k, [v.week, v.all]]));
  const order = rankOrder(
    c.popups.map((p) => ({ ...p, start: ymd(p.start) })),
    sc,
  ).map((p) => p.id);
  const okScore = JSON.stringify(Object.entries(got).sort()) === JSON.stringify(Object.entries(c.scores).sort());
  const okOrder = JSON.stringify(order) === JSON.stringify(c.expected);
  if (!okScore || !okOrder) {
    bad++;
    console.log(`실패: ${c.name}\n  점수 ${JSON.stringify(got)}\n  순서 ${order.join(",")} (기대 ${c.expected.join(",")})`);
  } else console.log(`통과: ${c.name}`);
}
process.exit(bad ? 1 : 0);
