import "server-only";
import { cityName } from "../popup";
import { latest, type Row } from "./store";

// PO 지표 · 사용자 테스트 설문 — common/stats.py 를 그대로 옮긴 것 (/stats · 관리자 '사용자 테스트' 가 같은 숫자를 쓴다).

export const VISIT_FIELDS: Record<string, string> = {
  start_date: "기간",
  address: "주소",
  lat: "지도 좌표",
  links: "참고 링크",
  images: "포스터",
};
export const EXTRA_FIELDS: Record<string, string> = { intro: "팝업 소개", perks: "특전", goods: "굿즈" };
/** Notion 주간 가져오기(11/2 첫 실행) 를 넣기 직전. 개선 전후 비교의 기준 시점 */
export const NOTION_CUTOFF = "2026-10-30";

const r1 = (x: number) => Math.round(x * 10) / 10;

/** mycal._day: 'YYYY-MM-DD' 로 읽히면 그 날, 아니면 '' */
export function dayOf(v: unknown): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v ?? ""));
  if (!m) return "";
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return d.getUTCMonth() === Number(m[2]) - 1 ? d.toISOString().slice(0, 10) : "";
}
const diffDays = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);

function filled(row: Row, col: string): boolean {
  if (col === "start_date") return !!dayOf(row.start_date) && !!dayOf(row.end_date);
  return !!String(row[col] ?? "").trim();
}

/** entry_id 별 최신 행. until 을 주면 그날 전까지 쌓인 기록만. 삭제는 빼고 '기간 종료' 로 내린 것은 넣는다 */
export function popups(allRows: Row[], until?: string): Row[] {
  const rs = allRows.filter((r) => !until || String(r.updated_at ?? "").slice(0, 10) < until);
  return latest(rs).filter((r) => !(r.status === "deleted" && r.source !== "기간 종료"));
}

export type Completeness = { n: number; fields: Record<string, number>; complete: number };

export function completeness(rows: Row[]): Completeness {
  const n = rows.length;
  if (!n) return { n: 0, fields: {}, complete: 0 };
  const fields: Record<string, number> = {};
  for (const [col, name] of Object.entries({ ...VISIT_FIELDS, ...EXTRA_FIELDS }))
    fields[name] = r1((rows.filter((r) => filled(r, col)).length / n) * 100);
  const complete = (rows.filter((r) => Object.keys(VISIT_FIELDS).every((c) => filled(r, c))).length / n) * 100;
  return { n, fields, complete: r1(complete) };
}

export type BeforeAfter = { 항목: string; 이전: number; 지금: number };

/** stats.before_after 를 넓은 모양(항목 · 이전 · 지금)으로. 맨 위는 '방문 전 정보 모두' */
export function beforeAfter(allRows: Row[], cutoff = NOTION_CUTOFF): BeforeAfter[] {
  const before = completeness(popups(allRows, cutoff));
  const now = completeness(popups(allRows));
  const names = ["방문 전 정보 모두", ...Object.values({ ...VISIT_FIELDS, ...EXTRA_FIELDS })];
  return names.map((name) => ({
    항목: name,
    이전: name === "방문 전 정보 모두" ? before.complete : (before.fields[name] ?? 0),
    지금: name === "방문 전 정보 모두" ? now.complete : (now.fields[name] ?? 0),
  }));
}

export function statusCounts(rows: Row[], today: string): Record<"진행 중" | "예정" | "종료", number> {
  const out = { "진행 중": 0, 예정: 0, 종료: 0 };
  for (const r of rows) {
    const s = dayOf(r.start_date);
    const e = dayOf(r.end_date);
    if (!s || !e) continue;
    out[e < today ? "종료" : s > today ? "예정" : "진행 중"] += 1;
  }
  return out;
}

export function startingWithin(rows: Row[], today: string, days = 7): number {
  return rows.filter((r) => {
    const s = dayOf(r.start_date);
    if (!s) return false;
    const d = diffDays(today, s);
    return d >= 0 && d < days;
  }).length;
}

export type Count = { label: string; n: number };

