import Link from "next/link";
import { addDays } from "@/lib/popup";
import { posterBg } from "@/components/cards";
import { RankChip, RankStamp } from "@/components/RankStamp";
import { tierOf } from "@/lib/stamp";
import { dataCols, DATA_TABLES, joinMethods, noticeShown, popName, rawFilter } from "@/lib/server/a-admin";
import {
  dailyActive,
  dailyEvents,
  kstDay,
  lastVisit,
  memberEvents,
  periodMD,
  posterOf,
  RULES,
  ruleSettings,
  TARGET_LABEL,
  whenText,
  why,
  ymdOf,
} from "@/lib/server/admin";
import { isAdmin, PROVIDER_LABEL } from "@/lib/server/auth";
import { lvOfNick, stampCounts } from "@/lib/server/stamp";
import { popups, topBookmarked } from "@/lib/server/stats";
import { current, latest, mode, rows, type Row, type Table as TableName } from "@/lib/server/store";
import { AxNotices, CsvButton, RequestDecide, RuleRow, type RuleRowView } from "./AxClient";
import { AxCard, AxEmpty, AxHead, AxTag } from "./AxShell";

// 관리자 A안 페이지들 (AdmX-3 ~ AdmX-7). 숫자는 예전 관리자 탭 · /stats 와 같은 함수로 센다.

type SP = Record<string, string | undefined>;
const WD = "월화수목금토일";
const int = (v: string | undefined, d: number) => (/^\d{1,5}$/.test(v || "") ? Number(v) : d);
const md = (ymd: string) => (ymd ? `${Number(ymd.slice(5, 7))}.${ymd.slice(8, 10)}` : "");

