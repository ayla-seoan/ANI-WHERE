import "server-only";
import { promises as fs } from "node:fs";
import type { SurveyRow } from "./stats";

// 사용자 테스트 설문: n8n 이 쌓은 구글 시트 '정리' 탭을 CSV 로 읽는다 (앱 _survey_rows 와 같은 주소 · 1분 기억).
// 시트 번호는 서버 환경변수 SURVEY_SHEET_ID (구글 시트 주소의 /d/ 와 /edit 사이). 없으면 화면이 연결 안내만 보여 준다.

/** 시험용 (WEB_STORAGE=local 일 때만): 구글 시트 대신 읽을 CSV 파일 (e2e 화면 점검용, 배포에는 넣지 않는다) */
const testCsv = () => ((process.env.WEB_STORAGE || "").toLowerCase() === "local" ? process.env.SURVEY_CSV_FILE || "" : "");

export const surveySheetId = () => (process.env.SURVEY_SHEET_ID || "").trim() || (testCsv() ? "local-test-sheet" : "");

/** RFC 4180 CSV (따옴표 · 따옴표 안 쉼표/줄바꿈 · "" 이스케이프) */
export function parseCsv(text: string): string[][] {
  const out: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let q = false;
  const src = text.replace(/^﻿/, "");
  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    if (q) {
      if (c === '"') {
        if (src[i + 1] === '"') {
          cell += '"';
          i++;
        } else q = false;
      } else cell += c;
    } else if (c === '"') q = true;
    else if (c === ",") {
      row.push(cell);
      cell = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && src[i + 1] === "\n") i++;
      row.push(cell);
      out.push(row);
      row = [];
      cell = "";
    } else cell += c;
  }
  if (cell || row.length) {
    row.push(cell);
    out.push(row);
  }
  return out.filter((r) => r.some((x) => x !== ""));
}

/** CSV → 머리줄을 이름으로 한 줄들 (pandas read_csv(dtype=str).fillna("") 처럼 빈칸은 '') */
export function csvRecords(text: string): SurveyRow[] {
  const [head, ...body] = parseCsv(text);
  if (!head) return [];
  const names: string[] = [];
  const seen = new Map<string, number>();
  head.forEach((h, i) => {
    let name = h.trim() || `Unnamed: ${i}`;
    const n = seen.get(name) ?? 0;
    seen.set(name, n + 1);
    if (n) name = `${name}.${n}`; // pandas 처럼 같은 이름은 .1 .2
    names.push(name);
  });
  return body.map((r) => Object.fromEntries(names.map((n, i) => [n, r[i] ?? ""])));
}

/** (줄들, 오류 글). 네트워크 · 형식 오류여도 화면이 멈추지 않게 안내만 */
export async function surveyRows(sheetId: string, tab = "정리"): Promise<{ rows: SurveyRow[]; error: string }> {
  if (testCsv()) {
    if (tab !== "정리") return { rows: [], error: "" }; // 시험용 CSV 는 정리 탭만
    try {
      return { rows: csvRecords(await fs.readFile(testCsv(), "utf8")), error: "" };
    } catch {
      return { rows: [], error: "시험용 CSV 를 읽지 못했어요." };
    }
  }
  if (!/^[\w-]{10,200}$/.test(sheetId)) return { rows: [], error: "시트를 읽지 못했어요 (SURVEY_SHEET_ID 를 확인해 주세요)." };
  const qs = new URLSearchParams({ tqx: "out:csv", sheet: tab });
  try {
    const res = await fetch(`https://docs.google.com/spreadsheets/d/${sheetId}/gviz/tq?${qs}`, {
      next: { revalidate: 60, tags: ["survey"] },
      signal: AbortSignal.timeout(10_000),
    });
    if (res.status !== 200 || !(res.headers.get("content-type") || "").includes("text/csv"))
      return { rows: [], error: "시트를 읽지 못했어요 (공유 설정이 '링크가 있는 모든 사용자 · 보기' 인지 확인해 주세요)." };
    return { rows: csvRecords(await res.text()), error: "" };
  } catch (e) {
    const name = e instanceof Error ? e.name : "Error";
    return { rows: [], error: `시트를 읽지 못했어요 (${name}). 잠시 뒤 다시 열어 주세요.` };
  }
}