/** collections.Counter.most_common 과 같은 순서 (수 내림차순, 같으면 처음 나온 순) */
export function mostCommon(items: string[]): Count[] {
  const m = new Map<string, number>();
  for (const x of items) m.set(x, (m.get(x) ?? 0) + 1);
  return [...m.entries()].map(([label, n]) => ({ label, n })).sort((a, b) => b.n - a.n);
}

function top(items: string[], n: number): Count[] {
  const all = mostCommon(items);
  const head = all.slice(0, n);
  const rest = all.slice(n);
  if (rest.length) head.push({ label: "그 외", n: rest.reduce((a, b) => a + b.n, 0) });
  return head;
}

/** geo.city_name: 서울 동네는 '서울', 경기는 시 이름 */
function city(address: string): string {
  const a = (address || "").trim();
  if (a.startsWith("서울")) return "서울";
  if (a.startsWith("경기")) {
    const m = /([가-힣]{2,})시(?:\s|$)/.exec(a);
    if (m) return m[1];
  }
  return cityName(a);
}

export const byCity = (rows: Row[], n = 10) => top(rows.map((r) => city(String(r.address || "")) || "지역 미상"), n);
export const byWork = (rows: Row[], n = 10) => top(rows.map((r) => String(r.work || "").trim() || "작품 미상"), n);

/** 시작 월별 팝업 수 (빈 달도 0) */
export function byMonth(rows: Row[]): Count[] {
  const months = rows.map((r) => dayOf(r.start_date).slice(0, 7)).filter(Boolean);
  if (!months.length) return [];
  const c = new Map<string, number>();
  for (const m of months) c.set(m, (c.get(m) ?? 0) + 1);
  const sorted = [...months].sort();
  const out: Count[] = [];
  let [y, mo] = sorted[0].split("-").map(Number);
  const last = sorted[sorted.length - 1];
  for (;;) {
    const key = `${y}-${String(mo).padStart(2, "0")}`;
    out.push({ label: key, n: c.get(key) ?? 0 });
    if (key >= last) break;
    mo += 1;
    if (mo > 12) [y, mo] = [y + 1, 1];
  }
  return out;
}

export function durations(rows: Row[]): number[] {
  const out: number[] = [];
  for (const r of rows) {
    const s = dayOf(r.start_date);
    const e = dayOf(r.end_date);
    if (s && e && e >= s) out.push(diffDays(s, e) + 1);
  }
  return out;
}

export function durationBuckets(days: number[]): Count[] {
  const bins: [string, number, number][] = [
    ["1~7일", 1, 7],
    ["8~14일", 8, 14],
    ["15~30일", 15, 30],
    ["31~60일", 31, 60],
    ["61일 이상", 61, 1e6],
  ];
  return bins.map(([label, lo, hi]) => ({ label, n: days.filter((d) => lo <= d && d <= hi).length }));
}

/** 별점 1~5 분포 (리뷰 current 행) */
export function ratingDist(reviewRows: Row[]): Count[] {
  const c = [0, 0, 0, 0, 0];
  for (const r of reviewRows) {
    const raw = String(r.rating ?? "").trim();
    if (!/^-?\d+$/.test(raw)) continue;
    const n = Number(raw);
    if (n >= 1 && n <= 5) c[n - 1] += 1;
  }
  return c.map((n, i) => ({ label: `${i + 1}점`, n }));
}

/** 북마크·리뷰 참여 현황 (current 행) */
export function engagement(favRows: Row[], reviewRows: Row[]): [string, number][] {
  const users = new Set(favRows.map((r) => String(r.user)));
  const people = new Set(
    reviewRows
      .filter((r) => r.nickname)
      .map((r) => {
        const n = String(r.nickname);
        return n.includes("#") ? n.slice(n.lastIndexOf("#") + 1) : n;
      }),
  );
  return [
    ["북마크 수", favRows.length],
    ["북마크한 사람", users.size],
    ["1인당 북마크", users.size ? r1(favRows.length / users.size) : 0],
    ["리뷰 수", reviewRows.length],
    ["리뷰 쓴 사람", people.size],
  ];
}

