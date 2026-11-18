import "server-only";
import { createHash, randomBytes, scrypt as scryptCb, timingSafeEqual } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";
import { promisify } from "node:util";
import { mask, scan } from "../guard";
import { same } from "../nickrule";
import { AuthError, checkState, makeState, memberKey, secretOk } from "./sign";
export { memberKey };
import { autoNickname, MAX_NICK, validateNick } from "./nick";
import { append, current, localDir, mode, rows, rpc, type Row } from "./store";

// 간편 로그인(카카오·네이버) · 아이디 로그인 · 회원 기록 — common/auth.py 를 옮긴 것.
// 같은 회원 번호(member_key) 규칙 · 같은 표(members) · 같은 DB 함수(005)라서 Streamlit 앱과 같은 계정을 쓴다.
//  - 이메일·전화번호·실명은 요청하지도 저장하지도 않는다. 카카오·네이버 고유 번호도 소금 친 해시(member_key)로만.
//  - 비밀값(AUTH_SECRET, client secret)은 서버 환경변수에만 (NEXT_PUBLIC_ 없음).

export { AuthError };
export const PROVIDER_LABEL: Record<string, string> = { kakao: "카카오", naver: "네이버", local: "아이디" };
export const WITHDRAWN = "탈퇴한 회원";

type Provider = {
  label: string;
  authorize: string;
  token: string;
  profile: string;
  idEnv: string;
  secretEnv: string;
  extra: Record<string, string>;
};

export const PROVIDERS: Record<"kakao" | "naver", Provider> = {
  kakao: {
    label: "카카오",
    authorize: "https://kauth.kakao.com/oauth/authorize",
    token: "https://kauth.kakao.com/oauth/token",
    profile: "https://kapi.kakao.com/v2/user/me",
    idEnv: "KAKAO_LOGIN_CLIENT_ID",
    secretEnv: "KAKAO_LOGIN_CLIENT_SECRET",
    extra: { prompt: "select_account" }, // 늘 계정 고르는 화면 (로그아웃 뒤 다른 계정으로)
  },
  naver: {
    label: "네이버",
    authorize: "https://nid.naver.com/oauth2.0/authorize",
    token: "https://nid.naver.com/oauth2.0/token",
    profile: "https://openapi.naver.com/v1/nid/me",
    idEnv: "NAVER_LOGIN_CLIENT_ID",
    secretEnv: "NAVER_LOGIN_CLIENT_SECRET",
    extra: { auth_type: "reauthenticate" },
  },
};
export type ProviderKey = keyof typeof PROVIDERS;
const PROVIDER_KEYS = Object.keys(PROVIDERS);

export type Identity = { provider: string; memberKey: string; nickname: string; avatar: string };

/** 시험용 가짜 간편 로그인: WEB_STORAGE=local 이고 WEB_OAUTH_MOCK=1 일 때만 (배포에서는 켜지지 않는다) */
export function oauthMock(): boolean {
  return mode() === "local" && process.env.WEB_OAUTH_MOCK === "1";
}

export function siteUrl(): string {
  return (process.env.SITE_URL || "https://ani-where.vercel.app").replace(/\/+$/, "");
}

export function redirectUri(): string {
  return `${siteUrl()}/auth`;
}

export function enabled(provider: string): boolean {
  if (!secretOk()) return false;
  if (oauthMock()) return provider in PROVIDERS;
  const p = PROVIDERS[provider as ProviderKey];
  if (!p || !process.env[p.idEnv]) return false;
  return provider !== "naver" || !!process.env[p.secretEnv]; // 네이버는 secret 필수
}

export function authorizeUrl(provider: ProviderKey): string {
  const state = makeState(provider);
  if (oauthMock()) return `/auth/mock?provider=${provider}&state=${encodeURIComponent(state)}`;
  const p = PROVIDERS[provider];
  const q = new URLSearchParams({
    response_type: "code",
    client_id: process.env[p.idEnv] || "",
    redirect_uri: redirectUri(),
    state,
    ...p.extra,
  });
  return `${p.authorize}?${q}`;
}

export function cleanNick(nick: string): string {
  return [
    ...mask(
      String(nick || "")
        .split(/\s+/)
        .filter(Boolean)
        .join(" "),
    ),
  ]
    .slice(0, MAX_NICK)
    .join("");
}

