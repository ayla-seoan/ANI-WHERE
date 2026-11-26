import Link from "next/link";
import {
  avg,
  SURVEY_TARGET,
  SURVEY_TASKS,
  surveyCompare,
  surveySummary,
  surveyVersion,
  type SurveyCheck,
  type SurveyRow,
} from "@/lib/server/stats";
import { IcCompare, IcHourglass, IcLinkOff } from "./AdminIcons";
import { AxGroupBars } from "./AxCharts";
import { AxHead } from "./AxShell";
import { Caption, Expander, Metric, Note, Table } from "./Bits";
import { HBar, VBar } from "./Charts";
import { SurveyReload } from "./AdminClient";

// 관리자 '사용자 테스트' (앱 _admin_survey · _survey_improve · _survey_detail). 숫자는 lib/server/stats (stats.py 와 같은 규칙).

/** 버전: (참여자에게 보낼 주소, 폼 고치기). 1차 = 로그인 · 물어보기 없던 첫 버전, 2차 = 지금 */
export const SURVEY_FORMS: Record<string, [string, string]> = {
  "1차": [
    "https://docs.google.com/forms/d/e/1FAIpQLSe8ZKxd1bcF4jgTYwHgFdmXGsX5Y2PcGe9KTZTDLl6V_gzHpA/viewform",
    "https://docs.google.com/forms/d/1E53ZHq-zHC0qy4jfwwekTV-KrbsfU8PakrsJH77A8m8/edit",
  ],
  "2차": [
    "https://docs.google.com/forms/d/e/1FAIpQLScp02W0zqeqYRwdMPW4D9Az-2hJny5sFDFkg0gRlnqvnF71mA/viewform",
    "https://docs.google.com/forms/d/1P1TZjlF-YR-80fa4s2-ABUFRJfiSU0b4aQo_raosceg/edit",
  ],
};
const N8N_URL = "http://localhost:5678"; // n8n 은 운영자 컴퓨터에서 돈다
export const SURVEY_VIEWS: [string, string][] = [
  ["improve", "1차 → 2차 개선"],
  ["2", "2차 자세히"],
  ["1", "1차 자세히"],
];

const fmt = (v: number | null, unit = "") => (v === null ? "-" : `${Math.round(v * 1000) / 1000}${unit}`);
const signed = (x: number, unit: string) => {
  const v = Math.round(x * 10) / 10;
  return `${v >= 0 ? "+" : ""}${v}${unit}`;
};

/** 설문 바로가기 (시안: 머리 오른쪽 알약 링크 ↗) */
function SurveyLinks({ sheetId }: { sheetId: string }) {
  const links: [string, string][] = [];
  for (const [ver, [form, edit]] of Object.entries(SURVEY_FORMS)) {
    links.push([`${ver} 폼`, form]);
    links.push([`${ver} 폼 고치기`, edit]);
  }
  if (sheetId) links.push(["응답 시트", `https://docs.google.com/spreadsheets/d/${encodeURIComponent(sheetId)}/edit`]);
  links.push(["n8n", process.env.N8N_URL || N8N_URL]);
  return (
    <div className="ax-extlinks">
      {links.map(([label, href]) => (
        <a key={label} className="ax-btn line sm" href={href} target="_blank" rel="noopener noreferrer">
          {label} ↗
        </a>
      ))}
    </div>
  );
}

type Item = [string, string, string | null, "normal" | "inverse"];

