"use server";
import { headers } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  allMembers,
  AuthError,
  changePassword,
  checkPassword,
  displayName,
  dropPassword,
  findMember,
  LOCK_SECONDS,
  MAX_FAILS,
  purgeWithdrawn,
  registerPassword,
  rename,
  setAvatar,
  signup,
  suggestNick,
  withdraw,
} from "@/lib/server/auth";
import {
  canEdit,
  KINDS,
  myFavIds,
  RATED_KIND,
  reviewRow,
  ruleSettings,
  tagOf,
  toggleFav,
  toReviewRow,
  validateReview,
} from "@/lib/server/member";
import { clearPending, endSession, getMe, getPending, setFlash, startSession } from "@/lib/server/session";
import { append, StorageWriteError, type Row } from "@/lib/server/store";
import { filesFrom, LIMIT_MB, saveImage } from "@/lib/server/upload";
import { sensitiveWarning } from "@/lib/guard";
import { reviewRemoved } from "@/lib/server/admin";

// 쓰기는 모두 여기 서버 코드로만 (브라우저는 키를 모른다). Streamlit 앱과 같은 검사 · 같은 표 · append-only.

export type FormState = { error?: string; ok?: string } | null;

const say = (e: unknown) =>
  e instanceof AuthError || e instanceof StorageWriteError
    ? e.message
    : "요청을 처리하지 못했어요. 잠시 뒤 다시 시도해 주세요.";
const str = (f: FormData, k: string) => String(f.get(k) ?? "");
const tidy = (s: string) => s.split(/\s+/).filter(Boolean).join(" ");
/** 돌아갈 주소는 이 사이트 안(/로 시작)만 */
const safeNext = (s: string) => (/^\/(?!\/)[\w\-/?=&%.]*$/.test(s) ? s : "/");

function consentError(f: FormData): string {
  if (!f.get("age")) return "만 14세 이상만 가입할 수 있어요.";
  if (!(f.get("terms") && f.get("privacy")))
    return "필수 항목(이용약관 · 개인정보 수집·이용)에 동의해야 가입할 수 있어요.";
  return "";
}

// ---- 아이디 로그인 (5번 틀리면 5분 잠금, 앱과 같은 규칙. 서버 메모리라 서버가 바뀌면 처음부터) ----
const fails = new Map<string, { n: number; until: number }>();

export async function loginAction(_: FormState, f: FormData): Promise<FormState> {
  const ip = ((await headers()).get("x-forwarded-for") || "local").split(",")[0].trim();
  const lid = str(f, "login_id").trim().toLowerCase();
  const slot = `${ip}:${lid}`;
  const st = fails.get(slot);
  if (st && st.until > Date.now())
    return {
      error: `비밀번호를 여러 번 틀려서 잠시 막았어요. ${Math.floor((st.until - Date.now()) / 60000) + 1}분 뒤 다시 시도해 주세요.`,
    };
  let row: Row | null = null;
  try {
    const key = await checkPassword(lid, str(f, "password"));
    row = key ? await findMember(key) : null;
  } catch (e) {
    return { error: say(e) };
  }
  if (!row) {
    const n = (st?.n ?? 0) + 1;
    fails.set(slot, n >= MAX_FAILS ? { n: 0, until: Date.now() + LOCK_SECONDS * 1000 } : { n, until: 0 });
    return { error: "아이디나 비밀번호가 맞지 않아요." }; // 어느 쪽이 틀렸는지는 알려 주지 않는다
  }
  fails.delete(slot);
  await startSession(String(row.entry_id), String(row.provider));
  await setFlash(`${row.nickname}님, 환영합니다!`, "wave");
  redirect(safeNext(str(f, "next")));
}

export async function signupAction(_: FormState, f: FormData): Promise<FormState> {
  const err = consentError(f);
  if (err) return { error: err };
  let row: Row;
  try {
    let nick = tidy(str(f, "nickname"));
    if (!nick) nick = await suggestNick(); // 비워 두면 '꾸밈말 + 캐릭터' 로 자동
    row = await registerPassword(str(f, "login_id"), str(f, "password"), str(f, "password2"), nick);
  } catch (e) {
    return { error: say(e) };
  }
  await startSession(String(row.entry_id), "local");
  await setFlash("가입했어요!", "wave");
  redirect("/");
}

