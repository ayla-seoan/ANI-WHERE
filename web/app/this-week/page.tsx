import type { Metadata } from "next";
import { getPopupData } from "@/lib/data";
import { shortDate, sortPopups, thisSunday, todayKST, type Popup } from "@/lib/popup";
import PopupCard from "@/components/PopupCard";
import EmptyState from "@/components/EmptyState";

export const revalidate = 600;

export const metadata: Metadata = {
  title: "이번 주 팝업",
  description: "오늘부터 이번 주 일요일까지 열려 있는 애니 팝업·콜라보 카페를 지역별로 모았어요.",
};

export default async function ThisWeek() {
  const { popups } = await getPopupData();
  const today = todayKST();
  const sunday = thisSunday(today);

  // 날짜가 있는 것 중 [오늘, 일요일] 과 겹치는 것
  const week = sortPopups(
    popups.filter((p) => p.start && p.end && p.start <= sunday && p.end >= today),
    today,
  );

  const groups = new Map<string, Popup[]>();
  for (const p of week) {
    const g = groups.get(p.region) ?? [];
    g.push(p);
    groups.set(p.region, g);
  }
  const ordered = [...groups.entries()].sort(
    (a, b) => (a[0] === "기타" ? 1 : 0) - (b[0] === "기타" ? 1 : 0) || b[1].length - a[1].length,
  );
  const closing = week.filter((p) => p.end <= sunday).length;

  return (
    <>
      <div className="week-head">
        <h1 className="page-title">이번 주 갈 수 있는 팝업</h1>
        <p className="page-sub">
          {today === sunday ? `오늘 ${shortDate(today, today)}` : `${shortDate(today, today)} ~ ${shortDate(sunday, today)}`} ·{" "}
          {week.length}곳{closing > 0 ? ` · 이번 주에 끝나는 곳 ${closing}` : ""}
        </p>
      </div>

      {ordered.length === 0 ? (
        <EmptyState title="이번 주에 열린 팝업이 없어요" hint="찾기 화면의 '예정' 탭에서 다음 일정을 확인해 보세요." />
      ) : (
        <>
          <nav className="chips region-nav" aria-label="지역 바로 가기">
            {ordered.map(([r, list], i) => (
              <a key={r} className="chip" href={`#region-${i}`}>
                {r}
                <small>{list.length}</small>
              </a>
            ))}
          </nav>
          {ordered.map(([r, list], i) => (
            <section key={r} id={`region-${i}`} className="region-block" style={{ scrollMarginTop: 70 }}>
              <h2>
                {r} <small>{list.length}곳</small>
              </h2>
              <div className="grid">
                {list.map((p) => (
                  <PopupCard
                    key={p.id}
                    today={today}
                    showRegion={false}
                    p={{ id: p.id, name: p.name, work: p.work, region: p.region, start: p.start, end: p.end, poster: p.images[0] ?? "" }}
                  />
                ))}
              </div>
            </section>
          ))}
        </>
      )}
    </>
  );
}
