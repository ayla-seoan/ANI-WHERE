"use server";
import { revalidateTag } from "next/cache";
import { redirect } from "next/navigation";
import {
  ALWAYS_END,
  blockSensitive,
  EVENT_TAGS,
  EXTRA_MB,
  linksErrors,
  MAX_EXTRAS,
  MAX_INTRO,
  PERIOD_TAGS,
  POSTER_MB,
  split,
  splitImages,
  TAG_ALWAYS,
  TAG_CHECK,
  tooBig,
  validateCafe,
  validYmd,
  type CafeEntry,
  type Picked,
} from "@/lib/cafe-rules";
import { badgeOf as aiBadge, buildUserContent, CAFE_SCHEMA, callStructured, validateCafeExtraction, type AiCafeEntry } from "@/lib/server/ai";

import { cafeHistory, canonicalWork, currentCafes, entryToRow, keepNotion } from "@/lib/server/cafe";
import { badgeOf, locate, postcodePick, search, type Candidate, type SearchResult } from "@/lib/server/geo";
import { parseNotice, type Parsed } from "@/lib/server/parse";
import { getMe, requireAdmin, setFlash } from "@/lib/server/session";
import { AuthError, displayName } from "@/lib/server/auth";
import { append, current, HEADERS, StorageWriteError, type Row } from "@/lib/server/store";
import { filesFrom, saveImage } from "@/lib/server/upload";
import { todayKST } from "@/lib/popup";

// 팝업 등록 · 수정하기 · 되돌리기 · 지도에서 내리기 (app_cafemap.py page_add · render_edit · confirm_delete).
// 쓰기는 모두 이 서버 코드에서 store.append() 로만 (append-only: 수정·되돌리기·내리기도 새 revision 행).

export type EditState = { ok?: string; error?: string; errors?: string[]; warnings?: string[] } | null;

const say = (e: unknown) =>
  e instanceof AuthError || e instanceof StorageWriteError ? e.message : "요청을 처리하지 못했어요. 잠시 뒤 다시 시도해 주세요.";
const str = (f: FormData, k: string) => String(f.get(k) ?? "");
const validId = (id: string) => /^[\w-]{1,64}$/.test(id);

function pickedFrom(f: FormData): Picked | null {
  try {
    const p = JSON.parse(str(f, "picked") || "null") as Picked | null;
    if (!p || typeof p.address !== "string") return null;
    return { address: p.address, lat: Number(p.lat), lng: Number(p.lng), source: String(p.source || ""), precision: String(p.precision || "exact") };
  } catch {
    return null;
  }
}

function listFrom(f: FormData, k: string): string[] {
  try {
    const v = JSON.parse(str(f, k) || "[]");
    return Array.isArray(v) ? v.map((x) => String(x).trim()).filter(Boolean) : [];
  } catch {
    return split(str(f, k));
  }
}

function imageErrors(poster: File | undefined, extras: File[], total: number, posterLabel: string): string[] {
  const errors: string[] = [];
  if (poster && tooBig(poster.size, POSTER_MB)) errors.push(`${posterLabel}는 ${POSTER_MB} MB 까지 올릴 수 있습니다.`);
  if (extras.some((x) => tooBig(x.size, EXTRA_MB))) errors.push(`추가 이미지는 한 장에 ${EXTRA_MB} MB 까지 올릴 수 있습니다.`);
  if (total > MAX_EXTRAS) errors.push(`추가 이미지는 ${MAX_EXTRAS}장까지 둘 수 있습니다. 몇 장 지워 주세요.`);
  return errors;
}

async function latestRow(entryId: string): Promise<Row | null> {
  const all = await cafeHistory(entryId);
  return all.length ? all[all.length - 1] : null;
}

// ---------------------------------------------------------------- 주소
/** 카카오 우편번호에서 고른 주소 → 좌표를 붙인 후보 (앱 _postcode_field) */
export async function postcodeAction(address: string, jibun: string): Promise<Candidate> {
  return postcodePick(String(address || "").slice(0, 200), String(jibun || "").slice(0, 200));
}

/** 주소 · 가게 이름 검색 후보 (geo.search) */
export async function searchAddressAction(query: string): Promise<SearchResult> {
  return search(String(query || "").slice(0, 100));
}

