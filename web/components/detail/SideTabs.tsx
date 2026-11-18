"use client";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { ChatIcon, EditIcon } from "../Icons";

// 상세 화면 오른쪽: 리뷰 / 수정하기 탭 (앱 render_detail_tabs). 고른 탭은 주소 ?tab=edit 로 기억해서
// 이미지를 지우거나 저장해 다시 그려도 첫 탭(리뷰)으로 돌아가지 않는다. 두 탭 모두 그려 두고 안 고른 쪽만 숨긴다.

export default function SideTabs({
  reviewCount,
  review,
  edit,
}: {
  reviewCount: number;
  review: React.ReactNode;
  edit: React.ReactNode;
}) {
  const sp = useSearchParams();
  const [tab, setTab] = useState<"review" | "edit">(sp.get("tab") === "edit" ? "edit" : "review");
  const pick = (t: "review" | "edit") => {
    setTab(t);
    try {
      const u = new URL(window.location.href);
      if (t === "edit") u.searchParams.set("tab", "edit");
      else u.searchParams.delete("tab");
      window.history.replaceState(window.history.state, "", u.pathname + u.search + u.hash);
    } catch {
      /* 주소를 못 바꿔도 탭은 바뀐다 */
    }
  };
  return (
    <aside className="detail-side" aria-label="리뷰 · 수정하기">
      <div className="side-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          id="tab-review"
          aria-selected={tab === "review"}
          aria-controls="pane-review"
          className={tab === "review" ? "on" : ""}
          onClick={() => pick("review")}
        >
          <ChatIcon />
          리뷰 {reviewCount}
        </button>
        <button
          type="button"
          role="tab"
          id="tab-edit"
          aria-selected={tab === "edit"}
          aria-controls="pane-edit"
          className={tab === "edit" ? "on" : ""}
          onClick={() => pick("edit")}
        >
          <EditIcon />
          수정하기
        </button>
      </div>
      <div role="tabpanel" id="pane-review" aria-labelledby="tab-review" hidden={tab !== "review"}>
        {review}
      </div>
      <div role="tabpanel" id="pane-edit" aria-labelledby="tab-edit" hidden={tab !== "edit"}>
        {edit}
      </div>
    </aside>
  );
}