/** 간편 로그인으로 처음 온 사람: '거의 다 됐어요' 화면의 닉네임 · 동의 */
export async function socialJoinAction(_: FormState, f: FormData): Promise<FormState> {
  const p = await getPending();
  if (!p) return { error: "로그인 시간이 지났어요 (10분). 처음부터 다시 시도해 주세요." };
  const err = consentError(f);
  if (err) return { error: err };
  let row: Row;
  try {
    const existing = await findMember(p.k);
    if (existing) row = existing;
    else {
      let nick = tidy(str(f, "nickname"));
      if (!nick) nick = await suggestNick();
      // 사진은 [선택] 동의한 경우에만 저장 (안 했으면 'none' = 기본 그림)
      row = await signup(
        { provider: p.p, memberKey: p.k, nickname: nick, avatar: f.get("photo") ? p.a : "none" },
        nick,
      );
    }
  } catch (e) {
    return { error: say(e) };
  }
  await clearPending();
  await startSession(String(row.entry_id), String(row.provider));
  await setFlash("가입했어요!", "wave");
  redirect("/");
}

export async function logoutAction(): Promise<void> {
  await endSession();
  await setFlash("로그아웃했어요.", "logout");
  redirect("/login");
}

// ---- 마이페이지 ----
async function needMe() {
  const me = await getMe();
  if (!me) throw new AuthError("로그인이 풀렸어요. 다시 로그인해 주세요.");
  return me;
}

export async function renameAction(_: FormState, f: FormData): Promise<FormState> {
  try {
    const me = await needMe();
    const nick = tidy(str(f, "nickname")) || (await suggestNick()); // 비워 두고 저장 → 랜덤 닉네임
    await rename(me.row, nick);
    revalidatePath("/", "layout");
    return { ok: `닉네임을 '${nick}'(으)로 바꿨어요.` };
  } catch (e) {
    return { error: say(e) };
  }
}

export async function avatarDefaultAction(): Promise<FormState> {
  try {
    const me = await needMe();
    await setAvatar(me.row, "none");
    revalidatePath("/", "layout");
    return { ok: "기본 사진으로 바꿨어요." };
  } catch (e) {
    return { error: say(e) };
  }
}

/** 프로필 사진 올리기 (앱 _my_account): [선택] 동의가 있어야 저장. 가운데를 256px 정사각형 webp 로 줄이고 위치 정보(EXIF)는 지운다 */
export async function avatarUploadAction(_: FormState, f: FormData): Promise<FormState> {
  try {
    const me = await needMe();
    if (!f.get("agree")) return { error: "[선택] 프로필 사진 수집·이용에 동의해야 저장할 수 있어요." };
    const file = f.get("photo");
    if (!(file instanceof File) || !file.size) return { error: "올릴 사진을 골라 주세요." };
    if (file.size > LIMIT_MB.avatar * 1024 * 1024) return { error: `${LIMIT_MB.avatar}MB 이하 사진만 올릴 수 있어요.` };
    if (!/\.(png|jpe?g|webp)$/i.test(file.name || "")) return { error: "png·jpg·webp 사진만 올릴 수 있어요." };
    const url = await saveImage(file, "avatar");
    await setAvatar(me.row, url);
    revalidatePath("/", "layout");
    return { ok: "프로필 사진을 바꿨어요." };
  } catch (e) {
    return { error: say(e) };
  }
}

export async function changePasswordAction(_: FormState, f: FormData): Promise<FormState> {
  try {
    await needMe();
    await changePassword(str(f, "login_id"), str(f, "old"), str(f, "new"), str(f, "new2"));
    return { ok: "비밀번호를 바꿨어요." };
  } catch (e) {
    return { error: say(e) };
  }
}

export async function withdrawAction(_: FormState, f: FormData): Promise<FormState> {
  try {
    const me = await needMe();
    if (me.row.provider === "local") await dropPassword(str(f, "login_id"), str(f, "password"));
    await withdraw(me.row);
    await purgeWithdrawn(me.key); // 개인정보 파기 (지난 기록까지)
  } catch (e) {
    return { error: say(e) };
  }
  await endSession();
  await setFlash("탈퇴했어요. 그동안 고마웠어요.");
  redirect("/");
}

