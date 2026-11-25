import Link from "next/link";
import { darken, regionColor, stateOf, type Item } from "@/lib/popup";
import { posterBg } from "../cards";
import BookmarkButton from "../member/BookmarkButton";

const two = (n: number) => String(n).padStart(2, "0");
const md = (ymd: string) => {
  const [, m, d] = ymd.split("-").map(Number);
  return `${two(m)}.${two(d)}`;
};

/** 카드 아래 기간 한 줄 (A-Home): 열기 전이면 '11.28 ~', 열렸으면 '~ 12.20' */
export function shortPeriod(p: Pick<Item, "start" | "end">, today: string): string {
  if (!p.start) return "기간 확인 필요";
  if (p.start > today) return `${md(p.start)} ~`;
  return p.end ? `~ ${md(p.end)}` : "상시";
}

/** 홈 A안 포스터 카드 (신규 등록): 3:4 포스터(민트 테두리) 위에 상태(왼쪽 위) · 지역(오른쪽 위) · 북마크(오른쪽 아래),
 *  아래 Jua 제목 + '장소 · 기간'. 북마크 버튼은 링크 밖(형제)에 둔다 */
export default function FreshCard({ p, today }: { p: Item; today: string }) {
  const s = stateOf(p, today);
  const period = shortPeriod(p, today);
  return (
    <div className="ah-pc">
      <Link href={`/popup/${p.id}`} className="ah-pc-a" prefetch={false}>
        <span className="ah-pc-pic" style={posterBg(p.poster)}>
          <span className={`ah-st ${s.color}`}>{s.label}</span>
          {p.area && (
            <span className="ah-area" style={{ background: darken(regionColor(p.city)) }}>
              {p.area}
            </span>
          )}
        </span>
        <span className="ah-pc-t">{p.work}</span>
        <span className="ah-pc-m">
          <span className="pc-only">{p.name || p.area}</span>
          <span className="m-only">{p.area || p.name}</span>
          {" · "}
          {period}
        </span>
      </Link>
      <BookmarkButton cafeId={p.id} />
    </div>
  );
}
