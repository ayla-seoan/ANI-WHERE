import Link from "next/link";
import { daysBetween, periodDot, weekday, type Item } from "@/lib/popup";
import { posterBg } from "../cards";
import { ReserveLine } from "./Icons2";
import ReserveAlert from "./ReserveAlert";

const SHOW_MAX = 8; // 타임라인에는 빨리 여는 8곳까지, 나머지는 '사전예약 팝업만 보기'
const two = (n: number) => String(n).padStart(2, "0");

// 사전예약 팝업 (A-Home, 보라 #6c5ce7): 왼쪽 요약 카드 + 오른쪽 타임라인 (모바일은 세로 타임라인, A-Mobile).
// 데이터에 '예약이 열리는 시각' · '예약하는 곳' 칸이 없어서 (lib/popup.ts Popup) 타임라인 날짜는 팝업 오픈일(start)이고,
// 시안의 '예약 · 어디서' 줄은 뺐다. items = 아직 열기 전인 사전예약 팝업, 빨리 여는 순.
export default function ReserveSection({ items, today }: { items: Item[]; today: string }) {
  const shown = items.slice(0, SHOW_MAX);
  return (
    <section className="ah-pre" aria-labelledby="ah-pre-h">
      <div className="ah-pre-sum">
        <h2 className="ah-h" id="ah-pre-h">
          <ReserveLine />
          사전예약 팝업
        </h2>
        <p className="ah-pre-p">
          예약해야 들어갈 수 있는 팝업이에요. <span>팝업이 열리는 날 순서로 모았어요.</span>
        </p>
        <span className="ah-pre-n">
          {items.length}
          <span> 곳 예약 대기</span>
        </span>
        <Link href="/list?reserve=1&sort=open" className="ah-pre-all" prefetch={false}>
          사전예약 팝업만 보기
        </Link>
      </div>
      {shown.length ? (
        <ol className="ah-pre-line">
          {shown.map((p, i) => {
            const [, m, d] = p.start.split("-").map(Number);
            const badge = `사전예약 D-${daysBetween(today, p.start)}`;
            return (
              <li key={p.id} className={`ah-pre-i${i === 0 ? " first" : ""}`}>
                <span className="ah-pre-date">
                  {two(m)}.{two(d)} ({weekday(p.start)}) 팝업 오픈
                </span>
                <span className="ah-pre-dot" aria-hidden />
                <div className="ah-pre-body">
                  <Link href={`/popup/${p.id}`} className="ah-pre-card" prefetch={false}>
                    <span className="ah-pre-pic" style={posterBg(p.poster)}>
                      <span className="ah-pre-badge">{badge}</span>
                    </span>
                    <span className="ah-pre-txt">
                      <span className="ah-pre-badge m" aria-hidden>
                        {badge}
                      </span>
                      <span className="ah-pre-t">{p.work}</span>
                      <span className="ah-pre-m">
                        {p.name || p.area} · {periodDot(p)}
                      </span>
                    </span>
                  </Link>
                  <ReserveAlert cafeId={p.id} name={p.work} />
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <div className="ah-empty ah-pre-none">곧 열리는 팝업 중 사전예약을 받는 곳이 없어요.</div>
      )}
    </section>
  );
}
