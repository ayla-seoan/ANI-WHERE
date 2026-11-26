import Link from "next/link";
import { addDays } from "@/lib/popup";
import { kpiLists, lastCollect, needFix, popName, purgeDue, recentActivity, type Feed } from "@/lib/server/a-admin";
import { dailyActive, dailyEvents, memberEvents, periodMD, popupBoard, whenText, ymdOf } from "@/lib/server/admin";
import { monthCalls, monthlyLimit } from "@/lib/server/blog";
import { lvOfNick } from "@/lib/server/stamp";
import { completeness, NOTION_CUTOFF, popups } from "@/lib/server/stats";
import { current, mode, type Row } from "@/lib/server/store";
import { RankChip } from "@/components/RankStamp";
import { PopupCard } from "./Board";
import { AxCard, AxEmpty, AxHead, AxTag } from "./AxShell";
import { TodoDecide } from "./AxClient";

// 한눈에 보기 (AdmX-1Home, 새 첫 화면). 숫자는 기존 관리자 탭 · /stats 와 같은 함수로 센다.

type SP = Record<string, string | undefined>;

export const HOME_KPIS: [string, string][] = [
  ["new", "이번 주 새로 등록"],
  ["live", "진행 중"],
  ["soon", "오픈 예정"],
  ["members", "회원 (활동)"],
  ["requests", "삭제 요청 대기"],
];
const FIX_PAGE = 6;
const FEED_TONE: Record<Feed["kind"], string> = {
  등록: "mint",
  수정: "blue",
  내림: "gray",
  "삭제 요청": "red-soft",
  처리: "gray",
  리뷰: "purple",
  가입: "gray",
};

const sign = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `${n}` : "±0");
const md = (ymd: string) => `${Number(ymd.slice(5, 7))}/${Number(ymd.slice(8, 10))}`;

