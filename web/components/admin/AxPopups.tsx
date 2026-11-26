import Link from "next/link";
import { addDays, mondayOf } from "@/lib/popup";
import { posterBg } from "@/components/cards";
import { missingOf, popName } from "@/lib/server/a-admin";
import { BOARD_COLS, ganttRows, popupBoard, posterOf, ymdOf } from "@/lib/server/admin";
import type { Row } from "@/lib/server/store";
import { AxCard, AxEmpty, AxHead } from "./AxShell";
import { popupHref } from "./Board";

// 팝업 현황 (AdmX-2Popups): 상태 필터 카드 · 주간 간트 · 상태별 보드. 칸 나누기는 예전 관리자와 같은 admin.popupBoard · ganttRows.

type SP = Record<string, string | undefined>;
export const GANTT_PAGE = 20;
export const BOARD_PAGE = 10;
const WD = "월화수목금토일";
/** 상태 필터 칸 (주소 ?st=) */
const SEG: [string, string][] = [
  ["", "전체"],
  ["new", "새로 생성"],
  ["soon", "예정"],
  ["live", "진행"],
  ["end", "종료"],
];
const COL_OF: Record<string, (typeof BOARD_COLS)[number]> = { new: "새로 생성", soon: "예정", live: "진행", end: "종료" };
const COL_CLS: Record<string, string> = { "새로 생성": "new", 예정: "soon", 진행: "live", 종료: "end" };

const md = (ymd: string) => (ymd ? `${Number(ymd.slice(5, 7))}.${ymd.slice(8, 10)}` : "?");
const diff = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
const int = (v: string | undefined, d: number) => (/^\d{1,4}$/.test(v || "") ? Number(v) : d);

