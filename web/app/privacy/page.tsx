import type { Metadata } from "next";
import { PRIVACY_MD } from "@/content/docs.gen";
import { markdown } from "@/components/pages/markdown";

// 개인정보처리방침 · 이용약관 (앱 page_privacy). 상시 공개, 로그인 없이 누구나.
// 내용은 docs/privacy-policy.md 한 곳 — scripts/sync_docs.mjs 가 빌드 전에 옮겨 온다.
export const metadata: Metadata = {
  title: "개인정보처리방침 · 이용약관",
  description: "ANI:WHERE 개인정보처리방침과 이용약관 (받는 정보 · 보유 기간 · 위탁 · 이용자의 권리 · 연락처).",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return <div className="pg-wrap pg-doc" dangerouslySetInnerHTML={{ __html: markdown(PRIVACY_MD) }} />;
}
