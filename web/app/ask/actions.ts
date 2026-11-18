"use server";
import { getPopupData } from "@/lib/data";
import { answer, MAX_QUESTION } from "@/lib/ask";
import { mask } from "@/lib/guard";
import { todayKST, toItem, type Popup } from "@/lib/popup";
import { badgeOf, callStructured } from "@/lib/server/askai";

// /ask 화면의 'AI 로 답 다듬기' (앱 ask.answer 의 AI 부분). 규칙으로 찾은 후보(최대 6곳) 안에서만 답하게 하고,
// 첫 문장은 늘 규칙으로 센 건수, 그 뒤에 AI 설명을 붙인다. 키가 없거나 실패하면 규칙 기반 대체.
// 질문은 guard.mask() 를 거친 뒤에만 OpenAI 로 보낸다. 질문은 어디에도 저장하지 않는다.

const TOP_K = 6;
const WEEK = "월화수목금토일";

export type AskAiResult = {
  /** 규칙 답과 같은 질문 경로(작품·지역·날짜 검색)가 아니면 false → 화면은 규칙 답 그대로 */
  applies: boolean;
  text: string;
  hitIds: string[];
  usedIds: string[];
  dropped: number;
  confidence: "high" | "low";
  source: "ai" | "fallback";
  badge: string;
};

type AskAnswer = { answer: string; used_ids: string[]; confidence: "high" | "low" };

// common/schema.py AskAnswer 와 같은 모양
const SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["answer", "used_ids", "confidence"],
  properties: {
    answer: { type: "string", description: "질문에 대한 답. 후보 팝업 정보에 있는 사실만, 3~5문장" },
    used_ids: { type: "array", items: { type: "string" }, description: "답에 쓴 팝업의 id. 후보 목록의 id 그대로" },
    confidence: {
      type: "string",
      enum: ["high", "low"],
      description: "후보 중 질문 조건(작품·지역·날짜)에 딱 맞는 팝업이 없으면 low",
    },
  },
};

function validate(v: unknown): AskAnswer | null {
  if (!v || typeof v !== "object") return null;
  const o = v as Record<string, unknown>;
  if (typeof o.answer !== "string" || [...o.answer].length > 600) return null;
  if (!Array.isArray(o.used_ids) || !o.used_ids.every((x) => typeof x === "string")) return null;
  if (o.confidence !== "high" && o.confidence !== "low") return null;
  return { answer: o.answer, used_ids: o.used_ids as string[], confidence: o.confidence };
}

/** 앱 Query.describe() */
function describe(q: { works: string[]; characters: string[]; places: string[]; windowLabel: string }): string {
  const parts: string[] = [];
  if (q.works.length) parts.push("작품 " + q.works.join(", "));
  if (q.characters.length) parts.push("캐릭터 " + q.characters.join(", "));
  if (q.places.length) parts.push("지역 " + q.places.join(", "));
  if (q.windowLabel) parts.push(q.windowLabel);
  return parts.join(" · ") || "조건 없음 (낱말로만 찾음)";
}

/** 앱 ask._card: 후보 팝업 한 줄 (주소·소개는 가린 뒤) */
function card(p: Popup, today: string): string {
  const state = p.end && p.end < today ? "종료" : p.start && p.start > today ? "예정" : "진행 중";
  const intro = [...mask(p.intro || "")].slice(0, 160).join("").replace(/\n/g, " ");
  return (
    `- id: ${p.id} | ${p.work} · ${p.name} | ${p.start} ~ ${p.end} (${state}) | ${p.area} ${mask(p.address || "")} | ` +
    `특전: ${p.perks.join(", ") || "-"} | 소개: ${intro || "-"}`
  );
}

export async function askAi(question: string): Promise<AskAiResult> {
  const q = mask(String(question || "").trim()).slice(0, MAX_QUESTION);
  const today = todayKST();
  const { popups } = await getPopupData();
  const items = popups.map(toItem);
  const res = answer(q, items, today);
  const none: AskAiResult = {
    applies: false,
    text: res.text,
    hitIds: [],
    usedIds: [],
    dropped: 0,
    confidence: "low",
    source: "fallback",
    badge: badgeOf("rule"),
  };
  // 자주 묻는 질문 · 못 알아들음 · 0건은 규칙 답 그대로 (앱과 같게 AI 를 부르지 않는다)
  if (res.guide || res.query.intent || !res.hits.length) return none;
  const hits = res.hits.slice(0, TOP_K);
  const byId = new Map(popups.map((p) => [p.id, p]));
  const head = res.text;
  const content =
    `질문: ${q}\n오늘: ${today} (${WEEK[(new Date(`${today}T00:00:00Z`).getUTCDay() + 6) % 7]})\n` +
    `질문에서 읽은 조건: ${describe(res.query)}\n조건에 모두 맞는 팝업 수: ${res.hits.length}건\n\n[후보 팝업]\n` +
    hits
      .map((h) => byId.get(h.id))
      .filter((p): p is Popup => Boolean(p))
      .map((p) => card(p, today))
      .join("\n");
  const rule = (): AskAnswer => ({
    answer: "",
    used_ids: hits.slice(0, 3).map((h) => h.id),
    confidence: "high",
  });
  const out = await callStructured<AskAnswer>({
    prompt: "ask",
    content,
    schemaName: "AskAnswer",
    schema: SCHEMA,
    validate,
    fallback: rule,
  });
  const data = out.data ?? rule();
  const allowed = new Set(hits.map((h) => h.id));
  const used = data.used_ids.filter((i) => allowed.has(i));
  const dropped = data.used_ids.filter((i) => !allowed.has(i)).length;
  const extra = out.source === "ai" ? mask(data.answer) : "";
  return {
    applies: true,
    text: head + (extra ? "\n" + extra : ""),
    hitIds: hits.map((h) => h.id),
    usedIds: used,
    dropped,
    confidence: data.confidence,
    source: out.source,
    badge: badgeOf(out.source),
  };
}
