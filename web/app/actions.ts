"use server";
import { headers } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
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
import { canEdit, KINDS, RATED_KIND, reviewRow, toggleFav, toReviewRow, validateReview } from "@/lib/server/member";
import { clearPending, endSession, getMe, getPending, setFlash, startSession } from "@/lib/server/session";
import { append, StorageWriteError, type Row } from "@/lib/server/store";

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
  await setFlash(`${row.nickname}님, 환영합니다!`);
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
  await setFlash("가입했어요!");
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
  await setFlash("가입했어요!");
  redirect("/");
}

export async function logoutAction(): Promise<void> {
  await endSession();
  await setFlash("로그아웃했어요.");
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

// ---- 리뷰 ----
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
  const errors = validateReview(body, nick, kind === RATED_KIND && rating !== null);
  if (errors.length) return { error: errors[0] };
  try {
    await append("reviews", toReviewRow(cafeId, body, nick, kind, parentId, rating));
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
  if (!isReply) {
    payload.kind = kind;
    payload.rating = kind === RATED_KIND && rating ? String(rating) : ""; // 종류를 바꾸면 별점은 비운다
  }
  try {
    await append("reviews", payload, id);
  } catch (e) {
    return { error: say(e) };
  }
  revalidatePath(`/popup/${cur.cafe_id}`);
  return { ok: "수정했습니다." };
}

export async function reviewDeleteAction(entryId: string): Promise<FormState> {
  const me = await getMe();
  if (!me) return { error: "로그인이 풀렸어요. 다시 로그인해 주세요." };
  const cur = /^[\w-]{1,64}$/.test(entryId) ? await reviewRow(entryId) : null;
  if (!cur) return { error: "이미 지워진 글이에요." };
  if (!canEdit(cur, displayName(me.row))) return { error: "내가 쓴 리뷰만 삭제할 수 있어요." };
  const payload: Row = {};
  for (const k of ["cafe_id", "parent_id", "kind", "nickname", "body", "rating", "images"]) payload[k] = cur[k] ?? "";
  try {
    await append("reviews", payload, entryId, "deleted"); // 지우지 않고 '삭제됨' 행을 쌓는다
  } catch (e) {
    return { error: say(e) };
  }
  revalidatePath(`/popup/${cur.cafe_id}`);
  return { ok: "삭제했어요." };
}
