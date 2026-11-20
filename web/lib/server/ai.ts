import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { mask } from "@/lib/guard";
import { RAW_ROOT, rawHeaders } from "./github";

// OpenAI 호출 한 곳 (common/ai.py call_structured 를 옮긴 것).
//  - 프롬프트는 코드에 두지 않고 common/prompts/<이름>.<버전>.txt 를 서버에서 읽는다
//    (저장소의 파일을 먼저, 배포 묶음에 없으면 같은 저장소의 GitHub 공개 파일).
//    버전: <이름>_PROMPT_VERSION → PROMPT_VERSION → 가장 높은 버전 파일.
//  - temperature=0 · seed=42 고정, Structured Outputs(json_schema strict) + 받은 값 스키마 검사(schema.py 와 같은 칸).
//  - OPENAI_API_KEY 가 없으면 부르지 않고 바로 규칙 기반 대체. 실패해도 멈추지 않는다.
//  - 키는 서버 환경변수에만 (NEXT_PUBLIC_ 아님).

const REPO_RAW = `${RAW_ROOT}/common/prompts`; // lib/server/github.ts
// 배포 묶음 안의 사본(content/prompts, scripts/sync_docs.mjs 가 옮김) → 저장소 원본(../common/prompts) 차례로
const LOCAL_DIRS = [
  path.join(process.cwd(), "content", "prompts"),
  path.join(process.cwd(), "..", "common", "prompts"),
  path.join(process.cwd(), "common", "prompts"),
];

export type AIResult<T> = {
  ok: boolean;
  data: T | null;
  source: "ai" | "fallback";
  error: string | null;
  elapsedMs: number;
  promptVersion: string;
  attempts: number;
};
export const badgeOf = (r: { source: "ai" | "fallback" }) => (r.source === "ai" ? "AI 산출" : "규칙 기반 대체");

const versionCache = new Map<string, string>();
async function latestVersion(name: string): Promise<string> {
  if (versionCache.has(name)) return versionCache.get(name) as string;
  let best = 0;
  for (const dir of LOCAL_DIRS) {
    try {
      for (const f of await fs.readdir(dir)) {
        const m = new RegExp(`^${name}\\.v(\\d+)\\.txt$`).exec(f);
        if (m) best = Math.max(best, Number(m[1]));
      }
      if (best) break;
    } catch {
      /* 다음 자리 */
    }
  }
  if (!best) {
    // 배포 묶음에 프롬프트 폴더가 없으면 공개 저장소에서 v1, v2, … 차례로 있는지 본다
    for (let v = 1; v <= 20; v++) {
      try {
        const res = await fetch(`${REPO_RAW}/${name}.v${v}.txt`, { method: "HEAD", headers: rawHeaders(), cache: "no-store", signal: AbortSignal.timeout(4000) });
        if (!res.ok) break;
        best = v;
      } catch {
        break;
      }
    }
  }
  const out = `v${best || 1}`;
  versionCache.set(name, out);
  return out;
}

/** common/prompts/<name>.<version>.txt 읽기 (ai.load_prompt) */
export async function loadPrompt(name: string, version?: string): Promise<[string, string]> {
  const v =
    version || process.env[`${name.toUpperCase()}_PROMPT_VERSION`] || process.env.PROMPT_VERSION || (await latestVersion(name));
  if (!/^v\d+$/.test(v) || !/^[a-z_]+$/.test(name)) throw new Error("프롬프트 이름·버전이 올바르지 않습니다.");
  for (const dir of LOCAL_DIRS) {
    try {
      return [await fs.readFile(path.join(dir, `${name}.${v}.txt`), "utf8"), v];
    } catch {
      /* 다음 자리 */
    }
  }
  const res = await fetch(`${REPO_RAW}/${name}.${v}.txt`, { headers: rawHeaders(), cache: "force-cache", signal: AbortSignal.timeout(6000) });
  if (!res.ok) throw new Error(`프롬프트 파일이 없습니다: ${name}.${v}.txt`);
  return [await res.text(), v];
}

