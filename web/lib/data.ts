import "server-only";
import { cache } from "react";
import { regionOf, type DataSource, type Popup } from "./popup";

// 데이터를 읽는 곳은 이 파일 하나뿐이다. 서버에서만 실행되므로 SUPABASE_ANON_KEY 는 브라우저로 내려가지 않는다.
// (NEXT_PUBLIC_ 접두사를 붙이지 않는다.)

const REPO_RAW = "https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main";
const CAFES_JSON = `${REPO_RAW}/data/cafes.json`;
const REVIEWS_JSON = `${REPO_RAW}/data/reviews.json`;
const UPLOADS = `${REPO_RAW}/static/uploads/`;
const REVALIDATE = 600; // 10분 (ISR)
const TIMEOUT_MS = 10_000;

export type PopupData = {
  popups: Popup[];
  source: DataSource;
  /** 사람이 읽는 출처 표시 (푸터에 그대로 보인다) */
  sourceLabel: string;
  /** 대체 경로로 내려간 이유 (있으면) */
  note: string;
};

type Row = Record<string, unknown>;

// ---------- 정리(normalize) ----------

function str(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "string") return v.trim();
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  return "";
}

function num(v: unknown): number | null {
  const n = typeof v === "number" ? v : typeof v === "string" && v.trim() ? Number(v) : NaN;
  return Number.isFinite(n) ? n : null;
}

/** 여러 모양의 날짜를 YYYY-MM-DD 로. 알아볼 수 없으면 '' */
function ymd(v: unknown): string {
  const m = str(v).match(/(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})/);
  if (!m) return "";
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return "";
  const date = new Date(Date.UTC(y, mo - 1, d));
  if (date.getUTCMonth() !== mo - 1) return ""; // 2월 30일 같은 날짜
  return date.toISOString().slice(0, 10);
}

