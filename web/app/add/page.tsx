import type { Metadata } from "next";
import AddWizard from "@/components/edit/AddWizard";
import LoginFirst from "@/components/edit/LoginFirst";
import { todayKST } from "@/lib/popup";
import { charactersByWork, currentCafes, existingLite } from "@/lib/server/cafe";
import { getMe } from "@/lib/server/session";
import type { Row } from "@/lib/server/store";

// /add 등록하기 (앱 page_add). 팝업 등록은 로그인한 회원만 (주소로 바로 들어와도 로그인 화면으로).
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "팝업 카페 등록하기", robots: { index: false } };

export default async function AddPage() {
  const me = await getMe();
  if (!me) return <LoginFirst msg="팝업 등록은 로그인하면 할 수 있어요." next="/add" />;
  let cur: Row[] = [];
  try {
    cur = await currentCafes();
  } catch (e) {
    console.error("[add] 팝업 기록을 읽지 못함", e instanceof Error ? e.message : e);
  }
  return <AddWizard byWork={charactersByWork(cur)} existing={existingLite(cur)} today={todayKST()} />;
}
