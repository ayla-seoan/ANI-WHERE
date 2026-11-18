import "server-only";
import catalogData from "./catalog.json";
import { mask } from "@/lib/guard";
import {
  EVENT_TAGS,
  isAlways,
  MAX_INTRO,
  MAX_LINKS,
  PERIOD_TAGS,
  RAW_MARK,
  rawFromNote,
  siteName,
  split,
  splitImages,
  TAG_CHECK,
  type CafeEntry,
  type ExistingRow,
} from "@/lib/cafe-rules";
import { authorMap } from "./member";
import { current, rows, type Row } from "./store";

// 팝업(cafes) 쓰기 쪽 규칙 — common/catalog.py · cafe.entry_to_row · app_cafemap.py 의 _characters_by_work ·
// _keep_notion · 수정 이력(_history_card_html · _SOURCE_VIEW · _HISTORY_FIELDS · _image_changes · _editor) 을 옮긴 것.

type Work = { work: string; characters?: string[]; aliases?: string[]; character_aliases?: Record<string, string[]> };
const WORKS = catalogData as Work[];

// ---------------- catalog.py ----------------
export function catalogByWork(): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const w of WORKS) out[w.work] = [...(w.characters || [])];
  return out;
}

/** 작품 → 공지에서 찾을 이름들 (catalog.work_aliases) */
export function workAliases(): [string, string[]][] {
  return WORKS.map((w) => {
    const name = w.work;
    const base = name.replace(/\s*\(.*?\)\s*$/, "");
    const names = [name, base, base.replace(/[!?！？]+$/, "")];
    for (const m of name.matchAll(/\((.*?)\)/g)) names.push(m[1].trim());
    names.push(...(w.aliases || []));
    return [name, [...new Set(names.filter(Boolean))]];
  });
}

/** 그 작품의 캐릭터 이름(별칭 포함) → 목록의 이름 (catalog.character_aliases) */
export function characterAliases(work: string): Record<string, string> {
  const w = WORKS.find((x) => x.work === work);
  if (!w) return {};
  const out: Record<string, string> = {};
  for (const c of w.characters || []) out[c] = c;
  for (const [full, shorts] of Object.entries(w.character_aliases || {})) for (const s of shorts) out[s] = full;
  return out;
}

const key = (name: string) => name.replace(/[\s!?·:]+/g, "").toLowerCase();
/** '귀멸의칼날' 처럼 띄어쓰기만 다른 이름을 목록의 이름으로 (catalog.canonical_work) */
export function canonicalWork(name: string): string {
  const k = key(name);
  return WORKS.find((w) => key(w.work) === k)?.work ?? name.trim();
}

// ---------------- 읽기 ----------------
/** 지금 지도에 있는 팝업 기록 (storage.current_rows) */
export async function currentCafes(): Promise<Row[]> {
  return current(await rows("cafes"));
}

/** 작품별 캐릭터 목록: 작품 목록 + 이미 등록된 카페에서 쓰인 이름 (앱 _characters_by_work) */
export function charactersByWork(cur: Row[]): Record<string, string[]> {
  const found = catalogByWork();
  for (const r of cur) {
    const work = canonicalWork(String(r.work || ""));
    if (!work) continue;
    const chars = (found[work] ||= []);
    for (const c of split(r.characters)) if (!chars.some((x) => c === x || x.includes(c))) chars.push(c);
  }
  return found;
}

/** 중복 확인용으로 브라우저에 넘길 칸만 */
export function existingLite(cur: Row[]): ExistingRow[] {
  return cur.map((r) => ({
    cafe_name: String(r.cafe_name || ""),
    address: String(r.address || ""),
    work: String(r.work || ""),
    status: String(r.status || ""),
    start_date: String(r.start_date || "").slice(0, 10),
    end_date: String(r.end_date || "").slice(0, 10),
  }));
}

/** 한 팝업의 모든 기록 (revision 오름차순) */
export async function cafeHistory(entryId: string): Promise<Row[]> {
  return (await rows("cafes", { entry_id: entryId })).sort((a, b) => Number(a.revision) - Number(b.revision));
}