export default async function AxHome({
  cafes,
  reqs,
  members,
  reviews,
  visits,
  today,
  mon,
  monNow,
  weekNav,
  refresh,
  sp,
  href,
}: {
  cafes: Row[];
  reqs: Row[];
  members: Row[];
  reviews: Row[];
  visits: Row[];
  today: string;
  mon: string;
  monNow: string;
  weekNav: React.ReactNode;
  refresh: React.ReactNode;
  sp: SP;
  href: (p: SP) => string;
}) {
  const reqNow = current(reqs);
  const pending = reqNow
    .filter((r) => r.decision === "pending")
    .sort((a, b) => String(a.updated_at || "").localeCompare(String(b.updated_at || "")));
  const fixes = needFix(cafes, today);
  const nTodo = pending.length + fixes.length;
  const lv = await lvOfNick();

  // ---- 숫자 카드 (예전 관리자 숫자 카드와 같은 계산) ----
  const lists = kpiLists(cafes, today, monNow);
  const lastNew = popupBoard(cafes, addDays(monNow, -7))["새로 생성"].filter((r) => r.status !== "deleted").length;
  const ev = memberEvents(members);
  const joinedThisWeek = dailyEvents(ev, "가입", monNow).reduce((a, b) => a + b.n, 0);
  const in7 = addDays(today, 6);
  const nums: Record<string, [number, string, string]> = {
    new: [lists.new.length, `지난주 ${lastNew}곳보다 ${sign(lists.new.length - lastNew)}`, lists.new.length >= lastNew ? "up" : ""],
    live: [lists.live.length, `오늘 끝나는 곳 ${lists.live.filter((r) => ymdOf(r.end_date) === today).length}곳`, ""],
    soon: [lists.soon.length, `7일 안에 시작 ${lists.soon.filter((r) => ymdOf(r.start_date) <= in7).length}곳`, ""],
    members: [current(members).length, `이번 주 가입 ${joinedThisWeek}명`, joinedThisWeek ? "up" : ""],
    requests: [pending.length, pending.length ? `가장 오래된 것 ${whenText(pending[0].updated_at)}` : "처리할 요청 없음", pending.length ? "red" : ""],
  };
  const picked = sp.kpi && sp.kpi in lists ? (sp.kpi as keyof typeof lists) : null;

  // ---- 수집 상태 알약 (웹이 기록으로 알 수 있는 것만) ----
  const col = lastCollect(cafes);
  const colDays = col ? Math.round((Date.parse(today) - Date.parse(col.day)) / 86400000) : null;
  const purge = purgeDue(cafes, today);
  let blog: [number, number] | null = null;
  if (mode() !== "none") {
    try {
      blog = [await monthCalls(), monthlyLimit()];
    } catch {
      blog = null;
    }
  }

  // ---- 북극성 · 일별 접속 · 최근 활동 ----
  const now = completeness(popups(cafes));
  const before = completeness(popups(cafes, NOTION_CUTOFF));
  const days = dailyActive(visits, mon);
  const dmax = Math.max(1, ...days.map((d) => d.n));
  const feed = recentActivity({ cafes, reqs, reviews, members }, 8);
  const feedWhen = (at: string) => {
    const w = whenText(at);
    return w.startsWith(`${today.slice(5, 7)}/${today.slice(8, 10)}`) ? `오늘 ${w.slice(6)}` : w;
  };
  const allFix = sp.hall === "1";

  return (
    <>
      <AxHead
        eyebrow={`한눈에 보기 · ${today.replaceAll("-", ".")}`}
        title={
          <>
            오늘 처리할 일 <span className={nTodo ? "ax-red" : undefined}>{nTodo}건</span>
          </>
        }
        right={
          <>
            {weekNav}
            {refresh}
          </>
        }
      />

      <div className="ax-pills" aria-label="수집 상태">
        {col ? (
          <span className={`ax-pill${colDays !== null && colDays <= 1 ? " ok" : " warn"}`}>
            <i aria-hidden />
            <strong>최근 자동 수집</strong>
            {col.day === today ? `오늘 ${col.when.slice(6)}` : col.when} · 그날 새 팝업 {col.added}곳
            {colDays !== null && colDays > 1 ? ` · ${colDays}일째 새 기록 없음` : ""}
          </span>
        ) : (
          <span className="ax-pill warn">
            <i aria-hidden />
            자동 수집(AI) 기록이 아직 없어요
          </span>
        )}
        <span className="ax-pill gray">
          <i aria-hidden />
          다음 주 월 {md(purge.monday)} 00:10 · 종료 · 내린 팝업 정리 {purge.n}곳
        </span>
        {blog && (
          <span className="ax-pill blue">
            <i aria-hidden />
            블로그 검색 이번 달 {blog[0].toLocaleString("ko-KR")} / {blog[1].toLocaleString("ko-KR")}번
          </span>
        )}
      </div>

      <div className="ax-kpis">
        {HOME_KPIS.map(([k, label]) => {
          const [n, delta, tone] = nums[k];
          const to =
            k === "members"
              ? href({ tab: "members", kpi: undefined, kall: undefined, hall: undefined })
              : k === "requests"
                ? href({ tab: "requests", kpi: undefined, kall: undefined, hall: undefined })
                : href({ kpi: picked === k ? undefined : k, kall: undefined });
          const alert = k === "requests" && n > 0;
          return (
            <Link
              key={k}
              href={to}
              scroll={false}
              className={`ax-kpi${alert ? " alert" : ""}${picked === k ? " on" : ""}`}
              aria-expanded={k in lists ? picked === k : undefined}
            >
              <span className="ax-kpi-l">{label}</span>
              <strong>{n}</strong>
              <span className={`ax-kpi-d ${tone}`}>{delta}</span>
            </Link>
          );
        })}
      </div>
      {picked && <KpiList picked={picked} rows={lists[picked]} all={sp.kall === "1"} href={href} />}

      <div className="ax-row">
        <AxCard id="ax-todo" className="ax-grow ax-todo" title="처리할 일" right={<span className="ax-muted">오래된 순</span>}>
          {!nTodo && <AxEmpty>지금 처리할 일이 없어요. 새 삭제 요청이 오면 여기와 왼쪽 메뉴에 빨간 숫자로 보여요.</AxEmpty>}
          {pending.map((r) => {
            const title = String(r.target_title || "") || "(제목 없음)";
            const nick = String(r.requester_nick || "");
            return (
              <article key={String(r.entry_id)} className="ax-todo-i">
                <AxTag tone="red">삭제 요청</AxTag>
                <div className="ax-todo-b">
                  <strong>
                    {r.target_type === "review" ? "리뷰 · " : ""}
                    {title}
                  </strong>
                  <span>
                    {String(r.reason || "")} · {nick} <RankChip lv={lv(nick)} /> · {whenText(r.updated_at)}
                  </span>
                </div>
                <TodoDecide entryId={String(r.entry_id)} title={title} />
              </article>
            );
          })}
          {(allFix ? fixes : fixes.slice(0, FIX_PAGE)).map(({ row, missing }) => (
            <article key={String(row.entry_id)} className="ax-todo-i">
              <AxTag tone="yellow">정보 빠짐</AxTag>
              <div className="ax-todo-b">
                <strong>{popName(row)}</strong>
                <span>
                  빠진 정보: {missing.join(" · ")} · {periodMD(row)}
                </span>
              </div>
              <Link className="ax-btn mint sm" href={`/popup/${encodeURIComponent(String(row.entry_id))}?tab=edit`}>
                수정하기
              </Link>
            </article>
          ))}
          {fixes.length > FIX_PAGE && (
            <Link className="ax-btn soft sm ax-center" href={href({ hall: allFix ? undefined : "1" })} scroll={false}>
              {allFix ? "접기" : `정보 빠진 팝업 ${fixes.length - FIX_PAGE}곳 더 보기`}
            </Link>
          )}
          <p className="ax-cap">
            정보 빠짐 = 아직 끝나지 않은 팝업 중 완결률이 세는 방문 전 정보(기간 · 주소 · 지도 좌표 · 참고 링크 · 포스터)가 하나라도 빈
            곳.
          </p>
        </AxCard>

        <div className="ax-col ax-side-col">
          <AxCard id="ax-north" title="북극성 · 방문 전 정보 완결률">
            <span className="ax-big">
              {now.complete.toFixed(1)}
              <small>%</small>
            </span>
            {before.n > 0 && (
              <span className="ax-north-d">
                Notion 주간 수집 전 <strong>{before.complete.toFixed(1)}%</strong> → 지금 <strong>{now.complete.toFixed(1)}%</strong>{" "}
                <span className="ax-muted">
                  ({sign(Math.round((now.complete - before.complete) * 10) / 10)}%p)
                </span>
              </span>
            )}
            <div
              className="ax-meter"
              role="img"
              aria-label={`완결률 ${now.complete.toFixed(1)}%${before.n ? `, 세로선은 수집 전 ${before.complete.toFixed(1)}%` : ""}`}
            >
              <span style={{ width: `${Math.min(100, now.complete)}%` }} />
              {before.n > 0 && <i style={{ left: `${Math.min(100, before.complete)}%` }} />}
            </div>
            <span className="ax-muted ax-sm">팝업 {now.n}곳 기준 · /stats 와 같은 숫자</span>
            <Link className="ax-link" href={href({ hall: "1", kpi: undefined }) + "#ax-todo"} scroll={false}>
              빠진 정보 있는 팝업 보기 →
            </Link>
          </AxCard>

          <figure className="ax-card" aria-labelledby="ax-daily-h">
            <figcaption className="ax-card-h">
              <h2 id="ax-daily-h">일별 접속 회원</h2>
              <Link className="ax-link" href={href({ tab: "usage", kpi: undefined, kall: undefined, hall: undefined })}>
                이용 지표 →
              </Link>
            </figcaption>
            <div className="ax-mini" role="img" aria-label={`일별 접속 회원: ${days.map((d) => `${d.label} ${d.n}명`).join(", ")}`}>
              {days.map((d, i) => {
                const isToday = addDays(mon, i) === today;
                return (
                  <span key={d.label} className={isToday ? "today" : undefined}>
                    <b>{d.n}</b>
                    <i style={{ height: `${Math.round((d.n / dmax) * 100)}%` }} />
                  </span>
                );
              })}
            </div>
            <div className="ax-mini-x" aria-hidden>
              {days.map((d, i) => (
                <span key={d.label} className={addDays(mon, i) === today ? "today" : undefined}>
                  {"월화수목금토일"[i]}
                </span>
              ))}
            </div>
            <p className="ax-cap">로그인한 회원만 세요 (같은 날 여러 번 와도 1명) · 진한 막대 = 오늘</p>
          </figure>
        </div>
      </div>

      <AxCard id="ax-feed" title="최근 활동">
        {!feed.length && <AxEmpty>아직 쌓인 기록이 없어요.</AxEmpty>}
        {feed.map((f, i) => (
          <div key={i} className="ax-feed-i">
            <AxTag tone={FEED_TONE[f.kind]}>{f.kind}</AxTag>
            <span className="ax-feed-t">{f.text}</span>
            <span className="ax-feed-w">{feedWhen(f.at)}</span>
          </div>
        ))}
      </AxCard>
    </>
  );
}