// ---- 북마크 ----
export async function toggleFavAction(
  cafeId: string,
  on: boolean,
): Promise<{ ok: boolean; error?: string; login?: boolean }> {
  const me = await getMe();
  if (!me) return { ok: false, login: true, error: "북마크는 로그인하면 쓸 수 있어요." };
  if (!/^[\w-]{1,64}$/.test(cafeId)) return { ok: false, error: "알 수 없는 팝업이에요." };
  try {
    await toggleFav(me.key, cafeId, on);
  } catch (e) {
    return { ok: false, error: say(e) };
  }
  revalidatePath("/calendar");
  return { ok: true };
}

/** '최애 추가하기' 저장 (앱 bookmark_pick_dialog): 고른 것은 북마크, 고르지 않은 내 북마크는 해제 */
export async function bookmarkSetAction(pick: string[]): Promise<FormState> {
  const me = await getMe();
  if (!me) return { error: "북마크는 로그인하면 쓸 수 있어요." };
  const want = [...new Set((Array.isArray(pick) ? pick : []).map(String))].filter((x) => /^[\w-]{1,64}$/.test(x)).slice(0, 500);
  try {
    const mine = new Set(await myFavIds(me.key));
    for (const id of want.filter((x) => !mine.has(x))) await toggleFav(me.key, id, true);
    for (const id of [...mine].filter((x) => !want.includes(x))) await toggleFav(me.key, id, false);
  } catch (e) {
    return { error: e instanceof StorageWriteError ? "저장하지 못했어요. 잠시 뒤 다시 눌러 주세요." : say(e) };
  }
  revalidatePath("/", "layout");
  return { ok: `북마크 ${want.length}개를 저장했어요. 내 캘린더에서 볼 수 있어요.` };
}

// ---- 리뷰 ----
const MAX_IMAGES = 4; // review.MAX_IMAGES — 리뷰 한 건에 붙일 수 있는 사진 수
const IMAGE_MB = LIMIT_MB.review; // review.IMAGE_MB

/** 리뷰에 붙인 새 사진 (앞의 room 장만, 앱과 같게). 너무 큰 사진이 있으면 오류 문구 */
function reviewPhotos(f: FormData, room: number): File[] | string {
  const files = filesFrom(f, "photos").slice(0, Math.max(0, room));
  const heavy = files.filter((x) => x.size > IMAGE_MB * 1024 * 1024).map((x) => x.name);
  if (heavy.length) return `${IMAGE_MB}MB 를 넘는 사진은 올릴 수 없어요: ${heavy.join(", ")}`;
  return files;
}

export async function reviewCreateAction(_: FormState, f: FormData): Promise<FormState> {
  const me = await getMe();
  if (!me) return { error: "리뷰는 로그인하면 쓸 수 있어요." };
  const cafeId = str(f, "cafe_id");
  const parentId = str(f, "parent_id");
  if (!/^[\w-]{1,64}$/.test(cafeId) || (parentId && !/^[\w-]{1,64}$/.test(parentId)))
    return { error: "알 수 없는 팝업이에요." };
  const kind = parentId ? "" : (KINDS as readonly string[]).includes(str(f, "kind")) ? str(f, "kind") : KINDS[0];
  const r = Number(str(f, "rating"));
  const rating = kind === RATED_KIND && r >= 1 && r <= 5 ? r : null;
  const body = str(f, "body");
  const nick = displayName(me.row);
  // 사진 첨부는 원글만 (답글 칸은 가볍게). 다녀온 후기는 별점만 골라도, 사진만 올려도 등록할 수 있다
  const photos = parentId ? [] : reviewPhotos(f, MAX_IMAGES);
  if (typeof photos === "string") return { error: photos };
  const errors = validateReview(body, nick, kind === RATED_KIND && (rating !== null || photos.length > 0));
  if (errors.length) return { error: errors[0] };
  try {
    const saved: string[] = [];
    for (const p of photos) saved.push(await saveImage(p, "review"));
    await append("reviews", toReviewRow(cafeId, body, nick, kind, parentId, rating, saved));
  } catch (e) {
    return { error: say(e) };
  }
  revalidatePath(`/popup/${cafeId}`);
  return { ok: parentId ? "답글을 남겼습니다." : "리뷰를 남겼습니다." };
}

