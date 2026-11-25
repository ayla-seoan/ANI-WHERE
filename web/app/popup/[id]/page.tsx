import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPopup, getPopupData } from "@/lib/data";
import {
  dayLabel,
  daysBetween,
  detailSpan,
  detailState,
  hostOf,
  isReserve,
  mapLink,
  periodText,
  regionColor,
  stateOf,
  todayKST,
  toItem,
  workKey,
  type Popup,
} from "@/lib/popup";
import Gallery from "@/components/detail/Gallery";
import { SimCard } from "@/components/cards";
import HScroll from "@/components/HScroll";
import { CalendarIcon, OpenIcon, PinIcon, SparkleIcon } from "@/components/Icons";
import Reviews from "@/components/detail/Reviews";
import SideTabs from "@/components/detail/SideTabs";
import EditPanel, { type EditData } from "@/components/detail/EditPanel";
import ShareButtons from "@/components/detail/ShareButtons";
import BookmarkButton from "@/components/member/BookmarkButton";
import RememberRecent from "@/components/member/RememberRecent";
import { displayName } from "@/lib/server/auth";
import { threadsFor } from "@/lib/server/member";
import { getMe } from "@/lib/server/session";
import { lvOfNick, myStamps } from "@/lib/server/stamp";
import { charactersByWork, currentCafes, cafeHistory, historyCards, type HistoryCard } from "@/lib/server/cafe";
import { ALWAYS_END, parseLinks, rawFromNote, split, splitImages, TAG_CHECK, EVENT_TAGS } from "@/lib/cafe-rules";
import { PLACEHOLDER_POSTER } from "@/lib/popup";
import type { Row } from "@/lib/server/store";

// 회원 리뷰·북마크가 있어 요청마다 그린다 (팝업 데이터는 lib/data.ts 가 10분 캐시)
export const dynamic = "force-dynamic";

type Props = { params: Promise<{ id: string }> };

function validId(id: string) {
  return /^[\w-]{1,64}$/.test(id);
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const p = validId(id) ? await getPopup(id) : null;
  if (!p) return { title: "팝업을 찾을 수 없어요" };
  const today = todayKST();
  const title = `${p.work} · ${p.name}`;
  const description = [periodText(p, today), p.address, p.perks.length ? `특전: ${p.perks.join(", ")}` : ""]
    .filter(Boolean)
    .join(" · ")
    .slice(0, 160);
  const image = p.images[0] || "/icons/icon-512.png";
  return {
    title,
    description,
    alternates: { canonical: `/popup/${p.id}` },
    openGraph: { title, description, images: [image], type: "article" },
    twitter: { card: p.images[0] ? "summary_large_image" : "summary", title, description, images: [image] },
  };
}

/** 비슷한 팝업 (앱 similar_popups): 같은 작품의 다른 팝업 — 같은 행사의 다른 지역 지점이 먼저, 그다음 같은 작품의 다른 행사. 끝난 건 뺀다 */
function similar(cur: Popup, all: Popup[], today: string, limit = 8): Popup[] {
  const key = workKey(cur.work);
  if (key.length < 2) return [];
  const myCafe = workKey(cur.name);
  const out: [number, number, string, Popup][] = [];
  for (const r of all) {
    if (r.id === cur.id) continue;
    const k = workKey(r.work);
    if (!k || !(k === key || (Math.min(k.length, key.length) >= 3 && (k.includes(key) || key.includes(k))))) continue;
    const rank = stateOf(r, today).rank;
    if (rank === 2) continue;
    const otherBranch = workKey(r.name) === myCafe && r.area !== cur.area;
    out.push([otherBranch ? 0 : 1, rank, r.start, r]);
  }
  out.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2].localeCompare(b[2]));
  return out.slice(0, limit).map((t) => t[3]);
}

