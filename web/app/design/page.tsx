import type { Metadata } from "next";
import { DESIGN, type DesignToken } from "@/content/docs.gen";
import { markdown } from "@/components/pages/markdown";
import IconFont from "@/components/pages/IconFont";

// ANI:WHERE 디자인 시스템 (앱 page_design, 누구나 열람). docs/design/ (tokens.json · README.md · components/) 와
// static/design/*.css 를 scripts/sync_docs.mjs 가 옮겨 온 것을 그대로 그린다 — 값은 원본 파일 한 곳에서만 고친다.
export const metadata: Metadata = {
  title: "디자인 시스템",
  description: "ANI:WHERE 디자인 시스템: 말투 · 색 토큰 · 글꼴 · 간격 · 모서리 · 그림자 · 컴포넌트 · 로고.",
  alternates: { canonical: "/design" },
};

const COMPONENTS: [string, string][] = [
  ["Badge", "배지"],
  ["Button", "버튼"],
  ["PillTabs", "알약 탭 · 메뉴바"],
  ["PosterCard", "포스터 카드"],
  ["StoryCircle", "북마크 팝업 동그라미"],
  ["Chip", "칩"],
  ["RankStamp", "후기 도장"],
  ["PreTimeline", "사전예약 타임라인"],
  ["ReviewCard", "후기 카드"],
];
const GROUPS: [string, string[]][] = [
  ["포인트 · 브랜드", ["accent", "logo", "mint", "gnb"]],
  ["글자 · 바탕 · 선", ["ink", "muted", "subtle", "line", "surface", "gray"]],
  ["강조 · 상태", ["coral", "blue", "red", "purple", "orange", "star", "today", "gantt"]],
  ["후기 도장 랭크", ["rank"]],
  ["지역", ["city"]],
];
const LOGOS: [string, string][] = [
  ["logo.png", "기본 로고"],
  ["mascot.png", "마스코트"],
  ["ask_avatar.png", "물어보기 도우미"],
  ["default_poster.png", "기본 포스터"],
];

const val = (t: DesignToken) => (typeof t.value === "string" ? t.value : String(Object.values(t.value)[0] ?? ""));
const dropTitle = (md: string) => (md.startsWith("# ") ? md.split("\n").slice(1).join("\n") : md);

/** tokens.json → CSS 변수 (앱 _design_vars). 별칭 {mint} 은 var(--mint) */
function vars(): string {
  const tok = DESIGN.tokens;
  const out: string[] = [];
  for (const t of tok.color.tokens) {
    const v = val(t);
    out.push(`--${t.name}: ${v.startsWith("{") ? `var(--${v.slice(1, -1)})` : v};`);
  }
  for (const fam of [tok.spacing, tok.radius, tok.shadow]) for (const t of fam?.tokens ?? []) out.push(`--${t.name}: ${val(t)};`);
  for (const [k, v] of Object.entries(tok.type.families)) out.push(`--font-${k}: ${v};`);
  return `.pg-design { ${out.join(" ")} }`;
}

