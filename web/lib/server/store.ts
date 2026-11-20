import "server-only";
import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { RAW_ROOT, rawHeaders } from "./github";

// 회원 데이터 저장소 — common/storage.py 와 같은 append-only 규칙.
//  - 고치기·지우기도 새 행(revision + 1)을 쌓는다. 기존 행을 고치거나 지우는 코드는 없다.
//  - supabase 모드: SUPABASE_URL + SUPABASE_ANON_KEY (Streamlit 과 같은 anon 키, 서버에서만). SELECT·INSERT 만 쓴다.
//  - local 모드: WEB_STORAGE=local 일 때만 (시험용). WEB_DATA_DIR(없으면 임시 폴더)에 표마다 JSON 파일.
//  - 둘 다 아니면 읽기는 빈 목록, 쓰기는 거절 (회원 기능이 꺼진 상태로 안내).

export type Row = Record<string, string | number>;
export type Mode = "supabase" | "local" | "none";

export class StorageWriteError extends Error {}

const BASE = ["row_id", "entry_id", "revision", "status", "updated_at"];
export const HEADERS: Record<string, string[]> = {
  members: [...BASE, "provider", "nickname", "agreed_at", "avatar"],
  favorites: [...BASE, "cafe_id", "user"],
  reviews: [...BASE, "cafe_id", "parent_id", "kind", "nickname", "body", "rating", "images"],
  notices: [...BASE, "target", "kind", "title", "body"],
  alert_rules: [...BASE, "rule", "enabled", "days", "max_items"],
  visits: [...BASE, "member", "day"],
  // storage.HEADERS (팝업). 등록 · 수정하기 · 되돌리기 · 지도에서 내리기가 새 행을 쌓는다
  cafes: [
    ...BASE,
    "cafe_name", "work", "characters", "address", "lat", "lng", "start_date", "end_date", "perks", "goods", "source",
    "note", "images", "tags", "links", "editor", "intro", "intro_src",
  ],
  // admin.REQ_HEADERS (삭제 요청)
  del_requests: [
    ...BASE,
    "target_type", "target_id", "target_title", "reason", "requester", "requester_nick", "decision", "admin_reason",
    "decided_at",
  ],
  // 010_api_usage (외부 API 호출 수 — 블로그 검색 한 달 한도)
  api_usage: [...BASE, "api", "month", "calls"],
  // 013_blog_posts (찾아 둔 블로그 후기 · 팝업마다 네이버에 물어본 날, 11/19). common/blog.py POST_HEADERS · CHECK_HEADERS
  blog_posts: [...BASE, "cafe_id", "link", "title", "descr", "blogger", "day", "thumb"],
  blog_checks: [...BASE, "cafe_id", "day", "found"],
};
const FLOATS = new Set(["lat", "lng"]); // DB 는 double precision (빈칸 ↔ null)
const INTS = new Set(["revision", "calls"]); // DB 는 integer
export type Table = keyof typeof HEADERS;

export function mode(): Mode {
  if ((process.env.WEB_STORAGE || "").toLowerCase() === "local") return "local";
  if (process.env.SUPABASE_URL?.trim() && process.env.SUPABASE_ANON_KEY?.trim()) return "supabase";
  return "none";
}

export function localDir(): string {
  return process.env.WEB_DATA_DIR || path.join(os.tmpdir(), "aniwhere-web-data");
}

function sb() {
  const root = (process.env.SUPABASE_URL || "").trim().replace(/\/+$/, "");
  const key = (process.env.SUPABASE_ANON_KEY || "").trim();
  // 새 형식 키(sb_publishable_…)는 apikey 에만, 옛 형식(anon JWT, eyJ…)은 Authorization 에도 (lib/data.ts 와 같게)
  const headers: Record<string, string> = key.startsWith("eyJ")
    ? { apikey: key, Authorization: `Bearer ${key}` }
    : { apikey: key };
  return { root, headers };
}

/** DB 한 행 → 앱 모양 (revision 은 숫자, 나머지는 문자열) */
function fromDb(table: Table, r: Record<string, unknown>): Row {
  const out: Row = {};
  for (const h of HEADERS[table]) {
    const v = r[h];
    out[h] = INTS.has(h) ? Number(v || 0) : v === null || v === undefined ? "" : String(v);
  }
  return out;
}

function toDb(table: Table, r: Row): Record<string, string | number | null> {
  const out: Record<string, string | number | null> = {};
  for (const h of HEADERS[table]) {
    const v = r[h];
    if (FLOATS.has(h)) out[h] = v === "" || v === null || v === undefined || !Number.isFinite(Number(v)) ? null : Number(v);
    else out[h] = INTS.has(h) ? Number(v || 0) : v === null || v === undefined ? "" : String(v);
  }
  return out;
}

