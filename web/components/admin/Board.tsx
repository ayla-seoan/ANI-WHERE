import Link from "next/link";
import { addDays, todayKST } from "@/lib/popup";
import { posterBg } from "@/components/cards";
import { BOARD_COLS, ganttRows, popupBoard, posterOf, ymdOf } from "@/lib/server/admin";
import type { Row } from "@/lib/server/store";
import { IcMore } from "./AdminIcons";
import { Caption } from "./Bits";

// 관리자 '팝업 현황' (앱 _admin_gantt · _admin_board): 고른 주의 하루 단위 간트 차트 + 네 칸 현황.

export const GANTT_COLOR: Record<string, string> = { 예정: "#3672BD", 진행: "#14B8A6", 종료: "#A9B3B0" };
export const GANTT_PAGE = 20; // 이 주 일정: 처음 20곳, 더보기마다 20곳 더
export const BOARD_PAGE = 10; // 고른 주 현황: 칸마다 처음 10곳, 더보기마다 10곳 더
const BOARD_COLOR: Record<string, string> = { "새로 생성": "#14B8A6", 예정: "#3672BD", 진행: "#23866A", 종료: "#8A9592" };
const WD = "월화수목금토일";

export const popupHref = (r: Row) => `/popup/${encodeURIComponent(String(r.entry_id || ""))}`;
const md = (ymd: string) => `${Number(ymd.slice(5, 7))}/${Number(ymd.slice(8, 10))}`;

/** 포스터 카드 (칸반 · 숫자 카드 목록 같은 모양) */
export function PopupCard({ r, period, link = true }: { r: Row; period: string; link?: boolean }) {
  const body = (
    <>
      <i className="adm-poster" style={posterBg(posterOf(r.images))} aria-hidden />
      <div>
        <b>{String(r.work || "")}</b>
        <span>{String(r.cafe_name || "")}</span>
        <em>{period}</em>
      </div>
    </>
  );
  // 종료 칸은 정보만 (11/19 요청: 눌러도 상세로 가지 않음 — 끝난 팝업은 지도에서 내려가 있다)
  if (!link) return <div className="adm-card adm-pcard adm-static">{body}</div>;
  return (
    <Link className="adm-card adm-link adm-pcard" href={popupHref(r)}>
      {body}
    </Link>
  );
}

/** 이번 주 월요일 (한국 날짜) */
function thisMonday(): string {
  const t = todayKST();
  const wd = (new Date(`${t}T00:00:00Z`).getUTCDay() + 6) % 7; // 월=0
  return addDays(t, -wd);
}

