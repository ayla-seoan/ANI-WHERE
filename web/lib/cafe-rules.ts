// 팝업 등록·수정하기 규칙 (서버·브라우저가 같이 쓴다) — common/cafe.py · dates.py · guard.validate_cafe ·
// images.py 상수 · notice.possible_duplicates 를 옮긴 것. 화면 문구도 앱(app_cafemap.py)과 같다.
import { scan } from "./guard";

// ---- cafe.py ----
/** 등록 화면의 '이벤트 추가 정보' 항목 (cafe.EVENT_TAGS) */
export const EVENT_TAGS = ["사전 예약", "럭키 드로우", "가챠", "미성년자 입장불가", "포토부스", "스탬프 투어", "랜덤 특전"];
/** 기간 표시용 (dates.py): 이벤트 칩이 아니라 기간 옆 표시 */
export const PERIOD_TAGS = ["상시", "기간 확인 필요"];
export const MAX_LINKS = 5;
export const MAX_INTRO = 3000;

// ---- dates.py ----
export const ALWAYS_END = "2099-12-31";
export const TAG_ALWAYS = "상시";
export const TAG_CHECK = "기간 확인 필요";
export const RAW_MARK = "기간원문:";

// ---- images.py ----
export const IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "gif"];
export const IMAGE_ACCEPT = ".png,.jpg,.jpeg,.webp,.gif,image/png,image/jpeg,image/webp,image/gif";
export const POSTER_MB = 20;
export const EXTRA_MB = 10;
export const MAX_EXTRAS = 10;
export const tooBig = (size: number, mb: number) => size > mb * 1024 * 1024;

/** 쉼표로 나눈 목록 (앱 _split) */
export function split(text: unknown): string[] {
  return String(text ?? "")
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
}

/** images 칸 → 파일 이름(또는 주소) 목록 (images.split) */
export const splitImages = split;

export function isAlways(end: unknown): boolean {
  return String(end ?? "").slice(0, 10) === ALWAYS_END;
}

/** note 칸의 '| 기간원문:<원문>' 에서 원문만 (dates.raw_from_note) */
export function rawFromNote(note: unknown): string {
  const text = String(note ?? "");
  const i = text.indexOf(RAW_MARK);
  if (i < 0) return "";
  return text.slice(i + RAW_MARK.length).split("|", 1)[0].trim();
}

/** 참고 웹사이트 입력 → [쓸 수 있는 주소들, 잘못된 값들] (cafe.parse_links) */
export function parseLinks(text: unknown): [string[], string[]] {
  const good: string[] = [];
  const bad: string[] = [];
  const seen = new Set<string>();
  for (const part of String(text ?? "").trim().split(/[\s,]+/)) {
    if (!part) continue;
    if (/^https?:\/\/[^\s/$.?#][^\s]*$/i.test(part)) {
      const rest = part.replace(/^https?:\/\/(www\.)?/i, "");
      const slash = rest.indexOf("/");
      const host = slash < 0 ? rest : rest.slice(0, slash);
      const path = slash < 0 ? "" : rest.slice(slash + 1);
      const key = `${host.toLowerCase()}/${path}`.replace(/\/+$/, "");
      if (!seen.has(key)) {
        seen.add(key);
        good.push(part);
      }
    } else bad.push(part);
  }
  return [good, bad];
}

const AGGREGATOR_HOSTS = ["recal.kr"];
/** 참고 웹사이트 순서: recal.kr 같은 모음 사이트는 맨 뒤로 (cafe.order_links) */
export function orderLinks(links: string[]): string[] {
  const agg = (u: string) => {
    const host = u.replace(/^https?:\/\/(www\.)?/i, "").split("/")[0].toLowerCase();
    return AGGREGATOR_HOSTS.some((h) => host === h || host.endsWith("." + h));
  };
  return [...links.filter((u) => !agg(u)), ...links.filter(agg)];
}

/** 링크에 보여 줄 짧은 이름 (앱 _site_name) */
export function siteName(url: string): string {
  const host = url.replace(/^https?:\/\/(www\.)?/i, "").split("/")[0];
  return host || url;
}

function hasBatchim(label: string): boolean {
  const last = label.slice(-1);
  const c = last.charCodeAt(0);
  return c >= 0xac00 && c <= 0xd7a3 && (c - 0xac00) % 28 !== 0;
}

/** '(카페명)을 입력해주세요' — 받침에 따라 을/를 (앱 _ask) */
export function askPh(label: string): string {
  return `(${label})${hasBatchim(label) ? "을" : "를"} 입력해주세요`;
}

/** 목록 끝 글자 받침 → 을/를 (앱 _quick_report) */
export const objJosa = (word: string) => (hasBatchim(word) ? "을" : "를");

export function addDays(ymd: string, n: number): string {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}

export function daysBetween(a: string, b: string): number {
  const t = (s: string) => {
    const [y, m, d] = s.split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  };
  return Math.round((t(b) - t(a)) / 86400000);
}

export const validYmd = (s: unknown) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(s ?? ""));
  if (!m) return false;
  const dt = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return dt.getUTCMonth() === +m[2] - 1 && dt.getUTCDate() === +m[3];
};