export default function DesignPage() {
  const tok = DESIGN.tokens;
  const comp = DESIGN.components;
  return (
    <>
      <IconFont />
      <style dangerouslySetInnerHTML={{ __html: DESIGN.css + "\n" + vars() }} />
      <div className="pg-design pg-doc">
        {/* 표지 (Claude Design 표지와 같은 그림). 960px 로 그리고 화면이 좁으면 줄여 보인다 */}
        <div className="ds-cover" dangerouslySetInnerHTML={{ __html: comp["Cover.html"] || "" }} />
        <div className="ds-sub">
          ANI:WHERE 화면 코드(앱 · 공개 웹)에서 값을 그대로 옮긴 디자인 시스템이에요 (A안, 2026.11.26 기준). Claude Design 에
          같은 내용이 있고, 이 페이지는 누구나 볼 수 있게 앱 안에 둔 것이에요.
        </div>

        {/* 1) 브랜드 안내서 */}
        <div dangerouslySetInnerHTML={{ __html: markdown(dropTitle(DESIGN.readme)) }} />

        {/* 2) 색 토큰 */}
        <div className="ds-h2">색 토큰</div>
        <div className="ds-sub">이름 · 값 · 언제 쓰는지. 칸의 색은 실제 값이에요.</div>
        {GROUPS.map(([title, pre]) => (
          <div key={title}>
            <div className="ds-grp">{title}</div>
            <div className="ds-sw">
              {tok.color.tokens
                .filter((t) => pre.some((p) => t.name.startsWith(p)))
                .map((t) => (
                  <div key={t.name}>
                    <div className="chip" style={{ background: `var(--${t.name})` }} />
                    <div className="nm">{t.name}</div>
                    <div className="vl">{val(t)}</div>
                    <div className="us">{t.usage || ""}</div>
                  </div>
                ))}
            </div>
          </div>
        ))}

        {/* 3) 글꼴 */}
        <div className="ds-h2">글꼴</div>
        <div className="ds-sub">제목은 Jua, 본문은 나눔스퀘어라운드 → Pretendard, 아이콘은 Material Symbols Rounded.</div>
        <div className="ds-type">
          {tok.type.groups.flatMap((g) =>
            g.styles.map((s) => (
              <div key={`${g.name}-${s.name}`}>
                <div className="meta">
                  <b>{s.name}</b>
                  {g.name} · {s.fontSize} / {s.lineHeight} · {s.fontWeight}
                  <br />
                  {s.usage || ""}
                </div>
                <div
                  style={{
                    fontFamily: `var(--font-${g.family})`,
                    fontSize: s.fontSize,
                    lineHeight: String(s.lineHeight),
                    fontWeight: Number(s.fontWeight) || 400,
                    minWidth: 0,
                    overflowWrap: "anywhere",
                  }}
                >
                  {s.sample || ""}
                </div>
              </div>
            )),
          )}
        </div>

        {/* 4) 간격 · 모서리 · 그림자 */}
        <div className="ds-h2">간격 · 모서리 · 그림자</div>
        <div className="ds-grp">간격</div>
        <div className="ds-scale">
          {tok.spacing.tokens.map((t) => (
            <div key={t.name}>
              <div className="bar" style={{ width: val(t), height: 40 }} />
              <b>{t.name}</b>
              <br />
              {val(t)}
            </div>
          ))}
        </div>
        <div className="ds-grp">모서리</div>
        <div className="ds-scale">
          {tok.radius.tokens.map((t) => (
            <div key={t.name}>
              <div className="box" style={{ borderRadius: val(t) }} />
              <b>{t.name}</b>
              <br />
              {val(t)}
            </div>
          ))}
        </div>
        <div className="ds-grp">그림자</div>
        <div className="ds-scale">
          {tok.shadow.tokens.map((t) => (
            <div key={t.name}>
              <div className="shd" style={{ boxShadow: val(t) }} />
              <b>{t.name}</b>
            </div>
          ))}
        </div>

        {/* 5) 컴포넌트 (앱 CSS 를 옮긴 모습 + 쓰는 규칙) */}
        <div className="ds-h2">컴포넌트</div>
        <div className="ds-sub">앱 화면의 CSS 를 보고 옮긴 모습이에요 (누르는 동작은 없어요).</div>
        {COMPONENTS.map(([key, label]) => {
          const html = comp[`${key}.html`];
          const doc = comp[`${key}.md`];
          if (!html || !doc) return null;
          return (
            <div key={key}>
              <div className="ds-grp">
                {label} <span style={{ color: "#9AA5A1", fontWeight: 600 }}>{key}</span>
              </div>
              <div className="ds-comp">
                <div className="stage" dangerouslySetInnerHTML={{ __html: html }} />
              </div>
              <div dangerouslySetInnerHTML={{ __html: markdown(dropTitle(doc)) }} />
            </div>
          );
        })}

        {/* 6) 로고 · 그림 */}
        <div className="ds-h2">로고 · 그림</div>
        <div className="ds-sub">저장소 static/ 의 파일 그대로. 다시 그리거나 색을 바꾸지 않아요.</div>
        <div className="ds-logos">
          {LOGOS.map(([f, a]) => (
            <figure key={f}>
              <img src={`/design/${f}`} alt={a} loading="lazy" />
              <figcaption>
                {f} · {a}
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </>
  );
}
