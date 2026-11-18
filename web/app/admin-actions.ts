"use server";
import { revalidatePath, revalidateTag } from "next/cache";
import { scan } from "@/lib/guard";
import {
  decide,
  MAX_REASON,
  pendingFor,
  requestDelete,
  requestRows,
  RULES,
  ruleSettings,
  saveRule,
  send,
  softDelete,
  validateReason,
  type TargetType,
} from "@/lib/server/admin";
import { AuthError, displayName } from "@/lib/server/auth";
import { getMe, requireAdmin } from "@/lib/server/session";
import { current, rows, StorageWriteError } from "@/lib/server/store";

// 삭제 요청(회원) · 관리자 대시보드 쓰기. 모두 서버에서 다시 확인한다 (관리자 액션은 맨 앞에서 requireAdmin).
// 앱(app_cafemap.py)의 delete_request_dialog · _admin_decide · _admin_notice_save · _admin_rule_save 와 같은 규칙 · 같은 문구.

export type AdminState = { ok?: string; error?: string; login?: boolean } | null;

const str = (f: FormData, k: string) => String(f.get(k) ?? "");
const tidy = (s: string) => s.split(/\s+/).filter(Boolean).join(" ");
const say = (e: unknown) =>
  e instanceof AuthError || e instanceof StorageWriteError
    ? e.message
    : "요청을 처리하지 못했어요. 잠시 뒤 다시 시도해 주세요.";

async function admin(): Promise<AdminState | null> {
  try {
    await requireAdmin();
    return null;
  } catch (e) {
    return { error: e instanceof AuthError ? e.message : "관리자만 볼 수 있어요." };
  }
}

// ------------------------------------------------------------------ 삭제 요청 (일반 회원)
/** 앱 delete_request_dialog '요청 보내기' */
export async function requestDeleteAction(_: AdminState, f: FormData): Promise<AdminState> {
  const targetType = str(f, "target_type") as TargetType;
  const targetId = str(f, "target_id").trim();
  const title = str(f, "title");
  const reason = str(f, "reason");
  if (!["cafe", "review"].includes(targetType) || !/^[\w:-]{1,80}$/.test(targetId))
    return { error: "요청을 처리하지 못했어요. 잠시 뒤 다시 시도해 주세요." };
  const me = await getMe();
  if (!me) return { error: "로그인한 회원만 삭제를 요청할 수 있어요.", login: true };
  try {
    if (pendingFor(await requestRows(), targetId, me.key)) return { error: "이 글에 보낸 요청이 아직 처리 중이에요." };
    const errors = validateReason(reason);
    if (errors.length) return { error: errors[0] };
    await requestDelete(targetType, targetId, title, reason, me);
  } catch (e) {
    return { error: say(e) };
  }
  revalidatePath("/data");
  return { ok: "삭제 요청을 보냈어요. 처리 결과는 알림으로 알려 드려요." };
}

// ------------------------------------------------------------------ 관리자: 승인 / 거부
/** 앱 _admin_decide: 승인 → 게시글 삭제('삭제됨' 새 행) + 기록 + 알림 / 거부 → 사유와 함께 기록 + 알림 */
export async function decideAction(_: AdminState, f: FormData): Promise<AdminState> {
  const denied = await admin();
  if (denied) return denied;
  const me = (await getMe())!;
  const id = str(f, "entry_id");
  const approve = str(f, "approve") === "1";
  const reason = str(f, "admin_reason").slice(0, MAX_REASON);
  if (!approve && [...tidy(reason)].length < 2) return { error: "거부 사유를 적어 주세요." };
  if (scan(reason).length) return { error: "사유에 전화번호·이메일 같은 개인정보는 넣지 말아 주세요." };
  try {
    const req = (await requestRows()).find((r) => String(r.entry_id) === id);
    if (!req) return { error: "요청을 찾지 못했어요. 새로고침해 주세요." };
    if (req.decision !== "pending") return { error: "이미 처리한 요청이에요." };
    if (approve) {
      // 지우지 않고 '삭제됨' 행. 이미 지워진 글이어도 요청 처리는 끝낸다 (앱과 같게)
      try {
        if (req.target_type === "review") await softDelete("reviews", String(req.target_id));
        else
          await softDelete("cafes", String(req.target_id), {
            source: "삭제 요청 승인",
            editor: displayName(me.row),
          });
      } catch (e) {
        if (e instanceof StorageWriteError) throw e;
        console.error("[admin] 게시글 삭제 실패", e instanceof Error ? e.message : e);
      }
    }
    const rules = await ruleSettings();
    await decide(req, approve, reason, rules[approve ? "del_ok" : "del_no"].enabled);
  } catch (e) {
    return { error: say(e) };
  }
  if (approve) revalidateTag("popups");
  revalidatePath("/data");
  return {
    ok: approve ? "승인했어요. 게시글을 삭제하고 요청자에게 알렸어요." : "거부했어요. 요청자에게 사유를 알렸어요.",
  };
}