/** 프롬프트 + 사용자 입력 → 스키마를 통과한 값. fallback 이 있으면 AI 가 끝내 실패해도 규칙 기반 결과 */
export async function callStructured<T>(
  promptName: string,
  userContent: string,
  schema: { name: string; schema: Record<string, unknown> },
  validate: (raw: unknown) => T,
  fallback?: () => T,
  maxAttempts = 2,
  timeoutMs = 45_000,
): Promise<AIResult<T>> {
  const started = Date.now();
  const runId = Math.random().toString(16).slice(2, 10);
  let version = "";
  let lastError: string | null = null;
  let systemPrompt = "";
  try {
    [systemPrompt, version] = await loadPrompt(promptName);
  } catch (e) {
    lastError = e instanceof Error ? e.message : String(e);
    maxAttempts = 0;
  }
  const key = (process.env.OPENAI_API_KEY || "").trim();
  if (!key) {
    maxAttempts = 0;
    lastError = lastError || "RuntimeError: OPENAI_API_KEY 없음";
  }
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      // OPENAI_BASE_URL: 파이썬 openai 라이브러리와 같은 이름 (비우면 OpenAI 기본 주소)
      const base = ((process.env.OPENAI_BASE_URL || "").trim() || "https://api.openai.com/v1").replace(/\/+$/, "");
      const res = await fetch(`${base}/chat/completions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          model: process.env.OPENAI_MODEL || "gpt-4o-mini",
          temperature: 0, // 재현성 지표를 위해 고정
          seed: 42,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userContent },
          ],
          response_format: { type: "json_schema", json_schema: { name: schema.name, strict: true, schema: schema.schema } },
        }),
        cache: "no-store",
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (!res.ok) {
        const err = new Error(`OpenAI HTTP ${res.status}`);
        // 인증·권한·할당량·모델 없음은 다시 해도 같아서 바로 규칙 기반으로
        if ([401, 403, 404, 429].includes(res.status)) {
          lastError = err.message;
          break;
        }
        throw err;
      }
      const j = (await res.json()) as { choices?: { message?: { content?: string; refusal?: string } }[] };
      const msg = j.choices?.[0]?.message;
      if (msg?.refusal) throw new Error(`모델이 거부했습니다: ${msg.refusal}`);
      if (!msg?.content) throw new Error("스키마를 통과한 응답이 없습니다.");
      const data = validate(JSON.parse(msg.content));
      const elapsed = Date.now() - started;
      console.info(JSON.stringify({ run_id: runId, at: new Date().toISOString(), prompt: promptName, version, attempt, ok: true, elapsed_ms: elapsed, input_chars: userContent.length }));
      return { ok: true, data, source: "ai", error: null, elapsedMs: elapsed, promptVersion: version, attempts: attempt };
    } catch (e) {
      lastError = `${e instanceof Error ? e.name : "Error"}: ${e instanceof Error ? e.message : e}`;
      if (attempt < maxAttempts) await new Promise((r) => setTimeout(r, 1500 * attempt));
    }
  }
  const elapsed = Date.now() - started;
  console.info(JSON.stringify({ run_id: runId, at: new Date().toISOString(), prompt: promptName, version, attempt: maxAttempts, ok: false, error: lastError, elapsed_ms: elapsed }));
  if (fallback)
    return { ok: true, data: fallback(), source: "fallback", error: lastError, elapsedMs: elapsed, promptVersion: version, attempts: maxAttempts };
  return { ok: false, data: null, source: "fallback", error: lastError, elapsedMs: elapsed, promptVersion: version, attempts: maxAttempts };
}

// ---------------- 팝업 공지 (cafe 프롬프트 · schema.CafeExtraction) ----------------
export type AiCafeEntry = {
  cafe_name: string;
  work: string;
  characters: string[];
  address: string;
  start_date: string;
  end_date: string;
  perks: string[];
  goods: string[];
  confidence: "high" | "low";
};

const strList = { type: "array", items: { type: "string" } };
export const CAFE_SCHEMA = {
  name: "CafeExtraction",
  schema: {
    type: "object",
    additionalProperties: false,
    required: ["entries"],
    properties: {
      entries: {
        type: "array",
        items: {
          type: "object",
          additionalProperties: false,
          required: ["cafe_name", "work", "characters", "address", "start_date", "end_date", "perks", "goods", "confidence"],
          properties: {
            cafe_name: { type: "string" },
            work: { type: "string", description: "작품명. 예: 귀멸의 칼날, 짱구는 못말려" },
            characters: { ...strList, description: "등장 캐릭터. 원문에 있는 것만" },
            address: { type: "string", description: "지도에 꽂을 수 있는 주소. 추측하지 말 것" },
            start_date: { type: "string", description: "YYYY-MM-DD" },
            end_date: { type: "string", description: "YYYY-MM-DD" },
            perks: { ...strList, description: "특전. 예: 입장 특전 코스터, 음료 특전 포토카드" },
            goods: { ...strList, description: "판매 굿즈. 예: 아크릴 스탠드, 캔뱃지" },
            confidence: { type: "string", enum: ["high", "low"], description: "주소나 기간이 원문에 명확히 없으면 low" },
          },
        },
      },
    },
  },
};

const isDate = (s: unknown) => typeof s === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s) && !Number.isNaN(Date.parse(s));
const isStrs = (x: unknown): x is string[] => Array.isArray(x) && x.every((s) => typeof s === "string");

/** schema.CafeExtraction 검사: 칸이 하나라도 어긋나면 실패 (규칙 기반으로 넘어간다) */
export function validateCafeExtraction(raw: unknown): AiCafeEntry[] {
  const entries = (raw as { entries?: unknown })?.entries;
  if (!Array.isArray(entries)) throw new Error("ValidationError: entries 가 목록이 아님");
  return entries.map((e: Record<string, unknown>, i) => {
    const ok =
      e &&
      typeof e.cafe_name === "string" &&
      typeof e.work === "string" &&
      typeof e.address === "string" &&
      isStrs(e.characters) &&
      isStrs(e.perks) &&
      isStrs(e.goods) &&
      isDate(e.start_date) &&
      isDate(e.end_date) &&
      (e.confidence === "high" || e.confidence === "low");
    if (!ok) throw new Error(`ValidationError: entries[${i}] 형식이 맞지 않음`);
    return e as unknown as AiCafeEntry;
  });
}

/** cafe.build_user_content — 외부로 보내기 전 민감정보를 가린다 */
export function buildUserContent(rawText: string, today: string): string {
  return (
    `오늘 날짜는 ${today} 이다. 연도가 없는 날짜는 올해로 본다.\n` +
    `아래는 애니메이션 캐릭터 팝업 카페 공지 글이다. 여러 건이 섞여 있을 수 있다.\n\n` +
    mask(rawText)
  );
}