export function topBookmarked(favRows: Row[], cafeRows: Row[], n = 5): { 팝업: string; 북마크: number }[] {
  const names = new Map(
    cafeRows.map((r) => [
      String(r.entry_id),
      `${r.work || ""} · ${r.cafe_name || ""}`.replace(/^[\s·]+|[\s·]+$/g, ""),
    ]),
  );
  return mostCommon(favRows.map((r) => String(r.cafe_id)))
    .slice(0, n)
    .map((c) => ({ 팝업: names.get(c.label) ?? "(내려간 팝업)", 북마크: c.n }));
}

// ------------------------------------------------------------------ 사용자 테스트 설문 ('정리' 탭)
export const SURVEY_TARGET = { success: 80.0, q1: 60.0 };
export const SURVEY_TASKS: Record<string, string> = {
  "질문 1": "이번 주말 서울 팝업 찾기",
  "질문 2": "작품 팝업 북마크",
  "질문 3": "내 캘린더에서 확인",
  "질문 4": "공식 공지 열기",
};
const SURVEY_OK = ["해냈어요", "어렵게 해냈어요"];
export type SurveyRow = Record<string, string>;

function nums(values: unknown[]): number[] {
  const out: number[] = [];
  for (const v of values) {
    const t = String(v ?? "").trim();
    if (!t) continue;
    const x = Number(t);
    if (Number.isFinite(x) && x > 0) out.push(x);
  }
  return out;
}

export function avg(values: unknown[]): number | null {
  const xs = nums(values);
  return xs.length ? r1(xs.reduce((a, b) => a + b, 0) / xs.length) : null;
}

export type TaskStat = { 명: number; 성공률: number | null; 평균초: number | null; 결과: Record<string, number> };
export type SurveySummary = {
  응답자: number;
  성공률: number | null;
  평소초: number | null;
  질문1초: number | null;
  비교: number | null;
  만족도: number | null;
  다시쓸의향: number | null;
  과제별: Record<string, TaskStat>;
  불편한점: Count[];
  정보출처: Count[];
  방문빈도: Count[];
  만족도분포: Record<string, number>;
  막힌곳: Count[];
  바라는점: string[];
};

const s = (r: SurveyRow, k: string) => String(r[k] ?? "");

/** stats.survey_summary (성공 = 해냈어요 + 어렵게 해냈어요, 평균 시간 = 성공한 줄만) */
export function surveySummary(input: SurveyRow[]): SurveySummary {
  const rows = input.filter((r) => s(r, "닉네임").trim() && s(r, "과제").trim());
  const people = rows.filter((r) => r["과제"] === "질문 1");
  const ok = (r: SurveyRow) => SURVEY_OK.includes(s(r, "결과"));
  const pct = (a: number, b: number) => (b ? r1((a / b) * 100) : null);
  const tasks: Record<string, TaskStat> = {};
  for (const t of Object.keys(SURVEY_TASKS)) {
    const ts = rows.filter((r) => r["과제"] === t);
    const res: Record<string, number> = {};
    for (const r of ts) {
      const k = s(r, "결과") || "응답 없음";
      res[k] = (res[k] ?? 0) + 1;
    }
    tasks[t] = {
      명: ts.length,
      성공률: pct(ts.filter(ok).length, ts.length),
      평균초: avg(ts.filter(ok).map((r) => r["걸린시간초"])),
      결과: res,
    };
  }
  const multi = (key: string) =>
    mostCommon(
      people.flatMap((r) =>
        s(r, key)
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),
      ),
    );
  const sat: Record<string, number> = {};
  for (const r of people) {
    const v = s(r, "만족도");
    if (v.trim()) sat[v] = (sat[v] ?? 0) + 1;
  }
  return {
    응답자: people.length,
    성공률: pct(rows.filter(ok).length, rows.length),
    평소초: avg(people.map((r) => r["평소걸린시간초"])),
    질문1초: tasks["질문 1"].평균초,
    비교: avg(people.map((r) => r["비교"])),
    만족도: avg(people.map((r) => r["만족도"])),
    다시쓸의향: pct(people.filter((r) => s(r, "다시쓸의향") === "있어요").length, people.length),
    과제별: tasks,
    불편한점: multi("불편한점"),
    정보출처: multi("정보출처"),
    방문빈도: mostCommon(people.filter((r) => r["방문빈도"]).map((r) => s(r, "방문빈도"))),
    만족도분포: sat,
    막힌곳: mostCommon(
      rows.filter((r) => s(r, "막힌 지점").trim()).map((r) => `${s(r, "과제")} · ${s(r, "막힌 지점").trim()}`),
    ).slice(0, 5),
    바라는점: people.map((r) => s(r, "바라는점").trim()).filter(Boolean),
  };
}

