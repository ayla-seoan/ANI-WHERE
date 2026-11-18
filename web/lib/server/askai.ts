import "server-only";
import { randomUUID } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";

// OpenAI 호출 한 곳 (웹) — common/ai.py call_structured 를 옮긴 것.
//  1. 프롬프트는 코드에 두지 않고 content/prompts/<이름>.<버전>.txt 를 읽는다 (원본 common/prompts, scripts/sync_docs.mjs 가 옮김).
//     버전: 인자 → <NAME>_PROMPT_VERSION → PROMPT_VERSION → 가장 높은 버전 파일.
//  2. Structured Outputs(JSON 스키마 strict)로 모양을 강제하고, 받은 뒤에도 validate 로 한 번 더 검사한다 (Pydantic 대신).
//  3. temperature 0 · seed 42 고정 (재현성). 키가 없으면 부르지 않고 바로 규칙 기반 대체.
//  4. 실패하면 한 번 더 해 보고, 그래도 안 되면 fallback. 호출 기록은 서버 로그에 한 줄(JSON)로 남긴다 (질문 글은 남기지 않는다).
// 보내는 글은 부르는 쪽에서 guard.mask() 를 거친다. OPENAI_API_KEY 는 서버 환경변수에만.

const PROMPT_DIR = path.join(process.cwd(), "content", "prompts");

export type AIResult<T> = {
  ok: boolean;
  data: T | null;
  source: "ai" | "fallback";
  error: string | null;
  elapsedMs: number;
  promptVersion: string;
  attempts: number;
};

export const badgeOf = (source: string) => (source === "ai" ? "AI 산출" : "규칙 기반 대체");

async function latestVersion(name: string): Promise<string> {
  try {
    const found = (await fs.readdir(PROMPT_DIR))
      .map((f) => f.match(new RegExp(`^${name}\\.v(\\d+)\\.txt$`)))
      .filter((m): m is RegExpMatchArray => Boolean(m))
      .map((m) => Number(m[1]));
    return found.length ? `v${Math.max(...found)}` : "v1";
  } catch {
    return "v1";
  }
}

/** content/prompts/<name>.<version>.txt 를 읽는다 → [본문, 버전] */
export async function loadPrompt(name: string, version?: string): Promise<[string, string]> {
  const v =
    version ||
    process.env[`${name.toUpperCase()}_PROMPT_VERSION`] ||
    process.env.PROMPT_VERSION ||
    (await latestVersion(name));
  if (!/^v\d+$/.test(v)) throw new Error(`프롬프트 버전 형식이 아닙니다: ${v}`);
  const text = await fs.readFile(path.join(PROMPT_DIR, `${name}.${v}.txt`), "utf8");
  return [text, v];
}

function log(rec: Record<string, unknown>) {
  console.info("[ai-run] " + JSON.stringify(rec));
}

async function callOpenAI(
  system: string,
  user: string,
  schemaName: string,
  schema: Record<string, unknown>,
  timeoutMs: number,
): Promise<unknown> {
  const key = (process.env.OPENAI_API_KEY || "").trim();
  if (!key) throw new Error("OPENAI_API_KEY 가 설정되지 않았습니다.");
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
        { role: "system", content: system },
        { role: "user", content: user },
      ],
      response_format: { type: "json_schema", json_schema: { name: schemaName, strict: true, schema } },
    }),
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) {
    const e = new Error(`HTTP ${res.status}`);
    e.name = [401, 403].includes(res.status) ? "Authentication" : res.status === 429 ? "RateLimit" : "HTTPError";
    throw e;
  }
  const body = (await res.json()) as {
    choices?: { message?: { content?: string | null; refusal?: string | null } }[];
  };
  const msg = body.choices?.[0]?.message;
  if (msg?.refusal) throw new Error(`모델이 거부했습니다: ${msg.refusal}`);
  if (!msg?.content) throw new Error("스키마를 통과한 응답이 없습니다.");
  return JSON.parse(msg.content);
}

/** 프롬프트 + 입력 → 스키마를 통과한 값. fallback 이 있으면 AI 가 끝내 실패해도 규칙 기반 결과를 돌려준다 */
export async function callStructured<T>(opts: {
  prompt: string;
  content: string;
  schemaName: string;
  schema: Record<string, unknown>;
  validate: (v: unknown) => T | null;
  fallback?: () => T;
  version?: string;
  maxAttempts?: number;
  timeoutMs?: number;
}): Promise<AIResult<T>> {
  const runId = randomUUID().replace(/-/g, "").slice(0, 8);
  const started = Date.now();
  let version = "";
  let lastError: string | null = null;
  let attempts = opts.maxAttempts ?? 2;
  let system = "";
  try {
    [system, version] = await loadPrompt(opts.prompt, opts.version);
  } catch (e) {
    attempts = 0;
    lastError = `PromptError: ${e instanceof Error ? e.message : e}`;
  }
  // 키가 없으면 부르지 않고 바로 규칙 기반으로 (질문마다 기다리지 않게)
  if (attempts && !(process.env.OPENAI_API_KEY || "").trim()) {
    attempts = 0;
    lastError = "RuntimeError: OPENAI_API_KEY 없음";
  }
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      const raw = await callOpenAI(system, opts.content, opts.schemaName, opts.schema, opts.timeoutMs ?? 25_000);
      const data = opts.validate(raw);
      if (data === null) throw new Error("ValidationError: 스키마를 통과하지 못했습니다.");
      const elapsedMs = Date.now() - started;
      log({ run_id: runId, at: new Date().toISOString(), prompt: opts.prompt, version, attempt, ok: true, elapsed_ms: elapsedMs, input_chars: opts.content.length, app: "web" });
      return { ok: true, data, source: "ai", error: null, elapsedMs, promptVersion: version, attempts: attempt };
    } catch (e) {
      const name = e instanceof Error ? e.name : "Error";
      lastError = `${name}: ${e instanceof Error ? e.message : e}`;
      // 인증·할당량 오류는 다시 해도 같아서 기다리지 않고 바로 규칙 기반으로
      if (["Authentication", "RateLimit"].includes(name)) break;
      if (attempt < attempts) await new Promise((r) => setTimeout(r, 1500 * attempt));
    }
  }
  const elapsedMs = Date.now() - started;
  log({ run_id: runId, at: new Date().toISOString(), prompt: opts.prompt, version, attempt: attempts, ok: false, error: lastError, elapsed_ms: elapsedMs, app: "web" });
  if (opts.fallback)
    return { ok: true, data: opts.fallback(), source: "fallback", error: lastError, elapsedMs, promptVersion: version, attempts };
  return { ok: false, data: null, source: "fallback", error: lastError, elapsedMs, promptVersion: version, attempts };
}
