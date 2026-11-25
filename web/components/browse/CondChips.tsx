"use client";
import { weekday } from "@/lib/popup";
import { CloseIcon } from "../Icons";
import { EMPTY, type Cond } from "./filters";

// 걸린 필터 칩 (A-List / A-MList 목록 위 줄): 누르면 그 조건만 풀린다.
// 지역은 리스트에서는 '지역 고르기' 칩이 따로 보여 주므로 withArea 일 때(지도)만 여기에 넣는다.
export function condChips(cond: Cond, withArea = false): { key: string; label: string; patch: Partial<Cond>; res?: boolean }[] {
  const out: { key: string; label: string; patch: Partial<Cond>; res?: boolean }[] = [];
  if (cond.q.trim()) out.push({ key: "q", label: `검색: ${cond.q.trim()}`, patch: { q: "" } });
  if (withArea && cond.area) out.push({ key: "area", label: cond.area.split(",").join(" · "), patch: { area: "" } });
  if (cond.span !== EMPTY.span) out.push({ key: "span", label: cond.span, patch: { span: EMPTY.span } });
  if (cond.day)
    out.push({
      key: "day",
      label: `${Number(cond.day.slice(5, 7))}.${Number(cond.day.slice(8, 10))} (${weekday(cond.day)})`,
      patch: { day: "" },
    });
  if (cond.work) out.push({ key: "work", label: `작품: ${cond.work}`, patch: { work: "" } });
  if (cond.reserve) out.push({ key: "reserve", label: "사전예약 팝업만", patch: { reserve: false }, res: true });
  return out;
}

export default function CondChips({
  cond,
  set,
  withArea = false,
}: {
  cond: Cond;
  set: (p: Partial<Cond>) => void;
  withArea?: boolean;
}) {
  const chips = condChips(cond, withArea);
  if (!chips.length) return null;
  return (
    <>
      {chips.map((c) => (
        <button
          key={c.key}
          type="button"
          className={`fchip${c.res ? " res" : ""}`}
          aria-label={`${c.label} 조건 풀기`}
          onClick={() => set(c.patch)}
        >
          <span>{c.label}</span>
          <CloseIcon />
        </button>
      ))}
    </>
  );
}
