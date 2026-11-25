import type { Metadata } from "next";
import { redirect } from "next/navigation";
import LoginBox from "@/components/auth/LoginBox";
import { authorizeUrl, enabled, suggestNick } from "@/lib/server/auth";
import { getMe } from "@/lib/server/session";
import { mode } from "@/lib/server/store";

// /login: 손님이면 로그인 · 회원가입. 회원이면 /mypage 로 보낸다 (next 가 있으면 거기로)
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "로그인 · 회원가입", robots: { index: false } };

type Props = { searchParams: Promise<{ next?: string; err?: string }> };

export default async function LoginPage({ searchParams }: Props) {
  const sp = await searchParams;
  const me = await getMe();
  // 돌아갈 주소는 이 사이트 안(/로 시작)만
  const next = /^\/(?!\/)/.test(sp.next || "") ? String(sp.next) : "/";
  // 회원이 오면 마이페이지로 ('내 계정' 은 /mypage 설정으로 옮겼다, 11/25). 돌아갈 곳(next)이 있으면 거기로
  // (로그인 액션의 safeNext 와 같은 글자만 허용 — '/\' 같은 바깥 주소로 새지 않게)
  if (me) redirect(/^\/(?!\/)[\w\-/?=&%.]*$/.test(next) && next !== "/" && !next.startsWith("/login") ? next : "/mypage");
  let suggest = "졸린 고양이";
  try {
    suggest = await suggestNick();
  } catch {
    /* 회원 목록을 못 읽어도 화면은 그린다 */
  }
  return (
    <>
      <LoginBox
        links={{
          kakao: enabled("kakao") ? authorizeUrl("kakao") : null,
          naver: enabled("naver") ? authorizeUrl("naver") : null,
        }}
        suggest={suggest}
        next={next}
        error={(sp.err || "").slice(0, 200)}
      />
      {mode() === "none" && (
        <p className="auth-admin-note">
          관리자 안내: 회원 저장소(SUPABASE_URL · SUPABASE_ANON_KEY)가 연결되지 않아 가입·로그인을 할 수 없어요.
        </p>
      )}
    </>
  );
}
