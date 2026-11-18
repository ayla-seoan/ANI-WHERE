import "server-only";
import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";

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
};
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
    out[h] = h === "revision" ? Number(v || 0) : v === null || v === undefined ? "" : String(v);
  }
  return out;
}

function toDb(table: Table, r: Row): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  for (const h of HEADERS[table]) {
    const v = r[h];
    out[h] = h === "revision" ? Number(v || 0) : v === null || v === undefined ? "" : String(v);
  }
  return out;
}

// ---------- local ----------
async function readLocal(table: Table): Promise<Row[]> {
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
    revision: await nextRevision(table, id),
    status,
    updated_at: nowIso(),
  });
  if (m === "local") {
    const all = await readLocal(table);
    all.push(record);
    await writeLocal(table, all);
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