const AVATAR_URL = /^https:\/\/[A-Za-z0-9._~:/?#[\]@!$&()*+,;=%-]+$/;
const AVATAR_FILE = /^[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)$/;

/** auth.clean_avatar: https 주소 · static/uploads 파일 이름 · 'none' · '' 만 */
export function cleanAvatar(value: unknown): string {
  let v = String(value ?? "").trim();
  if (v === "none") return v;
  if (v.startsWith("http://")) v = "https://" + v.slice(7);
  if (v.length <= 500 && AVATAR_URL.test(v)) return v;
  if (AVATAR_FILE.test(v)) return v;
  // 시험용 local 모드에서 올린 사진 (/uploads/<12자>.webp)
  if (mode() === "local" && /^\/uploads\/[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)$/.test(v)) return v;
  return "";
}

/** 리뷰·수정 이력에 쓰는 이름 '닉네임#m1a2b' (끝의 #m네 글자로 '내 글' 을 알아본다) */
export function displayName(row: Row): string {
  return `${row.nickname || ""}#m${String(row.entry_id).slice(0, 4)}`;
}

// ------------------------------------------------------------------ 회원 기록
export async function allMembers(): Promise<Row[]> {
  return current(await rows("members"));
}

/** 가입한 회원이면 최신 행, 아니면(탈퇴했으면) null */
export async function findMember(key: string): Promise<Row | null> {
  if (!key) return null;
  const mine = current(await rows("members", { entry_id: key }));
  return mine[0] ?? null;
}

export async function nickTaken(nickname: string, exceptKey = ""): Promise<boolean> {
  return (await allMembers()).some((r) => same(String(r.nickname), nickname) && String(r.entry_id) !== exceptKey);
}

async function checkUnique(nickname: string, exceptKey = ""): Promise<void> {
  if (await nickTaken(nickname, exceptKey))
    throw new AuthError("이미 다른 회원이 쓰고 있는 닉네임이에요. 다른 닉네임을 골라 주세요.");
}

const tidy = (s: string) =>
  String(s || "")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");

/** 지금 시각 '2026-11-18T13:05:09' (파이썬 time.strftime("%Y-%m-%dT%H:%M:%S") 와 같은 모양, 서버 시간대) */
function agreedNow(): string {
  const kst = new Date(Date.now() + 9 * 3600_000); // 서버가 UTC 여도 앱(한국)과 같은 시각으로
  return kst.toISOString().slice(0, 19);
}

export async function signup(ident: Identity, nickname: string): Promise<Row> {
  const errors = validateNick(nickname);
  if (errors.length) throw new AuthError(errors[0]);
  await checkUnique(nickname, ident.memberKey);
  return append(
    "members",
    { provider: ident.provider, nickname: tidy(nickname), agreed_at: agreedNow(), avatar: cleanAvatar(ident.avatar) },
    ident.memberKey,
  );
}

export async function rename(row: Row, nickname: string): Promise<Row> {
  const errors = validateNick(nickname);
  if (errors.length) throw new AuthError(errors[0]);
  await checkUnique(nickname, String(row.entry_id));
  return append(
    "members",
    { provider: row.provider, nickname: tidy(nickname), agreed_at: row.agreed_at, avatar: cleanAvatar(row.avatar) },
    String(row.entry_id),
  );
}

export async function setAvatar(row: Row, avatar: string): Promise<Row> {
  return append(
    "members",
    { provider: row.provider, nickname: row.nickname, agreed_at: row.agreed_at, avatar: cleanAvatar(avatar) },
    String(row.entry_id),
  );
}

export async function withdraw(row: Row): Promise<Row> {
  return append(
    "members",
    { provider: row.provider, nickname: "", agreed_at: "", avatar: "" },
    String(row.entry_id),
    "deleted",
  );
}

/** 가입 화면 닉네임 칸에 흐리게 보일 랜덤 닉네임 (이미 있는 닉네임·쓸 수 없는 말이면 다른 조합, 앱 _auto_nick) */
export async function suggestNick(seed = randomBytes(16).toString("hex")): Promise<string> {
  const taken = (await allMembers()).map((r) => String(r.nickname));
  for (let i = 0; i < 30; i++) {
    const cand = autoNickname(`${seed}${i || ""}`);
    if (!validateNick(cand).length && !taken.some((t) => same(t, cand))) return cand;
  }
  return autoNickname(`${seed}${Date.now()}`);
}

// ------------------------------------------------------------------ 간편 로그인 (OAuth)
const exchanged = new Map<string, [number, Identity]>(); // 같은 code 를 두 번 내지 않게 (10분)

export async function exchange(code: string, state: string): Promise<Identity> {
  const provider = checkState(state, PROVIDER_KEYS) as ProviderKey;
  const ck = createHash("sha256").update(code).digest("hex");
  const now = Date.now();
  for (const [k, [t]] of exchanged) if (now - t > 600_000) exchanged.delete(k);
  const hit = exchanged.get(ck);
  if (hit) return hit[1];
  const ident = oauthMock() ? mockIdentity(provider, code) : await realExchange(provider, code, state);
  exchanged.set(ck, [now, ident]);
  return ident;
}

function mockIdentity(provider: ProviderKey, code: string): Identity {
  // 시험용: code = 'mock-<번호>' → 그 번호의 가짜 계정 (네트워크 없음)
  const uid = code.replace(/^mock-/, "") || "1";
  return { provider, memberKey: memberKey(provider, `mock-${uid}`), nickname: cleanNick(`시험${uid}`), avatar: "" };
}

async function realExchange(provider: ProviderKey, code: string, state: string): Promise<Identity> {
  const p = PROVIDERS[provider];
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: process.env[p.idEnv] || "",
    redirect_uri: redirectUri(),
    code,
  });
  if (process.env[p.secretEnv]) body.set("client_secret", process.env[p.secretEnv] || "");
  if (provider === "naver") body.set("state", state);
  let prof: Record<string, unknown>;
  try {
    const tok = (await (
      await fetch(p.token, { method: "POST", body, cache: "no-store", signal: AbortSignal.timeout(10_000) })
    ).json()) as Record<string, unknown>;
    const access = tok.access_token;
    if (!access) {
      const why = String(tok.error_code || tok.error || "?");
      console.error(`[auth] ${provider} token 실패: ${why} ${String(tok.error_description || "").slice(0, 120)}`);
      throw new AuthError(`${p.label} 로그인 확인에 실패했어요 (${why}). 다시 시도해 주세요.`);
    }
    prof = (await (
      await fetch(p.profile, {
        headers: { Authorization: `Bearer ${access}` },
        cache: "no-store",
        signal: AbortSignal.timeout(10_000),
      })
    ).json()) as Record<string, unknown>;
  } catch (e) {
    if (e instanceof AuthError) throw e;
    throw new AuthError(`${p.label} 서버에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.`);
  }
  let uid = "";
  let nick = "";
  let pic = "";
  if (provider === "kakao") {
    uid = String(prof.id ?? "");
    const acc = (prof.kakao_account || {}) as Record<string, unknown>;
    const kp = (acc.profile || {}) as Record<string, unknown>;
    const props = (prof.properties || {}) as Record<string, unknown>;
    nick = String(kp.nickname || props.nickname || "");
    pic = kp.is_default_image
      ? ""
      : String(kp.profile_image_url || kp.thumbnail_image_url || props.profile_image || "");
  } else {
    const res = (prof.response || {}) as Record<string, unknown>;
    uid = String(res.id ?? "");
    nick = String(res.nickname || "");
    pic = String(res.profile_image || "");
  }
  if (!uid) throw new AuthError(`${p.label} 계정 정보를 받지 못했어요. 동의 화면에서 필수 항목을 확인해 주세요.`);
  return { provider, memberKey: memberKey(provider, uid), nickname: cleanNick(nick), avatar: cleanAvatar(pic) };
}