// ================================================================== 이용 지표 (AdmX-3Usage)
export async function AxUsage({
  members,
  cafes,
  mon,
  today,
  weekNav,
}: {
  members: Row[];
  cafes: Row[];
  mon: string;
  today: string;
  weekNav: React.ReactNode;
}) {
  let visits: Row[] = [];
  let favs: Row[] = [];
  try {
    [visits, favs] = await Promise.all([rows("visits"), rows("favorites")]);
  } catch {
    /* 읽지 못하면 0 으로 */
  }
  const ev = memberEvents(members);
  const joined = dailyEvents(ev, "가입", mon);
  const active = dailyActive(visits, mon);
  const quit = dailyEvents(ev, "탈퇴", mon);
  const sum = (xs: { n: number }[]) => xs.reduce((a, b) => a + b.n, 0);
  // 하루 평균: 지난 날까지만 나눈다 (이번 주면 오늘까지)
  const passed = Math.max(1, Math.min(7, Math.round((Date.parse(today) - Date.parse(mon)) / 86400000) + 1));
  const avg = Math.round((sum(active) / passed) * 10) / 10;
  const peak = active.reduce((a, b, i) => (b.n > active[a].n ? i : a), 0);
  const todayIdx = Math.round((Date.parse(today) - Date.parse(mon)) / 86400000);
  const lines: [string, { label: string; n: number }[], string, string][] = [
    ["신규 가입", joined, "blue", "명"],
    ["접속 회원", active, "teal", "명 (연인원)"],
    ["탈퇴 회원", quit, "amber", "명"],
  ];
  const joins = joinMethods(members);
  const top = topBookmarked(current(favs), popups(cafes), 5);
  const names = new Map(latest(cafes).map((r) => [popName(r), r]));
  return (
    <>
      <AxHead eyebrow="이용 지표" title={todayIdx >= 0 && todayIdx < 7 ? "이번 주 이용" : "고른 주 이용"} right={weekNav} />
      <div className="ax-flow">
        <div className="ax-flow-c">
          <span className="ax-kpi-l">신규 가입</span>
          <strong>{sum(joined)}</strong>
          <span className="ax-muted ax-sm">그 주에 가입한 회원 (손님 방문은 세지 않아요)</span>
        </div>
        <div className="ax-flow-c">
          <span className="ax-kpi-l">접속 회원 (하루 평균)</span>
          <strong className="ax-deep">{avg}</strong>
          <span className="ax-muted ax-sm">
            연인원 {sum(active)}명 · 가장 많은 날 {WD[peak]} {active[peak].n}명
          </span>
        </div>
        <div className="ax-flow-c">
          <span className="ax-kpi-l">탈퇴 회원</span>
          <strong>{sum(quit)}</strong>
          <span className="ax-muted ax-sm">그 주에 탈퇴한 회원</span>
        </div>
      </div>

      <AxCard id="ax-daily" title="날짜별 · 신규 가입 → 접속 회원 → 탈퇴 회원">
        <div className="ax-lines">
          <div className="ax-lines-h" aria-hidden>
            <span />
            {Array.from({ length: 7 }, (_, i) => (
              <span key={i} className={i === todayIdx ? "today" : undefined}>
                {WD[i]} {Number(addDays(mon, i).slice(8, 10))}
                {i === todayIdx ? " (오늘)" : ""}
              </span>
            ))}
            <span>합계</span>
          </div>
          {lines.map(([title, data, tone]) => {
            const max = Math.max(1, ...data.map((d) => d.n));
            return (
              <div
                key={title}
                className={`ax-lines-r ${tone}`}
                role="img"
                aria-label={`${title} 월~일: ${data.map((d) => d.n).join(", ")}, 합계 ${sum(data)}`}
              >
                <span className="ax-lines-t">{title}</span>
                {data.map((d) => (
                  <span key={d.label} className="ax-lines-b">
                    <b>{d.n}</b>
                    <i style={{ height: `${Math.round((d.n / max) * 44)}px` }} />
                  </span>
                ))}
                <strong className="ax-lines-s">{sum(data)}</strong>
              </div>
            );
          })}
        </div>
        <p className="ax-cap">
          줄마다 따로 눈금을 써요 (숫자 크기가 달라서). 막대 위 숫자가 실제 값이에요. 신규 = 그날 가입한 회원 · 접속 회원 = 그날
          로그인한 상태로 한 번 이상 들어온 회원 (같은 날 여러 번 와도 1명, 손님은 세지 않아요) · 탈퇴 = 그날 탈퇴한 회원. 날짜는 한국
          시간.
        </p>
        <details className="ax-details">
          <summary>표로 보기</summary>
          <div className="ax-tbl-box">
            <table className="ax-tbl">
              <thead>
                <tr>
                  <th>날짜</th>
                  {lines.map(([t]) => (
                    <th key={t} className="num">
                      {t}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {joined.map((d, i) => (
                  <tr key={d.label}>
                    <td>{d.label}</td>
                    {lines.map(([t, data]) => (
                      <td key={t} className="num">
                        {data[i].n}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </AxCard>

      <div className="ax-grid3">
        <AxCard id="ax-join" title="가입 방법">
          {!joins.length && <AxEmpty>아직 가입한 회원이 없어요.</AxEmpty>}
          {joins.map((j) => (
            <div key={j.label} className="ax-bar-l">
              <span>
                <b>{j.label}</b>
                <span>
                  {j.n}명 · {j.pct}%
                </span>
              </span>
              <i>
                <span style={{ width: `${j.pct}%` }} />
              </i>
            </div>
          ))}
          <p className="ax-cap">지금 회원 기준 (탈퇴 제외)</p>
        </AxCard>
        <AxCard id="ax-bm" title="북마크 많은 팝업">
          {!top.length && <AxEmpty>아직 북마크가 없어요.</AxEmpty>}
          {top.map((t, i) => {
            const r = names.get(t.팝업);
            return (
              <div key={t.팝업 + i} className="ax-rank-i">
                <span className="ax-rank-n">{i + 1}</span>
                <i className="ax-thumb" style={posterBg(posterOf(r?.images))} aria-hidden />
                <span className="ax-rank-t">{t.팝업}</span>
                <span className="ax-muted">{t.북마크}</span>
              </div>
            );
          })}
          <p className="ax-cap">지금 북마크 수 (/stats 와 같은 숫자)</p>
        </AxCard>
        <AxCard id="ax-ask" title="물어보기 많이 한 질문">
          <AxEmpty>
            웹의 물어보기 질문은 저장소에 쌓지 않아서 (서버 로그에만 남아요) 여기서 셀 수 없어요. 질문을 저장하게 되면 건수부터
            보여 줄게요.
          </AxEmpty>
        </AxCard>
      </div>
    </>
  );
}

// ================================================================== 삭제 요청 (AdmX-4Delete)
export async function AxRequests({ reqs, cafes, sp, href }: { reqs: Row[]; cafes: Row[]; sp: SP; href: (p: SP) => string }) {
  let favs: Row[] = [];
  let reviews: Row[] = [];
  try {
    [favs, reviews] = await Promise.all([rows("favorites"), rows("reviews")]);
  } catch {
    /* 없으면 0 */
  }
  const lv = await lvOfNick();
  const now = current(reqs);
  const pending = now
    .filter((r) => r.decision === "pending")
    .sort((a, b) => String(a.updated_at || "").localeCompare(String(b.updated_at || "")));
  const done = now
    .filter((r) => r.decision !== "pending")
    .sort((a, b) => String(b.decided_at || b.updated_at || "").localeCompare(String(a.decided_at || a.updated_at || "")));
  const view = sp.rq === "done" ? "done" : "pending";
  const open = pending.find((r) => String(r.entry_id) === sp.open) || pending[0];
  const cafeLatest = new Map(latest(cafes).map((r) => [String(r.entry_id), r]));
  const reviewLatest = new Map(latest(reviews).map((r) => [String(r.entry_id), r]));
  const favNow = current(favs);
  const revNow = current(reviews);

  return (
    <>
      <AxHead
        eyebrow="삭제 요청"
        title="회원이 내려 달라고 한 글"
        sub="승인하면 지도 · 리스트에서 내리고(기록은 남김) 요청자에게 알림, 거부하면 사유와 함께 알림이 가요."
      />
      <div className="ax-tabs2" role="tablist" aria-label="삭제 요청 보기">
        <Link role="tab" aria-selected={view === "pending"} className={view === "pending" ? "on" : undefined} href={href({ rq: undefined, open: undefined })} scroll={false}>
          대기 {pending.length}
        </Link>
        <Link role="tab" aria-selected={view === "done"} className={view === "done" ? "on" : undefined} href={href({ rq: "done", open: undefined })} scroll={false}>
          처리 완료 {done.length}
        </Link>
      </div>

      {view === "pending" && (
        <>
          {!pending.length && <AxEmpty>처리할 삭제 요청이 없어요. 회원이 상세 화면에서 &apos;삭제 요청&apos;을 보내면 여기에 와요.</AxEmpty>}
          {open && (
            <ReqCard
              r={open}
              lv={lv(String(open.requester_nick || ""))}
              cafe={open.target_type === "cafe" ? cafeLatest.get(String(open.target_id)) : undefined}
              review={open.target_type === "review" ? reviewLatest.get(String(open.target_id)) : undefined}
              cafeOf={(id) => cafeLatest.get(id)}
              favN={(id) => favNow.filter((f) => String(f.cafe_id) === id).length}
              revN={(id) => revNow.filter((x) => String(x.cafe_id) === id && !String(x.parent_id || "")).length}
            />
          )}
          {pending
            .filter((r) => r !== open)
            .map((r) => {
              const c = r.target_type === "cafe" ? cafeLatest.get(String(r.target_id)) : undefined;
              const nick = String(r.requester_nick || "");
              return (
                <article key={String(r.entry_id)} className="ax-card ax-req-mini" data-req={String(r.entry_id)}>
                  <i className="ax-thumb md" style={posterBg(posterOf(c?.images))} aria-hidden />
                  <div className="ax-req-mini-b">
                    <strong>
                      {TARGET_LABEL[String(r.target_type)] || "글"} · {String(r.target_title || "")}
                    </strong>
                    <span>&ldquo;{String(r.reason || "")}&rdquo;</span>
                    <small>
                      {nick} <RankChip lv={lv(nick)} /> · {whenText(r.updated_at)}
                    </small>
                  </div>
                  <Link className="ax-btn soft-line" href={href({ open: String(r.entry_id) })} scroll={false}>
                    열어서 처리
                  </Link>
                </article>
              );
            })}
        </>
      )}

      <AxCard id="ax-hist" title={view === "done" ? `처리 기록 ${done.length}건` : "최근 처리 기록"}>
        {!done.length ? (
          <AxEmpty>아직 처리한 요청이 없어요.</AxEmpty>
        ) : (
          <div className="ax-tbl-box">
            <table className="ax-tbl ax-hist">
              <thead>
                <tr>
                  <th>처리일</th>
                  <th>대상</th>
                  <th>결과</th>
                  <th>처리 사유</th>
                  <th>요청 사유</th>
                  <th>요청자</th>
                </tr>
              </thead>
              <tbody>
                {(view === "done" ? done.slice(0, 50) : done.slice(0, 5)).map((r) => {
                  const d = String(r.decision || "");
                  return (
                    <tr key={String(r.entry_id)}>
                      <td className="nowrap">{whenText(r.updated_at)}</td>
                      <td>
                        <b>
                          {TARGET_LABEL[String(r.target_type)] || "글"} · {String(r.target_title || "")}
                        </b>
                      </td>
                      <td>
                        <AxTag tone={d === "approved" ? "dark" : "gray"}>{d === "approved" ? "승인" : d === "rejected" ? "거부" : d}</AxTag>
                      </td>
                      <td>{String(r.admin_reason || "") || "-"}</td>
                      <td>{String(r.reason || "")}</td>
                      <td className="ax-muted">{String(r.requester_nick || "")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {view === "pending" && done.length > 5 && (
          <Link className="ax-link" href={href({ rq: "done", open: undefined })} scroll={false}>
            처리 기록 {done.length}건 모두 보기 →
          </Link>
        )}
      </AxCard>
    </>
  );
}

function ReqCard({
  r,
  lv,
  cafe,
  review,
  cafeOf,
  favN,
  revN,
}: {
  r: Row;
  lv: number;
  cafe?: Row;
  review?: Row;
  cafeOf: (id: string) => Row | undefined;
  favN: (id: string) => number;
  revN: (id: string) => number;
}) {
  const isCafe = r.target_type === "cafe";
  const target = isCafe ? cafe : review;
  const alive = !!target && target.status !== "deleted";
  const cafeId = isCafe ? String(r.target_id) : String(review?.cafe_id || "");
  const host = cafeOf(cafeId);
  const nick = String(r.requester_nick || "");
  const s = ymdOf(host?.start_date);
  const e = ymdOf(host?.end_date);
  return (
    <article className="ax-card ax-req-open" data-req={String(r.entry_id)}>
      <i className="ax-thumb xl" style={posterBg(posterOf(host?.images))} aria-hidden />
      <div className="ax-req-b">
        <div className="ax-req-title">
          <strong>
            {isCafe ? "" : "리뷰 · "}
            {String(r.target_title || "") || "(제목 없음)"}
          </strong>
          <AxTag tone={alive ? "mint" : "gray"}>
            {alive ? (isCafe ? "지금 지도에 보임" : "지금 보임") : isCafe ? "이미 내려감" : "이미 지워짐"}
          </AxTag>
          {cafeId && (
            <Link className="ax-link" href={`/popup/${encodeURIComponent(cafeId)}`} target="_blank">
              상세 열기 ↗
            </Link>
          )}
        </div>
        {host && (
          <span className="ax-muted">
            {isCafe ? "" : `${popName(host)} 의 리뷰 · `}
            등록된 기간 {s ? `${md(s)} ~ ${md(e)}` : periodMD(host)} · 북마크 {favN(cafeId)} · 리뷰 {revN(cafeId)}
          </span>
        )}
        {!isCafe && review && <p className="ax-quote sm">리뷰 내용: {String(review.body || "").slice(0, 160) || "(별점만)"}</p>}
        <div className="ax-req-who">
          <span>
            {lv > 0 ? <RankStamp lv={lv} size={20} /> : null}
            <strong>{nick}</strong>
            <span className="ax-muted">
              {lv > 0 ? `Lv.${lv} · ` : "도장 없음 · "}
              {whenText(r.updated_at)} 요청
            </span>
          </span>
          <p className="ax-quote">&ldquo;{String(r.reason || "")}&rdquo;</p>
        </div>
        <RequestDecide
          entryId={String(r.entry_id)}
          approveLabel={isCafe ? "승인하고 내리기" : "승인하고 리뷰 지우기"}
          editHref={isCafe && alive ? `/popup/${encodeURIComponent(cafeId)}?tab=edit` : null}
        />
      </div>
    </article>
  );
}

// ================================================================== 알림 관리 (AdmX-5Alerts)
export async function AxNoticesPage({ cafes, today }: { cafes: Row[]; today: string }) {
  const rules = await ruleSettings();
  let notices: Row[] = [];
  try {
    notices = current(await rows("notices"));
  } catch {
    notices = [];
  }
  const list = notices
    .filter((r) => r.target === "all")
    .sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
  const shown = noticeShown(list, rules.notice, today);
  const views: RuleRowView[] = Object.entries(RULES).map(([k, d]) => ({
    key: k,
    name: d.name,
    why: why(k, rules),
    when: d.when.replace("{days}", String(rules[k].days)),
    where: d.where,
    who: d.who,
    enabled: rules[k].enabled,
    days: rules[k].days,
    max_items: rules[k].max_items,
    hasDays: d.days !== null,
    hasMax: d.max_items !== null,
    dayUnit: k === "notice" ? "일 동안" : "일 전부터",
  }));
  // 미리보기: 지금 데이터로 만든 알림 모양 (켜진 규칙만)
  const pops = popups(cafes).filter((r) => r.status !== "deleted");
  const diff = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);
  const opening = pops
    .filter((r) => {
      const s = ymdOf(r.start_date);
      return s && s >= today;
    })
    .sort((a, b) => String(a.start_date).localeCompare(String(b.start_date)))[0];
  const ending = pops
    .filter((r) => {
      const s = ymdOf(r.start_date);
      const e = ymdOf(r.end_date);
      return s && e && s <= today && e >= today && e !== "2099-12-31";
    })
    .sort((a, b) => String(a.end_date).localeCompare(String(b.end_date)))[0];
  const preview: { title: string; why: string; img?: string }[] = [];
  if (rules.open.enabled && opening) {
    const d = diff(today, ymdOf(opening.start_date));
    preview.push({ title: `${d === 0 ? "오늘 오픈" : `오픈 D-${d}`} · ${popName(opening)}`, why: why("open", rules), img: posterOf(opening.images) });
  }
  if (rules.end.enabled && ending) {
    const d = diff(today, ymdOf(ending.end_date));
    preview.push({ title: `${d === 0 ? "오늘 종료" : `종료 D-${d}`} · ${popName(ending)}`, why: why("end", rules), img: posterOf(ending.images) });
  }
  if (rules.notice.enabled && list[0]) preview.push({ title: String(list[0].title || ""), why: why("notice", rules) });
  if (rules.del_ok.enabled) preview.push({ title: "삭제 요청이 승인되었어요", why: why("del_ok", rules) });
  const brief = { name: "주간 브리핑 메일", when: "매주 월요일 11:00", who: "운영자 본인 메일", where: "메일 (automation/weekly_briefing.gs)" };

  return (
    <>
      <AxHead eyebrow="알림 관리" title="자동 알림 규칙과 공지" />
      <div className="ax-row">
        <AxCard id="ax-rules" className="ax-grow" title="자동으로 나가는 알림" right={<span className="ax-muted">바꾸면 다음 알림부터 적용돼요</span>}>
          <div className="ax-tbl-box">
            <table className="ax-tbl ax-rules">
              <thead>
                <tr>
                  <th>알림</th>
                  <th>받는 사람</th>
                  <th>며칠</th>
                  <th>최대 개수</th>
                  <th>켜기</th>
                  <th>
                    <span className="ax-sr">저장</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {views.map((v) => (
                  <RuleRow key={`${v.key}:${v.enabled}:${v.days}:${v.max_items}`} r={v} />
                ))}
                <tr className="off fixed">
                  <td>
                    <b className="ax-rule-n">랭크 승급 (제안)</b>
                    <small>후기 도장 다음 단계에 닿았을 때</small>
                    <small className="ax-rule-when">아직 없는 기능 — 표시만 해 둬요</small>
                  </td>
                  <td>해당 회원</td>
                  <td>
                    <span className="ax-dash">—</span>
                  </td>
                  <td>
                    <span className="ax-dash">—</span>
                  </td>
                  <td>
                    <span className="ax-sw-cell">
                      <button type="button" role="switch" aria-checked={false} aria-label="랭크 승급 켜기 (아직 없는 기능)" className="ax-switch" disabled>
                        <i />
                      </button>
                      <span className="ax-sw-t">꺼짐</span>
                    </span>
                  </td>
                  <td>
                    <span className="ax-muted ax-sm">아직 없는 기능</span>
                  </td>
                </tr>
                <tr className="fixed">
                  <td>
                    <b className="ax-rule-n">{brief.name}</b>
                    <small className="ax-rule-when">
                      {brief.when} · {brief.where}
                    </small>
                  </td>
                  <td>{brief.who}</td>
                  <td>
                    <span className="ax-dash">—</span>
                  </td>
                  <td>
                    <span className="ax-dash">—</span>
                  </td>
                  <td>
                    <span className="ax-sw-t">켜짐</span>
                  </td>
                  <td>
                    <span className="ax-muted ax-sm">Apps Script 에서 고쳐요</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="ax-cap">끈 규칙은 회원에게 더 이상 나가지 않아요. 기록은 남아서 언제든 다시 켤 수 있어요.</p>
        </AxCard>
        <aside className="ax-card ax-preview" aria-labelledby="ax-prev-h">
          <div className="ax-card-h">
            <h2 id="ax-prev-h">회원에게 이렇게 보여요</h2>
          </div>
          <div className="ax-prev-box">
            {!preview.length && <AxEmpty>켜진 규칙으로 지금 보낼 알림이 없어요.</AxEmpty>}
            {preview.map((p, i) => (
              <div key={i} className="ax-prev-i">
                {p.img ? <i className="ax-thumb md" style={posterBg(p.img)} aria-hidden /> : <i className="ax-thumb md blank" aria-hidden />}
                <span>
                  <small className="ax-new">새 알림</small>
                  <strong>{p.title}</strong>
                  <span>{p.why}</span>
                </span>
              </div>
            ))}
          </div>
          <p className="ax-cap">지금 데이터로 만든 모양이에요. 알림마다 &apos;왜 왔는지&apos; 한 줄이 붙어요 (북마크 알림은 그 팝업을 북마크한 회원에게만).</p>
        </aside>
      </div>
      <AxNotices
        days={rules.notice.days ?? 14}
        rows={list.map((r) => ({
          id: String(r.entry_id),
          title: String(r.title || ""),
          body: String(r.body || ""),
          when: whenText(r.updated_at),
          edits: Number(r.revision || 1) - 1,
          shown: shown.get(String(r.entry_id)) ?? false,
        }))}
      />
    </>
  );
}

// ================================================================== 회원 정보 (AdmX-6Members)
const YES = [
  "닉네임",
  "로그인 수단 (카카오 · 네이버 · 아이디)",
  "회원 번호 (계정 고유 번호를 알아볼 수 없게 바꾼 값)",
  "약관 동의 시각",
  "프로필 사진 [선택]",
  "아이디 · 암호화한 비밀번호 (아이디 가입)",
  "접속한 날 (일별 접속 수)",
];
const NO = ["이메일", "전화번호", "실명", "생일", "카카오 · 네이버 고유 번호 원래 값"];

export async function AxMembers({ members, sp, href }: { members: Row[]; sp: SP; href: (p: SP) => string }) {
  let visits: Row[] = [];
  try {
    visits = await rows("visits");
  } catch {
    visits = [];
  }
  const stamps = await stampCounts();
  const first = new Map<string, string>();
  for (const r of members) if (Number(r.revision || 0) === 1) first.set(String(r.entry_id), kstDay(r.updated_at));
  const last = lastVisit(visits);
  const all = latest(members).map((r) => {
    const id = String(r.entry_id);
    const st = stamps.get(`m${id.slice(0, 4)}`) ?? 0;
    return {
      id,
      nick: String(r.nickname || "") || "(탈퇴)",
      via: PROVIDER_LABEL[String(r.provider)] || "-",
      joined: first.get(id) || "",
      agreed: String(r.agreed_at || "").slice(0, 16).replace("T", " "),
      last: last.get(id) || "",
      gone: r.status === "deleted",
      admin: isAdmin(id),
      stamps: r.status === "deleted" ? 0 : st,
      lv: r.status === "deleted" ? 0 : (tierOf(st)?.lv ?? 0),
    };
  });
  const q = (sp.mq || "").trim().toLowerCase();
  const via = sp.mp && Object.values(PROVIDER_LABEL).includes(sp.mp) ? sp.mp : "";
  const sort = sp.ms === "visit" || sp.ms === "stamp" ? sp.ms : "join";
  const list = all
    .filter((m) => (!q || m.nick.toLowerCase().includes(q)) && (!via || m.via === via))
    .sort((a, b) =>
      sort === "visit"
        ? b.last.localeCompare(a.last)
        : sort === "stamp"
          ? b.stamps - a.stamps || b.joined.localeCompare(a.joined)
          : b.joined.localeCompare(a.joined),
    );
  const active = all.filter((m) => !m.gone).length;
  const keep = Object.entries(sp).filter(([k, v]) => v && !["mq", "mp", "ms"].includes(k));
  return (
    <>
      <AxHead eyebrow="회원 정보" title={`회원 ${active}명`} sub={all.length > active ? `탈퇴 ${all.length - active}명 기록 포함 ${all.length}명` : undefined} />
      <div className="ax-grid2">
        <AxCard id="ax-yes" className="ax-top-teal" title="받는 정보">
          <div className="ax-chips">
            {YES.map((y) => (
              <span key={y} className="ax-chip yes">
                {y}
              </span>
            ))}
          </div>
          <p className="ax-cap">비밀번호는 직접 저장하지 않고 Supabase DB 함수가 암호화해요. 사진은 선택 동의가 있을 때만 저장해요.</p>
        </AxCard>
        <AxCard id="ax-no" className="ax-top-gray" title="받지 않는 정보">
          <div className="ax-chips">
            {NO.map((n) => (
              <span key={n} className="ax-chip no">
                {n}
              </span>
            ))}
          </div>
          <p className="ax-cap">만 14세 이상인지는 가입 화면의 [필수] 동의로 확인해요.</p>
        </AxCard>
      </div>

      <AxCard id="ax-mlist" title={`회원 목록 ${list.length}명`}>
        <form className="ax-filters" action="/data" method="get">
          {keep.map(([k, v]) => (
            <input key={k} type="hidden" name={k} value={v} />
          ))}
          <label>
            <span className="ax-sr">닉네임 검색</span>
            <input className="ax-input pill" name="mq" defaultValue={sp.mq || ""} placeholder="닉네임 검색" />
          </label>
          <label className="ax-sel">
            가입 방법
            <select className="ax-input pill" name="mp" defaultValue={via}>
              <option value="">전체</option>
              {Object.values(PROVIDER_LABEL).map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label className="ax-sel">
            정렬
            <select className="ax-input pill" name="ms" defaultValue={sort}>
              <option value="join">최근 가입순</option>
              <option value="visit">최근 접속순</option>
              <option value="stamp">도장 많은 순</option>
            </select>
          </label>
          <button type="submit" className="ax-btn dark sm">
            보기
          </button>
          {(q || via || sort !== "join") && (
            <Link className="ax-link" href={href({ mq: undefined, mp: undefined, ms: undefined })} scroll={false}>
              처음대로
            </Link>
          )}
        </form>
        {!all.length ? (
          <AxEmpty>아직 가입한 회원이 없어요. 회원이 가입하면 여기에 쌓여요.</AxEmpty>
        ) : !list.length ? (
          <AxEmpty>조건에 맞는 회원이 없어요.</AxEmpty>
        ) : (
          <div className="ax-tbl-box tall">
            <table className="ax-tbl ax-members">
              <thead>
                <tr>
                  <th>닉네임</th>
                  <th>후기 도장</th>
                  <th>가입 방법</th>
                  <th>가입일</th>
                  <th>약관 동의</th>
                  <th>최근 접속</th>
                  <th>상태</th>
                  <th>권한</th>
                  <th>회원 번호</th>
                </tr>
              </thead>
              <tbody>
                {list.map((m) => (
                  <tr key={m.id} className={m.gone ? "gone" : undefined}>
                    <td>
                      <b>{m.nick}</b>
                    </td>
                    <td className="nowrap">
                      {m.lv ? <RankChip lv={m.lv} /> : null} <span className="ax-muted ax-sm">도장 {m.stamps}개</span>
                    </td>
                    <td>{m.via}</td>
                    <td className="nowrap">{m.joined}</td>
                    <td className="nowrap ax-muted">{m.agreed}</td>
                    <td className="nowrap">{m.last || "-"}</td>
                    <td>{m.gone ? <AxTag tone="gray">탈퇴</AxTag> : "활동"}</td>
                    <td>
                      <AxTag tone={m.admin ? "dark" : "gray"}>{m.admin ? "관리자" : "회원"}</AxTag>
                    </td>
                    <td className="mono ax-muted">{m.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="ax-foot-row">
          <span className="ax-muted ax-sm">관리자는 서버 환경변수 ADMIN_MEMBER_KEYS 의 회원 번호로 정해요. 후기 도장 = 다녀온 후기를 쓴 팝업 수.</span>
          <button type="button" className="ax-btn dashed" disabled>
            강제 탈퇴 · 파기 (공개 전 보완 예정)
          </button>
        </div>
      </AxCard>
    </>
  );
}

// ================================================================== 원본 데이터 (AdmX-7Raw)
const RAW_PAGE = 100;

export async function AxRaw({ sp, href, supabaseUrl }: { sp: SP; href: (p: SP) => string; supabaseUrl: string }) {
  const m = mode();
  const where =
    ({ local: "시험용 로컬 파일 (WEB_DATA_DIR 의 *.json)", supabase: "Supabase 클라우드 (PostgreSQL)" } as Record<string, string>)[m] ||
    "연결 없음";
  const names = Object.keys(DATA_TABLES) as TableName[];
  const all: Record<string, Row[]> = {};
  let err = "";
  await Promise.all(
    names.map(async (n) => {
      try {
        all[n] = await rows(n);
      } catch (e) {
        all[n] = [];
        err = e instanceof Error ? e.message : "읽기 실패";
      }
    }),
  );
  const t = names.includes(sp.t as TableName) ? (sp.t as TableName) : "cafes";
  const q = (sp.q || "").trim();
  const onlyNow = sp.now === "1";
  const cols = dataCols(t);
  const list = rawFilter(all[t], cols, q, onlyNow);
  const pages = Math.max(1, Math.ceil(list.length / RAW_PAGE));
  const page = Math.min(pages, Math.max(1, int(sp.rp, 1)));
  const shown = list.slice((page - 1) * RAW_PAGE, page * RAW_PAGE);
  const newest = new Map(latest(all[t]).map((r) => [String(r.entry_id), Number(r.revision)]));
  const keep = Object.entries(sp).filter(([k, v]) => v && !["q", "rp"].includes(k));
  return (
    <>
      <AxHead
        eyebrow="원본 데이터"
        title="표별 원본"
        sub={
          <>
            지금 저장소: <b>{where}</b> (WEB_STORAGE={process.env.WEB_STORAGE || "supabase"})
          </>
        }
        right={
          <>
            <CsvButton table={t} onlyNow={onlyNow} q={q} />
            <a className="ax-btn dark" href={supabaseUrl} target="_blank" rel="noopener noreferrer">
              Supabase 에서 열기 ↗
            </a>
          </>
        }
      />
      {err && <div className="ax-warnbox">일부 표를 읽지 못했어요: {err.slice(0, 200)}</div>}
      <div className="ax-tabsel" role="tablist" aria-label="표 고르기">
        {names.map((n) => (
          <Link
            key={n}
            href={href({ t: n === "cafes" ? undefined : n, rp: undefined })}
            scroll={false}
            role="tab"
            aria-selected={t === n}
            className={t === n ? "on" : undefined}
          >
            <span className="mono">{n}</span> {DATA_TABLES[n]}{" "}
            <small>
              {all[n].length.toLocaleString("ko-KR")}줄 · 지금 {current(all[n]).length.toLocaleString("ko-KR")}
            </small>
          </Link>
        ))}
      </div>
      <div className="ax-aonly">
        <strong>append-only 표</strong>
        <span>수정 · 삭제도 새 줄로 쌓여요. 같은 entry_id 의 마지막 revision 이 지금 내용이에요.</span>
        <div className="ax-radio" role="radiogroup" aria-label="보기">
          <Link role="radio" aria-checked={onlyNow} className={onlyNow ? "on" : undefined} href={href({ now: "1", rp: undefined })} scroll={false}>
            지금 내용만
          </Link>
          <Link role="radio" aria-checked={!onlyNow} className={!onlyNow ? "on" : undefined} href={href({ now: undefined, rp: undefined })} scroll={false}>
            모든 기록
          </Link>
        </div>
      </div>
      {!all[t].length ? (
        <AxEmpty>아직 기록이 없어요. 앱이나 웹에서 이 표에 쓰면 여기에 쌓여요.</AxEmpty>
      ) : (
        <section className="ax-card ax-raw" aria-label={`${t} 표`}>
          <form className="ax-filters" action="/data" method="get" role="search">
            {keep.map(([k, v]) => (
              <input key={k} type="hidden" name={k} value={v} />
            ))}
            <label>
              <span className="ax-sr">찾기</span>
              <input className="ax-input pill" name="q" defaultValue={q} placeholder="찾기: entry_id · 이름 · 작품 등" />
            </label>
            {q && (
              <Link className="ax-link" href={href({ q: undefined, rp: undefined })} scroll={false}>
                찾기 지우기
              </Link>
            )}
          </form>
          <div className="ax-tbl-box raw">
            <table className="ax-tbl ax-rawt">
              <thead>
                <tr>
                  {cols.map((c) => (
                    <th key={c} className="mono">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shown.map((r, i) => {
                  const isNow = newest.get(String(r.entry_id)) === Number(r.revision);
                  return (
                    <tr key={`${r.row_id}-${i}`} className={isNow && !onlyNow ? "now" : undefined}>
                      {cols.map((c) => {
                        const v = String(r[c] ?? "");
                        if (c === "revision")
                          return (
                            <td key={c} className="mono num">
                              {v}
                              {isNow && !onlyNow && <span className="ax-now">지금</span>}
                            </td>
                          );
                        if (c === "status")
                          return (
                            <td key={c}>
                              <AxTag tone={v === "deleted" ? "red-soft" : "mint"}>{v}</AxTag>
                            </td>
                          );
                        return (
                          <td key={c} className={["row_id", "entry_id", "updated_at"].includes(c) ? "mono ax-muted" : undefined}>
                            <span className="ax-cell">{v}</span>
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="ax-pager">
            <span className="ax-rawcount">
              {list.length}행 · 최근 쓴 순서 · {list.length ? `${(page - 1) * RAW_PAGE + 1}–${Math.min(page * RAW_PAGE, list.length)}` : 0}
              {t === "cafes" ? ` (팝업 ${current(all[t]).length}곳)` : ""}
            </span>
            {pages > 1 && (
              <span className="ax-pager-btns">
                {page > 1 ? (
                  <Link className="ax-wk-btn line" href={href({ rp: page - 1 === 1 ? undefined : String(page - 1) })} scroll={false} aria-label="이전 페이지">
                    ‹
                  </Link>
                ) : (
                  <span className="ax-wk-btn line dis" aria-hidden>
                    ‹
                  </span>
                )}
                <span className="ax-muted ax-sm">
                  {page} / {pages}
                </span>
                {page < pages ? (
                  <Link className="ax-wk-btn line" href={href({ rp: String(page + 1) })} scroll={false} aria-label="다음 페이지">
                    ›
                  </Link>
                ) : (
                  <span className="ax-wk-btn line dis" aria-hidden>
                    ›
                  </span>
                )}
              </span>
            )}
          </div>
        </section>
      )}
      <p className="ax-cap">
        Supabase 화면에서 직접 고쳤다면 &apos;데이터 새로 불러오기&apos;를 눌러야 앱에 보여요. 북마크 표의 회원 칸(user)은 화면 · CSV 에
        내보내지 않아요. {m === "local" ? "Supabase 로 옮기면 같은 표가 Supabase 대시보드 → Table Editor 에도 보여요 (db.md 6절)." : ""}
      </p>
    </>
  );
}
