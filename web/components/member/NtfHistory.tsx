"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { posterBg } from "../cards";
import { fetchNear, useNtfRead, type Near } from "./ntfRead";

// 내 캘린더 '알림 받은 내역' (앱 _render_notice_history · _ntf_cell · _render_near_picks).
// 오늘 알림은 종과 같은 번호를 써서 한쪽에서 읽으면 다른 쪽도 '읽음'. 지난 날 알림은 '지난 알림'.
// 아래 '내 주변 추천' 은 위치를 허용했을 때만 (20km 안, 별점 높은 순 → 다녀온 후기 많은 순 → 가까운 순, 3곳).

export type HistInbox = { id: string; title: string; body: string; why: string };
export type HistItem = {
  id: string;
  head: string; // 날짜 머리 ('오늘' · '11월 18일'), 같은 날 두 번째부터는 ''
  past: boolean;
  label: string;
  work: string;
  cafe: string;
  cafeId: string;
  poster: string;
  why: string;
};

export default function NtfHistory({
  cookie,
  initial,
  inbox,
  hist,
  nearKm,
}: {
  cookie: string;
  initial: string;
  inbox: HistInbox[];
  hist: HistItem[];
  nearKm: number;
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

  return (
    <>
      {inbox.length > 0 && <div className="nh-day">받은 알림</div>}
      {inbox.map((x) => (
        <div key={x.id} className={`ntf-item plain${read.has(x.id) ? " read" : ""}`}>
          <span className="ntf-st">{st(x.id)}</span>
          <b>{x.title}</b>
          <br />
          {x.body}
          <div className="ntf-why">{x.why}</div>
        </div>
      ))}
      {!hist.length && (
        <div className="ntf-empty">
          아직 받은 알림이 없어요. 리스트에서 팝업을 북마크하면 오픈·종료가 가까울 때 여기에 쌓여요.
        </div>
      )}
      {hist.map((h) => (
        <div key={h.id}>
          {h.head && <div className="nh-day">{h.head}</div>}
          <Link
            href={`/popup/${h.cafeId}`}
            className={`ntf-item has-pst${h.past || read.has(h.id) ? " read" : ""}`}
            onClick={() => mark([h.id])}
          >
            <span className="ntf-pst" style={posterBg(h.poster)} />
            <span className="ntf-body">
              <span className="ntf-st">{st(h.id, h.past)}</span>
              <b>{h.label}</b>
              <br />
              {h.work}
              <br />
              <span className="ntf-cafe">{h.cafe}</span>
              <span className="ntf-why">{h.why}</span>
            </span>
          </Link>
        </div>
      ))}

      <div className="nh-day">
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
      </div>
      {(near.state === "idle" || near.state === "denied" || near.state === "off") && (
        <div className="ntf-empty">
          위치를 허용하면 내 주변에서 별점 좋은 팝업을 추천해 드려요. 브라우저 주소창의 위치 권한을 허용해 주세요.
          {near.state === "idle" && (
            <>
              {" "}
              <button type="button" className="ntf-loc" onClick={ask}>
                내 위치 허용하기
              </button>
            </>
          )}
        </div>
      )}
      {near.state === "asking" && <div className="ntf-empty">내 위치를 확인하는 중이에요…</div>}
      {near.state === "done" && !near.items.length && (
        <div className="ntf-empty">내 위치에서 {nearKm}km 안에 지금 열려 있거나 곧 여는 팝업이 없어요.</div>
      )}
      {near.state === "done" &&
        near.items.map((x) => (
          <Link
            key={x.id}
            href={`/popup/${x.cafeId}`}
            className={`ntf-item has-pst${read.has(x.id) ? " read" : ""}`}
            onClick={() => mark([x.id])}
          >
            <span className="ntf-pst" style={posterBg(x.poster)} />
            <span className="ntf-body">
              <span className="ntf-st">{st(x.id)}</span>
              <b>내 주변 {x.dist}</b>
              <br />
              {x.work}
              <br />
              <span className="ntf-cafe">{x.cafe}</span>
            </span>
          </Link>
        ))}
    </>
  );
}
