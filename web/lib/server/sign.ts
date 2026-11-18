// 서버 전용 (node:crypto). 점검 스크립트(scripts/auth_check.ts)가 node 로 직접 불러서 "server-only" 는 붙이지 않는다.
import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";

// 서명 (common/auth.py _sign · _b64 · make_session · read_session · make_state · check_state 와 같은 형식).
// 같은 AUTH_SECRET 이면 Streamlit 앱이 만든 로그인 쿠키를 이 웹이 읽고, 이 웹이 만든 쿠키도 앱이 읽는다.
//   토큰 = base64url(JSON, '=' 없음) + '.' + HMAC-SHA256(AUTH_SECRET, 몸통) 16진수 앞 32자

export const COOKIE = "aw_session";
export const SESSION_DAYS = 30;
export const STATE_MAX_AGE = 600; // 동의 화면에서 10분 안에 돌아와야 한다

export class AuthError extends Error {} // 화면에 그대로 보여 줘도 되는 한국어 메시지만

export function secretOk(): boolean {
  return (process.env.AUTH_SECRET || "").length >= 16;
}

function secret(): string {
  const s = process.env.AUTH_SECRET || "";
  if (s.length < 16) throw new AuthError("로그인 설정이 끝나지 않았어요 (AUTH_SECRET). 관리자에게 알려 주세요.");
  return s;
}

export function sign(payload: string): string {
  return createHmac("sha256", secret()).update(payload, "utf8").digest("hex").slice(0, 32);
}

function sameSig(a: string, b: string): boolean {
  const x = Buffer.from(a, "utf8");
  const y = Buffer.from(b, "utf8");
  return x.length === y.length && timingSafeEqual(x, y);
}

/** 파이썬 json.dumps(separators=(",", ":")) 와 같은 모양: 한글 등은 \uXXXX 로 (ensure_ascii) */
function pyJson(data: unknown): string {
  return JSON.stringify(data).replace(/[\u007f-￿]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
}

export function b64(data: unknown): string {
  return Buffer.from(pyJson(data), "utf8").toString("base64url");
}

export function unb64<T = Record<string, unknown>>(s: string): T {
  return JSON.parse(Buffer.from(s, "base64url").toString("utf8")) as T;
}

/** 서명한 짧은 토큰 (몸통.서명) */
export function signed(data: unknown): string {
  const body = b64(data);
  return `${body}.${sign(body)}`;
}

/** 서명이 맞으면 몸통 JSON, 아니면 null */
export function verified<T = Record<string, unknown>>(token: string | null | undefined): T | null {
  if (!token || !token.includes(".")) return null;
  try {
    const i = token.lastIndexOf(".");
    const body = token.slice(0, i);
    const sig = token.slice(i + 1);
    if (!sameSig(sig, sign(body))) return null;
    return unb64<T>(body);
  } catch {
    return null;
  }
}

export type Session = { k: string; p: string; e: number };

export function makeSession(memberKey: string, provider: string, now = Date.now()): string {
  return signed({ k: memberKey, p: provider, e: Math.floor(now / 1000) + SESSION_DAYS * 86400 });
}

/** 쿠키 → {k: 회원 번호, p: 로그인 수단}. 서명이 틀렸거나 만료면 null (AUTH_SECRET 이 없어도 null) */
export function readSession(token: string | null | undefined, now = Date.now()): Session | null {
  if (!secretOk()) return null;
  const data = verified<Session>(token);
  if (!data || typeof data.k !== "string") return null;
  return Number(data.e || 0) > now / 1000 ? data : null;
}

export function makeState(provider: string): string {
  return signed({ p: provider, n: randomBytes(6).toString("base64url"), t: Math.floor(Date.now() / 1000) });
}

export function checkState(state: string, providers: string[]): string {
  let data: { p?: string; t?: number } | null = null;
  let body = "";
  let sig = "";
  try {
    const i = state.lastIndexOf(".");
    if (i < 0) throw new Error();
    body = state.slice(0, i);
    sig = state.slice(i + 1);
    data = unb64(body);
  } catch {
    throw new AuthError("로그인 요청이 올바르지 않아요. 처음부터 다시 시도해 주세요.");
  }
  if (!sameSig(sig, sign(body)))
    throw new AuthError("로그인 요청이 위조됐을 수 있어 막았어요. 처음부터 다시 시도해 주세요.");
  if (Date.now() / 1000 - Number(data?.t || 0) > STATE_MAX_AGE)
    throw new AuthError("로그인 시간이 지났어요 (10분). 처음부터 다시 시도해 주세요.");
  if (!data?.p || !providers.includes(data.p)) throw new AuthError("알 수 없는 로그인 방법이에요.");
  return data.p;
}

/** 회원 번호 (auth.member_key): 카카오·네이버 고유 번호 · 아이디를 그대로 두지 않고 소금 친 해시 앞 16자 */
export function memberKey(provider: string, uid: string): string {
  const salt = process.env.REVIEW_NICK_SALT || "popup-cafe-map";
  return createHash("sha256").update(`${salt}:member:${provider}:${uid}`, "utf8").digest("hex").slice(0, 16);
}
