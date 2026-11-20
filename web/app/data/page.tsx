import type { Metadata } from "next";
import Link from "next/link";
import { addDays, todayKST } from "@/lib/popup";
import {
  dailyActive,
  dailyEvents,
  dayLabel,
  kstDay,
  lastVisit,
  memberEvents,
  periodMD,
  popupBoard,
  RULES,
  ruleSettings,
  rulesTable,
  TARGET_LABEL,
  weekOf,
  whenText,
  ymdOf,
} from "@/lib/server/admin";
import { isAdmin, PROVIDER_LABEL } from "@/lib/server/auth";
import { getMe } from "@/lib/server/session";
import { popups, SURVEY_FORM_TABS, surveyVerify } from "@/lib/server/stats";
import { current, HEADERS, latest, mode, rows, type Row, type Table as TableName } from "@/lib/server/store";
import { surveyRows, surveySheetId } from "@/lib/server/survey";
import { IcClose, IcDatabase, IcLess, IcLogin, IcMore, IcRight, IcSchedule } from "@/components/admin/AdminIcons";
import { DecideForm, NoticesPanel, RefreshButton, RuleEditor, WeekNav, type RuleView } from "@/components/admin/AdminClient";
import { BoardCols, Gantt, GANTT_PAGE, BOARD_PAGE, PopupCard } from "@/components/admin/Board";
import { Caption, Expander, Metric, Note, Table } from "@/components/admin/Bits";
import { VBar } from "@/components/admin/Charts";
import Survey, { SURVEY_VIEWS } from "@/components/admin/Survey";

// 관리자 대시보드 (앱 page_data). 관리자(ADMIN_MEMBER_KEYS 회원 번호)만 — 서버가 매번 다시 확인한다.
// 앱의 화면 상태(보는 탭 · 주 · 더보기)는 주소 뒤 ?tab=…&w=… 로 둔다 (새로고침해도 그대로).
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "데이터 보기", robots: { index: false } };

const ADMIN_TABS: [string, string][] = [
  ["board", "팝업 현황"],
  ["usage", "이용 지표"],
  ["survey", "사용자 테스트"],
  ["requests", "삭제 요청"],
  ["notices", "알림 관리"],
  ["members", "회원 정보"],
  ["raw", "원본 데이터"],
];
const ADM_KPIS: [string, string, string][] = [
  ["new", "이번 주 새로 등록", "곳"],
  ["live", "진행 중", "곳"],
  ["soon", "예정", "곳"],
  ["members", "회원 (활동)", "명"],
  ["requests", "삭제 요청 대기", "건"],
];
const ST_COLOR: Record<string, string> = { pending: "#D9821B", approved: "#23866A", rejected: "#C8352A" };
const ST_LABEL: Record<string, string> = { pending: "대기", approved: "승인", rejected: "거부" };
const DATA_TABLES: Record<string, string> = {
  cafes: "팝업",
  reviews: "리뷰",
  favorites: "북마크",
  members: "회원",
  del_requests: "삭제 요청",
  notices: "알림",
  visits: "접속",
};
const DATA_HIDE: Record<string, string[]> = { favorites: ["user"] };
const MINT = "#56C2A7";
const RAW_CAP = 1000;

/** Claude 예약 작업 주소 (계정마다 달라서 ADMIN_ROUTINE_URL, 없으면 예약 작업 목록) */
const routineUrl = () => process.env.ADMIN_ROUTINE_URL || "https://claude.ai/code/routines";
/** Supabase 표 편집기 바로가기 (SUPABASE_URL 의 프로젝트 번호). 설정이 없으면 대시보드 첫 화면 */
function supabaseDashboardUrl(): string {
  let host = "";
  try {
    host = new URL(process.env.SUPABASE_URL || "").hostname;
  } catch {
    host = "";
  }
  const ref = host.endsWith(".supabase.co") ? host.split(".")[0] : "";
  return ref ? `https://supabase.com/dashboard/project/${ref}/editor` : "https://supabase.com/dashboard/projects";
}

