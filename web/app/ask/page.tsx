import type { Metadata } from "next";
import { getPopupData } from "@/lib/data";
import { todayKST, toItem } from "@/lib/popup";
import AskPage from "@/components/pages/AskPage";

// 물어보기 전체 화면 (앱 page_ask). 지도·리스트 오른쪽 창(AskPanel)과 같은 규칙(lib/ask.ts)으로 찾고,
// 작품·지역·날짜 검색이면 서버에서 AI 로 답을 다듬는다 ('AI 산출' / '규칙 기반 대체' 표시).
export const metadata: Metadata = {
  title: "팝업에게 물어보기",
  description: "작품 · 지역 · 날짜로 물어보면 ANI:WHERE 에 모인 애니 팝업 정보 안에서 찾아 답해요.",
  alternates: { canonical: "/ask" },
};

export default async function AskRoute() {
  const { popups } = await getPopupData();
  return <AskPage items={popups.map(toItem)} today={todayKST()} />;
}
