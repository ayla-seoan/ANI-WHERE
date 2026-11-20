import "server-only";
import { scan } from "../guard";
import { addDays, mondayOf } from "../popup";
import { displayName } from "./auth";
import type { Me } from "./session";
import { append, current, latest, rows, type Row } from "./store";
import { imgUrl } from "../uploads";

// 관리자 대시보드 · 삭제 요청 · 알림 · 접속 기록 — common/admin.py 를 옮긴 것 (화면과 상관없는 계산만).
// 저장소는 모두 append-only 다. 처리·수정·삭제도 새 행을 쌓는다 (store.append 만 쓴다).
//  - del_requests : 일반 회원의 게시글 삭제 요청 → 관리자가 승인/거부
//  - notices      : 회원에게 가는 알림 (target = 회원 번호, 또는 'all' = 전체 공지)
//  - visits       : 회원이 접속한 날 (회원 번호 × 날짜 1행)

export const TARGET_LABEL: Record<string, string> = { review: "리뷰", cafe: "팝업" };
export const MAX_REASON = 300;
export type TargetType = "cafe" | "review";

const tidy = (s: unknown) => String(s ?? "").split(/\s+/).filter(Boolean).join(" ");

/** 'YYYY-MM-DD' 로 읽히는 날짜면 그대로, 아니면 '' (mycal._day) */
export function ymdOf(v: unknown): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v ?? ""));
  if (!m) return "";
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return d.getUTCMonth() === Number(m[2]) - 1 ? d.toISOString().slice(0, 10) : "";
}

/** admin._day: 날짜 칸('2026-11-18') 또는 기록 시각(updated_at). 시간대가 있는 시각은 한국 시간 날짜로 */
export function kstDay(v: unknown): string {
  const text = String(v ?? "");
  if (text.includes("T") && /(Z|[+-]\d{2}:?\d{2})$/.test(text)) {
    const t = Date.parse(text);
    if (Number.isFinite(t)) return new Date(t + 9 * 3600_000).toISOString().slice(0, 10);
  }
  return ymdOf(text.slice(0, 10));
}

/** 그 날이 든 주의 월요일 */
export const weekOf = (ymd: string) => mondayOf(ymd);

const WD = "월화수목금토일";
/** '11/18(화)' */
export function dayLabel(ymd: string): string {
  const [, m, d] = ymd.split("-").map(Number);
  const dow = (new Date(`${ymd}T00:00:00Z`).getUTCDay() + 6) % 7;
  return `${m}/${d}(${WD[dow]})`;
}

/** 앱 _when: 기록 시각 → 한국 시간 '11/18 14:05' */
export function whenText(stamp: unknown): string {
  const t = Date.parse(String(stamp ?? ""));
  if (!Number.isFinite(t)) return "";
  const k = new Date(t + 9 * 3600_000).toISOString();
  return `${k.slice(5, 7)}/${k.slice(8, 10)} ${k.slice(11, 16)}`;
}