/** 등록 2단계 '다음': 주소로 좌표를 찾을 수 있는지 (앱 _step_cafe save) */
export async function locateAction(address: string, picked: Picked | null): Promise<{ ok: boolean; note: string }> {
  const g = await locate(String(address || "").trim(), picked);
  return g.ok ? { ok: true, note: `${badgeOf(g)} (${g.matched})` } : { ok: false, note: g.note };
}

// ---------------------------------------------------------------- 수정하기
/** '수정 저장' (앱 render_edit): 새 revision 행 + 수정한 사람 = 로그인 회원 화면 닉네임 */
export async function editSaveAction(_: EditState, f: FormData): Promise<EditState> {
  const me = await getMe();
  if (!me) return { error: "팝업 정보 수정은 로그인하면 할 수 있어요." };
  const entryId = str(f, "entry_id");
  if (!validId(entryId)) return { error: "팝업을 찾을 수 없어요." };
  let cur: Row | null;
  try {
    cur = await latestRow(entryId);
  } catch (e) {
    return { error: say(e) };
  }
  if (!cur || cur.status === "deleted") return { error: "지도에서 내려진 팝업이라 수정할 수 없어요." };

  const work = canonicalWork(str(f, "work").trim());
  const chars = listFrom(f, "characters");
  const name = str(f, "cafe_name");
  const addr = str(f, "address");
  const perks = str(f, "perks");
  const goods = str(f, "goods");
  const intro = [...str(f, "intro")].slice(0, MAX_INTRO).join("");
  const always = str(f, "always") === "1";
  const start = str(f, "start_date");
  let end = str(f, "end_date");
  if (always) end = ALWAYS_END;
  const bad = blockSensitive(name, addr, perks, goods, intro);
  if (bad) return { error: bad };
  const lk = linksErrors(str(f, "links"));
  if (lk.errors.length) return { errors: lk.errors };
  if (!validYmd(start) || !validYmd(end)) return { error: "시작일과 종료일을 골라 주세요." };

  // 이미지: 남길 기존 이미지(지금 기록에 있는 것만) + 새 포스터 + 추가 이미지
  const curImgs = splitImages(cur.images);
  const keep = listFrom(f, "keep").filter((x) => curImgs.includes(x));
  const poster = filesFrom(f, "poster")[0];
  const extras = filesFrom(f, "extras");
  const plan: (string | File)[] = [...(poster ? [poster, ...keep.slice(1)] : keep), ...extras];
  const imgErr = imageErrors(poster, extras, plan.length - 1, "포스터");
  if (imgErr.length) return { errors: imgErr };

  const entry: CafeEntry = {
    cafe_name: name,
    work,
    characters: chars,
    address: addr,
    start_date: start,
    end_date: end,
    perks: split(perks),
    goods: split(goods),
    confidence: "high",
  };
  const today = todayKST();
  const oldStart = String(cur.start_date || "").slice(0, 10);
  const oldEnd = String(cur.end_date || "").slice(0, 10);
  const oldFlags = split(cur.tags).filter((t) => PERIOD_TAGS.includes(t));
  const datesChanged = start !== oldStart || end !== oldEnd;
  const tags = [
    ...f.getAll("tags").map(String).filter((t) => EVENT_TAGS.includes(t)),
    ...(always ? [TAG_ALWAYS] : []),
    ...(oldFlags.includes(TAG_CHECK) && !datesChanged ? [TAG_CHECK] : []),
  ];
  const v = validateCafe(entry, today);
  const picked = pickedFrom(f);
  const g = await locate(entry.address, picked);
  if (!g.ok) v.errors.push(g.note);
  if (v.errors.length) return { errors: v.errors };

  try {
    // 새로 올린 파일만 저장한다. 지운 이미지 파일은 남겨 둔다 (되돌리기가 옛 행을 쓸 수 있다)
    const saved: string[] = [];
    for (const x of plan) saved.push(typeof x === "string" ? x : await saveImage(x, x === poster ? "poster" : "extra"));
    await append(
      "cafes",
      entryToRow(entry, g.lat, g.lng, {
        source: "직접 수정",
        note: keepNotion(badgeOf(g), cur),
        editor: displayName(me.row),
        intro,
        introSrc: intro.trim() ? String(cur.intro_src || "") : "",
        images: saved,
        tags,
        links: lk.links,
      }),
      entryId,
    );
  } catch (e) {
    return { error: say(e) };
  }
  revalidateTag("popups");
  return { ok: "수정했습니다." };
}