// ---------------- 쓰기 모양 ----------------
/** cafe.entry_to_row */
export function entryToRow(
  entry: CafeEntry,
  lat: number | null,
  lng: number | null,
  o: {
    source?: string;
    note?: string;
    images?: string[];
    tags?: string[];
    links?: string[];
    editor?: string;
    intro?: string;
    introSrc?: string;
  } = {},
): Row {
  const introSrc = (o.introSrc || "").trim();
  const round6 = (x: number) => Math.round(x * 1e6) / 1e6;
  return {
    intro_src: /^https?:\/\//.test(introSrc) ? introSrc.slice(0, 500) : "",
    editor: [...(o.editor || "")].slice(0, 40).join(""),
    intro: [...mask((o.intro || "").trim())].slice(0, MAX_INTRO).join(""),
    links: (o.links || []).slice(0, MAX_LINKS).join(" "),
    images: (o.images || []).join(", "),
    tags: (o.tags || []).filter((t) => [...EVENT_TAGS, ...PERIOD_TAGS].includes(t)).join(", "),
    cafe_name: entry.cafe_name,
    work: entry.work,
    characters: entry.characters.join(", "),
    address: entry.address,
    lat: lat === null ? "" : round6(lat),
    lng: lng === null ? "" : round6(lng),
    start_date: entry.start_date,
    end_date: entry.end_date,
    perks: entry.perks.join(", "),
    goods: entry.goods.join(", "),
    source: (o.source || "").slice(0, 200),
    note: (o.note || "").slice(0, 200),
  };
}

/** 고쳐 저장해도 Notion 표시('| notion:…')와 기간 원문은 남긴다 (앱 _keep_notion) */
export function keepNotion(note: string, cur: Row): string {
  const m = /\|\s*notion:\S+/.exec(String(cur.note || ""));
  const out = m ? `${note} ${m[0]}` : note;
  const raw = rawFromNote(cur.note);
  return raw ? `${out} | ${RAW_MARK}${raw}` : out;
}

// ---------------- 수정 이력 ----------------
const SOURCE_VIEW: Record<string, [string, string]> = {
  "노션 자동 수집": ["AI 자동 수집", "auto_awesome"],
  "AI 자동 수집": ["AI 자동 수집", "auto_awesome"],
  "직접 등록": ["직접 등록", "add_circle"],
  "직접 수정": ["직접 수정", "edit"],
  "간편 등록": ["간편 등록", "edit_note"],
  붙여넣기: ["붙여넣기", "content_paste"],
  되돌리기: ["되돌리기", "undo"],
  "지도에서 내림": ["지도에서 내림", "visibility_off"],
  "기간 종료": ["기간 종료", "event_busy"],
  샘플: ["샘플", "science"],
};
const HISTORY_FIELDS: [string, string][] = [
  ["status", "상태"],
  ["cafe_name", "카페명"],
  ["work", "작품"],
  ["characters", "캐릭터"],
  ["address", "주소"],
  ["start_date", "시작일"],
  ["end_date", "종료일"],
  ["perks", "특전"],
  ["goods", "굿즈"],
  ["tags", "이벤트"],
  ["images", "사진"],
  ["links", "참고 웹사이트"],
  ["intro", "팝업 소개"],
  ["intro_src", "소개 출처"],
];

/** 기록을 남긴 사람. editor 칸이 생기기 전 기록은 방법으로 짐작 (앱 _editor) */
function editorOf(r: Row): string {
  const who = String(r.editor || "").trim();
  if (who) return who;
  return ({ "노션 자동 수집": "AI", "AI 자동 수집": "AI", 샘플: "샘플" } as Record<string, string>)[String(r.source || "")] || "닉네임 기록 전";
}

function historyValue(col: string, value: unknown): string {
  const text = String(value ?? "").trim();
  if (col === "status") return ({ active: "지도에 표시", deleted: "지도에서 내림" } as Record<string, string>)[text] || text || "없음";
  if (!text) return "없음";
  if (col === "images") return `${text.split(",").filter((x) => x.trim()).length}장`;
  if (col === "links") return text.split(/\s+/).filter(Boolean).map(siteName).join(", ");
  if (col === "start_date" || col === "end_date") return text.slice(0, 10).replace(/-/g, ".");
  return [...text].length <= 60 ? text : [...text].slice(0, 60).join("") + "…";
}