// ---- schema.CafeEntry · guard.validate_cafe ----
export type CafeEntry = {
  cafe_name: string;
  work: string;
  characters: string[];
  address: string;
  start_date: string; // YYYY-MM-DD
  end_date: string;
  perks: string[];
  goods: string[];
  confidence: "high" | "low";
};
export type Validation = { ok: boolean; errors: string[]; warnings: string[] };
export type ExistingRow = { cafe_name: string; address: string; work: string; status?: string; start_date?: string; end_date?: string };

/** 지도에 올려도 되는 등록 건인지 (guard.validate_cafe) */
export function validateCafe(entry: CafeEntry, today: string, existing: ExistingRow[] = []): Validation {
  const v: Validation = { ok: true, errors: [], warnings: [] };
  const fail = (m: string) => {
    v.ok = false;
    v.errors.push(m);
  };
  if (!entry.cafe_name.trim()) fail("카페명이 비어 있습니다.");
  if (!entry.address.trim()) fail("주소가 없으면 지도에 표시할 수 없습니다.");
  if (entry.end_date < entry.start_date) fail("종료일이 시작일보다 빠릅니다.");
  if (entry.end_date < today) fail(`이미 끝난 일정입니다 (종료 ${entry.end_date}).`);
  if (daysBetween(entry.start_date, entry.end_date) > 90 && entry.end_date !== ALWAYS_END)
    v.warnings.push("기간이 90일을 넘습니다. 날짜를 잘못 읽었을 수 있습니다.");
  const blob = [entry.cafe_name, entry.work, ...entry.characters, entry.address, ...entry.perks, ...entry.goods].join(" ");
  for (const f of scan(blob)) fail(`${f.kind}로 보이는 값이 들어 있어 저장하지 않습니다.`);
  for (const row of existing) {
    if (
      row.cafe_name === entry.cafe_name &&
      row.address === entry.address &&
      String(row.work || "").trim() === entry.work.trim() &&
      row.status !== "deleted"
    ) {
      fail("같은 카페·주소에 같은 작품이 이미 등록되어 있습니다.");
      break;
    }
  }
  if (entry.confidence === "low") v.warnings.push("원문에 정보가 흐릿합니다. 저장 전에 직접 확인해 주세요.");
  return v;
}

/** 입력값 속 민감정보 종류 → 앱 _block_sensitive 문구 (없으면 '') */
export function blockSensitive(...texts: string[]): string {
  const kinds = [...new Set(scan(texts.map((t) => String(t ?? "")).join(" ")).map((f) => f.kind))].sort();
  return kinds.length
    ? `민감한 개인정보(${kinds.join(", ")})는 입력할 수 없습니다. 해당 내용을 지우고 다시 입력해 주세요.`
    : "";
}

/** 참고 웹사이트 칸 오류 (앱 _links_field) */
export function linksErrors(text: string): { links: string[]; errors: string[] } {
  const [links, bad] = parseLinks(text);
  const errors: string[] = [];
  if (bad.length) errors.push("웹사이트 주소는 http:// 또는 https:// 로 시작해야 해요: " + bad.slice(0, 3).join(", "));
  if (links.length > MAX_LINKS) errors.push(`참고 웹사이트는 ${MAX_LINKS}개까지 넣을 수 있어요.`);
  return { links, errors };
}

// ---- notice.possible_duplicates ----
function norm(s: unknown): string {
  const t = String(s ?? "")
    .toLowerCase()
    .replace(/[\s·:!?~\-–()]/g, "");
  return t.replace(/(점|지점|카페|cafe)$/, "");
}

/** 작품 + 장소(카페명, 없으면 지역) + 기간이 모두 같은 행 (notice.possible_duplicates) */
export function possibleDuplicates(
  result: { work: string; cafe_name: string; area?: string | null; start_date: string; end_date: string },
  rows: ExistingRow[],
): ExistingRow[] {
  if (!(result.work && result.start_date && result.end_date)) return [];
  const place = norm(result.cafe_name || result.area);
  return rows.filter((r) => {
    const samePlace = !!place && (place === norm(r.cafe_name) || norm(r.address).includes(place));
    return (
      norm(r.work) === norm(result.work) &&
      samePlace &&
      String(r.start_date || "").slice(0, 10) === result.start_date &&
      String(r.end_date || "").slice(0, 10) === result.end_date
    );
  });
}

/** 주소 검색·우편번호로 고른 주소 (앱 _picked) */
export type Picked = { address: string; lat: number; lng: number; source: string; precision: string };