/** 수정 이력 '이 버전으로 돌아가기' (store.restore): 그 revision 의 값으로 새 행 */
export async function restoreAction(entryId: string, revision: number): Promise<{ ok?: string; error?: string }> {
  const me = await getMe();
  if (!me) return { error: "팝업 정보 수정은 로그인하면 할 수 있어요." };
  if (!validId(entryId)) return { error: "팝업을 찾을 수 없어요." };
  try {
    const all = await cafeHistory(entryId);
    const target = all.find((r) => Number(r.revision) === Number(revision));
    if (!target) return { error: "그 버전을 찾을 수 없어요." };
    if (target.status === "deleted") return { error: "지도에서 내린 버전으로는 돌아갈 수 없어요." };
    const payload: Row = {};
    for (const h of HEADERS.cafes) if (!["row_id", "entry_id", "revision", "status", "updated_at"].includes(h)) payload[h] = target[h] ?? "";
    payload.source = `${revision}번째로 되돌리기`;
    payload.editor = displayName(me.row);
    await append("cafes", payload, entryId, target.status === "deleted" ? "deleted" : "active");
  } catch (e) {
    return { error: say(e) };
  }
  revalidateTag("popups");
  return { ok: `${revision}번째 버전으로 되돌렸어요.` };
}

/** 관리자 '지도에서 내리기' (store.soft_delete): 지금 값 그대로 + status deleted 새 행 */
export async function takeDownAction(entryId: string): Promise<{ error?: string }> {
  let me;
  try {
    me = await requireAdmin();
  } catch (e) {
    return { error: say(e) };
  }
  if (!validId(entryId)) return { error: "팝업을 찾을 수 없어요." };
  try {
    const cur = current(await cafeHistory(entryId))[0];
    if (!cur) return { error: "이미 지도에서 내려진 팝업이에요." };
    const payload: Row = {};
    for (const h of HEADERS.cafes) if (!["row_id", "entry_id", "revision", "status", "updated_at"].includes(h)) payload[h] = cur[h] ?? "";
    payload.source = "지도에서 내림";
    payload.editor = displayName(me.row);
    await append("cafes", payload, entryId, "deleted");
  } catch (e) {
    return { error: say(e) };
  }
  revalidateTag("popups");
  await setFlash("지도에서 내렸습니다. 이력은 남아 있습니다.");
  redirect("/");
}

// ---------------------------------------------------------------- 등록하기
export type QuickGot = Omit<Parsed, "start_date" | "end_date"> & { start_date: string | null; end_date: string | null };
export type QuickResult = { error?: string; got?: QuickGot; source?: "ai" | "fallback"; badge?: string };

/** 간편등록 '읽어오기': OPENAI_API_KEY 가 있으면 AI(cafe 프롬프트), 없거나 실패하면 규칙 기반(notice.parse_notice) */
export async function quickReadAction(raw: string): Promise<QuickResult> {
  const me = await getMe();
  if (!me) return { error: "팝업 등록은 로그인하면 할 수 있어요." };
  const text = String(raw || "").slice(0, 20000);
  if (!text.trim()) return { error: "공지 내용을 붙여넣어 주세요." };
  const bad = blockSensitive(text);
  if (bad) return { error: bad };
  const today = todayKST();
  const rule = parseNotice(text, today);
  const r = await callStructured<AiCafeEntry[]>("cafe", buildUserContent(text, today), CAFE_SCHEMA, validateCafeExtraction);
  if (r.source === "ai" && r.data && r.data.length) {
    const e = r.data[0];
    const work = canonicalWork(e.work.trim()) || rule.work;
    const ended = e.end_date < today;
    const got: QuickGot = {
      ...rule,
      work: work || null,
      cafe_name: e.cafe_name.trim() || null,
      address: e.address.trim() || null,
      start_date: e.start_date,
      end_date: e.end_date,
      characters: e.characters,
      perks: e.perks,
      goods: e.goods,
      status: work && e.address.trim() && e.confidence === "high" && !ended ? "자동등록" : "검토대기",
      reasons: [
        ...(e.confidence === "low" ? ["원문에 정보가 흐릿합니다. 저장 전에 직접 확인해 주세요."] : []),
        ...(ended ? [`이미 끝난 행사예요 (${e.start_date} ~ ${e.end_date}).`] : []),
      ],
    };
    return { got, source: "ai", badge: aiBadge(r) };
  }
  return { got: rule, source: "fallback", badge: "규칙 기반 대체" };
}