// ------------------------------------------------------------------ 아이디·비밀번호
export const LOGIN_ID_RE = /^[a-z0-9_]{4,20}$/;
export const PW_MIN = 8;
export const PW_MAX = 72;
export const MAX_FAILS = 5;
export const LOCK_SECONDS = 300;

/** auth.validate_signup */
export function validateSignup(loginId: string, pw: string, pw2: string, nickname: string): string[] {
  const errors: string[] = [];
  const lid = (loginId || "").trim().toLowerCase();
  if (!LOGIN_ID_RE.test(lid)) errors.push("아이디는 영어 소문자·숫자·밑줄(_)로 4~20자예요.");
  if (scan(lid).length) errors.push("아이디에 전화번호 같은 개인정보는 쓸 수 없어요.");
  const n = [...(pw || "")].length;
  if (!(n >= PW_MIN && n <= PW_MAX)) errors.push(`비밀번호는 ${PW_MIN}~${PW_MAX}자예요.`);
  else if (!(/[A-Za-z]/.test(pw) && /\d/.test(pw))) errors.push("비밀번호에 영문과 숫자를 함께 넣어 주세요.");
  else if (lid && pw.toLowerCase().includes(lid)) errors.push("비밀번호에 아이디를 넣지 말아 주세요.");
  if (pw !== pw2) errors.push("비밀번호 확인이 달라요.");
  return [...errors, ...validateNick(nickname)];
}