/** '정리' 탭 한 줄의 버전. 1차 폼 응답만 '1차', 나머지는 '2차' */
export const surveyVersion = (r: SurveyRow) => (s(r, "버전").trim() === "1차" ? "1차" : "2차");

// ---- 응답 검증 (11/20, 앱 stats.survey_verify 와 같은 규칙) ----------------------------------------------------
// '정리' 탭 줄은 손으로도 넣을 수 있어서, 구글 폼 응답 탭(1차 응답 · 2차 응답)에 같은 닉네임이 있고
// 폼이 찍은 받은 시각이 지금보다 앞선 것만 실제 응답으로 센다.
export const SURVEY_FORM_TABS = { "1차": "1차 응답", "2차": "2차 응답" } as const;
export type SurveyCheck = { 전체: number; 검증: number; 제외: number; 미래: number; 시각없음: number; 폼에없음: number };

/** 구글 폼 타임스탬프 → 한국 시각 'YYYY-MM-DDTHH:MM:SS' 글자 (비교용). 못 읽으면 '' */
export function formTime(text: string): string {
  const t = String(text || "").trim();
  const m = /(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*(오전|오후)?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(t);
  const p2 = (n: number | string) => String(n).padStart(2, "0");
  if (m) {
    let h = Number(m[5]);
    if (m[4] === "오후" && h < 12) h += 12;
    if (m[4] === "오전" && h === 12) h = 0;
    return `${m[1]}-${p2(m[2])}-${p2(m[3])}T${p2(h)}:${m[6]}:${p2(m[7] ?? 0)}`;
  }
  const iso = /^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T](\d{1,2}):(\d{2})(?::(\d{2}))?/.exec(t);
  return iso ? `${iso[1]}-${p2(iso[2])}-${p2(iso[3])}T${p2(iso[4])}:${iso[5]}:${p2(iso[6] ?? 0)}` : "";
}

export function surveyVerify(
  rows: SurveyRow[],
  forms: Record<string, SurveyRow[]>,
  now = new Date(Date.now() + 9 * 3600_000).toISOString().slice(0, 19),
): { rows: SurveyRow[]; check: SurveyCheck } {
  const ok = new Set<string>();
  const inForm = new Set<string>();
  let 미래 = 0;
  let 시각없음 = 0;
  for (const [ver, rs] of Object.entries(forms)) {
    for (const r of rs) {
      const nick = s(r, "닉네임").trim();
      if (!nick) continue;
      inForm.add(`${ver}|${nick}`);
      const t = formTime(s(r, "타임스탬프"));
      if (!t) 시각없음++;
      else if (t > now) 미래++;
      else ok.add(`${ver}|${nick}`);
    }
  }
  const key = (r: SurveyRow) => `${surveyVersion(r)}|${s(r, "닉네임").trim()}`;
  const people = new Set(rows.filter((r) => s(r, "닉네임").trim()).map(key));
  const kept = rows.filter((r) => ok.has(key(r)));
  const good = new Set(kept.map(key));
  const out = [...people].filter((p) => !good.has(p));
  return {
    rows: kept,
    check: { 전체: people.size, 검증: good.size, 제외: out.length, 미래, 시각없음, 폼에없음: out.filter((p) => !inForm.has(p)).length },
  };
}

export type Metric = [string, number | null, number | null, string, boolean, number | null];
export type Pair = {
  닉네임: string;
  "질문 1 (1차)": number | null;
  "질문 1 (2차)": number | null;
  "해낸 과제 (1차)": number;
  "해낸 과제 (2차)": number;
  "만족도 (1차)": number | null;
  "만족도 (2차)": number | null;
};
export type SurveyCompare = {
  "1차": SurveySummary;
  "2차": SurveySummary;
  지표: Metric[];
  "같은 사람": {
    명: number;
    "빨라진 사람": number;
    "시간 잰 사람": number;
    "평균 줄어든 초": number | null;
    "더 해낸 사람": number;
    "만족도 오른 사람": number;
  };
  짝: Pair[];
};

