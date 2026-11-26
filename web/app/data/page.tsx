import type { Metadata } from "next";
import Link from "next/link";
import { addDays, todayKST } from "@/lib/popup";
import { weekLabel } from "@/lib/server/a-admin";
import { weekOf } from "@/lib/server/admin";
import { isAdmin } from "@/lib/server/auth";
import { getMe } from "@/lib/server/session";
import { SURVEY_FORM_TABS, surveyVerify } from "@/lib/server/stats";
import { current, rows, type Row } from "@/lib/server/store";
import { surveyRows, surveySheetId } from "@/lib/server/survey";
import { IcLogin } from "@/components/admin/AdminIcons";
import { AxRefresh, AxWeek } from "@/components/admin/AxClient";
import AxHome from "@/components/admin/AxHome";
import { AxMembers, AxNoticesPage, AxRaw, AxRequests, AxUsage } from "@/components/admin/AxPages";
import AxPopups from "@/components/admin/AxPopups";
import { AX_PAGES, AxNav } from "@/components/admin/AxShell";
import Survey, { SURVEY_VIEWS } from "@/components/admin/Survey";

// 관리자 대시보드 (앱 page_data) — A안 (11/26, docs/design/admin-handoff): 왼쪽 사이드바 + 8페이지.
// 관리자(ADMIN_MEMBER_KEYS 회원 번호)만 — 서버가 매번 다시 확인한다.
// 화면 상태(보는 페이지 · 주 · 더보기)는 주소 뒤 ?tab=…&w=… 로 둔다. 예전 주소(?tab=board 등)도 그대로 열린다.
// ?tab 이 없으면 새 첫 화면 '한눈에 보기'.
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "데이터 보기", robots: { index: false } };

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
  const tab = AX_PAGES.some(([t]) => t === sp.tab) ? String(sp.tab) : "home";
  /** 지금 주소에서 몇 칸만 바꾼 주소 (빈 값은 뺀다) */
  const href = (patch: SP) => {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries({ ...sp, ...patch })) if (v !== undefined && v !== "") p.set(k, v);
    const qs = p.toString();
    return qs ? `/data?${qs}` : "/data";
  };
  /** 메뉴: 페이지를 바꾸면 고른 주(w)만 가져간다 */
  const pageHref = (t: string) => {
    const p = new URLSearchParams();
    if (t !== "home") p.set("tab", t);
    if (sp.w) p.set("w", sp.w);
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
  const pend = current(reqs).filter((r) => r.decision === "pending").length;
  const monNow = weekOf(today);

  // ---- 주 (한눈에 보기 · 팝업 현황 · 이용 지표가 같이 쓴다, 앱 adm_week) ----
  const off = int(sp.w, 0);
  const mon = addDays(monNow, off * 7);
  const weekReset = { gn: undefined, b0: undefined, b1: undefined, b2: undefined, b3: undefined };
  const weekNav = (
    <AxWeek
      off={off}
      mon={mon}
      thisMon={monNow}
      label={weekLabel(mon)}
      hrefFor={{
        prev: href({ ...weekReset, w: String(off - 1) }),
        next: href({ ...weekReset, w: String(off + 1) }),
        now: href({ ...weekReset, w: undefined }),
        base: href({ ...weekReset, w: "__W__" }),
      }}
    />
  );

  let page: React.ReactNode = null;
  if (tab === "home") {
    let reviews: Row[] = [];
    let visits: Row[] = [];
    try {
      [reviews, visits] = await Promise.all([rows("reviews"), rows("visits")]);
    } catch {
      /* 못 읽으면 빈 목록 */
    }
    page = (
      <AxHome
        cafes={cafes}
        reqs={reqs}
        members={members}
        reviews={reviews}
        visits={visits}
        today={today}
        mon={mon}
        monNow={monNow}
        weekNav={weekNav}
        refresh={<AxRefresh />}
        sp={sp}
        href={href}
      />
    );
  } else if (tab === "board") page = <AxPopups cafes={cafes} mon={mon} today={today} sp={sp} href={href} weekNav={weekNav} />;
  else if (tab === "usage") page = <AxUsage members={members} cafes={cafes} mon={mon} today={today} weekNav={weekNav} />;
  else if (tab === "requests") page = <AxRequests reqs={reqs} cafes={cafes} sp={sp} href={href} />;
  else if (tab === "notices") page = <AxNoticesPage cafes={cafes} today={today} />;
  else if (tab === "members") page = <AxMembers members={members} sp={sp} href={href} />;
  else if (tab === "raw") page = <AxRaw sp={sp} href={href} supabaseUrl={supabaseDashboardUrl()} />;
  else if (tab === "survey") page = <SurveyTab view={sp.sv} href={href} />;

  return (
    <div className="ax">
      <AxNav tab={tab} pend={pend} hrefOf={pageHref} routineUrl={routineUrl()} supabaseUrl={supabaseDashboardUrl()} />
      <div className="ax-main">
        {readError && (
          <div className="ax-warnbox" role="alert">
            데이터를 읽지 못했어요. 잠시 뒤 다시 열어 주세요. ({readError.slice(0, 120)})
          </div>
        )}
        {page}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ 사용자 테스트
async function SurveyTab({ view, href }: { view?: string; href: (p: SP) => string }) {
  const sheetId = surveySheetId();
  const { rows: all, error } = sheetId ? await surveyRows(sheetId) : { rows: [], error: "" };
  // 11/26 사용자 결정: '정리' 탭 응답을 모두 센다. 폼 응답 탭(1차 응답 · 2차 응답) 대조는 참고 숫자 (stats.surveyVerify)
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
