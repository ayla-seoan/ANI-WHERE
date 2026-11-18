import { NextResponse, type NextRequest } from "next/server";
import { getPopupData } from "@/lib/data";
import { todayKST } from "@/lib/popup";
import { ruleSettings } from "@/lib/server/member";
import { nearId, pickId } from "@/lib/server/ntf";
import { getMe, getMyFavs } from "@/lib/server/session";

// '내 주변 추천' (회원만). 위치는 브라우저가 허용했을 때만 보내고, 저장하지 않는다.
//  - for=bell (앱 _notices 2번 묶음): 지금 열려 있는 팝업 중 가까운 순, 알림 규칙 near 의 개수만큼 (북마크한 곳 제외)
//  - for=cal  (앱 _render_near_picks): 20km 안에서 진행 중이거나 3일 안에 여는 곳, 별점 높은 순 → 다녀온 후기 많은 순 → 가까운 순, 3곳
export const dynamic = "force-dynamic";

const NEAR_KM = 20;

function km(a: [number, number], b: [number, number]): number {
  // 앱 my_place._km 과 같은 하버사인 (지구 반지름 6371km)
  const R = 6371;
  const rad = (x: number) => (x * Math.PI) / 180;
  const dLat = rad(b[0] - a[0]);
  const dLng = rad(b[1] - a[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[0])) * Math.cos(rad(b[0])) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

const distText = (d: number) => (d < 1 ? `${Math.round(d * 1000)}m` : `${d.toFixed(1)}km`);
const diffDays = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);

export async function GET(req: NextRequest) {
  const me = await getMe();
  if (!me) return NextResponse.json({ error: "로그인이 필요해요." }, { status: 401 });
  const q = req.nextUrl.searchParams;
  const lat = Number(q.get("lat"));
  const lng = Number(q.get("lng"));
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180)
    return NextResponse.json({ error: "위치를 읽지 못했어요." }, { status: 400 });
  const mode = q.get("for") === "cal" ? "cal" : "bell";
  const today = todayKST();
  const [{ popups }, favIds, rules] = await Promise.all([getPopupData(), getMyFavs(), ruleSettings()]);
  const fav = new Set(favIds);
  const here: [number, number] = [lat, lng];
  const live = popups.filter((p) => !fav.has(p.id) && p.lat !== null && p.lng !== null && p.start && p.end);

  let items;
  if (mode === "bell") {
    if (!rules.near.enabled) return NextResponse.json({ enabled: false, items: [] }, { headers: { "Cache-Control": "no-store" } });
    items = live
      .filter((p) => p.start <= today && today <= p.end)
      .map((p) => ({ p, d: km(here, [p.lat as number, p.lng as number]) }))
      .sort((a, b) => a.d - b.d)
      .slice(0, rules.near.max ?? 3)
      .map(({ p, d }) => ({ id: nearId(today, p.id), cafeId: p.id, dist: distText(d), work: p.work, cafe: p.name, poster: p.images[0] || "" }));
  } else {
    items = live
      .filter((p) => p.end >= today && diffDays(today, p.start) <= 3)
      .map((p) => ({ p, d: km(here, [p.lat as number, p.lng as number]) }))
      .filter((x) => x.d <= NEAR_KM)
      .sort(
        (a, b) =>
          -(a.p.rating?.avg ?? 0) - -(b.p.rating?.avg ?? 0) || -(a.p.rating?.n ?? 0) - -(b.p.rating?.n ?? 0) || a.d - b.d,
      )
      .slice(0, 3)
      .map(({ p, d }) => ({ id: pickId(today, p.id), cafeId: p.id, dist: distText(d), work: p.work, cafe: p.name, poster: p.images[0] || "" }));
  }
  return NextResponse.json({ enabled: true, km: NEAR_KM, items }, { headers: { "Cache-Control": "no-store" } });
}
