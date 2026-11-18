import { NextResponse, type NextRequest } from "next/server";
import { AuthError, exchange, findMember } from "@/lib/server/auth";
import { setFlash, setPending, startSession } from "@/lib/server/session";

// 카카오·네이버가 돌려보내는 곳 ({SITE_URL}/auth, 개발자 콘솔에 등록한 Redirect URI).
// state 서명 확인 → code 로 토큰 → 프로필(고유 번호·별명·사진)만 → 가입한 회원이면 로그인, 처음이면 가입 화면.
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams;
  const to = (p: string) => NextResponse.redirect(new URL(p, req.nextUrl.origin));
  if (q.get("error")) {
    await setFlash("로그인을 취소했어요. 로그인하지 않아도 둘러볼 수 있어요.");
    return to("/login");
  }
  const code = q.get("code");
  const state = q.get("state");
  if (!code || !state) return to("/login");
  try {
    const ident = await exchange(code, state);
    const row = await findMember(ident.memberKey);
    if (row) {
      await startSession(String(row.entry_id), String(row.provider));
      await setFlash(`${row.nickname}님, 환영합니다!`);
      return to("/");
    }
    await setPending(ident);
    return to("/auth/join");
  } catch (e) {
    const msg = e instanceof AuthError ? e.message : "로그인을 처리하지 못했어요. 처음부터 다시 시도해 주세요.";
    return to(`/login?err=${encodeURIComponent(msg)}`);
  }
}