function list(v: unknown): string[] {
  return str(v)
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function imageUrls(v: unknown): string[] {
  const out: string[] = [];
  for (const raw of str(v).split(/[\s,]+/)) {
    const name = raw.trim();
    if (!name) continue;
    if (/^https:\/\//i.test(name)) out.push(name);
    else if (/^[\w.-]+\.(png|jpe?g|webp|gif|avif)$/i.test(name)) out.push(UPLOADS + encodeURIComponent(name));
  }
  return Array.from(new Set(out));
}

function linkUrls(v: unknown): string[] {
  const ok: string[] = [];
  for (const raw of str(v).split(/\s+/)) {
    try {
      const u = new URL(raw);
      if (u.protocol === "https:" || u.protocol === "http:") ok.push(u.toString());
    } catch {
      /* URL 이 아니면 버린다 */
    }
  }
  const uniq = Array.from(new Set(ok));
  // recal.kr 은 다른 사이트 뒤로 (cafe.order_links 와 같은 규칙)
  const isRecal = (u: string) => /(^|\.)recal\.kr$/i.test(new URL(u).hostname);
  return [...uniq.filter((u) => !isRecal(u)), ...uniq.filter(isRecal)];
}

function inKorea(lat: number | null, lng: number | null): boolean {
  return lat !== null && lng !== null && lat > 32 && lat < 39.5 && lng > 124 && lng < 132;
}

function normalize(row: Row): Popup | null {
  const id = str(row.entry_id);
  if (!id || !/^[\w-]+$/.test(id)) return null;
  const name = str(row.cafe_name);
  const work = str(row.work);
  if (!name && !work) return null;
  let start = ymd(row.start_date);
  let end = ymd(row.end_date);
  if (start && end && end < start) [start, end] = [end, start];
  const lat = num(row.lat);
  const lng = num(row.lng);
  const coordsOk = inKorea(lat, lng);
  const address = str(row.address);
  return {
    id,
    name: name || "매장 미정",
    work: work || "작품 미정",
    characters: str(row.characters),
    address,
    region: regionOf(address),
    lat: coordsOk ? lat : null,
    lng: coordsOk ? lng : null,
    start,
    end,
    perks: list(row.perks),
    goods: list(row.goods),
    tags: list(row.tags),
    images: imageUrls(row.images),
    links: linkUrls(row.links),
    intro: str(row.intro),
    updatedAt: str(row.updated_at),
    rating: null,
  };
}

/** append-only 표에서 entry_id 별 최신 revision 만 (popups_current 뷰와 같은 규칙) */
function latestActive(rows: Row[]): Row[] {
  const latest = new Map<string, Row>();
  for (const r of rows) {
    if (!r || typeof r !== "object") continue;
    const id = str(r.entry_id);
    if (!id) continue;
    const prev = latest.get(id);
    if (!prev || (num(r.revision) ?? 0) > (num(prev.revision) ?? 0)) latest.set(id, r);
  }
  return [...latest.values()].filter((r) => str(r.status) === "active");
}

function toPopups(rows: Row[]): Popup[] {
  const out: Popup[] = [];
  for (const r of rows) {
    try {
      const p = normalize(r);
      if (p) out.push(p);
    } catch {
      /* 한 행이 이상해도 나머지는 보여준다 */
    }
  }
  return out;
}

type Ratings = Map<string, { avg: number; n: number }>;

function attachRatings(popups: Popup[], ratings: Ratings): Popup[] {
  return popups.map((p) => ({ ...p, rating: ratings.get(p.id) ?? null }));
}

// ---------- 가져오기 ----------

async function getJSON(url: string, headers?: Record<string, string>): Promise<unknown> {
  const res = await fetch(url, {
    headers,
    next: { revalidate: REVALIDATE },
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

async function fromSupabase(base: string, key: string): Promise<Popup[]> {
  // 새 형식 키(sb_publishable_…)는 apikey 에만, 옛 형식(anon JWT, eyJ…)은 Authorization 에도
  const headers: Record<string, string> = key.startsWith("eyJ") ? { apikey: key, Authorization: `Bearer ${key}` } : { apikey: key };
  const root = base.replace(/\/+$/, "");
  const rows = await getJSON(`${root}/rest/v1/popups_current?select=*`, headers);
  if (!Array.isArray(rows)) throw new Error("popups_current 응답이 목록이 아님");
  // 뷰가 이미 최신·active 만 주지만, 같은 함수로 한 번 더 걸러도 결과는 같다
  const popups = toPopups(latestActive(rows.map((r) => ({ status: "active", ...r }))));
  const ratings: Ratings = new Map();
  try {
    const rs = await getJSON(`${root}/rest/v1/popup_ratings?select=*`, headers);
    if (Array.isArray(rs)) {
      for (const r of rs as Row[]) {
        const avg = num(r.avg_rating);
        const n = num(r.n);
        if (str(r.cafe_id) && avg !== null && n) ratings.set(str(r.cafe_id), { avg, n });
      }
    }
  } catch {
    /* 별점이 없어도 목록은 보여준다 */
  }
  return attachRatings(popups, ratings);
}

async function fromGitHub(): Promise<Popup[]> {
  const rows = await getJSON(CAFES_JSON);
  if (!Array.isArray(rows)) throw new Error("cafes.json 이 목록이 아님");
  const popups = toPopups(latestActive(rows as Row[]));
  const ratings: Ratings = new Map();
  try {
    const rs = await getJSON(REVIEWS_JSON);
    if (Array.isArray(rs)) {
      const sums = new Map<string, { s: number; n: number }>();
      for (const r of latestActive(rs as Row[])) {
        const rating = num(r.rating);
        if (str(r.parent_id) || rating === null || rating < 1 || rating > 5) continue;
        const k = str(r.cafe_id);
        const cur = sums.get(k) ?? { s: 0, n: 0 };
        sums.set(k, { s: cur.s + rating, n: cur.n + 1 });
      }
      for (const [k, v] of sums) ratings.set(k, { avg: Math.round((v.s / v.n) * 10) / 10, n: v.n });
    }
  } catch {
    /* 별점이 없어도 목록은 보여준다 */
  }
  return attachRatings(popups, ratings);
}

/** 한 요청 안에서는 한 번만 읽는다 (React cache). 요청 사이는 fetch 캐시(10분)가 맡는다. */
export const getPopupData = cache(async (): Promise<PopupData> => {
  const url = process.env.SUPABASE_URL?.trim();
  const key = process.env.SUPABASE_ANON_KEY?.trim();
  let note = "";
  if (url && key) {
    try {
      return { popups: await fromSupabase(url, key), source: "supabase", sourceLabel: "데이터: Supabase", note };
    } catch (e) {
      note = `Supabase 연결 실패로 GitHub 공개 데이터를 대신 씀 (${e instanceof Error ? e.message : "오류"})`;
      console.error("[data]", note);
    }
  }
  try {
    return { popups: await fromGitHub(), source: "github", sourceLabel: "데이터: GitHub 공개 데이터", note };
  } catch (e) {
    const why = e instanceof Error ? e.message : "오류";
    console.error("[data] GitHub 데이터도 읽지 못함:", why);
    return { popups: [], source: "none", sourceLabel: "데이터를 불러오지 못함", note: why };
  }
});

export async function getPopup(id: string): Promise<Popup | null> {
  const { popups } = await getPopupData();
  return popups.find((p) => p.id === id) ?? null;
}
