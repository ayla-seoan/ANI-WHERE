"use client";
import { useState } from "react";
import type { Item } from "@/lib/popup";
import { areaPill, HomeCard } from "../cards";
import HScroll from "../HScroll";

// 따끈따끈 신규 등록 팝업: 지역 알약(전체 + 팝업 많은 지역 3곳)으로 거르고, 처음 등록이 늦은 순 12곳
export default function NewSection({ items, areas, today }: { items: Item[]; areas: string[]; today: string }) {
  const [area, setArea] = useState("전체");
  const shown = (area === "전체" ? items : items.filter((p) => p.area === area)).slice(0, 12);
  const cityOf = (a: string) => items.find((p) => p.area === a)?.city || "";
  return (
    <>
      <div className="pills" role="group" aria-label="지역">
        {["전체", ...areas].map((a) => (
          <button
            key={a}
            type="button"
            className="pill"
            aria-pressed={area === a}
            onClick={() => setArea(a)}
            style={a === "전체" ? undefined : areaPill(cityOf(a), area === a)}
          >
            {a}
          </button>
        ))}
      </div>
      {shown.length ? (
        <HScroll className="home-row" label="신규 등록 팝업">
          {shown.map((p) => (
            <HomeCard key={p.id} p={p} today={today} />
          ))}
        </HScroll>
      ) : (
        <div className="home-empty">이 지역에 새로 등록된 팝업이 없어요.</div>
      )}
    </>
  );
}
