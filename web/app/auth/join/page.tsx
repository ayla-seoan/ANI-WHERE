import type { Metadata } from "next";
import Link from "next/link";
import SocialJoin from "@/components/auth/SocialJoin";
import { PROVIDER_LABEL, suggestNick } from "@/lib/server/auth";
import { getPending } from "@/lib/server/session";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "가입하기", robots: { index: false } };

export default async function JoinPage() {
  const p = await getPending();
  if (!p) {
    return (
      <div className="auth-wrap">
        <div className="auth-sub">로그인 화면에서 시작해 주세요.</div>
        <Link className="btn-main as-link" href="/login">
          로그인하기
        </Link>
      </div>
    );
  }
  let suggest = "졸린 고양이";
  try {
    suggest = await suggestNick();
  } catch {
    /* 그대로 */
  }
  return <SocialJoin label={PROVIDER_LABEL[p.p] || "간편"} nick={p.n} avatar={p.a} suggest={suggest} />;
}