export async function reviewEditAction(_: FormState, f: FormData): Promise<FormState> {
  const me = await getMe();
  if (!me) return { error: "로그인이 풀렸어요. 다시 로그인해 주세요." };
  const id = str(f, "entry_id");
  const cur = /^[\w-]{1,64}$/.test(id) ? await reviewRow(id) : null;
  const nick = displayName(me.row);
  if (!cur || !canEdit(cur, nick)) return { error: "내가 쓴 글만 수정할 수 있어요." }; // 저장하는 순간에도 한 번 더 확인
  const body = str(f, "body");
  const isReply = !!String(cur.parent_id || "");
  const kind = isReply ? "" : (KINDS as readonly string[]).includes(str(f, "kind")) ? str(f, "kind") : KINDS[0];
  const r = Number(str(f, "rating"));
  const rating = kind === RATED_KIND && r >= 1 && r <= 5 ? r : null;
  const errors = validateReview(body, nick, kind === RATED_KIND && rating !== null);
  if (errors.length) return { error: errors[0] };
  const payload: Row = {};
  for (const k of ["cafe_id", "parent_id", "kind", "nickname", "body", "rating", "images"]) payload[k] = cur[k] ?? "";
  payload.body = body.trim();
  // 사진 (원글만): 있던 사진은 '남기기' 를 푼 것만 빼고, 남은 자리만큼 새 사진을 더한다
  const had = String(cur.images || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  const keep = isReply ? had : had.filter((x) => f.getAll("keep").map(String).includes(x));
  const photos = isReply ? [] : reviewPhotos(f, MAX_IMAGES - keep.length);
  if (typeof photos === "string") return { error: photos };
  if (!isReply) {
    payload.kind = kind;
    payload.rating = kind === RATED_KIND && rating ? String(rating) : ""; // 종류를 바꾸면 별점은 비운다
  }
  try {
    const added: string[] = [];
    for (const p of photos) added.push(await saveImage(p, "review"));
    if (!isReply) payload.images = [...keep, ...added].join(",");
    await append("reviews", payload, id);
  } catch (e) {
    return { error: say(e) };
  }
  revalidatePath(`/popup/${cur.cafe_id}`);
  return { ok: "수정했습니다." };
}

/** 리뷰 삭제 (앱 confirm_review_delete): 쓴 사람은 내 글만, 관리자는 모든 글 — 관리자가 남의 글을 지울 땐 사유를 적고
 *  쓴 회원에게 알림이 간다 (알림 규칙 rv_del 이 켜져 있을 때) */
export async function reviewDeleteAction(entryId: string, reason = ""): Promise<FormState> {
  const me = await getMe();
  if (!me) return { error: "로그인이 풀렸어요. 다시 로그인해 주세요." };
  const cur = /^[\w-]{1,64}$/.test(entryId) ? await reviewRow(entryId) : null;
  if (!cur) return { error: "이미 지워진 글이에요." };
  const mine = canEdit(cur, displayName(me.row));
  if (!mine && !me.admin) return { error: "내가 쓴 리뷰만 삭제할 수 있어요." };
  const why = tidy(String(reason || "")).slice(0, 200);
  if (!mine && why.length < 2) return { error: "삭제 사유를 두 글자 이상 적어 주세요. 쓴 사람에게 알림으로 가요." };
  if (!mine && sensitiveWarning(why)) return { error: "사유에 전화번호·이메일 같은 개인정보는 넣지 말아 주세요." };
  const payload: Row = {};
  for (const k of ["cafe_id", "parent_id", "kind", "nickname", "body", "rating", "images"]) payload[k] = cur[k] ?? "";
  try {
    await append("reviews", payload, entryId, "deleted"); // 지우지 않고 '삭제됨' 행을 쌓는다
  } catch (e) {
    return { error: say(e) };
  }
  revalidatePath(`/popup/${cur.cafe_id}`);
  if (mine) return { ok: "삭제했어요." };
  // 관리자가 남의 글을 지움 → 쓴 회원(이름 끝 #m네 글자)에게 사유 알림 (admin.review_removed)
  const tag = tagOf(String(cur.nickname || ""));
  const writer = tag.startsWith("m")
    ? (await allMembers()).find((m) => `m${String(m.entry_id).slice(0, 4)}` === tag)
    : undefined;
  if (writer) {
    try {
      if ((await ruleSettings()).rv_del?.enabled !== false) {
        await reviewRemoved(String(writer.entry_id), String(cur.body || cur.kind || "").slice(0, 30), why);
      }
    } catch {
      /* 알림을 못 보내도 삭제는 끝났다 (앱과 같게) */
    }
  }
  return { ok: "삭제했어요." + (writer ? " 쓴 사람에게 사유를 알림으로 보냈어요." : "") };
}