export type ImgChange = { what: "포스터" | "이미지"; kind: "add" | "del" | "chg"; text: string };
/** 사진 칸이 어떻게 바뀌었는지 (앱 _image_changes). 첫 장이 포스터 */
function imageChanges(oldV: unknown, newV: unknown): ImgChange[] {
  const before = splitImages(oldV);
  const after = splitImages(newV);
  const p0 = before[0] || "";
  const p1 = after[0] || "";
  const out: ImgChange[] = [];
  if (p0 !== p1) {
    if (p0 && (!p1 || (before.includes(p1) && !after.includes(p0)))) out.push({ what: "포스터", kind: "del", text: "포스터 삭제" });
    else if (p1 && !p0) out.push({ what: "포스터", kind: "add", text: "포스터 추가" });
    else out.push({ what: "포스터", kind: "chg", text: "포스터 변경" });
  }
  const moved = new Set([p0, p1].filter(Boolean));
  const gone = before.slice(1).filter((x) => !after.includes(x) && !moved.has(x));
  const came = after.slice(1).filter((x) => !before.includes(x) && !moved.has(x));
  if (gone.length) out.push({ what: "이미지", kind: "del", text: `이미지 ${gone.length}장 삭제` });
  if (came.length) out.push({ what: "이미지", kind: "add", text: `이미지 ${came.length}장 추가` });
  if (!out.length) out.push({ what: "이미지", kind: "chg", text: "이미지 순서 변경" });
  return out;
}

function kstStamp(iso: string): string {
  const t = Date.parse(iso);
  if (!t) return "";
  const k = new Date(t + 9 * 3600_000);
  const two = (n: number) => String(n).padStart(2, "0");
  return `${k.getUTCFullYear()}.${two(k.getUTCMonth() + 1)}.${two(k.getUTCDate())} ${two(k.getUTCHours())}:${two(k.getUTCMinutes())}`;
}

/** 기간 글자 (앱 _period, fmt=%Y.%m.%d) */
function periodOf(r: Row): string {
  if (split(r.tags).includes(TAG_CHECK)) {
    const raw = rawFromNote(r.note);
    return "기간 확인 필요" + (raw && !raw.startsWith("(") ? ` · 원문 '${raw}'` : "");
  }
  const day = (v: unknown) => (/^\d{4}-\d{2}-\d{2}/.test(String(v ?? "")) ? String(v).slice(0, 10).replace(/-/g, ".") : "");
  const s = day(r.start_date);
  const e = day(r.end_date);
  if (!s) return "기간 확인 필요";
  if (!e || isAlways(r.end_date)) return `${s} ~ 상시`;
  return `${s} ~ ${e}`;
}

export type HistoryDiff = { k: string; old?: string; new?: string; act?: ImgChange };
export type HistoryCard = {
  revision: number;
  when: string;
  now: boolean;
  label: string;
  icon: string;
  who: string;
  first: { cafe: string; work: string; period: string; address: string } | null;
  diffs: HistoryDiff[];
  canRestore: boolean;
};

/** 수정 이력 카드들 (최근 것이 위). 처음 기록만 카페·기간·주소를 다 보여 주고, 그다음부터는 바뀐 칸만 */
export async function historyCards(all: Row[]): Promise<HistoryCard[]> {
  const author = await authorMap();
  const hist = [...all].sort((a, b) => Number(b.revision) - Number(a.revision));
  return hist.map((r, i) => {
    const older = hist[i + 1];
    const source = String(r.source || "");
    const [label, icon] =
      SOURCE_VIEW[source] || [source || "기록", source.endsWith("되돌리기") ? "undo" : "history"];
    let diffs: HistoryDiff[] = [];
    if (older) {
      for (const [col, name] of HISTORY_FIELDS) {
        if (String(r[col] ?? "") === String(older[col] ?? "")) continue;
        if (col === "images") {
          diffs = diffs.concat(imageChanges(older[col], r[col]).map((c) => ({ k: c.what, act: c })));
          continue;
        }
        diffs.push({ k: name, old: historyValue(col, older[col]), new: historyValue(col, r[col]) });
      }
    }
    return {
      revision: Number(r.revision),
      when: kstStamp(String(r.updated_at || "")),
      now: i === 0,
      label,
      icon,
      who: author(editorOf(r)).name,
      first: older
        ? null
        : {
            cafe: String(r.cafe_name || "-") || "-",
            work: String(r.work || "-") || "-",
            period: periodOf(r),
            address: String(r.address || "-") || "-",
          },
      diffs,
      canRestore: i > 0 && r.status !== "deleted",
    };
  });
}
