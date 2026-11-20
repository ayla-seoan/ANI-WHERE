import type { Metadata } from "next";
import { RAW_ROOT, rawHeaders } from "@/lib/server/github";
import { todayKST } from "@/lib/popup";
import {
  beforeAfter,
  byCity,
  byMonth,
  byWork,
  completeness,
  durationBuckets,
  durations,
  engagement,
  NOTION_CUTOFF,
  popups,
  ratingDist,
  startingWithin,
  statusCounts,
  topBookmarked,
} from "@/lib/server/stats";
import { current, mode, rows, type Row } from "@/lib/server/store";
import { Caption, Expander, Metric, Note, Table } from "@/components/admin/Bits";
import { HBar, VBar } from "@/components/admin/Charts";

// PO 지표 (앱 page_stats). 누구나 볼 수 있다 (앱과 같게). 숫자는 lib/server/stats (common/stats.py 와 같은 규칙).
export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "지표" };

const MINT = "#56C2A7";
const STATS_BEFORE = "#B8C2BF"; // 개선 전: 회색
const REPO_RAW = `${RAW_ROOT}/data`; // 서버에서만 (lib/server/github.ts)

/** 저장소 연결이 없으면(회원 기능 꺼짐) 앱처럼 공개 기록(GitHub data/*.json)으로 계산한다 */
async function table(name: "cafes" | "reviews" | "favorites"): Promise<Row[]> {
  if (mode() !== "none") return rows(name);
  try {
    const res = await fetch(`${REPO_RAW}/${name}.json`, {
      headers: rawHeaders(),
      next: { revalidate: 600 },
      signal: AbortSignal.timeout(10_000),
    });
    const raw = (await res.json()) as Row[];
    return Array.isArray(raw) ? raw.map((r) => ({ ...r, revision: Number(r.revision || 0) })) : [];
  } catch {
    return [];
  }
}

const H4 = ({ children }: { children: React.ReactNode }) => <h4 className="stats-h4">{children}</h4>;

export default async function StatsPage() {
  const today = todayKST();
  let all: Row[] = [];
  let reviewAll: Row[] = [];
  let favAll: Row[] = [];
  let err = "";
  try {
    [all, reviewAll, favAll] = await Promise.all([table("cafes"), table("reviews"), table("favorites")]);
  } catch (e) {
    err = e instanceof Error ? e.message : "읽기 실패";
  }
  const list = popups(all);
  const head = (
    <>
      <div className="stats-title">ANI:WHERE 지표</div>
      <div className="stats-sub">
        팝업 {list.length}건 · 기준일 {today} · 저장소가 append-only 라서 과거 시점의 상태를 그대로 다시 계산해요.
      </div>
    </>
  );
  if (!list.length)
    return (
      <div className="adm stats">
        {head}
        {err && <Note kind="warn">데이터를 읽지 못했어요. 잠시 뒤 다시 열어 주세요.</Note>}
        <Note>아직 팝업이 없어요. 첫 화면 오른쪽 위 + 로 팝업을 등록하면 지표가 채워져요.</Note>
      </div>
    );

  const now = completeness(list);
  const before = completeness(popups(all, NOTION_CUTOFF));
  const status = statusCounts(list, today);
  const days = durations(list);
  const ba = beforeAfter(all);
  const reviewRows = current(reviewAll);
  const favRows = current(favAll);
  const eng = engagement(favRows, reviewRows);
  const top = topBookmarked(favRows, list);
  const desc = (xs: { label: string; n: number }[]) => [...xs].sort((a, b) => b.n - a.n);
  const sign = (x: number) => `${x >= 0 ? "+" : ""}${Math.round(x)}`;

  return (
    <div className="adm stats">
      {head}
      <div className="st-cols4">
        <Metric
          border
          label="방문 전 정보 완결률"
          value={`${Math.round(now.complete)}%`}
          delta={before.n ? `${sign(now.complete - before.complete)}%p (Notion 주간 수집 전 대비)` : null}
        />
        <Metric border label="지금 갈 수 있는 팝업" value={`${status["진행 중"]}곳`} />
        <Metric border label="7일 안에 시작" value={`${startingWithin(list, today)}곳`} />
        <Metric
          border
          label="평균 진행 기간"
          value={days.length ? `${Math.round(days.reduce((a, b) => a + b, 0) / days.length)}일` : "-"}
        />
      </div>

      <H4>개선 전후: 방문 전 정보가 채워진 비율</H4>
      <Caption>
        이전 = {NOTION_CUTOFF} 전까지 쌓인 기록 ({before.n}건) · 지금 = 모든 기록 ({now.n}건). 방문 전 정보 = 기간·주소·지도
        좌표·참고 링크·포스터가 모두 있음. 회색 막대 = 이전, 민트 막대 = 지금
      </Caption>
      {before.n ? (
        <>
          <HBar
            rows={ba.map((r) => ({ label: r.항목, values: [r.이전, r.지금] }))}
            series={[
              { name: "이전", color: STATS_BEFORE },
              { name: "지금", color: MINT },
            ]}
            xLabel="채워진 비율(%)"
          />
          <Expander label="표로 보기">
            <Table
              columns={["항목", "이전", "지금"]}
              rows={[...ba].sort((a, b) => (a.항목 < b.항목 ? -1 : a.항목 > b.항목 ? 1 : 0))}
              numeric={["이전", "지금"]}
            />
          </Expander>
        </>
      ) : (
        <Note>비교할 이전 기록이 없어요.</Note>
      )}

      <H4>팝업은 어디에, 무엇이 많이 열리나</H4>
      <div className="st-cols2">
        <div>
          <Caption>지역별 팝업 수 (상위 10, 나머지는 &apos;그 외&apos;)</Caption>
          <HBar rows={desc(byCity(list)).map((c) => ({ label: c.label, values: [c.n] }))} series={[{ name: "팝업 수", color: MINT }]} />
        </div>
        <div>
          <Caption>작품별 팝업 수 (상위 10)</Caption>
          <HBar rows={desc(byWork(list)).map((c) => ({ label: c.label, values: [c.n] }))} series={[{ name: "팝업 수", color: MINT }]} />
        </div>
      </div>
      <div className="st-cols2">
        <div>
          <Caption>시작 월별 팝업 수</Caption>
          <VBar rows={byMonth(list).map((c) => ({ label: c.label, values: [c.n] }))} series={[{ name: "팝업 수", color: MINT }]} height={260} />
        </div>
        <div>
          <Caption>진행 기간 분포</Caption>
          <VBar
            rows={durationBuckets(days).map((c) => ({ label: c.label, values: [c.n] }))}
            series={[{ name: "팝업 수", color: MINT }]}
            height={260}
          />
        </div>
      </div>

      <H4>참여</H4>
      <div className="st-cols5">
        {eng.map(([k, v]) => (
          <Metric key={k} border label={k} value={v} />
        ))}
      </div>
      <div className="st-cols2">
        <div>
          <Caption>다녀온 후기 별점 분포</Caption>
          <VBar
            rows={ratingDist(reviewRows).map((c) => ({ label: c.label, values: [c.n] }))}
            series={[{ name: "후기 수", color: MINT }]}
            height={240}
          />
        </div>
        <div>
          <Caption>북마크가 많은 팝업</Caption>
          {top.length ? (
            <Table columns={["팝업", "북마크"]} rows={top} numeric={["북마크"]} />
          ) : (
            <Note>아직 북마크가 없어요.</Note>
          )}
        </div>
      </div>
    </div>
  );
}
