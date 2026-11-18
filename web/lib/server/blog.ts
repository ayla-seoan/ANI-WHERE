import "server-only";
import { mask } from "@/lib/guard";
import { areaName } from "@/lib/popup";
import { append, mode, rows } from "./store";

// 팝업별 블로그 후기 (네이버 블로그 검색) — common/blog.py 를 옮긴 것. 서버에서만 부른다.
//
// 네이버 검색 API 는 2026-07-31 부터 개발자센터 신규 신청이 막히고 네이버클라우드 NAVER API HUB 로 옮겨졌다.
//   NAVER_BLOG_CLIENT_ID      API HUB 의 Client ID
//   NAVER_BLOG_CLIENT_SECRET  API HUB 의 Client Secret
//   NAVER_BLOG_URL            블로그 검색 호출 주소. 비우면 https://naverapihub.apigw.ntruss.com/search/v1/blog
//   NAVER_BLOG_HEADERS        'ncp' (X-NCP-APIGW-API-KEY-ID / -KEY, 기본) 또는 'naver' (X-Naver-Client-Id / -Secret)
//
// 키가 없으면 아무것도 하지 않는다. 실패해도 화면은 멈추지 않는다.
// 보내는 것은 팝업 작품명·매장명뿐이고 회원 정보는 보내지 않는다. 결과는 제목·요약·링크만 보여 준다.
// 한 달 호출 한도(MONTHLY_LIMIT)는 api_usage 표에 25번마다 한 줄씩 쌓아 센다 (append-only).

export const HUB_URL = "https://naverapihub.apigw.ntruss.com/search/v1/blog"; // NAVER API HUB 블로그 검색
const TIMEOUT_MS = 6_000;

export type Post = {
  title: string;
  link: string;
  desc: string;
  blogger: string;
  /** YYYY-MM-DD 또는 '' */
  day: string;
};

/** 검색에 쓰는 팝업 정보 (cafes 표의 이름 그대로) */
export type BlogRow = { work?: string; cafe_name?: string; start_date?: string; address?: string };

export function enabled(): boolean {
  return Boolean(process.env.NAVER_BLOG_CLIENT_ID?.trim() && process.env.NAVER_BLOG_CLIENT_SECRET?.trim());
}

function headers(): Record<string, string> {
  const cid = (process.env.NAVER_BLOG_CLIENT_ID || "").trim();
  const sec = (process.env.NAVER_BLOG_CLIENT_SECRET || "").trim();
  if ((process.env.NAVER_BLOG_HEADERS || "ncp").toLowerCase() === "naver")
    return { "X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec };
  return { "X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": sec };
}

const hubUrl = () => (process.env.NAVER_BLOG_URL || "").trim() || HUB_URL;

const ENT: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
/** html.unescape (자주 나오는 이름 + 숫자 참조) */
export function unescapeHtml(s: string): string {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, k: string) => {
    if (k[0] === "#") {
      const n = k[1] === "x" || k[1] === "X" ? parseInt(k.slice(2), 16) : parseInt(k.slice(1), 10);
      return Number.isFinite(n) && n > 0 && n < 0x110000 ? String.fromCodePoint(n) : m;
    }
    return ENT[k.toLowerCase()] ?? m;
  });
}

function clean(text: unknown): string {
  return mask(unescapeHtml(String(text ?? "").replace(/<[^>]+>/g, "")).trim());
}

/** 검색어: '작품 매장 팝업' (매장 이름의 괄호·지점 꾸밈은 뺀다) */
export function queryFor(row: BlogRow): string {
  const work = String(row.work || "").trim();
  const cafe = String(row.cafe_name || "")
    .replace(/\(.*?\)/g, "")
    .trim();
  return [work, cafe, "팝업"].filter(Boolean).join(" ");
}

const GENERIC = new Set([
  "카페", "팝업", "스토어", "팝업스토어", "콜라보", "매장", "지점", "본점", "space", "cafe", "store", "the",
  "애니", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "경기", "더현",
]);

