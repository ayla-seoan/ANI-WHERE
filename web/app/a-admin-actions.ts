"use server";
import { dataCols, DATA_TABLES, rawFilter, toCsv } from "@/lib/server/a-admin";
import { AuthError } from "@/lib/server/auth";
import { requireAdmin } from "@/lib/server/session";
import { rows, type Table } from "@/lib/server/store";

// 관리자 화면 A안에서 새로 생긴 서버 액션. 기존 액션(admin-actions.ts)과 같이 맨 앞에서 관리자인지 다시 확인한다.

export type CsvState = { ok?: string; error?: string; csv?: string; name?: string };

/** 원본 데이터 'CSV 내려받기': 화면의 표와 같은 조건(찾기 · 지금 내용만)으로, 화면에 안 보이는 칸은 빼고 */
export async function rawCsvAction(table: string, onlyNow: boolean, q: string): Promise<CsvState> {
  try {
    await requireAdmin();
  } catch (e) {
    return { error: e instanceof AuthError ? e.message : "관리자만 볼 수 있어요." };
  }
  if (!Object.hasOwn(DATA_TABLES, String(table))) return { error: "표를 찾지 못했어요." };
  const cols = dataCols(table);
  try {
    const list = rawFilter(await rows(table as Table), cols, String(q || "").slice(0, 100), !!onlyNow);
    const day = new Date(Date.now() + 9 * 3600_000).toISOString().slice(0, 10);
    return { ok: `${list.length}줄을 내려받았어요.`, csv: toCsv(cols, list), name: `${table}_${day}.csv` };
  } catch {
    return { error: "표를 읽지 못했어요. 잠시 뒤 다시 시도해 주세요." };
  }
}