export default function AxPopups({
  cafes,
  mon,
  today,
  sp,
  href,
  weekNav,
}: {
  cafes: Row[];
  mon: string;
  today: string;
  sp: SP;
  href: (p: SP) => string;
  weekNav: React.ReactNode;
}) {
  const sun = addDays(mon, 6);
  const q = (sp.pq || "").trim().toLowerCase();
  const hit = (r: Row) => !q || `${r.work || ""} ${r.cafe_name || ""} ${r.characters || ""}`.toLowerCase().includes(q);
  const board = popupBoard(cafes, mon);
  for (const k of BOARD_COLS) board[k] = board[k].filter(hit);
  const st = sp.st && COL_OF[sp.st] ? sp.st : "";
  const ids = (k: (typeof BOARD_COLS)[number]) => new Set(board[k].map((r) => String(r.entry_id)));
  const union = new Set(BOARD_COLS.flatMap((k) => [...ids(k)]));
  const counts: Record<string, number> = {
    "": union.size,
    new: board["새로 생성"].length,
    soon: board.예정.length,
    live: board.진행.length,
    end: board.종료.length,
  };
  const keep = st ? ids(COL_OF[st]) : null;
  const every = ganttRows(cafes, mon, sun, 10_000).filter((r) => hit(r) && (!keep || keep.has(String(r.entry_id))));
  const gn = Math.max(GANTT_PAGE, int(sp.gn, GANTT_PAGE));
  const list = every.slice(0, gn);
  const inWeek = mon <= today && today <= sun;
  const pct = (d: string) => Math.max(0, Math.min(100, (diff(mon, d) / 7) * 100));
  const todayLeft = ((diff(mon, today) + 0.5) / 7) * 100;
  const pastWeek = mon < mondayOf(today);
  const cols = st ? [COL_OF[st]] : [...BOARD_COLS];
  const keepParams = Object.entries(sp).filter(([k, v]) => v && !["pq", "gn", "b0", "b1", "b2", "b3"].includes(k));

  return (
    <>
      <AxHead
        eyebrow="팝업 현황"
        title={`${mon === mondayOf(today) ? "이번 주" : "이 주"} 팝업 ${union.size}곳`}
        right={
          <>
            {weekNav}
            <form className="ax-search" action="/data" method="get" role="search">
              {keepParams.map(([k, v]) => (
                <input key={k} type="hidden" name={k} value={v} />
              ))}
              <label>
                <span className="ax-sr">팝업 검색</span>
                <input className="ax-input pill" name="pq" defaultValue={sp.pq || ""} placeholder="작품 · 팝업 이름 검색" />
              </label>
            </form>
          </>
        }
      />
      {q && (
        <p className="ax-cap">
          &apos;{sp.pq}&apos; 로 찾은 결과예요 ·{" "}
          <Link className="ax-link" href={href({ pq: undefined })} scroll={false}>
            찾기 지우기
          </Link>
        </p>
      )}

      <div className="ax-seg5" role="tablist" aria-label="상태로 거르기">
        {SEG.map(([k, label]) => (
          <Link
            key={k || "all"}
            role="tab"
            aria-selected={st === k}
            href={href({ st: k || undefined, gn: undefined })}
            scroll={false}
            className={`ax-segc${st === k ? " on" : ""}`}
          >
            <span>
              <i className={`ax-dot ${k || "all"}`} aria-hidden />
              {label}
            </span>
            <strong>{counts[k]}</strong>
          </Link>
        ))}
      </div>

      <AxCard
        id="ax-gantt"
        title="주간 간트"
        right={
          <span className="ax-legend">
            <span>
              <i className="ax-dot soon" aria-hidden />
              예정
            </span>
            <span>
              <i className="ax-dot live" aria-hidden />
              진행
            </span>
            <span>
              <i className="ax-dot end" aria-hidden />
              종료
            </span>
            <span>
              <i className="ax-dot today" aria-hidden />
              오늘
            </span>
            <span>
              <i className="ax-dot warn" aria-hidden />
              확인 = 정보 빠짐
            </span>
          </span>
        }
      >
        <div className="ax-gt">
          <div className="ax-gt-head">
            <span className="ax-gt-name">이 주에 걸친 {every.length}곳</span>
            <span className="ax-gt-days">
              {Array.from({ length: 7 }, (_, i) => {
                const d = addDays(mon, i);
                return (
                  <span key={d} className={d === today ? "today" : undefined}>
                    {WD[i]} {Number(d.slice(8, 10))}
                  </span>
                );
              })}
            </span>
          </div>
          {list.map((r) => {
            const s = ymdOf(r.start_date);
            const e = ymdOf(r.end_date);
            const kind = s > today ? "soon" : e < today ? "end" : "live";
            const left = pct(s > mon ? s : mon);
            const right = pct(addDays(e < sun ? e : sun, 1));
            const warn = kind !== "end" && missingOf(r).length > 0;
            const label = kind === "soon" ? "예정" : kind === "end" ? "종료" : "진행";
            return (
              <Link key={String(r.entry_id)} className="ax-gt-row" href={popupHref(r)}>
                <span className="ax-gt-name">
                  <i className="ax-thumb" style={posterBg(posterOf(r.images))} aria-hidden />
                  <span className="ax-gt-t">
                    <b>{String(r.work || "") || popName(r)}</b>
                    <small>
                      {String(r.cafe_name || "")} · {md(s)}~{md(e)}
                    </small>
                  </span>
                  {warn && <span className="ax-warn">확인</span>}
                </span>
                <span className="ax-gt-track" aria-label={`${label} ${md(s)}~${md(e)}`}>
                  {Array.from({ length: 6 }, (_, i) => (
                    <i key={i} className="ax-gt-grid" style={{ left: `${(((i + 1) / 7) * 100).toFixed(2)}%` }} />
                  ))}
                  {inWeek && <i className="ax-gt-today" style={{ left: `${todayLeft.toFixed(2)}%` }} />}
                  <span
                    className={`ax-gt-bar ${kind}${s < mon ? " cl" : ""}${e > sun ? " cr" : ""}`}
                    style={{ left: `${left.toFixed(2)}%`, width: `${Math.max(right - left, 1).toFixed(2)}%` }}
                  />
                </span>
              </Link>
            );
          })}
          {!list.length && (
            <AxEmpty>
              {st === "soon"
                ? "예정 = 이 주가 끝난 뒤 4주 안에 시작하는 팝업이라 이 주 간트에는 없어요. 아래 보드에서 보세요."
                : "이 주에 걸친 팝업이 없어요. 위에서 다른 주를 골라 보세요."}
            </AxEmpty>
          )}
        </div>
        {every.length > list.length && (
          <Link className="ax-btn soft ax-center" href={href({ gn: String(gn + GANTT_PAGE) })} scroll={false}>
            +{Math.min(GANTT_PAGE, every.length - list.length)}곳 더보기 (남은 {every.length - list.length}곳)
          </Link>
        )}
        <p className="ax-cap">막대 끝이 각지면 이 주 앞뒤로 이어져요. 줄을 누르면 팝업 상세로 가요.</p>
      </AxCard>

      <section className="ax-kanban-wrap" aria-labelledby="ax-kanban-h">
        <h2 id="ax-kanban-h" className="ax-h2">
          상태별 보드
        </h2>
        <div className={`ax-kanban${cols.length === 1 ? " one" : ""}`}>
          {cols.map((name) => {
            const i = BOARD_COLS.indexOf(name);
            const items = board[name];
            const n = Math.max(BOARD_PAGE, int(sp[`b${i}`], BOARD_PAGE));
            return (
              <div key={name} className="ax-kcol">
                <div className="ax-kcol-h">
                  <i className={`ax-dot ${COL_CLS[name]}`} aria-hidden />
                  <strong>{name}</strong>
                  <span>{items.length}</span>
                </div>
                {name === "종료" && pastWeek && (
                  <p className="ax-cap">지난 주에 끝난 팝업은 다음 주 월요일에 DB 에서 지워져 여기에 안 보일 수 있어요.</p>
                )}
                {items.slice(0, n).map((r) => (
                  <KCard key={String(r.entry_id)} r={r} col={name} today={today} />
                ))}
                {!items.length && <AxEmpty>없어요</AxEmpty>}
                {items.length > n && (
                  <Link className="ax-btn soft sm" href={href({ [`b${i}`]: String(n + BOARD_PAGE) })} scroll={false}>
                    {items.length - n}곳 더보기
                  </Link>
                )}
              </div>
            );
          })}
        </div>
        <p className="ax-cap">
          새로 생성 = 그 주에 처음 등록 · 예정 = 그 주가 끝난 뒤 4주 안에 시작 · 진행 = 그 주에 열려 있고 다음 주에도 이어짐 · 종료 = 그
          주에 끝남. 종료된 팝업은 월~일 한 주가 지나 다음 주 월요일 00:10 에 DB 에서도 정리돼요.
        </p>
      </section>
    </>
  );
}

