import "server-only";
import { cache } from "react";
import { tierOf } from "../stamp";
import { current, rows } from "./store";

// 후기 도장 수 (lib/stamp.ts 규칙). 리뷰 기록에서 센다 — 새 표 · 새 칸 없음.
const RATED_KIND = "다녀온 후기";
const tagOf = (nick: string) => (nick.includes("#") ? nick.slice(nick.lastIndexOf("#") + 1) : nick);

/** 글쓴이 꼬리표(닉네임 끝 '#m1a2b') → 도장 수. 한 요청 안에서는 한 번만 읽는다. 못 읽으면 빈 표 (도장 없이 보여 준다) */
export const stampCounts = cache(async (): Promise<Map<string, number>> => {
  const out = new Map<string, number>();
  try {
    const seen = new Set<string>();
    for (const r of current(await rows("reviews"))) {
      if (String(r.parent_id || "") || String(r.kind || "") !== RATED_KIND) continue;
      const nick = String(r.nickname || "");
      // 회원 글만 센다 (꼬리표가 'm' 으로 시작). 손님 닉네임(IP 꼬리표)과 탈퇴한 회원은 도장이 없다
      const tag = nick.includes("#") ? tagOf(nick) : "";
      if (!tag.startsWith("m") || nick.startsWith("탈퇴한 회원")) continue;
      const key = `${tag}|${String(r.cafe_id)}`;
      if (seen.has(key)) continue; // 같은 팝업은 1개
      seen.add(key);
      out.set(tag, (out.get(tag) ?? 0) + 1);
    }
  } catch {
    /* 저장소를 못 읽으면 도장 없이 */
  }
  return out;
});

/** 저장된 닉네임('닉네임#m1a2b') → 랭크 단계 (0 = 도장 없음) */
export async function lvOfNick(): Promise<(nick: string) => number> {
  const counts = await stampCounts();
  return (nick: string) => {
    const text = String(nick || "");
    return text.includes("#") ? (tierOf(counts.get(tagOf(text)) ?? 0)?.lv ?? 0) : 0;
  };
}

/** 내 도장 수 (myName = 회원의 저장용 이름 '닉네임#m1a2b') */
export async function myStamps(myName: string): Promise<number> {
  return myName ? ((await stampCounts()).get(tagOf(myName)) ?? 0) : 0;
}
