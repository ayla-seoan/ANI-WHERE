"use client";
import { APP_URL, type Item } from "@/lib/popup";
import { applyCond, EMPTY, type Cond } from "./filters";
import { SearchIcon } from "../Icons";

// 조건에 맞는 팝업이 0곳일 때: 빈 표 대신 '이 조건만 풀면 몇 곳' 버튼 (앱 _empty_state 와 같은 생각)
export default function NoResult({
  items,
  cond,
  set,
  reset,
  today,
}: {
  items: Item[];
  cond: Cond;
  set: (p: Partial<Cond>) => void;
  reset: () => void;
  today: string;
}) {
  const tries: { label: string; patch: Partial<Cond> }[] = [];
  if (cond.q.trim()) tries.push({ label: "검색어 지우기", patch: { q: "" } });
  if (cond.area) tries.push({ label: `지역(${cond.area}) 풀기`, patch: { area: "" } });
  if (cond.day) tries.push({ label: "날짜 풀기", patch: { day: "" } });
  if (cond.span !== EMPTY.span) tries.push({ label: "진행중 + 예정 보기", patch: { span: EMPTY.span } });
  if (cond.work) tries.push({ label: "작품 풀기", patch: { work: "" } });
  if (cond.reserve) tries.push({ label: "사전예약 조건 풀기", patch: { reserve: false } });
  const counted = tries
    .map((t) => ({ ...t, n: applyCond(items, { ...cond, ...t.patch }, today).length }))
    .filter((t) => t.n > 0);
  return (
    <div className="empty-box" role="status">
      <div className="empty-ic">
        <SearchIcon />
      </div>
      <div className="empty-t">조건에 맞는 팝업이 없어요</div>
      <div className="empty-s">조건을 하나씩 풀어 보거나, 찾는 팝업이 없다면 앱에서 직접 등록할 수 있어요.</div>
      <div className="empty-relax">
        {counted.map((t) => (
          <button key={t.label} type="button" className="pill" onClick={() => set(t.patch)}>
            {t.label} (+{t.n}곳)
          </button>
        ))}
        {!counted.length && (
          <button type="button" className="pill" onClick={reset}>
            조건 초기화
          </button>
        )}
        <a className="pill" href={APP_URL} target="_blank" rel="noopener noreferrer">
          앱에서 직접 등록
        </a>
      </div>
    </div>
  );
}