// ---------- local ----------
let githubCafes: Row[] | null = null;
/** local 모드의 팝업 표 = GitHub 공개 data/cafes.json (읽기만) + 이 폴더에 쌓은 시험 기록. revision 번호가 이어지게 */
async function baseCafes(): Promise<Row[]> {
  if (githubCafes) return githubCafes;
  try {
    const res = await fetch(`${RAW_ROOT}/data/cafes.json`, {
      headers: rawHeaders(),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    const raw = (await res.json()) as Record<string, unknown>[];
    const got = Array.isArray(raw) ? raw.map((r) => fromDb("cafes", r)) : [];
    if (got.length) githubCafes = got; // 받은 것만 기억한다 (한 번 실패해도 다음에 다시 받는다)
    return got;
  } catch {
    return [];
  }
}

async function readLocal(table: Table): Promise<Row[]> {
  let mine: Row[] = [];
  try {
    const raw = JSON.parse(await fs.readFile(path.join(localDir(), `${table}.json`), "utf8"));
    mine = Array.isArray(raw) ? raw.map((r) => fromDb(table, r)) : [];
  } catch {
    mine = [];
  }
  return table === "cafes" ? [...(await baseCafes()), ...mine] : mine;
}

/** local 모드: 이 폴더에 직접 쌓은 행만 (팝업 표에서 GitHub 분을 빼고) */
async function readLocalOwn(table: Table): Promise<Row[]> {
  try {
    const raw = JSON.parse(await fs.readFile(path.join(localDir(), `${table}.json`), "utf8"));
    return Array.isArray(raw) ? raw.map((r) => fromDb(table, r)) : [];
  } catch {
    return [];
  }
}

async function writeLocal(table: Table, rows: Row[]): Promise<void> {
  await fs.mkdir(localDir(), { recursive: true });
  await fs.writeFile(path.join(localDir(), `${table}.json`), JSON.stringify(rows, null, 2), "utf8");
}

// ---------- 읽기 ----------
/** 표의 모든 기록 (eq 조건이 있으면 그 행만). 회원 화면이라 캐시하지 않는다 */
export async function rows(table: Table, eq: Record<string, string> = {}): Promise<Row[]> {
  const m = mode();
  if (m === "local") {
    const all = await readLocal(table);
    return all.filter((r) => Object.entries(eq).every(([k, v]) => String(r[k]) === v));
  }
  if (m === "none") return [];
  const { root, headers } = sb();
  const out: Row[] = [];
  const PAGE = 1000;
  for (let offset = 0; ; offset += PAGE) {
    const qs = new URLSearchParams({
      select: "*",
      order: "updated_at.asc,revision.asc,row_id.asc",
      limit: String(PAGE),
      offset: String(offset),
    });
    for (const [k, v] of Object.entries(eq)) qs.set(k, `eq.${v}`);
    const res = await fetch(`${root}/rest/v1/${table}?${qs}`, {
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) throw new Error(`${table} 읽기 실패 (${res.status})`);
    const page = (await res.json()) as Record<string, unknown>[];
    out.push(...page.map((r) => fromDb(table, r)));
    if (page.length < PAGE) break;
  }
  return out;
}

/** entry_id 별 최신 revision (지운 것 포함) */
export function latest(all: Row[]): Row[] {
  const m = new Map<string, Row>();
  for (const r of all) {
    const k = String(r.entry_id);
    const prev = m.get(k);
    if (!prev || Number(r.revision) >= Number(prev.revision)) m.set(k, r);
  }
  return [...m.values()];
}

/** entry_id 별 최신 revision 중 지우지 않은 것 (storage.current_rows) */
export function current(all: Row[]): Row[] {
  return latest(all).filter((r) => r.status !== "deleted");
}

// ---------- 쓰기 ----------
function nowIso(): string {
  // 파이썬 datetime.now(timezone.utc).isoformat(timespec="seconds") 와 같은 모양
  return new Date().toISOString().slice(0, 19) + "+00:00";
}

async function nextRevision(table: Table, entryId: string): Promise<number> {
  const mine = await rows(table, { entry_id: entryId });
  return Math.max(0, ...mine.map((r) => Number(r.revision) || 0)) + 1;
}

/** 새 등록 또는 수정. 늘 새 행이 쌓인다 (storage.append) */
export async function append(
  table: Table,
  payload: Row,
  entryId?: string,
  status: "active" | "deleted" = "active",
): Promise<Row> {
  const m = mode();
  if (m === "none") throw new StorageWriteError("회원 기능이 아직 설정되지 않았어요 (저장소 연결 없음).");
  const id = entryId || randomUUID().replace(/-/g, "").slice(0, 10);
  const record: Row = {};
  for (const h of HEADERS[table]) record[h] = "";
  Object.assign(record, payload, {
    row_id: randomUUID().replace(/-/g, "").slice(0, 10),
    entry_id: id,
    // 새 글(번호를 새로 만든 것)은 revision 이 늘 1 — DB 를 다시 읽지 않는다 (11/20 리뷰 등록 속도)
    revision: entryId ? await nextRevision(table, id) : 1,
    status,
    updated_at: nowIso(),
  });
  if (m === "local") {
    const own = await readLocalOwn(table);
    own.push(record);
    await writeLocal(table, own);
    return record;
  }
  const { root, headers } = sb();
  let res: Response;
  try {
    res = await fetch(`${root}/rest/v1/${table}`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json", Prefer: "return=minimal" },
      body: JSON.stringify([toDb(table, record)]),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new StorageWriteError("저장하지 못했어요 (연결 실패). 잠시 뒤 다시 시도해 주세요.");
  }
  if (![200, 201, 204].includes(res.status)) {
    // RLS(남의 리뷰 수정) · 민감정보 검사 · revision 충돌이 여기로 온다. 자세한 내용은 서버 기록에만
    console.error(`[store] ${table} 저장 거부 ${res.status}: ${(await res.text()).slice(0, 300)}`);
    throw new StorageWriteError("저장하지 못했어요. 잠시 뒤 다시 시도해 주세요.");
  }
  return record;
}

/** 여러 행을 한 번에 쌓는다 (11/20 블로그 후기 속도: 글마다 번호 읽기 + 저장으로 왕복이 글 수 × 2번이었다).
 *  번호(revision)는 scope 로 좁힌 표를 한 번만 읽어(또는 known 으로 받아) 매기고, 저장도 한 번에 보낸다. 묶음 저장이 거부되면
 *  (한 행의 민감정보 · 번호 충돌 등) 한 행씩 append 로 다시 쌓아 나머지는 살린다. 쌓은 행을 돌려준다 */
export async function appendMany(
  table: Table,
  items: { payload: Row; entryId: string }[],
  scope: Record<string, string> = {},
  known?: Row[],
): Promise<Row[]> {
  const m = mode();
  if (m === "none") throw new StorageWriteError("회원 기능이 아직 설정되지 않았어요 (저장소 연결 없음).");
  if (!items.length) return [];
  const top = new Map<string, number>();
  // known: 부르는 쪽이 방금 읽은 같은 범위의 행 (있으면 다시 읽지 않는다). 번호가 겹치면 DB 가 거부 → 아래 한 행씩
  for (const r of known ?? (await rows(table, scope))) {
    const k = String(r.entry_id);
    top.set(k, Math.max(top.get(k) ?? 0, Number(r.revision) || 0));
  }
  const records: Row[] = items.map(({ payload, entryId }) => {
    const record: Row = {};
    for (const h of HEADERS[table]) record[h] = "";
    const revision = (top.get(entryId) ?? 0) + 1;
    top.set(entryId, revision);
    return Object.assign(record, payload, {
      row_id: randomUUID().replace(/-/g, "").slice(0, 10),
      entry_id: entryId,
      revision,
      status: "active",
      updated_at: nowIso(),
    });
  });
  if (m === "local") {
    const own = await readLocalOwn(table);
    own.push(...records);
    await writeLocal(table, own);
    return records;
  }
  const { root, headers } = sb();
  try {
    const res = await fetch(`${root}/rest/v1/${table}`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json", Prefer: "return=minimal" },
      body: JSON.stringify(records.map((r) => toDb(table, r))),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    if ([200, 201, 204].includes(res.status)) return records;
    console.error(`[store] ${table} 묶음 저장 거부 ${res.status}: ${(await res.text()).slice(0, 300)}`);
  } catch {
    /* 아래에서 한 행씩 */
  }
  const ok: Row[] = [];
  for (const { payload, entryId } of items) {
    try {
      ok.push(await append(table, payload, entryId));
    } catch {
      /* 한 행을 못 쌓아도 나머지는 계속 */
    }
  }
  return ok;
}

/** Supabase DB 함수 부르기 (아이디 로그인 · 탈퇴 정리). local 모드는 부르는 쪽이 따로 처리한다 */
export async function rpc<T>(name: string, params: Record<string, string>): Promise<T> {
  const { root, headers } = sb();
  let res: Response;
  try {
    res = await fetch(`${root}/rest/v1/rpc/${name}`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(params),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new StorageWriteError("서버에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.");
  }
  if (res.status >= 400) throw new StorageWriteError("요청을 처리하지 못했어요. 입력을 확인해 주세요.");
  return (await res.json()) as T;
}