/** 카드에 쓸 포스터 주소 (앱 _poster_url · lib/data.ts 와 같은 규칙). 없으면 기본 그림 */
export function posterOf(images: unknown): string {
  for (const raw of String(images ?? "").split(/[\s,]+/)) {
    const name = raw.trim();
    if (!name) continue;
    if (/^https:\/\/[^\s"'<>]+$/i.test(name)) return name;
    if (/^\/uploads\/[0-9a-f]{12}\.(png|jpe?g|webp|gif)$/.test(name) && process.env.WEB_STORAGE === "local") return name;
    if (/^[\w.-]+\.(png|jpe?g|webp|gif|avif)$/i.test(name))
      return imgUrl(name);
  }
  return "/default_poster.webp";
}

/** 앱 _period(fmt=MM-DD, show_raw=False): '11-20 ~ 12-03' · '11-20 ~ 상시' · '기간 확인 필요' */
export function periodMD(r: Row): string {
  const tags = String(r.tags || "").split(",").map((t) => t.trim());
  if (tags.includes("기간 확인 필요")) return "기간 확인 필요";
  const s = ymdOf(r.start_date);
  const e = ymdOf(r.end_date);
  if (!s) return "기간 확인 필요";
  if (!e || e === "2099-12-31") return `${s.slice(5)} ~ 상시`;
  return `${s.slice(5)} ~ ${e.slice(5)}`;
}

/** 관리자가 내린 것은 빼고, 기간이 끝나 내려간 것은 센다 */
const shown = (r: Row) => !(r.status === "deleted" && r.source !== "기간 종료");

// ------------------------------------------------------------------ 팝업 현황 (주 단위 칸반)
export const BOARD_COLS = ["새로 생성", "예정", "진행", "종료"] as const;
export type Board = Record<(typeof BOARD_COLS)[number], Row[]>;

/** admin.popup_board: 고른 주(월~일) 기준 네 칸 */
export function popupBoard(allRows: Row[], mon: string): Board {
  const sun = addDays(mon, 6);
  const firstSeen = new Map<string, string>();
  for (const r of allRows) {
    const d = kstDay(r.updated_at);
    const id = String(r.entry_id);
    if (d && (!firstSeen.has(id) || d < firstSeen.get(id)!)) firstSeen.set(id, d);
  }
  const board: Board = { "새로 생성": [], 예정: [], 진행: [], 종료: [] };
  for (const r of latest(allRows)) {
    if (!shown(r)) continue;
    const id = String(r.entry_id);
    const s = ymdOf(r.start_date);
    const e = ymdOf(r.end_date);
    const fs = firstSeen.get(id);
    if (fs && mon <= fs && fs <= sun) board["새로 생성"].push(r);
    if (!(s && e)) continue;
    if (sun < s && s <= addDays(sun, 28)) board["예정"].push(r);
    else if (mon <= e && e <= sun) board["종료"].push(r);
    else if (s <= sun && e > sun) board["진행"].push(r);
  }
  for (const k of BOARD_COLS) board[k].sort((a, b) => String(a.start_date || "").localeCompare(String(b.start_date || "")));
  return board;
}

/** admin.gantt_rows: [start, end] 기간에 걸친 팝업 (기간 종료로 내려간 것 포함, 관리자 삭제 제외), 시작일 순 */
export function ganttRows(allRows: Row[], start: string, end: string, limit = 60): Row[] {
  const out = latest(allRows).filter((r) => {
    if (!shown(r)) return false;
    const s = ymdOf(r.start_date);
    const e = ymdOf(r.end_date);
    return !!(s && e && s <= end && e >= start);
  });
  out.sort(
    (a, b) =>
      String(a.start_date || "").localeCompare(String(b.start_date || "")) ||
      String(a.end_date || "").localeCompare(String(b.end_date || "")),
  );
  return out.slice(0, limit);
}

// ------------------------------------------------------------------ 이용 지표
export type MemberEvent = { day: string; event: "가입" | "탈퇴" };

/** admin.member_events: 회원 가입(revision 1)·탈퇴(status deleted) 날짜 */
export function memberEvents(memberRows: Row[]): MemberEvent[] {
  const out: MemberEvent[] = [];
  for (const r of memberRows) {
    const d = kstDay(r.updated_at);
    if (!d) continue;
    if (Number(r.revision || 0) === 1) out.push({ day: d, event: "가입" });
    if (r.status === "deleted") out.push({ day: d, event: "탈퇴" });
  }
  return out;
}

export type DayCount = { label: string; n: number };

/** admin.weekly_counts: 최근 weeks 주의 주별 수 ('11/10 주') */
export function weeklyCounts(events: MemberEvent[], event: string, today: string, weeks = 8): DayCount[] {
  const monNow = weekOf(today);
  const out: DayCount[] = [];
  for (let i = weeks - 1; i >= 0; i--) {
    const mon = addDays(monNow, -7 * i);
    const sun = addDays(mon, 6);
    const [, m, d] = mon.split("-").map(Number);
    out.push({ label: `${m}/${d} 주`, n: events.filter((e) => e.event === event && e.day >= mon && e.day <= sun).length });
  }
  return out;
}

/** admin.daily_events: 고른 주의 요일별 가입·탈퇴 수 */
export function dailyEvents(events: MemberEvent[], event: string, mon: string): DayCount[] {
  return Array.from({ length: 7 }, (_, i) => {
    const d = addDays(mon, i);
    return { label: dayLabel(d), n: events.filter((e) => e.event === event && e.day === d).length };
  });
}

/** admin.daily_active: 고른 주의 요일별 접속 회원 수 (같은 날 여러 번 와도 1명) */
export function dailyActive(visitRows: Row[], mon: string): DayCount[] {
  const seen = new Map<string, Set<string>>();
  for (let i = 0; i < 7; i++) seen.set(addDays(mon, i), new Set());
  for (const r of visitRows) {
    const d = kstDay(r.day);
    seen.get(d)?.add(String(r.member));
  }
  return [...seen.entries()].map(([d, s]) => ({ label: dayLabel(d), n: s.size }));
}

/** admin.last_visit: 회원 번호 → 마지막 접속 날 */
export function lastVisit(visitRows: Row[]): Map<string, string> {
  const out = new Map<string, string>();
  for (const r of visitRows) {
    const m = String(r.member);
    const d = String(r.day || "");
    if (d > (out.get(m) || "")) out.set(m, d);
  }
  return out;
}

// ------------------------------------------------------------------ 삭제 요청
/** admin.validate_reason */
export function validateReason(reason: string): string[] {
  const r = tidy(reason);
  const errors: string[] = [];
  if ([...r].length < 5) errors.push("삭제를 요청하는 이유를 5자 이상 적어 주세요.");
  if ([...r].length > MAX_REASON) errors.push(`이유는 ${MAX_REASON}자까지 적을 수 있어요.`);
  if (scan(r).length) errors.push("이유에 전화번호·이메일 같은 개인정보는 넣지 말아 주세요.");
  return errors;
}

/** admin.request_delete: 대기(pending) 요청 한 줄. 요청자 이름은 앱 _me() 와 같은 '닉네임#m네 글자' */
export async function requestDelete(
  targetType: TargetType,
  targetId: string,
  title: string,
  reason: string,
  me: Me,
): Promise<Row> {
  return append("del_requests", {
    target_type: targetType,
    target_id: String(targetId),
    target_title: [...String(title)].slice(0, 80).join(""),
    reason: tidy(reason),
    requester: me.key,
    requester_nick: displayName(me.row),
    decision: "pending",
    admin_reason: "",
    decided_at: "",
  });
}

/** 삭제 요청의 지금 상태 (entry_id 별 최신, 지운 것 제외 = del_requests.current_rows) */
export async function requestRows(): Promise<Row[]> {
  return current(await rows("del_requests"));
}

/** admin.pending_for: 같은 사람이 같은 글에 아직 처리 안 된 요청이 있는가 */
export function pendingFor(reqRows: Row[], targetId: string, requester: string): boolean {
  return reqRows.some(
    (r) => String(r.target_id) === String(targetId) && String(r.requester) === requester && r.decision === "pending",
  );
}

/** 오늘 날짜·시각 (파이썬 datetime.now().isoformat(timespec="seconds"), 서버는 한국 시간으로) */
function nowLocal(): string {
  return new Date(Date.now() + 9 * 3600_000).toISOString().slice(0, 19);
}

/** admin.decide: 승인/거부 기록을 쌓고, notify 면 요청한 회원에게 알림. 게시글 삭제는 부르는 쪽이 한다 */
export async function decide(req: Row, approve: boolean, adminReason = "", notify = true): Promise<Row> {
  const payload: Row = {};
  for (const k of [
    "target_type",
    "target_id",
    "target_title",
    "reason",
    "requester",
    "requester_nick",
    "decision",
    "admin_reason",
    "decided_at",
  ])
    payload[k] = req[k] ?? "";
  Object.assign(payload, {
    decision: approve ? "approved" : "rejected",
    admin_reason: tidy(adminReason),
    decided_at: nowLocal(),
  });
  const row = await append("del_requests", payload, String(req.entry_id));
  if (!notify) return row; // 관리자가 이 알림 규칙을 꺼 두었으면 처리 기록만 남긴다
  const what = `${TARGET_LABEL[String(req.target_type)] || "게시글"} '${req.target_title || ""}'`;
  if (approve)
    await send(
      String(req.requester),
      "삭제 승인",
      "삭제 요청이 승인되었어요",
      `요청하신 ${what} 이(가) 승인되어 게시글이 삭제되었습니다.`,
    );
  else
    await send(
      String(req.requester),
      "삭제 거부",
      "삭제 요청이 거부되었어요",
      `요청하신 ${what} 삭제가 거부되었어요. 사유: ${payload.admin_reason || "(사유 없음)"}`,
    );
  return row;
}

/** storage.soft_delete: 지금 행을 그대로 옮겨 '삭제됨' 새 행 (extra 는 이번 기록에만). 이미 없으면 null */
export async function softDelete(table: "cafes" | "reviews" | "notices", entryId: string, extra: Row = {}): Promise<Row | null> {
  const cur = current(await rows(table, { entry_id: String(entryId) }))[0];
  if (!cur) return null;
  const payload: Row = {};
  for (const [k, v] of Object.entries(cur))
    if (!["row_id", "entry_id", "revision", "status", "updated_at"].includes(k)) payload[k] = v;
  Object.assign(payload, extra);
  return append(table, payload, String(entryId), "deleted");
}

// ------------------------------------------------------------------ 알림
/** admin.send: target = 회원 번호 또는 'all' */
export async function send(target: string, kind: string, title: string, body: string, entryId?: string): Promise<Row> {
  return append(
    "notices",
    { target, kind, title: [...title].slice(0, 60).join(""), body: [...body].slice(0, 500).join("") },
    entryId,
  );
}

/** admin.notices_for: 이 회원이 받을 알림 (전체 공지 + 나에게 온 것), 최신순 */
export function noticesFor(noticeRows: Row[], memberKey: string, today: string, days = 60): Row[] {
  const diff = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  return noticeRows
    .filter((r) => {
      if (!["all", memberKey].includes(String(r.target))) return false;
      const d = kstDay(r.updated_at);
      return !(d && diff(d, today) > days);
    })
    .sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
}

/** admin.review_removed: 관리자가 리뷰를 지웠을 때 쓴 회원에게 알림 (사유 포함) */
export async function reviewRemoved(memberKey: string, preview: string, reason: string): Promise<Row> {
  const r = tidy(reason);
  return send(
    memberKey,
    "리뷰 삭제",
    "작성하신 리뷰가 삭제되었어요",
    `리뷰 '${preview}' 이(가) 관리자에 의해 삭제되었어요. 사유: ${r || "(사유 없음)"}`,
  );
}

// ------------------------------------------------------------------ 자동 알림 규칙 (관리자 '알림 관리')
export type RuleDef = {
  name: string;
  when: string;
  who: string;
  where: string;
  days: number | null;
  max_items: number | null;
  why: string;
};
export const RULES: Record<string, RuleDef> = {
  open: {
    name: "북마크한 팝업 오픈",
    when: "오픈 {days}일 전부터 오픈 당일까지 매일",
    who: "그 팝업을 북마크한 회원",
    where: "종 알림 · 내 캘린더 알림 내역",
    days: 3,
    max_items: 8,
    why: "북마크한 팝업이 곧 열려요 (오픈 {days}일 전부터 알려 드려요)",
  },
  end: {
    name: "북마크한 팝업 종료",
    when: "종료 {days}일 전부터 종료 당일까지 매일 (진행 중일 때)",
    who: "그 팝업을 북마크한 회원",
    where: "종 알림 · 내 캘린더 알림 내역",
    days: 3,
    max_items: 8,
    why: "북마크한 팝업이 곧 끝나요 (종료 {days}일 전부터 알려 드려요)",
  },
  near: {
    name: "내 주변 추천",
    when: "위치를 허용했을 때, 지금 열려 있는 가까운 팝업 (북마크한 곳 제외)",
    who: "로그인한 회원",
    where: "종 알림",
    days: null,
    max_items: 3,
    why: "내 위치에서 가까운 곳에 지금 열려 있어요",
  },
  del_ok: {
    name: "삭제 요청 승인",
    when: "관리자가 삭제 요청을 승인하고 게시글이 삭제됐을 때",
    who: "요청한 회원",
    where: "종 알림 · 내 캘린더 알림 내역",
    days: null,
    max_items: null,
    why: "내가 보낸 삭제 요청이 처리됐어요",
  },
  del_no: {
    name: "삭제 요청 거부",
    when: "관리자가 거부 사유를 적어 거부했을 때 (사유 포함)",
    who: "요청한 회원",
    where: "종 알림 · 내 캘린더 알림 내역",
    days: null,
    max_items: null,
    why: "내가 보낸 삭제 요청이 처리됐어요",
  },
  notice: {
    name: "관리자 공지",
    when: "관리자가 공지를 추가·수정했을 때 ({days}일간 종에 보임)",
    who: "모든 회원",
    where: "종 알림 · 내 캘린더 알림 내역",
    days: 14,
    max_items: 5,
    why: "ANI:WHERE 운영 공지예요",
  },
  rv_del: {
    name: "리뷰 삭제 (관리자)",
    when: "관리자가 내 리뷰를 사유를 적어 삭제했을 때 (사유 포함)",
    who: "리뷰를 쓴 회원",
    where: "종 알림 · 내 캘린더 알림 내역",
    days: null,
    max_items: null,
    why: "내가 쓴 리뷰를 관리자가 삭제했어요",
  },
};
export const KIND_RULE: Record<string, string> = {
  공지: "notice",
  "삭제 승인": "del_ok",
  "삭제 거부": "del_no",
  "리뷰 삭제": "rv_del",
};
export type RuleState = { enabled: boolean; days: number | null; max_items: number | null };
export type Rules = Record<string, RuleState>;

/** admin.rule_settings: 기본값 + 관리자가 고친 최신 기록. '삭제'(status=deleted) 한 규칙은 꺼진 것 */
export function ruleSettingsFrom(ruleRows: Row[]): Rules {
  const out: Rules = {};
  for (const [k, v] of Object.entries(RULES)) out[k] = { enabled: true, days: v.days, max_items: v.max_items };
  for (const r of latest(ruleRows)) {
    const k = String(r.entry_id);
    const cur = out[k];
    if (!cur) continue;
    cur.enabled = r.status !== "deleted" && !["0", "false", "False"].includes(String(r.enabled ?? "1") || "1");
    for (const f of ["days", "max_items"] as const) {
      const raw = String(r[f] ?? "").trim();
      if (RULES[k][f] !== null && /^\d+$/.test(raw)) cur[f] = Math.max(0, Number(raw));
    }
  }
  return out;
}

/** 지금 규칙 (표가 아직 없으면 기본값, 앱 _rules) */
export async function ruleSettings(): Promise<Rules> {
  let rs: Row[] = [];
  try {
    rs = await rows("alert_rules");
  } catch {
    rs = [];
  }
  return ruleSettingsFrom(rs);
}

/** admin.save_rule */
export async function saveRule(key: string, enabled: boolean, days: number | null, maxItems: number | null): Promise<Row> {
  const d = RULES[key];
  return append(
    "alert_rules",
    {
      rule: key,
      enabled: enabled ? "1" : "0",
      days: d.days === null || days === null ? "" : String(Math.trunc(days)),
      max_items: d.max_items === null || maxItems === null ? "" : String(Math.trunc(maxItems)),
    },
    key,
  );
}

export type RuleLine = { 알림: string; 상태: string; 언제: string; "최대 개수": string; 누구에게: string; 어디에: string };

/** admin.rules_table */
export function rulesTable(settings: Rules): RuleLine[] {
  const out: RuleLine[] = Object.entries(RULES).map(([k, d]) => {
    const cur = settings[k];
    return {
      알림: d.name,
      상태: cur.enabled ? "켜짐" : "꺼짐",
      언제: d.when.replace("{days}", String(cur.days)),
      "최대 개수": d.max_items === null ? "-" : `${cur.max_items}개`,
      누구에게: d.who,
      어디에: d.where,
    };
  });
  out.push({
    알림: "주간 브리핑 메일",
    상태: "켜짐",
    언제: "매주 월요일 11:00",
    "최대 개수": "-",
    누구에게: "운영자 본인 메일",
    어디에: "메일 (automation/weekly_briefing.gs) — 앱에서 못 고침",
  });
  return out;
}

/** admin.why: 이 알림이 왜 왔는지 한 줄 */
export function why(key: string, settings?: Rules): string {
  const d = RULES[key];
  if (!d) return "";
  const days = settings?.[key]?.days ?? d.days;
  return d.why.replace("{days}", String(days));
}
