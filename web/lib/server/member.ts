import "server-only";
import { scan } from "../guard";
import { allMembers, WITHDRAWN } from "./auth";
import { append, current, latest, rows, type Row } from "./store";

// 북마크 · 리뷰 · 알림 — common/favorite.py · review.py · admin.py 규칙 그대로 (append-only).

// ------------------------------------------------------------------ 북마크
/** 북마크 주인: 회원은 'm:<회원 번호>' (앱 _fav_user 와 같다. 손님 북마크는 없다) */
export const favUser = (key: string) => `m:${key}`;

export async function myFavIds(key: string): Promise<string[]> {
  const mine = current(await rows("favorites", { user: favUser(key) }));
  return mine.map((r) => String(r.cafe_id));
}

/** 북마크하기(on) / 해제(off). 지난 기록은 남기고 새 행 (favorite.toggle) */
export async function toggleFav(key: string, cafeId: string, on: boolean): Promise<void> {
  const user = favUser(key);
  await append("favorites", { cafe_id: cafeId, user }, `${user}:${cafeId}`, on ? "active" : "deleted");
}

// ------------------------------------------------------------------ 리뷰
export const KINDS = ["다녀온 후기", "기대평", "기타"] as const;
export const RATED_KIND = "다녀온 후기";
export const MAX_BODY = 1000;
const MAX_REVIEW_NICK = 40;

/** review.validate (allowEmpty: 다녀온 후기에 별점을 골랐으면 내용 없이도) */
export function validateReview(body: string, nickname: string, allowEmpty = false): string[] {
  const errors: string[] = [];
  if (!body.trim() && !allowEmpty) errors.push("내용을 입력해 주세요.");
  if ([...body].length > MAX_BODY) errors.push(`내용은 ${MAX_BODY}자까지 쓸 수 있습니다.`);
  if ([...nickname].length > MAX_REVIEW_NICK) errors.push(`닉네임은 ${MAX_REVIEW_NICK}자까지 쓸 수 있습니다.`);
  const kinds = [...new Set(scan(`${nickname} ${body}`).map((f) => f.kind))].sort();
  if (kinds.length) errors.push(`민감한 개인정보(${kinds.join(", ")})는 입력할 수 없습니다.`);
  return errors;
}

/** review._tag: 닉네임 끝 '#a3f9' / '#m1a2b' (없으면 닉네임 전체) */
export const tagOf = (nick: string) => (nick.includes("#") ? nick.slice(nick.lastIndexOf("#") + 1) : nick);

/** review.can_delete: 끝 꼬리표가 같을 때만 내 글 */
export const canEdit = (row: Row, myName: string) => !!myName && tagOf(String(row.nickname || "")) === tagOf(myName);

/** review.to_row */
export function toReviewRow(
  cafeId: string,
  body: string,
  nickname: string,
  kind: string,
  parentId: string,
  rating: number | null,
): Row {
  const k = parentId ? "" : (KINDS as readonly string[]).includes(kind) ? kind : KINDS[0];
  const ok = k === RATED_KIND && rating !== null && Number.isInteger(rating) && rating >= 1 && rating <= 5;
  return {
    cafe_id: cafeId,
    parent_id: parentId,
    kind: k,
    nickname: nickname.trim() || "익명",
    body: body.trim(),
    rating: ok ? String(rating) : "",
    images: "",
  };
}

export type Author = { name: string; avatar: string };

/** 저장된 이름('닉네임#m1a2b') → 지금 회원 닉네임·사진 (앱 _author). 탈퇴했으면 '탈퇴한 회원' */
export async function authorMap(): Promise<(nick: string) => Author> {
  const byTag = new Map<string, Row>();
  for (const r of await allMembers()) byTag.set(`m${String(r.entry_id).slice(0, 4)}`, r);
  return (nick: string) => {
    const text = String(nick || "");
    const tag = text.includes("#") ? text.slice(text.lastIndexOf("#") + 1) : "";
    const row = tag.startsWith("m") ? byTag.get(tag) : undefined;
    if (row && String(row.nickname || "").trim())
      return { name: String(row.nickname).trim(), avatar: String(row.avatar || "") };
    if (tag.startsWith("m")) return { name: WITHDRAWN, avatar: "" };
    return { name: (text.includes("#") ? text.slice(0, text.lastIndexOf("#")) : text).trim() || "익명", avatar: "" };
  };
}

