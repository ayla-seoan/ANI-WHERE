"use client";
import type { Item } from "@/lib/popup";
import AskChat from "./AskChat";

// PC 오른쪽 칸 '물어보기' (앱 render_ask_panel). 모바일에서는 숨기고 AskFab 시트로.
export default function AskPanel({
  items,
  today,
  onShowAll,
}: {
  items: Item[];
  today: string;
  onShowAll?: (ids: string[], label: string) => void;
}) {
  return (
    <aside className="ask-panel" aria-label="ANI:WHERE에게 물어보기">
      <div className="apn-head">
        <span className="apn-title">ANI:WHERE에게 물어보기</span>
      </div>
      <AskChat items={items} today={today} onShowAll={onShowAll} />
    </aside>
  );
}
