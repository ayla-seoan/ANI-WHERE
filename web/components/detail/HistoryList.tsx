"use client";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { restoreAction } from "@/app/popup-actions";
import type { HistoryCard } from "@/lib/server/cafe";
import { toast } from "../member/Toast";
import { RankStamp } from "../RankStamp";

// 수정 이력 (A-DetailEdit 시안 오른쪽 칸 · 앱 _history_card_html): 기록 하나가 카드 하나, 최근 것이 위.
// 지금 내용은 민트 바탕 + '지금 내용'. 지금 것 말고는 '이 버전으로 돌아가기' (지도에서 내린 기록은 빼고).
// 고친 회원 이름 앞에는 그 회원의 20px 후기 도장 (도장이 없으면 사람 아이콘). 처음엔 4개만 보이고 '이력 더보기'.
const FIRST = 4;

const P: Record<string, React.ReactNode> = {
  auto_awesome: <path d="M12 3l1.8 4.6L18 9.5l-4.2 1.9L12 16l-1.8-4.6L6 9.5l4.2-1.9L12 3zM18.5 15l.8 2 2 .8-2 .9-.8 2-.9-2-2-.9 2-.8.9-2z" />,
  add_circle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v8M8 12h8" />
    </>
  ),
  edit: <path d="M4 20h4L19 9l-4-4L4 16v4z" />,
  edit_note: <path d="M4 6h10M4 10h10M4 14h6M14 20h3l5-5-3-3-5 5v3z" />,
  content_paste: <path d="M9 4h6v3H9zM7 5H5v15h14V5h-2M8 11h8M8 15h6" />,
  undo: <path d="M9 14L4 9l5-5M4 9h10a6 6 0 010 12h-3" />,
  visibility_off: <path d="M3 3l18 18M10.6 6.1A9.9 9.9 0 0112 6c5 0 9 6 9 6a17 17 0 01-3.2 3.7M6.6 6.6A17 17 0 003 12s4 6 9 6a9.6 9.6 0 004.4-1.1M9.9 9.9a3 3 0 004.2 4.2" />,
  event_busy: <path d="M4 6h16v14H4zM8 3v4M16 3v4M4 10h16M10 13l4 4M14 13l-4 4" />,
  science: <path d="M9 3h6M10 3v6L5 18a2 2 0 002 3h10a2 2 0 002-3l-5-9V3M7.5 14h9" />,
  history: (
    <>
      <path d="M4 12a8 8 0 108-8 8 8 0 00-5.7 2.3L4 8.6M4 4v4.6h4.6" />
      <path d="M12 8v4.2l2.8 1.8" />
    </>
  ),
  restore: <path d="M4 12a8 8 0 108-8 8 8 0 00-5.7 2.3L4 8.6M4 4v4.6h4.6M12 8v4.2l2.8 1.8" />,
  local_cafe: <path d="M4 8h12v6a5 5 0 01-5 5H9a5 5 0 01-5-5V8zM16 9h2a2.5 2.5 0 010 5h-2M6 4v2M10 3v3M14 4v2" />,
  calendar_month: <path d="M4 6h16v14H4zM8 3v4M16 3v4M4 10h16" />,
  location_on: <path d="M12 21s-6-5.3-6-11a6 6 0 1112 0c0 5.7-6 11-6 11zM12 12a2 2 0 100-4 2 2 0 000 4z" />,
  person: <path d="M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c1-4.4 4.2-6.5 8-6.5s7 2.1 8 6.5" />,
  arrow_forward: <path d="M5 12h14M13 6l6 6-6 6" />,
};

export function Mi({ name }: { name: string }) {
  return (
    <svg className="mi" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      {P[name] || P.history}
    </svg>
  );
}

export default function HistoryList({
  entryId,
  cards,
  lv = {},
}: {
  entryId: string;
  cards: HistoryCard[];
  /** 기록 번호 → 고친 회원의 후기 도장 랭크 (0 = 없음) */
  lv?: Record<number, number>;
}) {
  const router = useRouter();
  const [busy, start] = useTransition();
  const [all, setAll] = useState(false);
  return (
    <div className="hx ade-hx">
      {(all ? cards : cards.slice(0, FIRST)).map((c) => (
        <div key={c.revision} className={`hx-item${c.now ? " now" : ""}`}>
          <div className="hx-card">
            <div className="hx-top">
              <b>{c.revision}번째</b>
              <span className="hx-when">{c.when}</span>
              <span className="hx-src">
                <Mi name={c.icon} />
                {c.label}
              </span>
              {c.now && <span className="hx-now">지금 내용</span>}
            </div>
            <div className="hx-who">
              {lv[c.revision] ? <RankStamp lv={lv[c.revision]} size={20} /> : <Mi name="person" />}
              {c.who}
            </div>
            {c.first ? (
              <>
                <div className="hx-chg">처음 등록</div>
                <div className="hx-meta">
                  <Mi name="local_cafe" />
                  {c.first.cafe} · {c.first.work}
                </div>
                <div className="hx-meta">
                  <Mi name="calendar_month" />
                  {c.first.period}
                </div>
                <div className="hx-meta">
                  <Mi name="location_on" />
                  {c.first.address}
                </div>
              </>
            ) : c.diffs.length ? (
              c.diffs.map((d, i) => (
                <div key={i} className="hx-diff">
                  <span className="hx-k">{d.k}</span>
                  {d.act ? (
                    <span className={`hx-act ${d.act.kind}`}>{d.act.text}</span>
                  ) : (
                    <>
                      <span className="hx-old">{d.old}</span>
                      <span className="hx-arrow">
                        <Mi name="arrow_forward" />
                      </span>
                      <span className="hx-new">{d.new}</span>
                    </>
                  )}
                </div>
              ))
            ) : (
              <div className="hx-meta">바뀐 내용 없음</div>
            )}
          </div>
          {c.canRestore && (
            <div className="hx-restore">
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  start(async () => {
                    const r = await restoreAction(entryId, c.revision);
                    if (r.error) {
                      toast(r.error, "error");
                      return;
                    }
                    toast(r.ok || "", "restore");
                    document.querySelector(".ad-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" });
                    router.refresh();
                  })
                }
              >
                <Mi name="restore" />이 버전으로 돌아가기
              </button>
            </div>
          )}
        </div>
      ))}
      {!all && cards.length > FIRST && (
        <button type="button" className="ade-add" onClick={() => setAll(true)}>
          이력 더보기 ({cards.length - FIRST})
        </button>
      )}
    </div>
  );
}