export type ReviewView = {
  id: string;
  kind: string;
  name: string;
  avatar: string;
  body: string;
  rating: number | null;
  images: string[];
  when: string;
  edited: boolean;
  mine: boolean;
  parentId: string;
};
export type ThreadView = { post: ReviewView; replies: ReviewView[] };

/** 한 팝업의 리뷰를 원글 최신순, 답글은 오래된 순으로 (review.threads). 리뷰 본문은 상세 화면에서만 보인다 */
export async function threadsFor(cafeId: string, myName: string): Promise<ThreadView[]> {
  const mine = current(await rows("reviews", { cafe_id: cafeId }));
  const who = await authorMap();
  const byId = new Map(mine.map((r) => [String(r.entry_id), r]));
  const root = (r: Row): string => {
    const seen = new Set<string>();
    let cur: Row | undefined = r;
    while (cur && String(cur.parent_id || "") && !seen.has(String(cur.entry_id))) {
      seen.add(String(cur.entry_id));
      cur = byId.get(String(cur.parent_id));
      if (!cur) return "";
    }
    return cur ? String(cur.entry_id) : "";
  };
  const view = (r: Row): ReviewView => {
    const a = who(String(r.nickname));
    const n = Number(r.rating);
    return {
      id: String(r.entry_id),
      kind: String(r.kind || ""),
      name: a.name,
      avatar: a.avatar,
      body: String(r.body || ""),
      rating: n >= 1 && n <= 5 ? n : null,
      images: String(r.images || "")
        .split(",")
        .map((x) => x.trim())
        .filter((x) => /^[\w.-]+\.(png|jpe?g|webp|gif)$/i.test(x)),
      when: String(r.updated_at || ""),
      edited: Number(r.revision || 1) > 1,
      mine: canEdit(r, myName),
      parentId: String(r.parent_id || ""),
    };
  };
  const posts = new Map<string, ThreadView>();
  for (const r of mine) if (!String(r.parent_id || "")) posts.set(String(r.entry_id), { post: view(r), replies: [] });
  for (const r of mine) {
    if (!String(r.parent_id || "")) continue;
    const top = posts.get(root(r));
    if (top) top.replies.push(view(r));
  }
  const out = [...posts.values()].sort((a, b) => b.post.when.localeCompare(a.post.when));
  for (const t of out) t.replies.sort((a, b) => a.when.localeCompare(b.when));
  return out;
}

export async function reviewRow(entryId: string): Promise<Row | null> {
  return current(await rows("reviews", { entry_id: entryId }))[0] ?? null;
}

/** 내가 쓴 '다녀온 후기' (내 캘린더 '다녀온 팝업') */
export async function myVisited(myName: string): Promise<Row[]> {
  const tag = tagOf(myName);
  const all = current(await rows("reviews"));
  return all.filter(
    (r) => r.kind === RATED_KIND && !String(r.parent_id || "") && tagOf(String(r.nickname || "")) === tag,
  );
}

// ------------------------------------------------------------------ 알림 (admin.RULES · notices_for)
export const RULES: Record<string, { days: number | null; max: number | null; why: string }> = {
  open: { days: 3, max: 8, why: "북마크한 팝업이 곧 열려요 (오픈 {days}일 전부터 알려 드려요)" },
  end: { days: 3, max: 8, why: "북마크한 팝업이 곧 끝나요 (종료 {days}일 전부터 알려 드려요)" },
  near: { days: null, max: 3, why: "내 위치에서 가까운 곳에 지금 열려 있어요" },
  del_ok: { days: null, max: null, why: "내가 보낸 삭제 요청이 처리됐어요" },
  del_no: { days: null, max: null, why: "내가 보낸 삭제 요청이 처리됐어요" },
  notice: { days: 14, max: 5, why: "ANI:WHERE 운영 공지예요" },
  rv_del: { days: null, max: null, why: "내가 쓴 리뷰를 관리자가 삭제했어요" },
};
const KIND_RULE: Record<string, string> = {
  공지: "notice",
  "삭제 승인": "del_ok",
  "삭제 거부": "del_no",
  "리뷰 삭제": "rv_del",
};
export type RuleSet = Record<string, { enabled: boolean; days: number | null; max: number | null }>;

