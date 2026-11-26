import type { Metadata } from "next";
import RankGuide from "@/components/mypage/RankGuide";
import { displayName } from "@/lib/server/auth";
import { getMe } from "@/lib/server/session";
import { myStamps } from "@/lib/server/stamp";

// 후기 도장 랭크 안내 (A-Rank). 누구나 볼 수 있고, 회원이면 내 지금 랭크를 강조한다.
// 평소에는 '랭크 안내 보기' 를 누르면 팝업(components/mypage/RankGuideLink)으로 뜨고, 이 주소는 직접 열었을 때 같은 내용을 보여 준다.
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "후기 도장 랭크", robots: { index: false } };

export default async function RankPage() {
  const me = await getMe();
  const stamps = me ? await myStamps(displayName(me.row)) : null;
  return <RankGuide stamps={stamps} />;
}