// ------------------------------------------------------------------ 관리자: 공지 알림
/** 앱 _admin_notice_save: entry_id 가 있으면 그 공지 수정(새 revision), 없으면 새 공지 */
export async function noticeSaveAction(_: AdminState, f: FormData): Promise<AdminState> {
  const denied = await admin();
  if (denied) return denied;
  const entryId = str(f, "entry_id").trim();
  const title = tidy(str(f, "title"));
  const body = str(f, "body").trim();
  if ([...title].length < 2 || !body) return { error: "제목(2자 이상)과 내용을 적어 주세요." };
  if (scan(`${title} ${body}`).length) return { error: "알림에 전화번호·이메일 같은 개인정보는 넣을 수 없어요." };
  try {
    if (entryId) {
      const cur = current(await rows("notices", { entry_id: entryId }))[0];
      if (!cur || cur.target !== "all") return { error: "공지를 찾지 못했어요. 새로고침해 주세요." };
    }
    await send("all", "공지", title, body, entryId || undefined);
  } catch (e) {
    return { error: say(e) };
  }
  revalidatePath("/", "layout");
  return { ok: "공지를 저장했어요. 모든 회원의 알림에 보여요." };
}

/** 앱 _admin_notice_delete: 지우지 않고 '삭제됨' 새 행 */
export async function noticeDeleteAction(entryId: string): Promise<AdminState> {
  const denied = await admin();
  if (denied) return denied;
  try {
    const cur = current(await rows("notices", { entry_id: String(entryId) }))[0];
    if (!cur || cur.target !== "all") return { error: "공지를 찾지 못했어요. 새로고침해 주세요." };
    await softDelete("notices", String(entryId));
  } catch (e) {
    return { error: say(e) };
  }
  revalidatePath("/", "layout");
  return { ok: "공지를 삭제했어요." };
}

// ------------------------------------------------------------------ 관리자: 자동 알림 규칙
/** 앱 _admin_rule_save: 켜기(저장) / 끄기(삭제). 기록은 지우지 않고 쌓인다 */
export async function ruleSaveAction(_: AdminState, f: FormData): Promise<AdminState> {
  const denied = await admin();
  if (denied) return denied;
  const key = str(f, "rule");
  const d = RULES[key];
  if (!d) return { error: "규칙을 찾지 못했어요." };
  const enabled = str(f, "enabled") === "1";
  const num = (k: string, lo: number, hi: number) => {
    const raw = str(f, k).trim();
    if (!/^\d+$/.test(raw)) return null;
    return Math.min(hi, Math.max(lo, Number(raw)));
  };
  const days = d.days !== null ? num("days", 0, 30) : null;
  const mx = d.max_items !== null ? num("max_items", 1, 30) : null;
  if ((d.days !== null && days === null) || (d.max_items !== null && mx === null))
    return { error: "숫자를 확인해 주세요." };
  try {
    await saveRule(key, enabled, days, mx);
  } catch {
    return { error: "저장하지 못했어요. Supabase 에 007_alert_rules.sql 을 먼저 돌려 주세요." };
  }
  revalidatePath("/", "layout");
  return { ok: `'${d.name}' 규칙을 ${enabled ? "저장했어요" : "껐어요"}.` };
}

// ------------------------------------------------------------------ 관리자: 데이터 새로 불러오기
/** 앱 '데이터 새로 불러오기' (storage.refresh_all): 팝업 목록 캐시를 비운다. 회원 기록은 원래 매번 새로 읽는다 */
export async function refreshAction(): Promise<AdminState> {
  const denied = await admin();
  if (denied) return denied;
  revalidateTag("popups");
  revalidatePath("/", "layout");
  return { ok: "Supabase 에서 새로 불러왔어요." };
}

/** 사용자 테스트 '새로고침': 설문 시트 1분 기억을 비운다 (앱 _survey_rows.clear) */
export async function surveyReloadAction(): Promise<AdminState> {
  const denied = await admin();
  if (denied) return denied;
  revalidateTag("survey");
  revalidatePath("/data");
  return { ok: "" };
}