/** 앱 _sv_groups: 숫자 카드를 항목별 상자로 묶는다 (상자 폭은 카드 수에 비례) */
function Groups({ groups }: { groups: [string, Item[]][] }) {
  return (
    <div className="svg-row">
      {groups.map(([title, items]) => (
        <div className="svg-box" key={title} style={{ flexGrow: Math.max(1, items.length) }}>
          <div className="sv-gh">{title}</div>
          <div className="svg-items">
            {items.map(([label, value, delta, color]) => (
              <Metric key={label} label={label} value={value} delta={delta} color={color} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

const H = ({ children }: { children: React.ReactNode }) => <div className="adm-panel-h">{children}</div>;

/** 1차 → 2차 개선 (AdmX-8Test): 숫자 카드 · 3계열 막대(평소 #c77a12 · 1차 #2c5bc5 · 2차 #0d9488) · 같은 사람 비교 · 막힌 곳 · 측정 한계 */
function Improve({ rows }: { rows: SurveyRow[] }) {
  const c = surveyCompare(rows);
  const a = c["1차"];
  const b = c["2차"];
  const tgt = SURVEY_TARGET;
  if (!a.응답자 || !b.응답자)
    return (
      <Note icon={<IcCompare />}>
        1차 응답 {a.응답자}명 · 2차 응답 {b.응답자}명이에요. 두 폼 모두 응답이 들어오면 여기서 1차 → 2차 를 비교해요.
        (지금은 &apos;2차 자세히&apos; · &apos;1차 자세히&apos; 에서 볼 수 있어요)
      </Note>
    );
  const delta = (x: number | null, y: number | null, unit: string) => (x === null || y === null ? null : signed(y - x, unit));
  const okS = b.성공률 !== null && b.성공률 >= tgt.success;
  const okT = b.질문1초 !== null && b.질문1초 <= tgt.q1;
  const base = avg([a.평소초, b.평소초].filter((x) => x !== null));
  const tasks = Object.entries(SURVEY_TASKS);
  const pains = new Map<string, number>();
  for (const v of [a, b]) for (const p of v.불편한점) pains.set(p.label, (pains.get(p.label) ?? 0) + p.n);
  const same = c["같은 사람"];
  const kpis: [string, string, React.ReactNode, string | null][] = [
    ["참여", `${a.응답자 + b.응답자}명`, <>1차 {a.응답자}명 · 2차 {b.응답자}명</>, null],
    [
      `과제 성공률 (목표 ${tgt.success}% 이상 ${okS ? "O" : "X"})`,
      fmt(b.성공률, "%"),
      <>
        1차 {fmt(a.성공률, "%")} → <strong>2차 {fmt(b.성공률, "%")}</strong>
      </>,
      delta(a.성공률, b.성공률, "%p"),
    ],
    [
      `질문 1 평균 시간 (목표 ${tgt.q1}초 이하 ${okT ? "O" : "X"})`,
      fmt(b.질문1초, "초"),
      <>
        평소 {fmt(base, "초")} → 1차 {fmt(a.질문1초, "초")} → <strong>2차 {fmt(b.질문1초, "초")}</strong>
      </>,
      delta(a.질문1초, b.질문1초, "초"),
    ],
    [
      "만족도 (5점) · 다시 쓸 의향",
      `${fmt(b.만족도)} · ${fmt(b.다시쓸의향, "%")}`,
      <>
        1차 {fmt(a.만족도)} · {fmt(a.다시쓸의향, "%")} → <strong>2차</strong>
      </>,
      delta(a.만족도, b.만족도, "점"),
    ],
  ];
  const V3 = [
    { name: "평소 방법", cls: "s-usual" },
    { name: "1차", cls: "s-v1" },
    { name: "2차", cls: "s-v2" },
  ];
  const V2 = V3.slice(1);
  const cmp: [string, string, string, string][] = [
    ["나아짐", "v2", "질문 1 이 빨라진 사람", `${same["빨라진 사람"]} / ${same["시간 잰 사람"]}명`],
    ["나아짐", "v2", "해낸 과제가 늘어난 사람", `${same["더 해낸 사람"]}명`],
    ["나아짐", "v2", "만족도가 오른 사람", `${same["만족도 오른 사람"]}명`],
    ["평균", "gray", "질문 1 에서 줄어든 시간 (시간 잰 사람)", fmt(same["평균 줄어든 초"], "초")],
  ];
  return (
    <>
      <div className="ax-kpis k4">
        {kpis.map(([label, v, sub, d]) => (
          <div key={label} className="ax-kpi static">
            <span className="ax-kpi-l">{label}</span>
            <strong>{v}</strong>
            <span className="ax-kpi-d">
              {sub}
              {d ? ` (${d})` : ""}
            </span>
          </div>
        ))}
      </div>
      <div className="ax-grid2">
        <section className="ax-card">
          <AxGroupBars
            title="팝업 하나 찾는 시간 (초) · 평소 → 1차 → 2차"
            unit="초"
            series={V3}
            groups={[{ label: "질문 1 · 이번 주말 서울 팝업 찾기", values: [base, a.질문1초, b.질문1초] }]}
          />
        </section>
        <section className="ax-card">
          <AxGroupBars
            title="과제별 성공률 (%) · 1차 vs 2차"
            unit="%"
            top={100}
            series={V2}
            groups={tasks.map(([t, n]) => ({ label: `${t} · ${n}`, values: [a.과제별[t].성공률, b.과제별[t].성공률] }))}
          />
        </section>
        <section className="ax-card">
          <AxGroupBars
            title="과제별 평균 시간 (초, 해낸 사람) · 1차 vs 2차"
            unit="초"
            series={V2}
            groups={tasks.map(([t, n]) => ({ label: `${t} · ${n}`, values: [a.과제별[t].평균초, b.과제별[t].평균초] }))}
          />
        </section>
        <section className="ax-card">
          <AxGroupBars
            title="만족도 분포 (명) · 1차 vs 2차"
            unit="명"
            series={V2}
            groups={[1, 2, 3, 4, 5].map((i) => ({ label: `${i}점`, values: [a.만족도분포[String(i)] ?? 0, b.만족도분포[String(i)] ?? 0] }))}
          />
        </section>
      </div>
      <div className="ax-grid2 wide-l">
        <section className="ax-card" aria-labelledby="ax-same-h">
          <div className="ax-card-h">
            <h2 id="ax-same-h">같은 사람 비교 (1차 → 2차) · {same.명}명</h2>
          </div>
          {!same.명 ? (
            <p className="ax-cap">1차 · 2차 모두 낸 사람이 아직 없어요 (1차 폼에는 2차 로그인 닉네임을 적게 안내해요).</p>
          ) : (
            <>
              {cmp.map(([k, tone, t, n]) => (
                <div key={t} className="ax-cmp-i">
                  <span className={`ax-tag t-${tone === "v2" ? "teal" : "gray"}`}>{k}</span>
                  <span className="ax-cmp-t">{t}</span>
                  <strong>{n}</strong>
                </div>
              ))}
              <Expander label={`사람별 (${same.명}명)`}>
                <Table
                  columns={["닉네임", "질문 1 (1차)", "질문 1 (2차)", "해낸 과제 (1차)", "해낸 과제 (2차)", "만족도 (1차)", "만족도 (2차)"]}
                  rows={c.짝}
                  numeric={["질문 1 (1차)", "질문 1 (2차)", "해낸 과제 (1차)", "해낸 과제 (2차)", "만족도 (1차)", "만족도 (2차)"]}
                />
              </Expander>
            </>
          )}
        </section>
        <section className="ax-card" aria-labelledby="ax-stuck-h">
          <div className="ax-card-h">
            <h2 id="ax-stuck-h">막힌 곳</h2>
          </div>
          {(["1차", "2차"] as const).map((v) => (
            <div key={v}>
              <b className="ax-sm">{v}</b>
              {c[v].막힌곳.length ? (
                <ul className="ax-stuck">
                  {c[v].막힌곳.map((x) => (
                    <li key={x.label}>
                      {x.label} — {x.n}번
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="ax-cap">없어요.</p>
              )}
            </div>
          ))}
          <p className="ax-cap">
            측정 한계 · 시간은 응답자가 고른 구간의 가운데 값(대략값)이에요.
            {Math.min(a.응답자, b.응답자) < 10 ? " 응답자가 10명보다 적어 참고용이에요." : ""}
          </p>
        </section>
      </div>
      <section className="ax-card">
        <div className="ax-card-h">
          <h2>무엇이 나아졌나 (1차 → 2차)</h2>
        </div>
        <Table
          columns={["지표", "1차", "2차", "변화", "판정", "목표"]}
          rows={c.지표.map(([name, x, y, unit, up, goal]) => ({
            지표: name,
            "1차": fmt(x, unit),
            "2차": fmt(y, unit),
            변화: x === null || y === null ? "-" : signed(y - x, unit === "%" ? "%p" : unit),
            판정:
              x === null || y === null ? "-" : Math.abs(y - x) < 1e-9 ? "그대로" : y > x === up ? "나아짐" : "나빠짐",
            목표: goal === null ? "-" : up ? `${goal}${unit} 이상` : `${goal}${unit} 이하`,
          }))}
        />
      </section>
      {pains.size > 0 && (
        <section className="ax-card">
          <div className="ax-card-h">
            <h2>평소 불편한 점 (문제 정의 · 1차 · 2차 응답 합계, 명)</h2>
          </div>
          <HBar
            rows={[...pains.entries()].sort((x, y) => y[1] - x[1]).map(([label, n]) => ({ label, values: [n] }))}
            series={[{ name: "명", color: "#c77a12" }]}
          />
        </section>
      )}
    </>
  );
}

function Detail({ rows }: { rows: SurveyRow[] }) {
  const s = surveySummary(rows);
  const tgt = SURVEY_TARGET;
  const okS = s.성공률 !== null && s.성공률 >= tgt.success;
  const okT = s.질문1초 !== null && s.질문1초 <= tgt.q1;
  const tasks = Object.entries(SURVEY_TASKS);
  const cols = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  return (
    <>
      <Groups
        groups={[
          ["참여", [["응답자", `${s.응답자}명`, null, "normal"]]],
          [
            "팝업 하나 찾는 시간 (A/B)",
            [
              ["A · 평소 방법", fmt(s.평소초, "초"), null, "normal"],
              [
                "B · ANI:WHERE",
                fmt(s.질문1초, "초"),
                s.평소초 === null || s.질문1초 === null ? null : signed(s.질문1초 - s.평소초, "초"),
                "inverse",
              ],
            ],
          ],
          ["과제", [["성공률 (목표 80% 이상)", fmt(s.성공률, "%"), null, "normal"]]],
          [
            "만족 · 의향",
            [
              ["만족도 (5점)", fmt(s.만족도), null, "normal"],
              ["평소보다 편함 (5점)", fmt(s.비교), null, "normal"],
              ["다시 쓸 의향", fmt(s.다시쓸의향, "%"), null, "normal"],
            ],
          ],
        ]}
      />
      <Caption>
        목표 달성: 과제 성공률 {okS ? "O" : "X"} · 질문 1 평균 {tgt.q1}초 이하 {okT ? "O" : "X"}  ·  A = 평소 방법(SNS ·
        커뮤니티 · 검색)으로 걸리던 시간(응답자가 고른 구간), B = ANI:WHERE 로 직접 해 본 시간
        {s.응답자 < 10 ? "  ·  응답자가 적어 참고용이에요" : ""}
      </Caption>
      <div className="st-cols2">
        <div>
          <H>A/B · 팝업 하나 찾는 시간 (초)</H>
          <HBar
            rows={[
              { label: "평소 방법", values: [s.평소초 ?? 0] },
              { label: "ANI:WHERE", values: [s.질문1초 ?? 0] },
            ]}
            series={[{ name: "초", color: "#56C2A7" }]}
          />
          <H>과제별 성공률 (%)</H>
          <HBar
            rows={tasks.map(([t, n]) => ({ label: `${t} · ${n}`, values: [s.과제별[t].성공률 ?? 0] }))}
            series={[{ name: "성공률", color: "#14B8A6" }]}
          />
        </div>
        <div>
          <H>평소 불편한 점 (문제 정의 · 명)</H>
          {s.불편한점.length > 0 && (
            <HBar rows={s.불편한점.map((x) => ({ label: x.label, values: [x.n] }))} series={[{ name: "명", color: "#F2A33A" }]} />
          )}
          <H>평소 정보를 찾는 곳 (명)</H>
          {s.정보출처.length > 0 && (
            <HBar rows={s.정보출처.map((x) => ({ label: x.label, values: [x.n] }))} series={[{ name: "명", color: "#A9C3EA" }]} />
          )}
        </div>
      </div>
      <div className="st-cols2">
        <div>
          <H>만족도 분포 (명)</H>
          <VBar
            rows={[1, 2, 3, 4, 5].map((i) => ({ label: `${i}점`, values: [s.만족도분포[String(i)] ?? 0] }))}
            series={[{ name: "명", color: "#9EDDCC" }]}
            height={180}
          />
        </div>
        <div>
          <H>팝업 방문 빈도 (명)</H>
          {s.방문빈도.length > 0 && (
            <VBar
              rows={s.방문빈도.map((x) => ({ label: x.label, values: [x.n] }))}
              series={[{ name: "명", color: "#56C2A7" }]}
              height={180}
            />
          )}
        </div>
      </div>
      <H>과제별</H>
      <Table
        columns={["과제", "응답", "성공률", "평균 시간(성공)", "해냈어요 / 어렵게 / 못 했어요"]}
        rows={tasks.map(([t, n]) => ({
          과제: `${t} · ${n}`,
          응답: s.과제별[t].명,
          성공률: fmt(s.과제별[t].성공률, "%"),
          "평균 시간(성공)": fmt(s.과제별[t].평균초, "초"),
          "해냈어요 / 어렵게 / 못 했어요": ["해냈어요", "어렵게 해냈어요", "못 했어요"]
            .map((k) => String(s.과제별[t].결과[k] ?? 0))
            .join(" / "),
        }))}
      />
      <div className="st-cols2">
        <div>
          <H>자주 막힌 곳</H>
          {s.막힌곳.length ? (
            <ul className="st-list">
              {s.막힌곳.map((x) => (
                <li key={x.label}>
                  {x.label} — {x.n}번
                </li>
              ))}
            </ul>
          ) : (
            <p className="st-p">아직 없어요.</p>
          )}
        </div>
        <div>
          <H>바라는 점</H>
          {s.바라는점.length ? (
            <ul className="st-list">
              {s.바라는점.slice(0, 10).map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          ) : (
            <p className="st-p">아직 없어요.</p>
          )}
        </div>
      </div>
      <Expander label={`원본 응답 (${rows.length}줄 · 한 사람 = 질문 1~4 네 줄)`}>
        <Table columns={cols} rows={rows} />
      </Expander>
    </>
  );
}

export default function Survey({
  sheetId,
  rows,
  check,
  error,
  view,
  viewHref,
}: {
  sheetId: string;
  rows: SurveyRow[];
  check?: SurveyCheck;
  error: string;
  view: string;
  viewHref: (v: string) => string;
}) {
  const title = (SURVEY_VIEWS.find(([k]) => k === view) || SURVEY_VIEWS[0])[1];
  const n = check?.전체 ?? new Set(rows.map((r) => `${surveyVersion(r)}|${String(r["닉네임"] || "").trim()}`)).size;
  return (
    <>
      <AxHead eyebrow="사용자 테스트" title={title} right={<SurveyLinks sheetId={sheetId} />} />
      {!sheetId ? (
        <Note icon={<IcLinkOff />}>
          설문 시트가 아직 연결되지 않았어요. <code>.env</code>(배포는 Vercel 환경변수)에 <code>SURVEY_SHEET_ID</code> 를 넣어
          주세요 (구글 시트 주소의 /d/ 와 /edit 사이 글자). 만드는 법: automation/n8n/README.md
        </Note>
      ) : (
        <>
          {/* 11/26 사용자 결정: '정리' 탭의 응답을 모두 센다. 폼 응답 탭과의 대조 수는 참고로만 (stats.surveyVerify) */}
          <div className={`ax-banner${!error && n > 0 ? " ok" : ""}`}>
            <span className="ax-banner-n">{error ? "-" : `${n}명`}</span>
            <span className="ax-banner-t">
              {error ? (
                <strong>설문 시트를 읽지 못했어요</strong>
              ) : n > 0 ? (
                <strong>
                  응답 {n}명 · 폼 응답 탭에서 확인 {check?.검증 ?? 0}명 · 폼 응답 탭에 없음 {check?.폼에없음 ?? 0}명
                </strong>
              ) : (
                <strong>아직 응답이 없어요 — 받는 중</strong>
              )}
              <span>
                &apos;정리&apos; 탭의 응답을 모두 세요. 구글 폼 응답 탭(1차 응답 · 2차 응답)과 닉네임을 맞춰 본 수는 참고예요.
                {check && (check.미래 > 0 || check.시각없음 > 0)
                  ? ` 받은 시각과 상관없이 모두 셉니다 — 폼 응답 중 받은 시각이 미래 ${check.미래}건 · 시각 없음 ${check.시각없음}건 포함.`
                  : ""}
              </span>
            </span>
            <SurveyReload className="ax-btn dark" />
          </div>
          {error ? (
            <Note kind="warn">{error}</Note>
          ) : !rows.length ? (
            <Note icon={<IcHourglass />}>아직 응답이 없어요. 참여자가 설문 폼을 내면 n8n 이 1분 안에 여기로 쌓아요.</Note>
          ) : (
            <>
              <div className="st-seg ax-seg" role="tablist" aria-label="보기">
                {SURVEY_VIEWS.map(([k, label]) => (
                  <Link
                    key={k}
                    href={viewHref(k)}
                    scroll={false}
                    role="tab"
                    aria-selected={view === k}
                    className={view === k ? "on" : undefined}
                  >
                    {k === "improve" && <IcCompare />}
                    {label}
                  </Link>
                ))}
              </div>
              {view === "improve" ? (
                <Improve rows={rows} />
              ) : (
                (() => {
                  const ver = view === "1" ? "1차" : "2차";
                  const sub = rows.filter((r) => surveyVersion(r) === ver);
                  return sub.length ? (
                    <div className="ax-detail">
                      <Detail rows={sub} />
                    </div>
                  ) : (
                    <Note icon={<IcHourglass />}>{ver} 폼 응답이 아직 없어요.</Note>
                  );
                })()
              )}
              <Caption>
                구글 폼(1차 · 2차) → n8n(운영자 컴퓨터, http://localhost:5678 에서만 열려요) → 구글 시트 &apos;정리&apos; 탭(버전 칸) →
                여기. 이메일 · 이름 · 연락처는 받지 않고, 자유 답변의 전화번호 · 이메일은 n8n 이 지워요.
              </Caption>
            </>
          )}
        </>
      )}
    </>
  );
}