export function Gantt({
  all,
  mon,
  today,
  shown,
  moreHref,
}: {
  all: Row[];
  mon: string;
  today: string;
  shown: number;
  moreHref: string;
}) {
  const start = mon;
  const end = addDays(mon, 6);
  const span = 7;
  const every = ganttRows(all, start, end, 10_000);
  const list = every.slice(0, shown);
  const dIdx = (d: string) => Math.round((Date.parse(d) - Date.parse(start)) / 86400000);
  const pct = (d: string) => Math.max(0, Math.min(100, (dIdx(d) / span) * 100));
  const inWeek = start <= today && today <= end;
  const marks = inWeek ? (
    <>
      <div className="gt-wk" style={{ left: `${pct(today).toFixed(2)}%`, width: `${(100 / span).toFixed(2)}%` }} />
      <div className="gt-today" style={{ left: `${(pct(today) + 50 / span).toFixed(2)}%` }} />
    </>
  ) : null;
  const grid = Array.from({ length: span - 1 }, (_, i) => (
    <div key={i} className="gt-grid" style={{ left: `${pct(addDays(start, i + 1)).toFixed(2)}%` }} />
  ));
  return (
    <>
      <div className="gt">
        <div className="gt-row gt-head">
          <div className="gt-lab">
            <b>팝업 {every.length}곳</b>
          </div>
          <div className="gt-track">
            {Array.from({ length: span }, (_, i) => {
              const d = addDays(start, i);
              const now = d === today;
              return (
                <div key={d} className={`gt-tick${now ? " now" : ""}`} style={{ left: `${(((i + 0.5) / span) * 100).toFixed(2)}%` }}>
                  <span className="gt-full">
                    {now ? "오늘 " : ""}
                    {md(d)}({WD[i]})
                  </span>
                  <span className="gt-short">{now ? "오늘" : WD[i]}</span>
                </div>
              );
            })}
          </div>
        </div>
        {list.map((r) => {
          const s = ymdOf(r.start_date);
          const e = ymdOf(r.end_date);
          const kind = s > today ? "예정" : e < today ? "종료" : "진행";
          const left = pct(s > start ? s : start);
          const right = pct(addDays(e < end ? e : end, 1));
          return (
            <div className="gt-row" key={String(r.entry_id)}>
              <div className="gt-lab">
                <Link className="adm-link" href={popupHref(r)}>
                  <b>{String(r.work || "")}</b>
                </Link>{" "}
                <span>
                  {String(r.cafe_name || "")} · {md(s)}~{md(e)}
                </span>
              </div>
              <div className="gt-track">
                {marks}
                {grid}
                <div
                  className={`gt-bar${s < start ? " cl" : ""}${e > end ? " cr" : ""}`}
                  style={{
                    ["--c" as string]: GANTT_COLOR[kind],
                    left: `${left.toFixed(2)}%`,
                    width: `${Math.max(right - left, 0.8).toFixed(2)}%`,
                  }}
                />
              </div>
            </div>
          );
        })}
        {!list.length && <div className="adm-empty">이 기간에 걸친 팝업이 없어요.</div>}
        <div className="gt-legend">
          {Object.entries(GANTT_COLOR).map(([k, c]) => (
            <span key={k}>
              <i style={{ background: c }} />
              {k}
            </span>
          ))}
          <span>
            <i style={{ background: "#FF5A5A" }} />
            오늘 (빨간 칸)
          </span>
          <span>막대가 칸 끝에 붙어 있으면 이 주 앞뒤로 이어져요</span>
        </div>
      </div>
      {every.length > list.length && (
        <div className="adm-more">
          <Link className="st-btn" href={moreHref} scroll={false}>
            <IcMore />
            {every.length - list.length}건 더보기
          </Link>
        </div>
      )}
    </>
  );
}

export function BoardCols({
  all,
  mon,
  shown,
  moreHref,
}: {
  all: Row[];
  mon: string;
  shown: number[];
  moreHref: (i: number) => string;
}) {
  const board = popupBoard(all, mon);
  // 지난 주를 고르면: 종료된 팝업은 다음 주 월요일에 DB 에서 지워져(supabase 012) 그 주에 끝난 팝업이 안 보일 수 있다
  const pastWeek = mon < thisMonday();
  return (
    <>
      <div className="adm-board">
        {BOARD_COLS.map((name, i) => {
          const list = board[name];
          const n = shown[i];
          return (
            <div key={name} className="adm-boardcol">
              <div className="adm-col" style={{ ["--c" as string]: BOARD_COLOR[name] }}>
                <div className="adm-colhead">
                  {name}
                  <small>{list.length}곳</small>
                </div>
                {name === "종료" && pastWeek && (
                  <div className="adm-purge-note">
                    기간이 끝난 팝업은 일주일 단위로 다음 주 월요일에 삭제돼요. 지난 주에 종료된 팝업은 여기에 보이지 않을 수
                    있어요.
                  </div>
                )}
                {list.slice(0, n).map((r) => (
                  <PopupCard
                    key={String(r.entry_id)}
                    r={r}
                    link={name !== "종료"}
                    period={`${String(r.start_date || "").slice(5)} ~ ${String(r.end_date || "").slice(5)}`}
                  />
                ))}
                {!list.length && <div className="adm-empty">없어요</div>}
              </div>
              {list.length > n && (
                <div className="adm-more">
                  <Link className="st-btn" href={moreHref(i)} scroll={false}>
                    <IcMore />
                    {list.length - n}건 더보기
                  </Link>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <Caption>
        새로 생성 = 그 주에 처음 등록 · 예정 = 그 주가 끝난 뒤 4주 안에 시작 · 진행 = 그 주에 열려 있고 다음 주에도 이어짐 ·
        종료 = 그 주에 끝남
      </Caption>
    </>
  );
}