/** '등록하기' (앱 _step_confirm · _quick 의 등록): cafes 새 entry. 끝나면 상세로 */
export async function addAction(_: EditState, f: FormData): Promise<EditState> {
  const me = await getMe();
  if (!me) return { error: "팝업 등록은 로그인하면 할 수 있어요." };
  const quick = str(f, "mode") === "quick";
  const work = canonicalWork(str(f, "work").trim());
  const chars = listFrom(f, "characters");
  const name = str(f, "cafe_name").trim();
  const addr = str(f, "address").trim();
  const perks = str(f, "perks");
  const goods = str(f, "goods");
  const intro = [...str(f, "intro")].slice(0, MAX_INTRO).join("");
  const start = str(f, "start_date");
  const end = str(f, "end_date");
  if (!work) return { error: "작품을 골라 주세요." };
  const bad = blockSensitive(work, ...chars, name, addr, perks, goods, intro);
  if (bad) return { error: bad };
  const lk = linksErrors(str(f, "links"));
  if (lk.errors.length) return { errors: lk.errors };
  if (!validYmd(start) || !validYmd(end)) return { error: "시작일과 종료일을 골라 주세요." };
  const poster = filesFrom(f, "poster")[0];
  const extras = filesFrom(f, "extras");
  const imgErr: string[] = [];
  if (poster && tooBig(poster.size, POSTER_MB)) imgErr.push(`메인 이미지는 ${POSTER_MB} MB 까지 올릴 수 있습니다.`);
  if (extras.length > MAX_EXTRAS) imgErr.push(`추가 이미지는 ${MAX_EXTRAS}장까지 올릴 수 있습니다.`);
  if (extras.some((x) => tooBig(x.size, EXTRA_MB))) imgErr.push(`추가 이미지는 한 장에 ${EXTRA_MB} MB 까지 올릴 수 있습니다.`);
  if (imgErr.length) return { errors: imgErr };

  const entry: CafeEntry = {
    cafe_name: name,
    work,
    characters: chars,
    address: addr,
    start_date: start,
    end_date: end,
    perks: split(perks),
    goods: split(goods),
    confidence: "high",
  };
  const tags = f.getAll("tags").map(String).filter((t) => EVENT_TAGS.includes(t) || t === TAG_ALWAYS);
  let id = "";
  try {
    const cur = await currentCafes();
    const v = validateCafe(entry, todayKST(), cur.map((r) => ({ cafe_name: String(r.cafe_name), address: String(r.address), work: String(r.work), status: String(r.status) })));
    if (!v.ok) return { errors: v.errors, warnings: v.warnings };
    const g = await locate(entry.address, pickedFrom(f));
    if (!g.ok) return { error: g.note };
    // 첫 장이 포스터. 포스터 없이 추가 이미지만 올리면 그 첫 장이 포스터가 된다
    const files = [...(poster ? [poster] : []), ...extras];
    const saved: string[] = [];
    for (const x of files) saved.push(await saveImage(x, x === poster ? "poster" : "extra"));
    const row = await append(
      "cafes",
      entryToRow(entry, g.lat, g.lng, {
        source: quick ? "간편 등록" : "직접 등록",
        editor: displayName(me.row),
        note: `${badgeOf(g)} (${g.matched})`,
        intro,
        images: saved,
        tags,
        links: lk.links,
      }),
    );
    id = String(row.entry_id);
  } catch (e) {
    return { error: say(e) };
  }
  revalidateTag("popups");
  await setFlash("1곳을 지도에 올렸습니다.");
  redirect(`/popup/${id}`);
}
