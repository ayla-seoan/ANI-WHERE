import Link from "next/link";
import { badgeOf, periodText } from "@/lib/popup";
import PosterImg from "./PosterImg";

export type CardData = {
  id: string;
  name: string;
  work: string;
  region: string;
  start: string;
  end: string;
  poster: string;
};

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
  const badge = badgeOf(p, today);
  return (
    <Link href={`/popup/${p.id}`} className="card">
      <div className="poster">
        <PosterImg src={p.poster} alt={`${p.work} 포스터`} eager={eager} />
        <div className="badges">
          <span className={`badge ${badge.tone}`}>{badge.label}</span>
          {showRegion && <span className="badge">{p.region}</span>}
        </div>
      </div>
      <div className="card-body">
        <h3 className="card-work">{p.work}</h3>
        <p className="card-name">{p.name}</p>
        <p className="card-period">{periodText(p, today)}</p>
      </div>
    </Link>
  );
}
