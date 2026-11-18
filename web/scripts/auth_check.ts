// 로그인·회원 규칙이 Streamlit 앱(파이썬 common/)과 같은지 점검한다: 실행 npm run test:auth
//  1) 로그인 쿠키: 이 웹이 만든 aw_session 을 파이썬 auth.read_session 이 읽고, 파이썬 make_session 을 이 웹이 읽는다
//  2) 간편 로그인 state 도 서로 확인된다
//  3) 회원 번호(member_key) · 자동 닉네임(review.auto_nickname) · 민감정보 찾기(guard.scan) · 닉네임 검사가 같은 결과
// 시험용 AUTH_SECRET 만 쓰고, 저장소·네트워크는 건드리지 않는다.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { scan } from "../lib/guard";
import { autoNickname, validateNick } from "../lib/server/nick";
import { checkState, makeSession, makeState, memberKey, readSession } from "../lib/server/sign";

const SECRET = "test-secret-1234567890";
process.env.AUTH_SECRET = SECRET;
delete process.env.REVIEW_NICK_SALT;
const ROOT = path.resolve(__dirname, "..", "..", ".."); // .auth-check/scripts → web → 저장소 루트

function py(code: string, input: unknown): unknown {
  const out = execFileSync("python", ["-X", "utf8", "-c", code], {
    cwd: ROOT,
    input: JSON.stringify(input),
    env: { ...process.env, AUTH_SECRET: SECRET, PYTHONIOENCODING: "utf-8" },
    encoding: "utf8",
  });
  return JSON.parse(out.trim().split("\n").pop() || "null");
}

const SAMPLES_SCAN = [
  "연락 010-1234-5678 주세요",
  "메일 fan@example.com",
  "주민 900101-1234567",
  "카드 1234-5678-9012-3456",
  "계좌 110-456-789012 로",
  "가게 02-700-7200",
  "2026-11-01 오픈 12/5 까지",
  "그냥 후기예요 굿즈 많아요",
  "한글메일가나@다라.com",
];
const SAMPLES_NICK = [
  "졸린 고죠",
  "a",
  "관리자님",
  "시1발이",
  "010-1234-5678",
  "열한글자닉네임입니다요",
  "닉#네임",
  "덕질하는 토끼",
];
const SEEDS = ["", "user1", "abcdef0123456789", "kakao:12345", "아이디", "x".repeat(40)];
const UIDS: [string, string][] = [
  ["kakao", "1234567890"],
  ["naver", "AbC_dEf-123"],
  ["local", "myid_01"],
];

const pyCode = `
import json, sys
from common import auth, guard, nickrule, review
d = json.load(sys.stdin)
out = {
  "read_ts": auth.read_session(d["ts_session"]),
  "state_ts": auth.check_state(d["ts_state"]),
  "py_session": auth.make_session("f37119a9dd2d4c0b", "naver"),
  "py_state": auth.make_state("kakao"),
  "keys": [auth.member_key(p, u) for p, u in d["uids"]],
  "nicks": [review.auto_nickname(s) for s in d["seeds"]],
  "scan": [sorted({f.kind for f in guard.scan(t)}) for t in d["scan"]],
  "validate": [auth.validate_nick(n) for n in d["nick"]],
}
print(json.dumps(out, ensure_ascii=False))
`;

const tsSession = makeSession("abcd1234abcd1234", "kakao");
const got = py(pyCode, {
  ts_session: tsSession,
  ts_state: makeState("naver"),
  uids: UIDS,
  seeds: SEEDS,
  scan: SAMPLES_SCAN,
  nick: SAMPLES_NICK,
}) as {
  read_ts: { k: string; p: string; e: number } | null;
  state_ts: string;
  py_session: string;
  py_state: string;
  keys: string[];
  nicks: string[];
  scan: string[][];
  validate: string[][];
};

assert.ok(got.read_ts, "파이썬이 이 웹의 로그인 쿠키를 읽어야 한다");
assert.equal(got.read_ts!.k, "abcd1234abcd1234");
assert.equal(got.read_ts!.p, "kakao");
assert.equal(got.state_ts, "naver");
console.log("✓ 웹 쿠키 → 파이썬 read_session:", got.read_ts);

const back = readSession(got.py_session);
assert.ok(back, "이 웹이 파이썬이 만든 로그인 쿠키를 읽어야 한다");
assert.equal(back!.k, "f37119a9dd2d4c0b");
assert.equal(back!.p, "naver");
assert.equal(checkState(got.py_state, ["kakao", "naver"]), "kakao");
console.log("✓ 파이썬 make_session → 웹 readSession:", back);

// 서명을 바꾸면 거절
assert.equal(readSession(tsSession.slice(0, -1) + (tsSession.endsWith("a") ? "b" : "a")), null);
// 다른 비밀값이면 거절
process.env.AUTH_SECRET = "another-secret-12345";
assert.equal(readSession(got.py_session), null);
process.env.AUTH_SECRET = SECRET;
console.log("✓ 서명이 다르거나 비밀값이 다르면 거절");

assert.deepEqual(
  UIDS.map(([p, u]) => memberKey(p, u)),
  got.keys,
);
console.log("✓ 회원 번호(member_key) 같음:", got.keys.join(", "));

assert.deepEqual(
  SEEDS.map((s) => autoNickname(s)),
  got.nicks,
);
console.log("✓ 자동 닉네임 같음:", got.nicks.join(" / "));

assert.deepEqual(
  SAMPLES_SCAN.map((t) => [...new Set(scan(t).map((f) => f.kind))].sort()),
  got.scan,
);
console.log("✓ 민감정보 찾기 같음:", got.scan.map((k) => k.join("+") || "-").join(" | "));

assert.deepEqual(
  SAMPLES_NICK.map((n) => validateNick(n)),
  got.validate,
);
console.log("✓ 닉네임 검사 같음");
console.log("\n모든 점검 통과");