/** 보드 카드: 포스터 · 이름 · 한 줄 상태. 정보가 빠졌으면 노란 테두리 + '확인'. 종료 칸은 상세로 가지 않는다 (11/19) */
function KCard({ r, col, today }: { r: Row; col: string; today: string }) {
  const s = ymdOf(r.start_date);
  const e = ymdOf(r.end_date);
  const miss = col !== "종료" ? missingOf(r) : [];
  const sub =
    miss.length > 0
      ? `확인 필요: ${miss.join(" · ")}`
      : col === "예정"
        ? `${md(s)} 오픈 · D-${diff(today, s)}`
        : col === "진행"
          ? e === today
            ? "오늘 종료"
            : `~${md(e)}`
          : col === "종료"
            ? `${md(e)} 종료`
            : `${md(s)} ~ ${md(e)}`;
  const body = (
    <>
      <i className="ax-thumb lg" style={posterBg(posterOf(r.images))} aria-hidden />
      <span className="ax-kcard-t">
        <strong>{String(r.work || "") || popName(r)}</strong>
        <small>{String(r.cafe_name || "")}</small>
        <em>{sub}</em>
      </span>
    </>
  );
  const cls = `ax-kcard${miss.length ? " warn" : ""}`;
  if (col === "종료") return <div className={`${cls} static`}>{body}</div>;
  return (
    <Link className={cls} href={popupHref(r)}>
      {body}
    </Link>
  );
}
