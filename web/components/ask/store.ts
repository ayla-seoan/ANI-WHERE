"use client";
import { useSyncExternalStore } from "react";
import { answer, CARD_MAX, headOf, needsLocation, type AskResult, type LatLng } from "@/lib/ask";
import type { Item } from "@/lib/popup";

// 물어보기 대화 기록. 이 탭의 메모리에만 둔다 (지도 ↔ 리스트로 옮겨도 이어지고, 새로 고치면 사라진다).
// 질문·위치는 localStorage·서버 어디에도 저장하거나 보내지 않는다.

export type MeMsg = { role: "me"; text: string };
export type BotMsg = {
  role: "bot";
  text: string;
  /** 카드로 보이는 팝업 (최대 5건) */
  cards: Item[];
  distances: Record<string, number>;
  /** 카드보다 더 찾았으면: 리스트로 보기로 넘길 전부 */
  more: { ids: string[]; label: string } | null;
  head: string;
  guide: boolean;
  links: [string, string][];
};
export type Msg = MeMsg | BotMsg | { role: "wait" };

let msgs: Msg[] = [];
let loc: LatLng | null | undefined; // undefined = 아직 안 물어봄, null = 거절·실패
const subs = new Set<() => void>();
const EMPTY: Msg[] = [];

function set(next: Msg[]) {
  msgs = next.slice(-30); // 너무 길어지지 않게 최근 것만 (앱은 20개)
  subs.forEach((f) => f());
}

export function useChat(): Msg[] {
  return useSyncExternalStore(
    (f) => {
      subs.add(f);
      return () => subs.delete(f);
    },
    () => msgs,
    () => EMPTY,
  );
}

function askLocation(): Promise<LatLng | null> {
  if (loc !== undefined) return Promise.resolve(loc);
  if (typeof navigator === "undefined" || !navigator.geolocation) return Promise.resolve((loc = null));
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (p) => resolve((loc = { lat: p.coords.latitude, lng: p.coords.longitude })),
      () => resolve((loc = null)),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    );
  });
}

function toBot(q: string, res: AskResult): BotMsg {
  const intent = res.query.intent;
  const cards = res.hits.slice(0, CARD_MAX);
  let head = intent && res.hits.length ? headOf(intent) : "";
  if (intent === "near" && res.hits.length) head = `${head} ${res.hits.length}건 팝업이에요`;
  return {
    role: "bot",
    text: res.text,
    cards,
    distances: res.distances,
    more: res.hits.length > cards.length ? { ids: res.hits.map((h) => h.id), label: q.slice(0, 40) } : null,
    head,
    guide: res.guide,
    links: res.links,
  };
}

/** 질문 보내기: 내 기록 → (필요하면 위치 묻기) → 규칙으로 답 */
export async function send(question: string, items: Item[], today: string): Promise<void> {
  const q = question.trim().slice(0, 200);
  if (!q) return;
  set([...msgs, { role: "me", text: q }]);
  let here: LatLng | null = null;
  if (needsLocation(q, items, today)) {
    set([...msgs, { role: "wait" }]);
    here = await askLocation();
    set(msgs.filter((m) => m.role !== "wait"));
  }
  set([...msgs, toBot(q, answer(q, items, today, { loc: here }))]);
}