type SP = Record<string, string | undefined>;
type Props = { searchParams: Promise<SP> };

const int = (v: string | undefined, d: number) => (/^-?\d{1,4}$/.test(v || "") ? Number(v) : d);

export default async function DataPage({ searchParams }: Props) {
  const me = await getMe();
  if (!me || !isAdmin(me.key)) {
    return (
      <div className="adm adm-deny">
        <div className="stats-title">관리자 전용</div>
        <div className="stats-sub">이 화면은 관리자만 볼 수 있어요. 관리자 계정으로 로그인해 주세요.</div>
        <Link className="st-pagelink" href="/login?next=/data">
          <IcLogin />
          로그인하기
        </Link>
      </div>
    );
  }
  const sp = await searchParams;
  const today = todayKST();
  const tab = ADMIN_TABS.some(([t]) => t === sp.tab) ? String(sp.tab) : "board";
  /** 지금 주소에서 몇 칸만 바꾼 주소 (빈 값은 뺀다) */
  const href = (patch: SP) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries({ ...sp, ...patch })) if (v !== undefined && v !== "") p.set(k, v);
    const qs = p.toString();
    return qs ? `/data?${qs}` : "/data";
  };

  let cafes: Row[] = [];
  let reqs: Row[] = [];
  let members: Row[] = [];
  let readError = "";
  try {
    [cafes, reqs, members] = await Promise.all([rows("cafes"), rows("del_requests"), rows("members")]);
  } catch (e) {
    readError = e instanceof Error ? e.message : "읽기 실패";
  }
  const reqNow = current(reqs);
  const pend = reqNow.filter((r) => r.decision === "pending").length;
  const nMembers = current(members).length;
  const monNow = weekOf(today);

  // ---- 숫자 카드 (앱 _admin_kpis) ----
  const pops = popups(cafes);
  const live: Row[] = [];
  const soon: Row[] = [];
  for (const r of pops) {
    if (r.status === "deleted") continue;
    const s = ymdOf(r.start_date);
    const e = ymdOf(r.end_date);
    if (s && e && s <= today && today <= e) live.push(r);
    else if (s && s > today) soon.push(r);
  }
  const lists: Record<string, Row[]> = {
    new: popupBoard(cafes, monNow)["새로 생성"].filter((r) => r.status !== "deleted"),
    live: live.sort((a, b) => String(a.end_date || "").localeCompare(String(b.end_date || ""))),
    soon: soon.sort((a, b) => String(a.start_date || "").localeCompare(String(b.start_date || ""))),
  };
  const nums: Record<string, number> = {
    new: lists.new.length,
    live: live.length,
    soon: soon.length,
    members: nMembers,
    requests: pend,
  };
  const picked = sp.kpi && lists[sp.kpi] ? sp.kpi : "";
  const kpiHref = (k: string) =>
    k === "members" || k === "requests"
      ? href({ tab: k, kpi: undefined, kall: undefined })
      : href({ kpi: picked === k ? undefined : k, kall: undefined });

  // ---- 주 (팝업 현황 · 이용 지표가 같이 쓴다, 앱 adm_week) ----
  const off = int(sp.w, 0);
  const mon = addDays(monNow, off * 7);
  const sun = addDays(mon, 6);
  const weekReset = { gn: undefined, b0: undefined, b1: undefined, b2: undefined, b3: undefined };
  const weekNav = (
    <WeekNav
      off={off}
      mon={mon}
      thisMon={monNow}
      label={`${dayLabel(mon)} ~ ${dayLabel(sun)}`}
      hrefFor={{
        prev: href({ ...weekReset, w: String(off - 1) }),
        next: href({ ...weekReset, w: String(off + 1) }),
        now: href({ ...weekReset, w: undefined }),
        base: href({ ...weekReset, w: "__W__" }),
      }}
    />
  );

  return (
    <div className="adm">
      <div className="adm-links">
        <a className="adm-linkbtn" href={routineUrl()} target="_blank" rel="noopener noreferrer">
          <IcSchedule />
          Claude 예약 작업 (매일 08:00 수집)
        </a>
        <a className="adm-linkbtn" href={supabaseDashboardUrl()} target="_blank" rel="noopener noreferrer">
          <IcDatabase />
          Supabase 데이터 보기
        </a>
        <RefreshButton />
      </div>
      <div className="adm-eyebrow">ANI:WHERE ADMIN · {today.replaceAll("-", ".")}</div>
      <h1 className="adm-title">관리자 대시보드</h1>
      <div className="adm-sub">저장소: {mode()} · 모든 기록은 지우지 않고 쌓여요 (append-only)</div>
      {readError && <Note kind="warn">데이터를 읽지 못했어요. 잠시 뒤 다시 열어 주세요. ({readError.slice(0, 120)})</Note>}

      <div className="adm-kpis">
        {ADM_KPIS.map(([k, label, unit]) => {
          const alert = k === "requests" && pend ? " alert" : "";
          const on = picked === k;
          const Arrow = k === "members" || k === "requests" ? IcRight : on ? IcLess : IcMore;
          return (
            <Link key={k} href={kpiHref(k)} scroll={false} className={`adm-kpi${alert}${on ? " on" : ""}`}>
              <span>
                {label}
                <Arrow className="kpi-arr" />
              </span>
              <b>
                {nums[k]}
                <small>{unit}</small>
              </b>
            </Link>
          );
        })}
      </div>
      {picked && <KpiList picked={picked} rows={lists[picked]} all={sp.kall === "1"} href={href} />}

      <nav className="adm-tabs" aria-label="관리자 보기">
        {ADMIN_TABS.map(([t, label]) => (
          <Link
            key={t}
            href={href({ tab: t === "board" ? undefined : t })}
            scroll={false}
            className={tab === t ? "on" : undefined}
            aria-current={tab === t ? "page" : undefined}
          >
            {t === "requests" && pend ? `${label} ${pend}` : label}
          </Link>
        ))}
      </nav>

      {tab === "board" && (
        <>
          {weekNav}
          <div className="adm-panel-h">이 주 일정 (간트 차트 · 하루 단위)</div>
          <Gantt
            all={cafes}
            mon={mon}
            today={today}
            shown={Math.max(GANTT_PAGE, int(sp.gn, GANTT_PAGE))}
            moreHref={href({ gn: String(Math.max(GANTT_PAGE, int(sp.gn, GANTT_PAGE)) + GANTT_PAGE) })}
          />
          <div className="adm-panel-h">고른 주 현황</div>
          <BoardCols
            all={cafes}
            mon={mon}
            shown={[0, 1, 2, 3].map((i) => Math.max(BOARD_PAGE, int(sp[`b${i}`], BOARD_PAGE)))}
            moreHref={(i) => href({ [`b${i}`]: String(Math.max(BOARD_PAGE, int(sp[`b${i}`], BOARD_PAGE)) + BOARD_PAGE) })}
          />
        </>
      )}
      {tab === "usage" && <Usage mon={mon} members={members} weekNav={weekNav} />}
      {tab === "survey" && <SurveyTab view={sp.sv} href={href} />}
      {tab === "requests" && <Requests rows={reqNow} />}
      {tab === "notices" && <Notices />}
      {tab === "members" && <Members rows={members} />}
      {tab === "raw" && <Raw sp={sp} href={href} />}
    </div>
  );
}

