"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { areaFill, posterBg } from "../cards";
import { fetchNear, useNtfRead, type Near } from "./ntfRead";

// 내 캘린더 '알림 받은 내역' (A-Cal 오른쪽 단, 앱 _render_notice_history · _ntf_cell · _render_near_picks).
// 오늘 알림은 종과 같은 번호를 써서 한쪽에서 읽으면 다른 쪽도 '읽음'. 지난 날 알림은 '지난 알림'.
// 아래 '내 주변 추천' 은 위치를 허용했을 때만 (20km 안, 별점 높은 순 → 다녀온 후기 많은 순 → 가까운 순, 3곳).

export type HistInbox = { id: string; title: string; body: string; why: string; day: string };
export type HistItem = {
  id: string;
  day: string; // '오늘' · '11.18'
  past: boolean;
  label: string;
  work: string;
  cafe: string;
  cafeId: string;
  poster: string;
  area: string;
  city: string;
  why: string;
};

export default function NtfHistory({
  cookie,
  initial,
  inbox,
  hist,
  nearKm,
  help,
  tip,
}: {
  cookie: string;
  initial: string;
  inbox: HistInbox[];
  hist: HistItem[];
  nearKm: number;
  /** '?' 를 누르면 보이는 알림 기준 */
  help: string;
  /** 맨 아래 마스코트 안내 한 줄 ('' 이면 안 보임) */
  tip: string;
}) {
  const { read, mark } = useNtfRead(cookie, initial);
  const [near, setNear] = useState<Near>({ state: "idle", items: [] });
  useEffect(() => {
    let live = true;
    fetchNear("cal", false).then((n) => live && setNear(n));
    return () => {
      live = false;
    };
  }, []);
  const ask = () => {
    setNear({ state: "asking", items: [] });
    fetchNear("cal", true).then(setNear);
  };
  const st = (id: string, past = false) => (past ? "지난 알림" : read.has(id) ? "읽음" : "새 알림");
  // '모두 읽음': 받은 알림 + 오늘 알림 + 내 주변 추천 (지난 알림은 원래 읽음으로 보인다)
  const fresh = [...inbox.map((x) => x.id), ...hist.filter((h) => !h.past).map((h) => h.id), ...near.items.map((x) => x.id)].filter(
    (id) => !read.has(id),
  );

  return (
    <>
      <div className="nh-head">
        <h2>
          알림 받은 내역
          <span className="help" tabIndex={0}>
            ?<span className="tip">{help}</span>
          </span>
        </h2>
        {fresh.length > 0 && (
          <button type="button" className="nh-all" onClick={() => mark(fresh)}>
            모두 읽음
          </button>
        )}
      </div>
      <span className="nh-sub">최근 3일</span>
      {inbox.map((x) => (
        <div key={x.id} className={`nh-item plain${read.has(x.id) ? " read" : ""}`}>
          <span className="nh-body">
            <span className="nh-meta">
              <span className="nh-st">{st(x.id)}</span>
              <span className="nh-time">{x.day}</span>
            </span>
            <strong>{x.title}</strong>
            <span className="nh-txt">{x.body}</span>
            <span className="nh-why">{x.why}</span>
          </span>
        </div>
      ))}
      {!hist.length && !inbox.length && (
        <div className="nh-empty">아직 받은 알림이 없어요. 리스트에서 팝업을 북마크하면 오픈·종료가 가까울 때 여기에 쌓여요.</div>
      )}
      {hist.map((h) => (
        <Link
          key={h.id}
          href={`/popup/${h.cafeId}`}
          className={`nh-item${h.past || read.has(h.id) ? " read" : ""}`}
          onClick={() => mark([h.id])}
        >
          <span className="nh-pst" style={posterBg(h.poster)} />
          <span className="nh-body">
            <span className="nh-meta">
              <span className="nh-st">{st(h.id, h.past)}</span>
              <span className="nh-time">{h.day}</span>
              {h.area && (
                <span className="nh-area" style={areaFill(h.city)}>
                  {h.area}
                </span>
              )}
            </span>
            <strong>
              {h.label} · {h.work || h.cafe}
            </strong>
            {h.work && <span className="nh-txt">{h.cafe}</span>}
            <span className="nh-why">{h.why}</span>
          </span>
        </Link>
      ))}

      <section className="nh-near" aria-labelledby="nh-near-h">
        <h2 id="nh-near-h">
          내 주변 추천
          <span className="help" tabIndex={0}>
            ?
            <span className="tip">
              내 위치에서 {nearKm}km 안에 있는 팝업 중 <b>지금 진행 중</b>이거나 <b>3일 안에 여는</b> 곳을 골라요.
              <br />
              순서: 별점 높은 순 → 다녀온 후기 많은 순 → 가까운 순, 최대 3곳.
              <br />
              이미 북마크한 팝업은 위 알림에 있어서 빼요. 위치를 허용해야 보여요.
            </span>
          </span>
        </h2>
        <span className="nh-sub">{nearKm}km 안 · 진행 중이거나 3일 안에 열림 · 별점 높은 순</span>
        {(near.state === "idle" || near.state === "denied" || near.state === "off") && (
          <div className="nh-empty">
            위치를 허용하면 내 주변에서 별점 좋은 팝업을 추천해 드려요. 브라우저 주소창의 위치 권한을 허용해 주세요.
            {near.state === "idle" && (
              <button type="button" className="nh-loc" onClick={ask}>
                내 위치 허용하기
              </button>
            )}
          </div>
        )}
        {near.state === "asking" && <div className="nh-empty">내 위치를 확인하는 중이에요…</div>}
        {near.state === "done" && !near.items.length && (
          <div className="nh-empty">내 위치에서 {nearKm}km 안에 지금 열려 있거나 곧 여는 팝업이 없어요.</div>
        )}
        {near.state === "done" &&
          near.items.map((x) => (
            <Link key={x.id} href={`/popup/${x.cafeId}`} className={`nr-item${read.has(x.id) ? " read" : ""}`} onClick={() => mark([x.id])}>
              <span className="nr-pst" style={posterBg(x.poster)} />
              <span className="nr-body">
                <strong>{x.work || x.cafe}</strong>
                <span>
                  {[x.area, x.work ? x.cafe : ""].filter(Boolean).join(" · ")}
                </span>
              </span>
              <span className="nr-km">{x.dist}</span>
            </Link>
          ))}
      </section>

      {tip && (
        <div className="nh-tip">
          <img src="/mascot.png" alt="" />
          <span>{tip}</span>
        </div>
      )}
    </>
  );
}
