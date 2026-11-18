import type { Metadata } from "next";
import { getPopupData } from "@/lib/data";
import { shortDate, sortPopups, thisSunday, todayKST, toItem, type Popup } from "@/lib/popup";
import { PosterCard } from "@/components/cards";
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
    const k = p.area || "기타";
    groups.set(k, [...(groups.get(k) ?? []), p]);
  }
  const ordered = [...groups.entries()].sort(
    (a, b) => (a[0] === "기타" ? 1 : 0) - (b[0] === "기타" ? 1 : 0) || b[1].length - a[1].length,
  );
  const closing = week.filter((p) => p.end <= sunday).length;

  return (
    <div className="week-page">
      <h1 className="listbar">
        이번 주 갈 수 있는 팝업 <b>{week.length}</b>곳
      </h1>
      <p className="page-sub">
        {today === sunday
          ? `오늘 ${shortDate(today, today)}`
          : `${shortDate(today, today)} ~ ${shortDate(sunday, today)}`}
        {closing > 0 ? ` · 이번 주에 끝나는 곳 ${closing}` : ""}
      </p>
      {ordered.length === 0 ? (
        <EmptyState title="이번 주에 열린 팝업이 없어요" hint="리스트로 보기에서 '예정' 팝업을 확인해 보세요." />
      ) : (
        <>
          <nav className="pills" aria-label="지역 바로 가기">
            {ordered.map(([r, list], i) => (
              <a key={r} className="pill" href={`#region-${i}`}>
                {r} {list.length}
              </a>
            ))}
          </nav>
          {ordered.map(([r, list], i) => (
            <section key={r} id={`region-${i}`} className="region-block">
              <h2 className="home-h">
                {r} <small>{list.length}곳</small>
              </h2>
              <div className="wide-grid">
                {list.map((p) => (
                  <PosterCard key={p.id} p={toItem(p)} today={today} />
                ))}
              </div>
            </section>
          ))}
        </>
      )}
    </div>
  );
}
