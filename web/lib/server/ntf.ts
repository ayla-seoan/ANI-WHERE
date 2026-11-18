import "server-only";
import { createHash } from "node:crypto";
import { cookies } from "next/headers";

// 종 알림 번호 · 읽음 쿠키 — 앱(app_cafemap.py _ntf_id · _ntf_cookie · _ntf_read · _why_html)과 같은 모양.
//  - 알림 번호 = sha1(글)[:8]. 북마크 알림은 앱이 화면에 그리는 HTML 글 그대로를 넣어 번호를 만든다
//    (같은 날 같은 글이면 같은 번호 → 종과 '알림 받은 내역' 이 읽음을 같이 쓴다)
//  - 읽은 번호는 회원마다 따로 쿠키 aw_ntf_read_<sha1(회원 번호)[:8]> 에 '.' 로 이어 둔다 (최근 200개, 60일, SameSite=Lax)

export const NTF_COOKIE = "aw_ntf_read";
export const NTF_MAX_AGE = 5184000; // 60일

const sha1 = (text: string) => createHash("sha1").update(text, "utf8").digest("hex");

/** 앱 _ntf_id */
export const ntfId = (text: string) => sha1(text).slice(0, 8);

/** 앱 _ntf_cookie: 읽은 알림 쿠키 이름 (회원마다 따로) */
export const ntfCookieName = (memberKey: string) => `${NTF_COOKIE}_${sha1(memberKey || "guest").slice(0, 8)}`;

/** 앱 _ntf_read: 쿠키에 남은 읽은 번호들 ('.' 로 이은 8자리) */
export async function ntfRead(memberKey: string): Promise<string> {
  const raw = (await cookies()).get(ntfCookieName(memberKey))?.value || "";
  return raw
    .split(".")
    .filter((x) => /^[0-9a-f]{8}$/.test(x))
    .join(".");
}

/** 파이썬 html.escape (quote=True) */
export const esc = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");

/** 앱 _why_html (안의 아이콘은 _mi("info")) */
export const whyHtml = (why: string) => `<div class="ntf-why"><span class="mi " aria-hidden="true">info</span> ${esc(why)}</div>`;

/** 앱의 f'{work} · {cafe_name}'.strip(" ·") */
export const ntfName = (work: string, cafe: string) => `${work || ""} · ${cafe || ""}`.replace(/^[ ·]+|[ ·]+$/g, "");

/** 북마크 알림 번호 (앱 items_marks: _ntf_id(f"m{TODAY}{eid}{text}")) */
export const markId = (today: string, cafeId: string, label: string, name: string, why: string) =>
  ntfId(`m${today}${cafeId}<b>${label}</b> · ${esc(name)}${whyHtml(why)}`);

/** 받은 알림 번호 (앱 items_inbox: _ntf_id("i" + row_id)) */
export const inboxId = (rowId: string) => ntfId(`i${rowId}`);

/** 종 '내 주변 추천' 번호 (앱 items_near: _ntf_id(f"n{TODAY}{eid}")) */
export const nearId = (today: string, cafeId: string) => ntfId(`n${today}${cafeId}`);

/** 내 캘린더 '내 주변 추천' 번호 (앱 _render_near_picks: _ntf_id(f"r{TODAY}{eid}")) */
export const pickId = (today: string, cafeId: string) => ntfId(`r${today}${cafeId}`);

/** 내 캘린더 지난 날 알림 번호 (앱 _render_notice_history: _ntf_id(f"h{day}{eid}{label}")) */
export const histId = (day: string, cafeId: string, label: string) => ntfId(`h${day}${cafeId}${label}`);