/** 관리자가 고친 알림 규칙 (alert_rules, admin.rule_settings). 표가 없으면 기본값 */
export async function ruleSettings(): Promise<RuleSet> {
  const out: RuleSet = {};
  for (const [k, v] of Object.entries(RULES)) out[k] = { enabled: true, days: v.days, max: v.max };
  let rs: Row[] = [];
  try {
    rs = latest(await rows("alert_rules"));
  } catch {
    return out;
  }
  for (const r of rs) {
    const k = String(r.entry_id);
    if (!out[k]) continue;
    out[k].enabled = r.status !== "deleted" && !["0", "false", "False"].includes(String(r.enabled ?? "1"));
    for (const f of ["days", "max"] as const) {
      const raw = String((f === "days" ? r.days : r.max_items) || "").trim();
      if (RULES[k][f] !== null && /^\d+$/.test(raw)) out[k][f] = Number(raw);
    }
  }
  return out;
}

export const whyOf = (key: string, rules: RuleSet) =>
  (RULES[key]?.why || "").replace("{days}", String(rules[key]?.days ?? ""));

export type InboxItem = { id: string; title: string; body: string; why: string; when: string };

/** 관리자가 보낸 알림 중 켜진 규칙 것 (앱 _inbox): 전체 공지 + 나에게 온 것, 최근 60일 */
export async function inbox(key: string, rules: RuleSet, todayYmd: string): Promise<InboxItem[]> {
  let all: Row[] = [];
  try {
    all = current(await rows("notices"));
  } catch {
    return [];
  }
  const dayOf = (s: string) => s.slice(0, 10);
  const diff = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  const mine = all
    .filter((r) => ["all", key].includes(String(r.target)) && diff(dayOf(String(r.updated_at)), todayYmd) <= 60)
    .sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)));
  const out: InboxItem[] = [];
  let nNotice = 0;
  for (const r of mine) {
    const rk = KIND_RULE[String(r.kind)] || "notice";
    if (!rules[rk]?.enabled) continue;
    if (rk === "notice") {
      if (diff(dayOf(String(r.updated_at)), todayYmd) > (rules.notice.days ?? 14)) continue;
      if (++nNotice > (rules.notice.max ?? 5)) continue;
    }
    out.push({
      id: `i${r.row_id}`,
      title: String(r.title || ""),
      body: String(r.body || ""),
      why: whyOf(rk, rules),
      when: String(r.updated_at),
    });
  }
  return out;
}

export type BellItem = { id: string; label: string; name: string; why: string; cafeId: string; kind: "open" | "end" };

/** 북마크한 팝업 알림 (앱 _notices 1번 묶음): 오픈 D-n ~ 당일, 진행 중이면 종료 D-n ~ 당일 */
export function bookmarkMarks(
  pops: { id: string; work: string; name: string; start: string; end: string }[],
  favs: Set<string>,
  rules: RuleSet,
  today: string,
): BellItem[] {
  const diff = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  const od = rules.open.days ?? 3;
  const ed = rules.end.days ?? 3;
  const marks: BellItem[] = [];
  for (const p of pops) {
    if (!favs.has(p.id)) continue;
    const name = [p.work, p.name].filter(Boolean).join(" · ");
    const ds = p.start ? diff(today, p.start) : NaN;
    const de = p.end ? diff(today, p.end) : NaN;
    if (rules.open.enabled && ds >= 0 && ds <= od) {
      const label = ds === 0 ? "오늘 오픈" : `오픈 D-${ds}`;
      marks.push({
        id: `m${today}${p.id}${label}`,
        label,
        name,
        why: whyOf("open", rules),
        cafeId: p.id,
        kind: "open",
      });
    } else if (rules.end.enabled && p.start && p.start <= today && de >= 0 && de <= ed) {
      const label = de === 0 ? "오늘 종료" : `종료 D-${de}`;
      marks.push({ id: `m${today}${p.id}${label}`, label, name, why: whyOf("end", rules), cafeId: p.id, kind: "end" });
    }
  }
  const key = (m: BellItem) => `${m.label} · ${m.name}`;
  marks.sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0));
  const opens = marks.filter((m) => m.kind === "open").slice(0, rules.open.max ?? 8);
  const ends = marks.filter((m) => m.kind === "end").slice(0, rules.end.max ?? 8);
  return [...opens, ...ends].sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0));
}
