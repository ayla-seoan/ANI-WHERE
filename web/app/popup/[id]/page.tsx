import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPopup, getPopupData } from "@/lib/data";
import {
  APP_URL,
  detailSpan,
  detailState,
  hostOf,
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
import { BagIcon, ChatIcon, GiftIcon, PartyIcon, PinIcon, SparkleIcon, StarIcon } from "@/components/Icons";

export const revalidate = 600;
// 빌드 때 미리 만들지 않고, 처음 열릴 때 만들어 10분 캐시한다 (ISR)
export const dynamicParams = true;
export async function generateStaticParams() {
  return [];
}

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
  const { popups } = await getPopupData();
  const p = popups.find((x) => x.id === id);
  if (!p) notFound();

  const today = todayKST();
  const state = detailState(p, today);
  const color = regionColor(p.city);
  const groups: [string, React.ReactNode, string[]][] = [
    ["특전", <GiftIcon key="g" />, p.perks],
    ["굿즈", <BagIcon key="b" />, p.goods],
    ["이벤트", <PartyIcon key="p" />, p.tags.filter((t) => t !== "상시" && t !== "기간 확인 필요")],
  ];
  const sims = similar(p, popups, today);
  const near = nearby(p, popups, today);
  const appLink = `${APP_URL}/?cafe=${encodeURIComponent(p.id)}`;

  return (
    <article className="detail">
      <div className="detail-cols">
        <div className="detail-left">
          <Gallery images={p.images} alt={`${p.work} 포스터`} />

          <div className="dhead dtop">
            <span className="dregion" style={{ color }}>
              {p.area && (
                <>
                  <PinIcon />
                  {p.area}
                </>
              )}
            </span>
            <span className={`dstate${state === "종료" ? " ended" : ""}`}>{state}</span>
          </div>
          <h1 className="dtitle">{p.work}</h1>
          {p.characters && (
            <div className="dsub">
              <span className="dchars">{p.characters}</span>
            </div>
          )}

          <div className="dinfo">
            <div className="dinfo-title">방문 전 확인</div>
            <div className="drow">
              <div className="dlabel">위치</div>
              <div className="dval">
                <div className="dcafe">{p.name}</div>
                <div className="daddr">{p.address || "-"}</div>
              </div>
              <a className="dbtn" href={mapLink(p)} target="_blank" rel="noopener noreferrer">
                <PinIcon />
                지도에서 확인하기
              </a>
            </div>
            <div className="drow">
              <div className="dlabel">일정</div>
              <div className="dval">{detailSpan(p)}</div>
            </div>
          </div>

          <section className="dsec">
            <h2 className="dsec-title">혜택</h2>
            {groups.some(([, , xs]) => xs.length) ? (
              groups
                .filter(([, , xs]) => xs.length)
                .map(([name, icon, xs]) => (
                  <div key={name} className="dgroup">
                    <span className="dpill">{name}</span>
                    <ul className="dbox">
                      {xs.map((x, i) => (
                        <li key={`${x}-${i}`}>
                          {icon}
                          <span>{x}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))
            ) : (
              <div className="dnone">등록된 특전·굿즈가 없어요</div>
            )}
          </section>

          {p.links.length > 0 && (
            <section className="dsec">
              <h2 className="dsec-title">참고 웹사이트</h2>
              {p.links.map((u) => (
                <a key={u} className="dlink" href={u} target="_blank" rel="noopener noreferrer nofollow">
                  <span className="dlink-text">
                    <span className="dlink-title">{hostOf(u)}</span>
                    <span className="dlink-url">{u}</span>
                  </span>
                  <span className="dlink-go" aria-hidden>
                    ↗
                  </span>
                </a>
              ))}
            </section>
          )}

          {p.intro && (
            <section className="dsec">
              <h2 className="dsec-title">팝업 소개</h2>
              <div className="dintro">
                <IntroBody text={p.intro} />
              </div>
            </section>
          )}
        </div>

        <aside className="detail-side" aria-label="리뷰·북마크 안내">
          <div className="side-tabs">
            <span className="on">
              <ChatIcon />
              리뷰 {p.rating?.n ?? 0}
            </span>
          </div>
          <div className="side-box">
            {p.rating ? (
              <div className="rv-avg">
                <span className="rv-avg-num">{p.rating.avg.toFixed(1)}</span>
                <span className="rv-avg-stars" aria-label={`별점 ${p.rating.avg.toFixed(1)}점`}>
                  <span className="rv-avg-bg">
                    {[0, 1, 2, 3, 4].map((k) => (
                      <StarIcon key={k} />
                    ))}
                  </span>
                  <span className="rv-avg-fg" style={{ width: `${(p.rating.avg / 5) * 100}%` }}>
                    {[0, 1, 2, 3, 4].map((k) => (
                      <StarIcon key={k} />
                    ))}
                  </span>
                </span>
                <span className="rv-avg-cnt">다녀온 후기 {p.rating.n}개</span>
              </div>
            ) : (
              <p className="side-note">아직 별점이 없어요. 다녀온 후기나 기대하는 점을 처음으로 남겨 보세요.</p>
            )}
            <p className="side-note">리뷰 쓰기 · 북마크 · 정보 수정은 ANI:WHERE 앱에서 할 수 있어요.</p>
            <a className="side-cta" href={appLink} target="_blank" rel="noopener noreferrer">
              리뷰·북마크는 ANI:WHERE 앱에서
            </a>
          </div>
        </aside>
      </div>

      {(sims.length > 0 || near.length > 0) && (
        <div className="similar">
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
