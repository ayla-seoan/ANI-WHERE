import Link from "next/link";
import { cardBadge, cardPeriod, regionColor } from "@/lib/popup";
import PosterImg from "./PosterImg";
import { StoreIcon } from "./Icons";

export type CardData = {
  id: string;
  name: string;
  work: string;
  region: string;
  start: string;
  end: string;
  poster: string;
};

/** 앱(Streamlit) 리스트 카드와 같은 모양: 포스터를 꽉 채우고, 아래 그라데이션 위에 제목·매장·기간을 흰 글씨로.
 *  왼쪽 위 = 지역 배지(시마다 다른 색), 오른쪽 위 = D-day / 진행 중 */
export default function PopupCard({
  p,
  today,
  showRegion = true,
  eager = false,
}: {
  p: CardData;
  today: string;
  showRegion?: boolean;
  eager?: boolean;
}) {
  const color = regionColor(p.region);
  return (
    <Link href={`/popup/${p.id}`} className="card" aria-label={`${p.work} ${p.name}`}>
      <PosterImg src={p.poster} alt="" eager={eager} />
      {showRegion && p.region && (
        <span className="area" style={{ borderColor: color, background: `${color}33` }}>
          {p.region}
        </span>
      )}
      <span className="dday">{cardBadge(p, today)}</span>
      <div className="card-over">
        <h3 className="card-work">{p.work}</h3>
        <p className="card-name">
          <StoreIcon />
          <span>{p.name}</span>
        </p>
        <p className="card-period">{cardPeriod(p, today)}</p>
      </div>
    </Link>
  );
}
