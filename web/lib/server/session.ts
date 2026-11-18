import "server-only";
import { cookies } from "next/headers";
import { cache } from "react";
import { findMember, isAdmin, logVisit } from "./auth";
import { myFavIds } from "./member";
import { AuthError, COOKIE, makeSession, readSession, SESSION_DAYS, signed, verified } from "./sign";
import type { Row } from "./store";

// 로그인 쿠키(aw_session): 서버가 HttpOnly · Secure · SameSite=Lax 로 심는다 (브라우저 스크립트는 못 읽는다).
// 값의 모양은 Streamlit 앱(auth.make_session)과 같아서, 같은 AUTH_SECRET 이면 서로의 쿠키를 읽을 수 있다
// (도메인이 달라 브라우저가 쿠키를 나눠 주지는 않으니, 사이트마다 따로 로그인한다).

export type Me = { key: string; provider: string; row: Row; admin: boolean };

function secureCookie(): boolean {
  return process.env.NODE_ENV === "production" && !(process.env.SITE_URL || "").startsWith("http://");
}

/** 지금 로그인한 회원 (한 요청에 한 번만 읽는다). 손님·만료·탈퇴면 null */
export const getMe = cache(async (): Promise<Me | null> => {
  const jar = await cookies();
  const sess = readSession(jar.get(COOKIE)?.value);
  if (!sess) return null;
  let row: Row | null = null;
  try {
    row = await findMember(sess.k);
  } catch (e) {
    console.error("[session] 회원 기록을 읽지 못함", e instanceof Error ? e.message : e);
    return null;
  }
  if (!row) return null;
  return { key: sess.k, provider: sess.p, row, admin: isAdmin(sess.k) };
});

/** 관리자만: 관리자가 아니면 AuthError (모든 관리자 읽기·쓰기 앞에서 서버가 다시 확인한다) */
export async function requireAdmin(): Promise<Me> {
  const me = await getMe();
  if (!me || !me.admin) throw new AuthError("관리자만 볼 수 있어요.");
  return me;
}

/** 내 북마크 팝업 id (한 요청에 한 번만). 손님이면 빈 목록 */
export const getMyFavs = cache(async (): Promise<string[]> => {
  const me = await getMe();
  if (!me) return [];
  try {
    return await myFavIds(me.key);
  } catch {
    return [];
  }
});

export async function startSession(key: string, provider: string): Promise<void> {
  const jar = await cookies();
  jar.set(COOKIE, makeSession(key, provider), {
    httpOnly: true,
    secure: secureCookie(),
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_DAYS * 86400,
  });
  await logVisit(key);
}

export async function endSession(): Promise<void> {
  const jar = await cookies();
  jar.set(COOKIE, "", { httpOnly: true, secure: secureCookie(), sameSite: "lax", path: "/", maxAge: 0 });
}

// ---- 간편 로그인으로 처음 온 사람: 가입 화면까지 들고 갈 계정 정보 (서명 · 10분) ----
const PENDING = "aw_pending";
export type Pending = { p: string; k: string; n: string; a: string; t: number };

export async function setPending(ident: { provider: string; memberKey: string; nickname: string; avatar: string }) {
  const jar = await cookies();
  jar.set(
    PENDING,
    signed({
      p: ident.provider,
      k: ident.memberKey,
      n: ident.nickname,
      a: ident.avatar,
      t: Math.floor(Date.now() / 1000),
    }),
    {
      httpOnly: true,
      secure: secureCookie(),
      sameSite: "lax",
      path: "/",
      maxAge: 600,
    },
  );
}

export async function getPending(): Promise<Pending | null> {
  const jar = await cookies();
  const v = verified<Pending>(jar.get(PENDING)?.value);
  if (!v || Date.now() / 1000 - Number(v.t || 0) > 600) return null;
  return v;
}

export async function clearPending(): Promise<void> {
  const jar = await cookies();
  jar.set(PENDING, "", { path: "/", maxAge: 0 });
}

// ---- 한 번 보이는 안내 (토스트) ----
const FLASH = "aw_flash";
/** 아이콘 종류 (앱 _toast 의 material 아이콘: check_circle · waving_hand · logout · login · error) */
export type FlashKind = "ok" | "wave" | "logout" | "login" | "error";
export async function setFlash(msg: string, kind: FlashKind = "ok"): Promise<void> {
  const jar = await cookies();
  // 값은 Next 가 쿠키에 넣을 때 한 번 인코딩한다 (여기서 또 인코딩하면 화면에 %EB%… 가 그대로 보였다)
  jar.set(FLASH, `${kind}|${msg.slice(0, 120)}`, { path: "/", maxAge: 30, sameSite: "lax" });
}