// local 모드 (시험용): credentials.json 에 scrypt 해시 (auth.py 와 같은 n=2^14, r=8, p=1, 32바이트)
const scrypt = promisify(scryptCb) as (pw: string, salt: Buffer, len: number, opt: object) => Promise<Buffer>;
const hashPw = async (pw: string, salt: Buffer) =>
  (await scrypt(pw, salt, 32, { N: 2 ** 14, r: 8, p: 1 })).toString("hex");
const credFile = () => path.join(localDir(), "credentials.json");
type Cred = { member_key: string; salt: string; hash: string };
async function credLoad(): Promise<Record<string, Cred>> {
  try {
    return JSON.parse(await fs.readFile(credFile(), "utf8"));
  } catch {
    return {};
  }
}
async function credSave(d: Record<string, Cred>) {
  await fs.mkdir(localDir(), { recursive: true });
  await fs.writeFile(credFile(), JSON.stringify(d, null, 2), "utf8");
}

export async function registerPassword(loginId: string, pw: string, pw2: string, nickname: string): Promise<Row> {
  const errors = validateSignup(loginId, pw, pw2, nickname);
  if (errors.length) throw new AuthError(errors[0]);
  const lid = loginId.trim().toLowerCase();
  const key = memberKey("local", lid);
  await checkUnique(nickname, key); // 비밀번호를 만들기 전에 막는다 (반쯤 가입되는 일 없게)
  if (mode() === "supabase") {
    if (!(await rpc<boolean>("register_login", { p_login_id: lid, p_password: pw, p_member_key: key })))
      throw new AuthError("이미 있는 아이디예요. 다른 아이디를 골라 주세요.");
  } else if (mode() === "local") {
    const d = await credLoad();
    if (d[lid]) throw new AuthError("이미 있는 아이디예요. 다른 아이디를 골라 주세요.");
    const salt = randomBytes(16);
    d[lid] = { member_key: key, salt: salt.toString("hex"), hash: await hashPw(pw, salt) };
    await credSave(d);
  } else throw new AuthError("회원 기능이 아직 설정되지 않았어요.");
  return signup({ provider: "local", memberKey: key, nickname, avatar: "" }, nickname);
}

/** 맞으면 회원 번호, 틀리면 null (아이디가 없는지 비밀번호가 틀렸는지는 알려 주지 않는다) */
export async function checkPassword(loginId: string, pw: string): Promise<string | null> {
  const lid = (loginId || "").trim().toLowerCase();
  if (!lid || !pw) return null;
  if (mode() === "supabase")
    return (await rpc<string | null>("check_login", { p_login_id: lid, p_password: pw })) || null;
  if (mode() !== "local") return null;
  const rec = (await credLoad())[lid];
  if (!rec) {
    await hashPw(pw, Buffer.alloc(16, "0")); // 없는 아이디도 같은 시간이 걸리게
    return null;
  }
  const got = Buffer.from(await hashPw(pw, Buffer.from(rec.salt, "hex")));
  const want = Buffer.from(rec.hash);
  return got.length === want.length && timingSafeEqual(got, want) ? rec.member_key : null;
}

