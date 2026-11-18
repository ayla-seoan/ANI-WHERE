import type { Metadata } from "next";
import { getPopupData } from "@/lib/data";
import { todayKST, toItem } from "@/lib/popup";
import ListView from "@/components/browse/ListView";
import EmptyState from "@/components/EmptyState";

export const revalidate = 600;

export const metadata: Metadata = {
  title: "리스트로 보기",
  description:
    "지금 열린·곧 열리는 애니 팝업스토어·콜라보 카페를 포스터 카드로 모아 봐요. 검색·지역·진행여부·날짜로 거를 수 있어요.",
  alternates: { canonical: "/list" },
};

export default async function ListPage() {
  const { popups } = await getPopupData();
  const today = todayKST();
  if (!popups.length)
    return <EmptyState title="지금은 팝업 정보를 불러오지 못했어요" hint="잠시 뒤 새로 고침해 보세요." />;
  return <ListView items={popups.map(toItem)} today={today} />;
}