// ------------------------------------------------------------------ 숫자 카드를 누르면 펼쳐지는 목록
function KpiList({
  picked,
  rows: list,
  all,
  href,
}: {
  picked: string;
  rows: Row[];
  all: boolean;
  href: (p: SP) => string;
}) {
  const label = Object.fromEntries(ADM_KPIS.map(([k, l]) => [k, l]))[picked];
  const color = ({ new: "#14B8A6", live: "#23866A", soon: "#3672BD" } as Record<string, string>)[picked];
  const shown = all ? list : list.slice(0, 12);
  return (
    <>
      <div className="adm-col adm-kpilist" style={{ ["--c" as string]: color }}>
        <div className="adm-colhead">
          {label}
          <small>{list.length}곳 · 누르면 상세로</small>
        </div>
        {shown.length ? (
          <div className="adm-kgrid">
            {shown.map((r) => (
              <PopupCard key={String(r.entry_id)} r={r} period={periodMD(r)} />
            ))}
          </div>
        ) : (
          <div className="adm-empty">해당하는 팝업이 없어요.</div>
        )}
      </div>
      <div className="adm-more adm-kpifoot">
        {list.length > 12 && (
          <Link className="st-btn" href={href({ kall: all ? undefined : "1" })} scroll={false}>
            {all ? <IcLess /> : <IcMore />}
            {all ? "접기" : `${list.length - 12}곳 더 보기`}
          </Link>
        )}
        <Link className="st-btn tertiary" href={href({ kpi: undefined, kall: undefined })} scroll={false}>
          <IcClose />
          목록 닫기
        </Link>
      </div>
    </>
  );
}

