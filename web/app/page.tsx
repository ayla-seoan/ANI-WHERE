import { getPopupData } from "@/lib/data";
import { searchText, sortPopups, todayKST } from "@/lib/popup";
import PopupBrowser, { type BrowserItem } from "@/components/PopupBrowser";
import EmptyState from "@/components/EmptyState";

export const revalidate = 600;

export default async function Home() {
  const { popups } = await getPopupData();
  const today = todayKST();
  // 브라우저로는 카드에 필요한 칸과 검색용 글자만 보낸다 (소개·링크 등은 상세에서)
  const items: BrowserItem[] = sortPopups(popups, today).map((p) => ({
    id: p.id,
    name: p.name,
    work: p.work,
    region: p.region,
    start: p.start,
    end: p.end,
    poster: p.images[0] ?? "",
    text: searchText(p),
  }));

  return (
    <>
      <h1 className="sr-only">애니 팝업·콜라보 카페 찾기</h1>
      {items.length > 0 ? (
        <PopupBrowser items={items} today={today} />
      ) : (
        <EmptyState
          title="지금은 팝업 정보를 불러오지 못했어요"
          hint="잠시 뒤 새로 고침해 보세요."
        />
      )}
    </>
  );
}
