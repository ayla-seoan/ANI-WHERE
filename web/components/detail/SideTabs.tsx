"use client";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { EditIcon } from "../Icons";
import BlogTab, { useBlogCount } from "./BlogTab";

// 상세 화면 틀 (A-Detail · A-DetailEdit 시안): 위 = 사진 + 정보 2단(hero), 아래 = 화면 폭 전체 탭 '리뷰 n · 블로그 후기 n · 수정하기'.
// 수정하기 탭에서는 위 2단을 접고 작은 머리(mini: 포스터 · 제목)만 보여 준다.
// 고른 탭은 주소 ?tab=edit · ?tab=blog 로 기억해서 저장해 다시 그려도 첫 탭(리뷰)으로 돌아가지 않는다.
// 리뷰 · 수정하기는 둘 다 그려 두고 안 고른 쪽만 숨긴다 (쓰던 글이 탭을 오가도 남는다).

type Tab = "review" | "blog" | "edit";
const of = (v: string | null): Tab => (v === "edit" || v === "blog" ? v : "review");

export default function SideTabs({
  cafeId,
  reviewCount,
  hero,
  mini,
  review,
  edit,
}: {
  cafeId: string;
  reviewCount: number;
  hero: React.ReactNode;
  mini: React.ReactNode;
  review: React.ReactNode;
  edit: React.ReactNode;
}) {
  const sp = useSearchParams();
  const [tab, setTab] = useState<Tab>(of(sp.get("tab")));
  const blogN = useBlogCount(cafeId); // 세는 중이면 null
  const pick = (t: Tab) => {
    setTab(t);
    try {
      const u = new URL(window.location.href);
      if (t === "review") u.searchParams.delete("tab");
      else u.searchParams.set("tab", t);
      window.history.replaceState(window.history.state, "", u.pathname + u.search + u.hash);
    } catch {
      /* 주소를 못 바꿔도 탭은 바뀐다 */
    }
  };
  const tabs: [Tab, React.ReactNode][] = [
    ["review", <>리뷰 {reviewCount}</>],
    ["blog", <>블로그 후기{blogN === null ? "" : ` ${blogN}`}</>],
    [
      "edit",
      <>
        <EditIcon />
        수정하기
      </>,
    ],
  ];
  return (
    <>
      <div hidden={tab === "edit"}>{hero}</div>
      {tab === "edit" && mini}
      <div className="ad-tabs" role="tablist" aria-label="상세 탭">
        {tabs.map(([t, label]) => (
          <button
            key={t}
            type="button"
            role="tab"
            id={`tab-${t}`}
            aria-selected={tab === t}
            aria-controls={`pane-${t}`}
            className={tab === t ? "on" : ""}
            onClick={() => pick(t)}
          >
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="pane-review" aria-labelledby="tab-review" hidden={tab !== "review"}>
        {review}
      </div>
      <div role="tabpanel" id="pane-blog" aria-labelledby="tab-blog" hidden={tab !== "blog"}>
        {tab === "blog" && <BlogTab cafeId={cafeId} />}
      </div>
      <div role="tabpanel" id="pane-edit" aria-labelledby="tab-edit" hidden={tab !== "edit"}>
        {edit}
      </div>
    </>
  );
}