// ------------------------------------------------------------------ 이용 지표 (앱 _admin_usage)
async function Usage({ mon, members, weekNav }: { mon: string; members: Row[]; weekNav: React.ReactNode }) {
  let visits: Row[] = [];
  try {
    visits = await rows("visits");
  } catch {
    visits = [];
  }
  const ev = memberEvents(members);
  const charts: [string, { label: string; n: number }[], string, string][] = [
    ["신규 이용자 수", dailyEvents(ev, "가입", mon), MINT, "명"],
    ["일별 접속 회원", dailyActive(visits, mon), "#3672BD", "명 (연인원)"],
    ["탈퇴한 회원 수", dailyEvents(ev, "탈퇴", mon), "#C8352A", "명"],
  ];
  return (
    <>
      {weekNav}
      {charts.map(([title, data, color, unit]) => (
        <div key={title}>
          <div className="adm-metric-h">
            <b>{title}</b>
            <span>
              이 주 합계 <strong>{data.reduce((a, b) => a + b.n, 0)}</strong>
              {unit}
            </span>
          </div>
          <VBar rows={data.map((d) => ({ label: d.label, values: [d.n] }))} series={[{ name: "명", color }]} height={200} />
        </div>
      ))}
      <Caption>
        신규 = 그날 가입한 회원 · 접속 회원 = 그날 로그인한 상태로 한 번 이상 들어온 회원 (같은 날 여러 번 와도 1명, 손님은
        세지 않아요) · 탈퇴 = 그날 탈퇴한 회원. 날짜는 한국 시간.
      </Caption>
    </>
  );
}

// ------------------------------------------------------------------ 사용자 테스트
async function SurveyTab({ view, href }: { view?: string; href: (p: SP) => string }) {
  const sheetId = surveySheetId();
  const { rows: all, error } = sheetId ? await surveyRows(sheetId) : { rows: [], error: "" };
  // 검증 (11/20): 구글 폼 응답 탭에 있고 받은 시각이 지금보다 앞선 응답만 센다 (앱 stats.survey_verify)
  const forms = Object.fromEntries(
    await Promise.all(
      Object.entries(SURVEY_FORM_TABS).map(async ([ver, tab]) => [ver, sheetId && !error ? (await surveyRows(sheetId, tab)).rows : []] as const),
    ),
  );
  const { rows: sv, check } = surveyVerify(all, forms);
  const v = SURVEY_VIEWS.some(([k]) => k === view) ? String(view) : "improve";
  return (
    <Survey
      sheetId={sheetId}
      rows={sv}
      check={check}
      error={error}
      view={v}
      viewHref={(k) => href({ sv: k === "improve" ? undefined : k })}
    />
  );
}

