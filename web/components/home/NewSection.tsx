"use client";
import Link from "next/link";
import { useState } from "react";
import type { Item } from "@/lib/popup";
import HScroll from "../HScroll";
import FreshCard from "./FreshCard";
import { SparkLine } from "./Icons2";
import SecHead from "./SecHead";

// 따끈따끈 신규 등록 팝업 (A-Home): 제목 오른쪽 지역 칩(전체 + 팝업 많은 지역)으로 거르고, 처음 등록이 늦은 순 12곳을
// 196px 포스터 카드로 옆으로 넘긴다. 맨 끝은 점선 '더보기' 카드 (리스트 최신순)
export default function NewSection({ items, areas, today }: { items: Item[]; areas: string[]; today: string }) {
  const [area, setArea] = useState("전체");
  const shown = (area === "전체" ? items : items.filter((p) => p.area === area)).slice(0, 12);
  return (
    <section className="ah-sec ah-new" aria-labelledby="ah-new-h">
      <SecHead id="ah-new-h" title="따끈따끈 신규 등록 팝업" icon={<SparkLine />}>
        <div className="ah-chips" role="group" aria-label="지역">
          {["전체", ...areas].map((a) => (
            <button key={a} type="button" className="ah-chip" aria-pressed={area === a} onClick={() => setArea(a)}>
              {a}
            </button>
          ))}
        </div>
      </SecHead>
      {shown.length ? (
        // key: 지역을 바꾸면 줄을 처음부터 다시 (넘긴 위치 · 화살표 초기화)
        <HScroll key={area} className="ah-row" label="신규 등록 팝업">
          {shown.map((p) => (
            <FreshCard key={p.id} p={p} today={today} />
          ))}
          <Link href="/list?sort=new" className="ah-morecard" prefetch={false}>
            더보기
            <span>리스트 최신순으로</span>
          </Link>
        </HScroll>
      ) : (
        <div className="ah-empty">이 지역에 새로 등록된 팝업이 없어요.</div>
      )}
    </section>
  );
}