/** stats.survey_compare: 1차 → 2차 비교 */
export function surveyCompare(rows: SurveyRow[]): SurveyCompare {
  const by = { "1차": rows.filter((r) => surveyVersion(r) === "1차"), "2차": rows.filter((r) => surveyVersion(r) === "2차") };
  const a = surveySummary(by["1차"]);
  const b = surveySummary(by["2차"]);
  const T = Object.entries(SURVEY_TASKS);
  const metrics: Metric[] = [
    ["과제 성공률", a.성공률, b.성공률, "%", true, SURVEY_TARGET.success],
    ["질문 1 평균 시간 (이번 주말 서울 팝업 찾기)", a.질문1초, b.질문1초, "초", false, SURVEY_TARGET.q1],
    ...T.map(([t, n]): Metric => [`${t} 성공률 (${n})`, a.과제별[t].성공률, b.과제별[t].성공률, "%", true, null]),
    ...T.filter(([t]) => t !== "질문 1").map(
      ([t, n]): Metric => [`${t} 평균 시간 (${n})`, a.과제별[t].평균초, b.과제별[t].평균초, "초", false, null],
    ),
    ["평소 방법보다 편함 (5점)", a.비교, b.비교, "점", true, null],
    ["만족도 (5점)", a.만족도, b.만족도, "점", true, null],
    ["다시 쓸 의향", a.다시쓸의향, b.다시쓸의향, "%", true, null],
  ];
  type P = { done: number; q1: number | null; sat: number | null };
  const person = (rs: SurveyRow[]) => {
    const out = new Map<string, P>();
    for (const r of rs) {
      const nick = s(r, "닉네임").trim();
      if (!nick) continue;
      if (!out.has(nick)) out.set(nick, { done: 0, q1: null, sat: null });
      const p = out.get(nick)!;
      if (SURVEY_OK.includes(s(r, "결과"))) p.done += 1;
      if (r["과제"] === "질문 1") {
        p.q1 = nums([r["걸린시간초"]])[0] ?? null;
        p.sat = nums([r["만족도"]])[0] ?? null;
      }
    }
    return out;
  };
  const p1 = person(by["1차"]);
  const p2 = person(by["2차"]);
  const pairs: Pair[] = [...p1.keys()]
    .filter((n) => p2.has(n))
    .sort()
    .map((n) => ({
      닉네임: n,
      "질문 1 (1차)": p1.get(n)!.q1,
      "질문 1 (2차)": p2.get(n)!.q1,
      "해낸 과제 (1차)": p1.get(n)!.done,
      "해낸 과제 (2차)": p2.get(n)!.done,
      "만족도 (1차)": p1.get(n)!.sat,
      "만족도 (2차)": p2.get(n)!.sat,
    }));
  const timed = pairs.filter((p) => p["질문 1 (1차)"] && p["질문 1 (2차)"]);
  return {
    "1차": a,
    "2차": b,
    지표: metrics,
    "같은 사람": {
      명: pairs.length,
      "빨라진 사람": timed.filter((p) => p["질문 1 (2차)"]! < p["질문 1 (1차)"]!).length,
      "시간 잰 사람": timed.length,
      "평균 줄어든 초": timed.length
        ? r1(timed.reduce((acc, p) => acc + (p["질문 1 (1차)"]! - p["질문 1 (2차)"]!), 0) / timed.length)
        : null,
      "더 해낸 사람": pairs.filter((p) => p["해낸 과제 (2차)"] > p["해낸 과제 (1차)"]).length,
      "만족도 오른 사람": pairs.filter(
        (p) => p["만족도 (1차)"] && p["만족도 (2차)"] && p["만족도 (2차)"]! > p["만족도 (1차)"]!,
      ).length,
    },
    짝: pairs,
  };
}