// ------------------------------------------------------------------ 삭제 요청 (앱 _admin_requests)
function Requests({ rows: list }: { rows: Row[] }) {
  const sorted = [...list].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
  const pending = sorted.filter((r) => r.decision === "pending");
  const done = sorted.filter((r) => r.decision !== "pending");
  return (
    <>
      <div className="adm-panel-h">처리 대기 {pending.length}건</div>
      {!pending.length && <div className="adm-empty">처리할 삭제 요청이 없어요.</div>}
      {pending.map((r) => (
        <div key={String(r.entry_id)} className="adm-reqitem">
          <div className="adm-req" style={{ ["--st" as string]: ST_COLOR.pending }}>
            <div className="rail" />
            <div>
              <div className="t">
                <span className="adm-pill">대기</span>
                {TARGET_LABEL[String(r.target_type)] || "글"} · {String(r.target_title || "")}
              </div>
              <div className="d">
                요청 {String(r.requester_nick || "")} · {whenText(r.updated_at)}
              </div>
              <div className="d">사유: {String(r.reason || "")}</div>
            </div>
          </div>
          <DecideForm entryId={String(r.entry_id)} />
        </div>
      ))}
      <Expander label={`처리한 요청 ${done.length}건`}>
        {done.slice(0, 50).map((r) => {
          const d = String(r.decision || "");
          return (
            <div key={String(r.entry_id)} className="adm-req" style={{ ["--st" as string]: ST_COLOR[d] || "#8A9592" }}>
              <div className="rail" />
              <div>
                <div className="t">
                  <span className="adm-pill">{ST_LABEL[d] || d}</span>
                  {String(r.target_title || "")}
                </div>
                <div className="d">
                  요청 {String(r.requester_nick || "")} · 사유 {String(r.reason || "")}
                </div>
                {d === "rejected" && <div className="d">거부 사유: {String(r.admin_reason || "")}</div>}
              </div>
            </div>
          );
        })}
      </Expander>
    </>
  );
}

// ------------------------------------------------------------------ 알림 관리 (앱 _admin_notices)
async function Notices() {
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
  const table = rulesTable(rules);
  const ruleViews: RuleView[] = Object.entries(RULES).map(([k, d]) => ({
    key: k,
    name: d.name,
    enabled: rules[k].enabled,
    days: rules[k].days,
    max_items: rules[k].max_items,
    hasDays: d.days !== null,
    hasMax: d.max_items !== null,
  }));
  return (
    <>
      <div className="adm-panel-h">자동으로 나가는 알림</div>
      <Table columns={["알림", "상태", "언제", "최대 개수", "누구에게", "어디에"]} rows={table} />
      <RuleEditor rules={ruleViews} />
      <div style={{ height: 8 }} />
      <NoticesPanel
        rows={list.map((r) => ({
          id: String(r.entry_id),
          title: String(r.title || ""),
          body: String(r.body || ""),
          when: whenText(r.updated_at),
          edits: Number(r.revision || 1) - 1,
        }))}
      />
    </>
  );
}

// ------------------------------------------------------------------ 회원 정보 (앱 _admin_members)
async function Members({ rows: all }: { rows: Row[] }) {
  let visits: Row[] = [];
  try {
    visits = await rows("visits");
  } catch {
    visits = [];
  }
  const first = new Map<string, string>();
  for (const r of all) if (Number(r.revision || 0) === 1) first.set(String(r.entry_id), kstDay(r.updated_at));
  const last = lastVisit(visits);
  const table = latest(all)
    .map((r) => {
      const id = String(r.entry_id);
      return {
        "회원 번호": id,
        닉네임: String(r.nickname || "") || "(탈퇴)",
        "로그인 수단": PROVIDER_LABEL[String(r.provider)] || "-",
        가입일: first.get(id) || "",
        "약관 동의": String(r.agreed_at || "").slice(0, 16).replace("T", " "),
        "최근 접속": last.get(id) || "-",
        상태: r.status === "deleted" ? "탈퇴" : "활동",
        권한: isAdmin(id) ? "관리자" : "일반 회원",
      };
    })
    .sort((a, b) => b.가입일.localeCompare(a.가입일));
  return (
    <>
      <div className="adm-info">
        <b>수집하는 정보</b> — 닉네임 · 로그인 수단(카카오/네이버/아이디) · 회원 번호(계정 고유 번호를 알아볼 수 없게 바꾼
        값) · 약관 동의 시각 · 프로필 사진(선택: 카카오·네이버 사진 주소 또는 직접 올린 사진) · 아이디 가입이면 아이디와{" "}
        <b>암호화한</b> 비밀번호 · 접속한 날(일별 접속 수)
        <br />
        <b>수집하지 않는 정보</b> — 이메일 · 전화번호 · 실명 · 생일 · 카카오/네이버 고유 번호 원래 값
      </div>
      <div className="adm-panel-h" style={{ marginTop: 12 }}>
        회원 {table.length}명
      </div>
      {table.length ? (
        <Table
          columns={["회원 번호", "닉네임", "로그인 수단", "가입일", "약관 동의", "최근 접속", "상태", "권한"]}
          rows={table}
        />
      ) : (
        <div className="adm-empty">아직 가입한 회원이 없어요.</div>
      )}
    </>
  );
}