function km(a: [number, number], b: [number, number]): number {
  const R = 6371;
  const toRad = (x: number) => (x * Math.PI) / 180;
  const dLat = toRad(b[0] - a[0]);
  const dLng = toRad(b[1] - a[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** 이 근처 다른 팝업 (앱 nearby_popups): 30km 안, 끝난 것 빼고 가까운 순 */
function nearby(cur: Popup, all: Popup[], today: string, limit = 8): [Popup, number][] {
  if (cur.lat === null || cur.lng === null) return [];
  const here: [number, number] = [cur.lat, cur.lng];
  return all
    .filter((r) => r.id !== cur.id && r.lat !== null && r.lng !== null && stateOf(r, today).rank !== 2)
    .map((r) => [r, km(here, [r.lat as number, r.lng as number])] as [Popup, number])
    .filter(([, d]) => d <= 30)
    .sort((a, b) => a[1] - b[1])
    .slice(0, limit);
}

function kmText(d: number): string {
  if (d < 0.05) return "같은 건물";
  return `거리 ${d < 1 ? `${Math.round(d * 1000)}m` : `${d.toFixed(1)}km`}`;
}

/** 저장된 참고 웹사이트 → 수정하기 입력칸 (한 줄에 하나, cafe.parse_links 의 쓸 수 있는 주소만) */
function parseLinksText(v: string): string {
  return parseLinks(v)[0].join("\n");
}

/** 소개 글: 줄바꿈 그대로, 줄 맨 앞 '[배경]' 같은 소제목은 굵게 (앱 _intro_body) */
function IntroBody({ text }: { text: string }) {
  return (
    <>
      {text.split(/\r?\n/).map((line, i) => {
        if (!line.trim()) return <span key={i} className="dintro-gap" />;
        const m = line.match(/^\[([^\]]{1,40})\](.*)$/);
        return (
          <span key={i} className="dintro-line">
            {m ? (
              <>
                <b className="dintro-h">{m[1]}</b>
                {m[2]}
              </>
            ) : (
              line
            )}
          </span>
        );
      })}
    </>
  );
}

export default async function PopupPage({ params }: Props) {
  const { id } = await params;
  if (!validId(id)) notFound();
  // 속도 (11/19): 팝업 목록 · 로그인 회원을 함께 읽는다 (예전엔 차례로)
  const [{ popups }, me] = await Promise.all([getPopupData(), getMe()]);
  const p = popups.find((x) => x.id === id);
  if (!p) notFound();

  const today = todayKST();
  const state = detailState(p, today);
  const color = regionColor(p.city);
  const groups: [string, string[]][] = [
    ["특전", p.perks],
    ["굿즈", p.goods],
    ["이벤트", p.tags.filter((t) => t !== "상시" && t !== "기간 확인 필요")],
  ];
  let threads: Awaited<ReturnType<typeof threadsFor>> = [];
  try {
    threads = await threadsFor(p.id, me ? displayName(me.row) : "");
  } catch (e) {
    console.error("[detail] 리뷰를 읽지 못함", e instanceof Error ? e.message : e);
  }
  // 수정하기 탭 (회원만): 이 팝업의 최신 기록 · 작품별 캐릭터 · 수정 이력
  let edit: EditData | null = null;
  let byWork: Record<string, string[]> = {};
  let history: HistoryCard[] = [];
  let histLv: Record<number, number> = {}; // 수정 이력: 기록 번호 → 고친 회원의 후기 도장 랭크 (0 = 없음)
  let stamps = 0; // 내 후기 도장 수 (리뷰 쓰기 칸)
  if (me) {
    try {
      stamps = await myStamps(displayName(me.row));
    } catch {
      /* 도장을 못 세면 도장 없이 */
    }
    try {
      const all = await cafeHistory(p.id);
      const cur: Row | undefined = all[all.length - 1];
      if (cur && cur.status !== "deleted") {
        const tags = split(cur.tags);
        edit = {
          entryId: p.id,
          revision: Number(cur.revision),
          work: String(cur.work || ""),
          characters: split(cur.characters),
          cafeName: String(cur.cafe_name || ""),
          address: String(cur.address || ""),
          start: String(cur.start_date || "").slice(0, 10),
          end: String(cur.end_date || "").slice(0, 10),
          tags: tags.filter((t) => EVENT_TAGS.includes(t)),
          perks: String(cur.perks || ""),
          goods: String(cur.goods || ""),
          links: parseLinksText(String(cur.links || "")),
          intro: String(cur.intro || ""),
          images: splitImages(cur.images),
          check: tags.includes(TAG_CHECK) ? { raw: rawFromNote(cur.note) } : null,
          title: `${cur.work || ""} · ${cur.cafe_name || ""}`,
        };
        const [cafes, cards, lvOf] = await Promise.all([currentCafes(), historyCards(all), lvOfNick()]);
        byWork = charactersByWork(cafes);
        history = cards;
        histLv = Object.fromEntries(all.map((r) => [Number(r.revision), lvOf(String(r.editor || ""))]));
      }
    } catch (e) {
      console.error("[detail] 수정하기 기록을 읽지 못함", e instanceof Error ? e.message : e);
    }
  }
  const reviewCount = threads.reduce((a, t) => a + 1 + t.replies.length, 0);
  const rated = threads.filter((t) => t.post.kind === "다녀온 후기" && t.post.rating).map((t) => t.post.rating as number);
  const avg = rated.length ? Math.round((rated.reduce((a, b) => a + b, 0) / rated.length) * 10) / 10 : 0;
  const sims = similar(p, popups, today);
  const near = nearby(p, popups, today);
  const title = `${p.work} · ${p.name}`;
  // 일정 칸 둘째 줄: 남은 날 (운영 시간은 데이터에 없어서 넣지 않는다)
  const left =
    !p.start || !p.end
      ? "공식 공지에서 기간을 확인해 주세요"
      : p.end < today
        ? "끝난 팝업이에요"
        : p.start > today
          ? `시작까지 ${daysBetween(today, p.start)}일`
          : p.tags.includes("상시")
            ? "상시 운영"
            : p.end === today
              ? "오늘까지예요"
              : `끝나는 날까지 ${daysBetween(today, p.end)}일`;

  const hero = (
    <div className="ad-hero">
      <div className="ad-hero-pic">
        <Gallery images={p.images} alt={`${p.work} 포스터`} />
      </div>
      <div className="ad-hero-info">
        <div className="ad-head">
          <div className="ad-badges">
            <span className={`ad-state${state === "종료" ? " ended" : ""}`}>{state}</span>
            {p.area && (
              <span className="ad-area" style={{ background: color }}>
                {p.area}
              </span>
            )}
          </div>
          <div className="ad-title-row">
            <h1 className="ad-title">{p.work}</h1>
            <ShareButtons
              id={p.id}
              title={title}
              text={`${p.start} ~ ${p.end} · ${p.address}`}
              image={p.images[0] || PLACEHOLDER_POSTER}
            />
            <BookmarkButton cafeId={p.id} variant="detail" />
          </div>
          {p.characters && <div className="ad-chars">{p.characters}</div>}
          {rated.length > 0 && (
            <div className="ad-avg">
              <span className="ad-stars" aria-hidden>
                <span>★★★★★</span>
                <span style={{ width: `${(avg / 5) * 100}%` }}>★★★★★</span>
              </span>
              <strong>{avg.toFixed(1)}</strong>
              <span>다녀온 후기 {rated.length}개 평균</span>
            </div>
          )}
        </div>

        <section className="ad-check" aria-labelledby="ad-check-h">
          <h2 id="ad-check-h" className="sr-only">
            방문 전 확인
          </h2>
          <div className="ad-box" role="group" aria-label="위치">
            <PinIcon />
            <div>
              <strong className="dcafe">{p.name}</strong>
              <span className="daddr">{p.address || "-"}</span>
              <a href={mapLink(p)} target="_blank" rel="noopener noreferrer">
                지도에서 확인하기
              </a>
            </div>
          </div>
          <div className="ad-box" role="group" aria-label="일정">
            <CalendarIcon />
            <div>
              <strong>{p.start && p.end === ALWAYS_END ? `${dayLabel(p.start, true)} ~ 상시` : detailSpan(p)}</strong>
              <span>
                {left}
                {isReserve(p) ? " · 사전 예약" : ""}
              </span>
            </div>
          </div>
        </section>

        <section className="ad-sec" aria-labelledby="ad-gift-h">
          <h2 id="ad-gift-h" className="ad-h2">
            혜택
          </h2>
          {groups.some(([, xs]) => xs.length) ? (
            <ul className="ad-chips">
              {groups.flatMap(([name, xs]) =>
                xs.map((x, i) => (
                  <li key={`${name}-${x}-${i}`} className={name === "특전" ? "perk" : undefined}>
                    <b>{name}</b>
                    {x}
                  </li>
                )),
              )}
            </ul>
          ) : (
            <div className="ad-none">등록된 특전·굿즈가 없어요</div>
          )}
        </section>

        {p.links.length > 0 && (
          <section className="ad-sec" aria-labelledby="ad-link-h">
            <h2 id="ad-link-h" className="ad-h2">
              참고 웹사이트
            </h2>
            <div className="ad-links">
              {p.links.map((u) => (
                <a key={u} href={u} target="_blank" rel="noopener noreferrer nofollow">
                  <span>{hostOf(u)}</span>
                  <OpenIcon />
                </a>
              ))}
            </div>
          </section>
        )}

        {p.intro && (
          <section className="ad-sec" aria-labelledby="ad-intro-h">
            <h2 id="ad-intro-h" className="ad-h2">
              팝업 소개
            </h2>
            <div className="ad-intro">
              <IntroBody text={p.intro} />
            </div>
          </section>
        )}
      </div>
    </div>
  );

  const mini = (
    <div className="ad-mini">
      <img src={p.images[0] || PLACEHOLDER_POSTER} alt="" />
      <div>
        <span>팝업 상세 · {p.name}</span>
        <h1 className="ad-title">{p.work}</h1>
      </div>
    </div>
  );

  return (
    <article className="ad">
      <RememberRecent id={p.id} />
      <SideTabs
        cafeId={p.id}
        reviewCount={reviewCount}
        hero={hero}
        mini={mini}
        review={
          <Reviews
            cafeId={p.id}
            threads={threads}
            me={me ? { nick: String(me.row.nickname || ""), avatar: String(me.row.avatar || "") } : null}
            stamps={stamps}
          />
        }
        edit={<EditPanel entryId={p.id} data={edit} byWork={byWork} history={history} histLv={histLv} />}
      />

      {(sims.length > 0 || near.length > 0) && (
        <div className="ad-similar">
          {sims.length > 0 && (
            <section className="simsec">
              <h2 className="sim-head">
                <SparkleIcon />
                비슷한 팝업
              </h2>
              <HScroll className="sim-row" label="비슷한 팝업">
                {sims.map((r) => (
                  <SimCard key={r.id} p={toItem(r)} today={today} title={r.name || r.work} />
                ))}
              </HScroll>
            </section>
          )}
          {near.length > 0 && (
            <section className="simsec">
              <h2 className="sim-head">
                <PinIcon />이 근처 다른 팝업
              </h2>
              <HScroll className="sim-row" label="이 근처 다른 팝업">
                {near.map(([r, d]) => (
                  <SimCard key={r.id} p={toItem(r)} today={today} title={r.work} meta={`${r.name} · ${kmText(d)}`} />
                ))}
              </HScroll>
            </section>
          )}
        </div>
      )}
    </article>
  );
}
