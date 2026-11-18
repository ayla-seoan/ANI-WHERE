// 닉네임: 검사(auth.validate_nick) · 자동 닉네임(review.auto_nickname) — 파이썬과 같은 결과가 나오게 옮긴 것.
// 서버 전용 (node:crypto). 점검 스크립트가 node 로 직접 불러서 "server-only" 는 붙이지 않는다.
import { createHash } from "node:crypto";
import { scan } from "../guard";
import { problem } from "../nickrule";
import SNAPSHOT from "./characters.json";

export const MAX_NICK = 10; // auth.MAX_NICK (11/18: 10자 이내. 랜덤 닉네임도 같게)

// review._ADJ 와 같은 순서 (순서가 바뀌면 같은 seed 에서 다른 닉네임이 나온다)
const ADJ = [
  "졸린",
  "배고픈",
  "신난",
  "수줍은",
  "용감한",
  "느긋한",
  "반짝이는",
  "꼼꼼한",
  "엉뚱한",
  "다정한",
  "씩씩한",
  "조용한",
  "행복한",
  "부지런한",
  "말랑한",
  "새침한",
  "꾸벅꾸벅 조는",
  "덕질하는",
  "굿즈 줍는",
  "줄 서는",
  "특전 노리는",
  "오픈런하는",
  "설레는",
  "두근두근",
  "방방 뛰는",
  "몰래 웃는",
  "커피 마시는",
  "산책하는",
  "노래하는",
  "춤추는",
  "길 잃은",
  "모험하는",
  "꿈꾸는",
  "반쯤 깬",
  "포근한",
  "까칠한",
  "쿨한",
  "수상한",
  "비밀스러운",
  "명랑한",
  "빛나는",
  "통통 튀는",
  "느릿느릿",
  "재빠른",
  "엉금엉금",
  "콧노래 부르는",
  "볼 빵빵한",
  "눈 반짝",
  "든든한",
  "귀여운",
  "멋쟁이",
  "낭만적인",
  "호기심 많은",
  "똑똑한",
  "덤벙대는",
  "늦잠 잔",
  "야식 먹는",
  "사진 찍는",
  "포카 모으는",
  "아크릴 든",
  "티켓 쥔",
  "응원하는",
  "기다리는",
  "웃음 많은",
];
const NOUN_FALLBACK = ["고양이", "토끼", "펭귄", "여우", "수달", "다람쥐", "판다", "햄스터"];

const len = (s: string) => [...s].length; // 파이썬 len 과 같게 (글자 수)

/** 닉네임 뒤에 붙일 캐릭터 이름들 (data/anime_catalog.json 의 캐릭터, 중복 없이 글자 코드 순).
 *  지금 목록은 lib/server/characters.json (scripts/make_characters.py 로 다시 만든다) */
export function characterNames(): string[] {
  const names = (SNAPSHOT as string[]).filter((n) => n && n.trim());
  return names.length ? names : NOUN_FALLBACK;
}

/** review.auto_nickname: 같은 seed 면 늘 같은 '꾸밈말 + 캐릭터', max_len 을 넘으면 캐릭터의 마지막 이름만 */
export function autoNickname(seed: string, maxLen = MAX_NICK, names = characterNames()): string {
  const h = createHash("sha256").update(`member-nick:${seed}`, "utf8").digest("hex");
  const pool = names.filter((n) => !n.includes("#"));
  const list = pool.length ? pool : NOUN_FALLBACK;
  const name = list[parseInt(h.slice(20, 28), 16) % list.length];
  const words = name.split(/\s+/).filter(Boolean);
  const last = words.length ? words[words.length - 1] : name;
  const start = parseInt(h.slice(12, 20), 16) % ADJ.length;
  for (const nm of [...new Set([name, last])]) {
    for (let i = 0; i < ADJ.length; i++) {
      const nick = `${ADJ[(start + i) % ADJ.length]} ${nm}`;
      if (len(nick) <= maxLen) return nick;
    }
  }
  if (len(last) >= 2 && len(last) <= maxLen) return last;
  return len(last) >= 2 ? [...last].slice(0, maxLen).join("") : NOUN_FALLBACK[0];
}

/** auth.validate_nick */
export function validateNick(nick: string): string[] {
  const n = String(nick || "")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
  const errors: string[] = [];
  if (len(n) < 2) errors.push("닉네임은 2자 이상 적어 주세요.");
  if (len(n) > MAX_NICK) errors.push(`닉네임은 ${MAX_NICK}자까지예요.`);
  if (n.includes("#")) errors.push("닉네임에 # 은 쓸 수 없어요 (뒤에 자동으로 붙어요).");
  if (scan(n).length) errors.push("닉네임에 전화번호·이메일 같은 개인정보는 넣을 수 없어요.");
  const bad = problem(n);
  if (bad === "사칭") errors.push("관리자·운영자로 오해할 수 있는 닉네임은 쓸 수 없어요.");
  else if (bad) errors.push("욕설이나 음란한 말이 든 닉네임은 쓸 수 없어요. 다른 닉네임을 골라 주세요.");
  return errors;
}
