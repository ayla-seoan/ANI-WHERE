import type { Metadata } from "next";
import { getPopupData } from "@/lib/data";
import { todayKST, toItem } from "@/lib/popup";
import MapView from "@/components/browse/MapView";
import EmptyState from "@/components/EmptyState";

export const revalidate = 600;

export const metadata: Metadata = {
  title: "지도로 보기",
  description:
    "애니 팝업스토어·콜라보 카페를 지도에서 찾아봐요. 데일리 팝업 노트로 오늘 열린 곳을 지역별로 볼 수 있어요.",
  alternates: { canonical: "/map" },
};

export default async function MapPage() {
  const { popups } = await getPopupData();
  const today = todayKST();
  if (!popups.length)
    return <EmptyState title="지금은 팝업 정보를 불러오지 못했어요" hint="잠시 뒤 새로 고침해 보세요." />;
  return <MapView items={popups.map(toItem)} today={today} />;
}
