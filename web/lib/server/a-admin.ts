import "server-only";
import { addDays } from "../popup";
import { dayLabel, kstDay, popupBoard, weekOf, whenText, ymdOf } from "./admin";
import { PROVIDER_LABEL } from "./auth";
import { completeness, popups, VISIT_FIELDS } from "./stats";
import { current, HEADERS, latest, type Row, type Table } from "./store";

// 관리자 화면 A안 (11/26, docs/design/admin-handoff) 에서 새로 필요한 조회 — 모두 읽기만 한다.
// 지표 숫자는 stats.ts · admin.ts 의 함수를 그대로 쓰고, 여기서는 그 결과를 화면에 맞게 묶기만 한다.

// ------------------------------------------------------------------ 원본 데이터에 보이는 표 (예전 page.tsx 의 DATA_TABLES)
export const DATA_TABLES: Record<string, string> = {
  cafes: "팝업",
  reviews: "리뷰",
  favorites: "북마크",
  members: "회원",
  del_requests: "삭제 요청",
  notices: "알림",
  visits: "접속",
};
/** 화면 · CSV 에 내보내지 않는 칸 */
export const DATA_HIDE: Record<string, string[]> = { favorites: ["user"] };
export const dataCols = (t: string) => (HEADERS[t] || []).filter((c) => !(DATA_HIDE[t] || []).includes(c));

/** 원본 데이터 표와 같은 걸러내기 · 순서 (찾기 → 지금 내용만 → 최근 쓴 순서) */
export function rawFilter(all: Row[], cols: string[], q: string, onlyNow: boolean): Row[] {
  let list = all;
  const low = q.trim().toLowerCase();
  if (low) list = list.filter((r) => cols.some((c) => String(r[c] ?? "").toLowerCase().includes(low)));
  if (onlyNow) list = latest(list);
  return [...list].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
}

