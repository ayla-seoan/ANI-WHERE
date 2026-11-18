import type { Metadata } from "next";
import LoginBox from "@/components/auth/LoginBox";
import MyAccount from "@/components/auth/MyAccount";
import { authorizeUrl, enabled, PROVIDER_LABEL, suggestNick } from "@/lib/server/auth";
import { getMe } from "@/lib/server/session";
import { mode } from "@/lib/server/store";

// /login: 손님이면 로그인 · 회원가입, 회원이면 마이페이지 '내 계정' (앱 page_login 과 같은 자리)
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "로그인 · 회원가입", robots: { index: false } };

type Props = { searchParams: Promise<{ next?: string; err?: string }> };

export default async function LoginPage({ searchParams }: Props) {
  const sp = await searchParams;
  const me = await getMe();
  let suggest = "졸린 고양이";
  try {
    suggest = await suggestNick();
  } catch {
    /* 회원 목록을 못 읽어도 화면은 그린다 */
  }
  if (me) {
    return (
      <MyAccount
        suggest={suggest}
        a={{
          nick: String(me.row.nickname || ""),
          avatar: String(me.row.avatar || ""),
          provider: String(me.row.provider || ""),
          providerLabel: PROVIDER_LABEL[String(me.row.provider)] || "",
          agreed: String(me.row.agreed_at || ""),
          key: me.key,
          admin: me.admin,
        }}
      />
    );
  }
  const next = /^\/(?!\/)/.test(sp.next || "") ? String(sp.next) : "/";
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