/** 매장 이름·동네에서 알아볼 낱말 ('애니메이트 카페 잠실롯데점' → 애니메이트, 잠실롯데, 잠실 …) */
export function placeWords(row: BlogRow): string[] {
  const words: string[] = [];
  const name = String(row.cafe_name || "").replace(/\(.*?\)/g, " ");
  for (const raw of name.match(/[가-힣A-Za-z0-9]{2,}/g) ?? []) {
    const w = raw.replace(/점$/, "").toLowerCase();
    if ([...w].length >= 2 && !GENERIC.has(w)) {
      words.push(w);
      const two = [...w].slice(0, 2).join("");
      if ([...w].length >= 4 && /^[가-힣]/.test(w) && !GENERIC.has(two)) words.push(two); // '잠실롯데' → '잠실'
    }
  }
  const a = areaName(String(row.address || "")); // 동네 이름만 (시 이름 '서울' 은 너무 넓다)
  if (a && [...a].length >= 2 && !GENERIC.has(a)) words.push(a.toLowerCase());
  return [...new Set(words)];
}

function ymdMinus(ymd: string, days: number): string | null {
  const m = ymd.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  if (d.getUTCMonth() !== +m[2] - 1) return null;
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

/** 네이버 postdate 'YYYYMMDD' → 'YYYY-MM-DD' (알아볼 수 없으면 '') */
function postDay(v: unknown): string {
  const m = String(v ?? "").match(/^(\d{4})(\d{2})(\d{2})$/);
  if (!m) return "";
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.getUTCMonth() === +m[2] - 1 ? `${m[1]}-${m[2]}-${m[3]}` : "";
}

type Usage = true | undefined;

/** (글 목록, 오류 이유). 팝업 시작 30일 전부터 쓴 글만, 최신순. 키가 없으면 ([], 'off').
 *  usage 를 주면 이번 달 MONTHLY_LIMIT 번을 넘으면 부르지 않는다 ([], 'limit'). */
export async function search(row: BlogRow, limit = 5, usage?: Usage): Promise<[Post[], string]> {
  if (!enabled()) return [[], "off"];
  if (usage) {
    if (!(await allowed())) return [[], "limit"];
    await record();
  }
  const qs = new URLSearchParams({ query: queryFor(row), display: "30", sort: "sim", format: "json" });
  let res: Response;
  try {
    res = await fetch(`${hubUrl()}?${qs}`, {
      headers: headers(),
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    return [[], "연결 실패"];
  }
  if (res.status !== 200) return [[], `HTTP ${res.status}`];
  let items: Record<string, unknown>[];
  try {
    const body = (await res.json()) as { items?: Record<string, unknown>[] };
    items = Array.isArray(body?.items) ? body.items : [];
  } catch {
    return [[], "응답 형식 오류"];
  }
  const since = ymdMinus(String(row.start_date || "").slice(0, 10), 30);
  const work = String(row.work || "")
    .replace(/\s+/g, "")
    .toLowerCase();
  const work4 = [...work].slice(0, 4).join("");
  const places = placeWords(row);
  const posts: Post[] = [];
  for (const it of items) {
    const day = postDay(it.postdate);
    if (since && day && day < since) continue; // 팝업과 상관없는 예전 글
    const title = clean(it.title);
    const desc = clean(it.description);
    const text = (title + desc).replace(/\s+/g, "").toLowerCase();
    if (work && !text.includes(work4)) continue; // 작품 이름이 없는 글은 뺀다
    if (places.length && !places.some((p) => text.includes(p))) continue; // 매장·동네 이름이 없는 글은 뺀다
    const link = String(it.link || "");
    if (!link.startsWith("https://") && !link.startsWith("http://")) continue;
    posts.push({
      title: [...title].slice(0, 80).join(""),
      link,
      desc: [...desc].slice(0, 120).join(""),
      blogger: [...clean(it.bloggername)].slice(0, 30).join(""),
      day,
    });
  }
  posts.sort((a, b) => (b.day || "0000").localeCompare(a.day || "0000"));
  return [posts.slice(0, limit), ""];
}

const OG = /<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i;

/** 블로그 글의 대표 사진(og:image) 주소. 못 찾으면 ''. 네이버 블로그는 모바일 주소가 가볍다 */
export async function thumbnail(link: string): Promise<string> {
  const url = link.replace("://blog.naver.com/", "://m.blog.naver.com/");
  try {
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; ANI-WHERE)" },
      cache: "no-store",
      signal: AbortSignal.timeout(3_000),
    });
    const m = OG.exec((await res.text()).slice(0, 200_000));
    const img = m ? unescapeHtml(m[1]) : "";
    return img.startsWith("https://") && !img.includes('"') && !img.includes("'") ? img : "";
  } catch {
    return "";
  }
}