/** CSV 한 칸. 엑셀이 수식으로 읽는 글(= + @ 로 시작)은 앞에 ' 를 붙인다 */
function csvCell(v: unknown): string {
  let s = String(v ?? "");
  if (/^[=+@\t]/.test(s)) s = `'${s}`;
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
export function toCsv(cols: string[], list: Row[]): string {
  return "﻿" + [cols, ...list.map((r) => cols.map((c) => r[c]))].map((line) => line.map(csvCell).join(",")).join("\r\n") + "\r\n";
}

// ------------------------------------------------------------------ 정보 빠진 팝업 (한눈에 보기 '처리할 일' · 간트 '확인')
const VISIT_NAMES = Object.values(VISIT_FIELDS);

/** 이 팝업에서 빠진 '방문 전 정보'. 완결률(stats.completeness)이 빠졌다고 보는 칸을 그대로 쓴다 */
export function missingOf(r: Row): string[] {
  const f = completeness([r]).fields;
  return VISIT_NAMES.filter((n) => !f[n]);
}

export type FixItem = { row: Row; missing: string[] };

/** 지금 보이는(내리지 않은) 팝업 중 아직 끝나지 않았고 방문 전 정보가 빠진 곳. 오래 손대지 않은 순 */
export function needFix(cafeRows: Row[], today: string): FixItem[] {
  const out: FixItem[] = [];
  for (const r of current(cafeRows)) {
    const e = ymdOf(r.end_date);
    if (e && e < today) continue; // 끝난 팝업은 고칠 일이 아니다
    const missing = missingOf(r);
    if (missing.length) out.push({ row: r, missing });
  }
  return out.sort((a, b) => String(a.row.updated_at || "").localeCompare(String(b.row.updated_at || "")));
}

// ------------------------------------------------------------------ 수집 상태 알약
export type Collect = { when: string; day: string; added: number };

/** 가장 최근 자동 수집 기록 (editor = 'AI', notion_sync 가 남김) 의 시각 · 그날 새로 들어온 팝업 수. 기록이 없으면 null */
export function lastCollect(cafeRows: Row[]): Collect | null {
  let last = "";
  for (const r of cafeRows) if (r.editor === "AI" && String(r.updated_at || "") > last) last = String(r.updated_at);
  if (!last) return null;
  const day = kstDay(last);
  const added = cafeRows.filter((r) => r.editor === "AI" && Number(r.revision) === 1 && kstDay(r.updated_at) === day).length;
  return { when: whenText(last), day, added };
}

// ------------------------------------------------------------------ 숫자 카드 (예전 page.tsx 의 _admin_kpis 계산을 그대로 옮김)
export type KpiLists = { new: Row[]; live: Row[]; soon: Row[] };

/** 이번 주 새로 등록 · 진행 중 · 예정 목록. popups()(stats) 기준, 관리자가 내린 것 제외 */
export function kpiLists(cafeRows: Row[], today: string, mon: string): KpiLists {
  const live: Row[] = [];
  const soon: Row[] = [];
  for (const r of popups(cafeRows)) {
    if (r.status === "deleted") continue;
    const s = ymdOf(r.start_date);
    const e = ymdOf(r.end_date);
    if (s && e && s <= today && today <= e) live.push(r);
    else if (s && s > today) soon.push(r);
  }
  return {
    new: popupBoard(cafeRows, mon)["새로 생성"].filter((r) => r.status !== "deleted"),
    live: live.sort((a, b) => String(a.end_date || "").localeCompare(String(b.end_date || ""))),
    soon: soon.sort((a, b) => String(a.start_date || "").localeCompare(String(b.start_date || ""))),
  };
}

// ------------------------------------------------------------------ 이용 지표 '가입 방법'
/** 지금 회원(탈퇴 제외)의 로그인 수단별 수 · 비율 */
export function joinMethods(memberRows: Row[]): { label: string; n: number; pct: number }[] {
  const now = current(memberRows);
  const by = new Map<string, number>();
  for (const r of now) {
    const p = PROVIDER_LABEL[String(r.provider)] || "기타";
    by.set(p, (by.get(p) ?? 0) + 1);
  }
  return [...by.entries()]
    .map(([label, n]) => ({ label, n, pct: now.length ? Math.round((n / now.length) * 100) : 0 }))
    .sort((a, b) => b.n - a.n);
}

// ------------------------------------------------------------------ 알림 관리 '보낸 공지' 상태
/** 회원 종에 지금 보이는 공지인가 (member.inbox 와 같은 규칙: 규칙이 켜져 있고, {days}일 안, 최근 {max}개 안) */
export function noticeShown(list: Row[], rule: { enabled: boolean; days: number | null; max_items: number | null }, today: string) {
  const out = new Map<string, boolean>();
  const diff = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  let n = 0;
  for (const r of [...list].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")))) {
    const d = String(r.updated_at || "").slice(0, 10);
    const ok = rule.enabled && diff(d, today) <= (rule.days ?? 14) && ++n <= (rule.max_items ?? 5);
    out.set(String(r.entry_id), ok);
  }
  return out;
}

/** 다음 월요일 00:10 정리(supabase 012)에서 지워질 팝업 수: 이번 주 일요일까지 끝났거나, 지금 내려가 있는 팝업 */
export function purgeDue(cafeRows: Row[], today: string): { n: number; monday: string } {
  const monday = addDays(weekOf(today), 7);
  const n = latest(cafeRows).filter((r) => {
    const e = ymdOf(r.end_date);
    return (e && e < monday) || r.status === "deleted";
  }).length;
  return { n, monday };
}

// ------------------------------------------------------------------ 최근 활동
export type Feed = { kind: "등록" | "수정" | "내림" | "삭제 요청" | "처리" | "리뷰" | "가입"; text: string; at: string };

export const popName = (r: Row) => `${r.work || ""} · ${r.cafe_name || ""}`.replace(/^[\s·]+|[\s·]+$/g, "") || "(이름 없음)";

/** 저장된 기록(팝업 · 삭제 요청 · 리뷰 · 회원)에서 최근 일을 모은다. 같은 날 같은 종류의 자동 기록은 한 줄로 묶는다 */
export function recentActivity(
  t: { cafes: Row[]; reqs: Row[]; reviews: Row[]; members: Row[] },
  limit = 8,
): Feed[] {
  const out: Feed[] = [];
  const groups = new Map<string, { kind: Feed["kind"]; at: string; n: number; text: (n: number) => string; by?: Map<string, number> }>();
  const group = (key: string, kind: Feed["kind"], at: string, text: (n: number) => string) => {
    const g = groups.get(key);
    if (!g) groups.set(key, { kind, at, n: 1, text });
    else {
      g.n += 1;
      if (at > g.at) g.at = at;
    }
    return groups.get(key)!;
  };
  for (const r of t.cafes) {
    const at = String(r.updated_at || "");
    const day = kstDay(at);
    if (!day) continue;
    const who = String(r.editor || "");
    if (r.status === "deleted") {
      if (r.source === "기간 종료") group(`end:${day}`, "내림", at, (n) => `기간이 끝난 팝업 ${n}곳을 지도에서 내림`);
      else out.push({ kind: "내림", text: `${popName(r)} 내림${r.source ? ` (${r.source})` : ""}`, at });
    } else if (who === "AI") {
      if (Number(r.revision) === 1) group(`ai-new:${day}`, "등록", at, (n) => `AI 자동 수집으로 새 팝업 ${n}곳`);
      else group(`ai-fix:${day}`, "수정", at, (n) => `AI 자동 수집이 팝업 ${n}곳 정보를 갱신`);
    } else if (Number(r.revision) === 1) out.push({ kind: "등록", text: `${who ? `${who}님이 ` : ""}${popName(r)} 등록`, at });
    else out.push({ kind: "수정", text: `${who ? `${who}님이 ` : ""}${popName(r)} 수정`, at });
  }
  for (const r of t.reqs) {
    const at = String(r.updated_at || "");
    const title = String(r.target_title || "");
    if (r.decision === "pending") out.push({ kind: "삭제 요청", text: `${r.requester_nick || "회원"}님이 ${title} 삭제 요청`, at });
    else if (r.decision === "approved") out.push({ kind: "처리", text: `${title} 삭제 요청 승인`, at });
    else if (r.decision === "rejected") out.push({ kind: "처리", text: `${title} 삭제 요청 거부`, at });
  }
  const names = new Map(latest(t.cafes).map((r) => [String(r.entry_id), popName(r)]));
  for (const r of t.reviews) {
    if (Number(r.revision) !== 1 || r.status === "deleted") continue;
    const at = String(r.updated_at || "");
    const name = names.get(String(r.cafe_id)) || "(내려간 팝업)";
    group(`rv:${kstDay(at)}:${r.cafe_id}`, "리뷰", at, (n) => `${name}에 새 글 ${n}개`);
  }
  for (const r of t.members) {
    if (Number(r.revision) !== 1) continue;
    const at = String(r.updated_at || "");
    const g = group(`join:${kstDay(at)}`, "가입", at, () => "");
    g.by ??= new Map();
    const p = PROVIDER_LABEL[String(r.provider)] || "기타";
    g.by.set(p, (g.by.get(p) ?? 0) + 1);
    const by = g.by;
    g.text = (n) => `새 회원 ${n}명 (${[...by.entries()].map(([k, v]) => `${k} ${v}`).join(" · ")})`;
  }
  for (const g of groups.values()) out.push({ kind: g.kind, text: g.text(g.n), at: g.at });
  return out.sort((a, b) => b.at.localeCompare(a.at)).slice(0, limit);
}

/** '11.23 – 11.29' */
export const weekLabel = (mon: string) => {
  const f = (d: string) => `${Number(d.slice(5, 7))}.${d.slice(8, 10)}`;
  return `${f(mon)} – ${f(addDays(mon, 6))}`;
};
export { dayLabel };
export type { Table };