// ------------------------------------------------------------------ 숫자 카드를 누르면 펼쳐지는 목록 (예전 KpiList)
function KpiList({ picked, rows: list, all, href }: { picked: string; rows: Row[]; all: boolean; href: (p: SP) => string }) {
  const label = Object.fromEntries(HOME_KPIS)[picked];
  const shown = all ? list : list.slice(0, 12);
  return (
    <AxCard
      id="ax-kpilist"
      className="ax-kpilist"
      title={
        <>
          {label} <span className="ax-muted">{list.length}곳 · 누르면 상세로</span>
        </>
      }
      right={
        <Link className="ax-btn line sm" href={href({ kpi: undefined, kall: undefined })} scroll={false}>
          목록 닫기
        </Link>
      }
    >
      {shown.length ? (
        <div className="ax-kgrid">
          {shown.map((r) => (
            <PopupCard key={String(r.entry_id)} r={r} period={periodMD(r)} />
          ))}
        </div>
      ) : (
        <AxEmpty>해당하는 팝업이 없어요.</AxEmpty>
      )}
      {list.length > 12 && (
        <Link className="ax-btn soft sm ax-center" href={href({ kall: all ? undefined : "1" })} scroll={false}>
          {all ? "접기" : `${list.length - 12}곳 더 보기`}
        </Link>
      )}
    </AxCard>
  );
}