/** 글마다 대표 사진을 함께 (동시에 최대 5개씩 가져온다) */
export async function withThumbs(posts: Post[]): Promise<[Post, string][]> {
  const out: [Post, string][] = [];
  for (let i = 0; i < posts.length; i += 5) {
    const part = posts.slice(i, i + 5);
    const thumbs = await Promise.all(part.map((p) => thumbnail(p.link)));
    part.forEach((p, j) => out.push([p, thumbs[j]]));
  }
  return out;
}

// ------------------------------------------------------------------ 호출 한도 (한 달 30,000번에서 완전히 멈춤)
export const MONTHLY_LIMIT = 30_000;
const FLUSH_EVERY = 25; // 25번마다 한 줄씩 쌓는다 (저장소가 한 달에 최대 1,200줄 정도)
let pending = 0;
let cacheMonth: { at: number; month: string; total: number } | null = null;

/** 이번 달 (한국 시간) 'YYYY-MM' */
function month(): string {
  return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 7);
}

/** 이번 달 블로그 검색 호출 수 = 저장된 합계 + 아직 안 적은 수. 못 읽으면 예외 */
export async function monthCalls(): Promise<number> {
  const m = month();
  const now = Date.now();
  if (!(cacheMonth && cacheMonth.month === m && now - cacheMonth.at < 60_000)) {
    // 저장소가 없으면(none) 셀 수가 없다 → 예외 (allowed 가 False 로 받는다)
    if (mode() === "none") throw new Error("api_usage 저장소 없음");
    const all = await rows("api_usage", { api: "blog", month: m });
    const total = all.reduce((s, r) => s + (Number(r.calls) || 0), 0);
    cacheMonth = { at: now, month: m, total };
  }
  return cacheMonth.total + pending;
}

/** 한도 안이면 true. 호출 수를 읽지 못하면(표가 없거나 연결 실패) 안전하게 false — 부르지 않는다 */
export async function allowed(): Promise<boolean> {
  try {
    return (await monthCalls()) < MONTHLY_LIMIT;
  } catch {
    return false;
  }
}

/** 한 번 불렀다고 센다. 25번마다 저장소에 한 줄 (새 행만 쌓는다) */
export async function record(): Promise<void> {
  pending += 1;
  if (pending < FLUSH_EVERY) return;
  const n = pending;
  pending = 0;
  try {
    await append("api_usage", { api: "blog", month: month(), calls: n });
    if (cacheMonth && cacheMonth.month === month()) cacheMonth = { ...cacheMonth, total: cacheMonth.total + n };
  } catch {
    pending += n; // 못 적었으면 다음에 다시
  }
}

/** 이 팝업의 네이버 블로그 글 수 (검색 결과 총수). 못 세면 null. 한도 안에서만 부른다 */
export async function total(row: BlogRow, usage?: Usage): Promise<number | null> {
  if (!enabled()) return null;
  if (usage) {
    if (!(await allowed())) return null;
    await record();
  }
  try {
    const qs = new URLSearchParams({ query: queryFor(row), display: "1", format: "json" });
    const res = await fetch(`${hubUrl()}?${qs}`, {
      headers: headers(),
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (res.status !== 200) return null;
    const body = (await res.json()) as { total?: unknown };
    const n = Number(body?.total ?? 0);
    return Number.isFinite(n) ? Math.trunc(n) : null;
  } catch {
    return null;
  }
}