export async function changePassword(loginId: string, old: string, nw: string, nw2: string): Promise<void> {
  const lid = (loginId || "").trim().toLowerCase();
  if (nw !== nw2) throw new AuthError("새 비밀번호 확인이 달라요.");
  const errs = validateSignup(lid, nw, nw, "닉네임").filter((e) => e.includes("비밀번호"));
  if (errs.length) throw new AuthError(errs[0]);
  if (mode() === "supabase") {
    if (!(await rpc<boolean>("change_password", { p_login_id: lid, p_old: old, p_new: nw })))
      throw new AuthError("아이디나 지금 비밀번호가 맞지 않아요.");
    return;
  }
  if (!(await checkPassword(lid, old))) throw new AuthError("아이디나 지금 비밀번호가 맞지 않아요.");
  const d = await credLoad();
  const salt = randomBytes(16);
  d[lid] = { ...d[lid], salt: salt.toString("hex"), hash: await hashPw(nw, salt) };
  await credSave(d);
}

export async function dropPassword(loginId: string, pw: string): Promise<void> {
  const lid = (loginId || "").trim().toLowerCase();
  if (mode() === "supabase") {
    if (!(await rpc<boolean>("drop_login", { p_login_id: lid, p_password: pw })))
      throw new AuthError("아이디나 비밀번호가 맞지 않아요.");
    return;
  }
  if (!(await checkPassword(lid, pw))) throw new AuthError("아이디나 비밀번호가 맞지 않아요.");
  const d = await credLoad();
  delete d[lid];
  await credSave(d);
}

/** 탈퇴 직후 지난 기록 파기 (009 purge_withdrawn, 법적 파기 의무라 예외로 예전 행을 고친다).
 *  supabase 는 DB 함수만 부른다. local(시험용)은 파일을 직접 고친다 — 앱 auth.purge_withdrawn 과 같다 */
export async function purgeWithdrawn(key: string): Promise<boolean> {
  if (mode() === "supabase") {
    try {
      return !!(await rpc<boolean>("purge_withdrawn", { p_member_key: key }));
    } catch {
      return false;
    }
  }
  if (mode() !== "local") return false;
  const tag = `#m${key.slice(0, 4)}`;
  const rewrite = async (name: string, fn: (rs: Row[]) => Row[]) => {
    const file = path.join(localDir(), `${name}.json`);
    try {
      const all = JSON.parse(await fs.readFile(file, "utf8")) as Row[];
      await fs.writeFile(file, JSON.stringify(fn(all), null, 2), "utf8");
    } catch {
      /* 파일이 없으면 지울 것도 없다 */
    }
  };
  await rewrite("members", (rs) =>
    rs.map((r) => (String(r.entry_id) === key ? { ...r, nickname: "", avatar: "" } : r)),
  );
  await rewrite("reviews", (rs) =>
    rs.map((r) => (String(r.nickname).endsWith(tag) ? { ...r, nickname: WITHDRAWN + tag } : r)),
  );
  await rewrite("visits", (rs) => rs.filter((r) => String(r.member) !== key));
  await rewrite("notices", (rs) => rs.filter((r) => String(r.target) !== key));
  const d = await credLoad();
  for (const [lid, v] of Object.entries(d)) if (v.member_key === key) delete d[lid];
  await credSave(d);
  return true;
}

/** 관리자: ADMIN_MEMBER_KEYS(쉼표로 구분한 회원 번호). 비워 두면 앱과 같은 기본 관리자 한 명 */
const DEFAULT_ADMIN = "f37119a9dd2d4c0b";
export function isAdmin(key: string): boolean {
  const keys = (process.env.ADMIN_MEMBER_KEYS || DEFAULT_ADMIN)
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);
  return !!key && keys.includes(key);
}

/** 오늘 처음 들어온 회원 한 줄 (관리자 '이용 지표', admin.log_visit). 실패해도 화면은 그대로 */
export async function logVisit(key: string): Promise<void> {
  const day = new Date(Date.now() + 9 * 3600_000).toISOString().slice(0, 10);
  const entry = `${key}:${day}`;
  try {
    if ((await rows("visits", { entry_id: entry })).length) return;
    await append("visits", { member: key, day }, entry);
  } catch {
    /* 기록이 실패해도 로그인은 그대로 */
  }
}