// ------------------------------------------------------------------ 원본 데이터 (앱 _admin_raw)
async function Raw({ sp, href }: { sp: SP; href: (p: SP) => string }) {
  const m = mode();
  const where =
    ({ local: "시험용 로컬 파일 (WEB_DATA_DIR 의 *.json)", supabase: "Supabase 클라우드 (PostgreSQL)" } as Record<string, string>)[
      m
    ] || "연결 없음";
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
  const cols = HEADERS[t].filter((c) => !(DATA_HIDE[t] || []).includes(c));
  let list = all[t];
  if (q) {
    const low = q.toLowerCase();
    list = list.filter((r) => cols.some((c) => String(r[c] ?? "").toLowerCase().includes(low)));
  }
  if (onlyNow) list = latest(list);
  list = [...list].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
  return (
    <>
      <div className="stats-title">데이터 보기</div>
      <div className="stats-sub">
        지금 저장소: <b>{where}</b> (WEB_STORAGE={process.env.WEB_STORAGE || "supabase"})
      </div>
      {err && <Note kind="warn">일부 표를 읽지 못했어요: {err.slice(0, 200)}</Note>}
      {m === "local" && <Caption>Supabase 로 옮기면 같은 표가 Supabase 대시보드 → Table Editor 에도 보여요 (db.md 6절).</Caption>}
      <div className="raw-metrics">
        {names.map((n) => (
          <Metric
            key={n}
            label={`${DATA_TABLES[n]} (${n})`}
            value={`${all[n].length}행`}
            delta={`지금 ${current(all[n]).length}건`}
            color="off"
            border
          />
        ))}
      </div>
      <div className="st-seg" role="tablist" aria-label="표">
        {names.map((n) => (
          <Link
            key={n}
            href={href({ t: n === "cafes" ? undefined : n })}
            scroll={false}
            role="tab"
            aria-selected={t === n}
            className={t === n ? "on" : undefined}
          >
            {DATA_TABLES[n]}
          </Link>
        ))}
      </div>
      {!all[t].length ? (
        <Note>아직 기록이 없어요.</Note>
      ) : (
        <>
          <form className="st-field raw-q" action="/data" method="get">
            {Object.entries(sp)
              .filter(([k, v]) => k !== "q" && v)
              .map(([k, v]) => (
                <input key={k} type="hidden" name={k} value={v} />
              ))}
            <span>찾기</span>
            <input className="st-input" name="q" defaultValue={q} placeholder="entry_id · 이름 · 작품 등" />
          </form>
          <Link
            className={`st-toggle${onlyNow ? " on" : ""}`}
            href={href({ now: onlyNow ? undefined : "1" })}
            scroll={false}
            role="switch"
            aria-checked={onlyNow}
          >
            <i />
            최신 기록만 (수정 이력 숨기기)
          </Link>
          <Caption>
            {list.length}행 · 최근 쓴 순서{list.length > RAW_CAP ? ` · 처음 ${RAW_CAP}행만 보여요 (찾기로 좁혀 보세요)` : ""}
          </Caption>
          <Table columns={cols} rows={list.slice(0, RAW_CAP)} height={520} numeric={["revision", "lat", "lng", "calls"]} />
        </>
      )}
    </>
  );
}
