import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getPopup } from "@/lib/data";
import { APP_URL, badgeOf, hostOf, periodText, PLACEHOLDER_POSTER, todayKST, type Popup } from "@/lib/popup";
import PosterImg from "@/components/PosterImg";
import { BackIcon, EditIcon, LinkIcon, MapIcon } from "@/components/Icons";

export const revalidate = 600;
// 빌드 때 미리 만들지 않고, 처음 열릴 때 만들어 10분 캐시한다 (ISR)
export const dynamicParams = true;
export async function generateStaticParams() {
  return [];
}

const INTRO_MAX = 600;

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

function mapLinks(p: Popup) {
  const links: { href: string; label: string }[] = [];
  if (p.lat !== null && p.lng !== null) {
    links.push({
      href: `https://map.kakao.com/link/map/${encodeURIComponent(p.name)},${p.lat},${p.lng}`,
      label: "지도에서 보기",
    });
  }
  const q = p.address || p.name;
  links.push({
    href: `https://map.kakao.com/?q=${encodeURIComponent(q)}`,
    label: links.length ? "주소로 검색" : "지도에서 보기",
  });
  return links;
}

export default async function PopupPage({ params }: Props) {
  const { id } = await params;
  if (!validId(id)) notFound();
  const p = await getPopup(id);
  if (!p) notFound();

  const today = todayKST();
  const badge = badgeOf(p, today);
  const introLong = p.intro.length > INTRO_MAX;

  return (
    <article>
      <Link href="/" className="back">
        <BackIcon />
        목록으로
      </Link>
      <div className="detail">
        <div className="poster-col">
          <div className="detail-poster">
            <PosterImg src={p.images[0] || PLACEHOLDER_POSTER} alt={`${p.work} 포스터`} eager />
          </div>
          {p.images.length > 1 && (
            <div className="thumbs" aria-label="이미지 더 보기">
              {p.images.slice(1, 12).map((src, i) => (
                <a key={src} href={src} target="_blank" rel="noopener noreferrer" aria-label={`이미지 ${i + 2} 크게 보기`}>
                  <PosterImg src={src} alt="" />
                </a>
              ))}
            </div>
          )}
        </div>

        <div>
          <span className={`badge ${badge.tone}`}>{badge.label}</span>{" "}
          <span className="badge">{p.region}</span>
          <h1>{p.work}</h1>
          <p className="cafe">{p.name}</p>
          {p.characters && <p className="chars">{p.characters}</p>}

          <dl className="info">
            <div className="info-row">
              <dt>기간</dt>
              <dd>{periodText(p, today)}</dd>
            </div>
            <div className="info-row">
              <dt>위치</dt>
              <dd>
                {p.address || "주소 미정"}
                <div className="map-links">
                  {mapLinks(p).map((l, i) => (
                    <a
                      key={l.href}
                      className={`btn${i === 0 ? "" : " ghost"}`}
                      href={l.href}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <MapIcon />
                      {l.label}
                    </a>
                  ))}
                </div>
              </dd>
            </div>
            {p.rating && (
              <div className="info-row">
                <dt>별점</dt>
                <dd className="rating">
                  <span className="star" aria-hidden>
                    ★
                  </span>{" "}
                  {p.rating.avg.toFixed(1)} <small>({p.rating.n}명)</small>
                </dd>
              </div>
            )}
          </dl>

          {p.perks.length > 0 && (
            <section className="section">
              <h2>특전</h2>
              <ul className="tagchips">
                {p.perks.map((x, i) => (
                  <li key={`${x}-${i}`}>{x}</li>
                ))}
              </ul>
            </section>
          )}

          {p.goods.length > 0 && (
            <section className="section">
              <h2>굿즈</h2>
              <ul className="tagchips goods">
                {p.goods.map((x, i) => (
                  <li key={`${x}-${i}`}>{x}</li>
                ))}
              </ul>
            </section>
          )}

          {p.intro && (
            <section className="section">
              <h2>소개</h2>
              {introLong ? (
                <details className="more">
                  <summary>
                    <span className="intro intro-preview">{p.intro.slice(0, INTRO_MAX).trimEnd()}…</span>
                    <span className="more-label open-label">전체 소개 펼치기</span>
                    <span className="more-label close-label">접기</span>
                  </summary>
                  <p className="intro">{p.intro}</p>
                </details>
              ) : (
                <p className="intro">{p.intro}</p>
              )}
            </section>
          )}

          {p.links.length > 0 && (
            <section className="section">
              <h2>참고 링크</h2>
              <ul className="links">
                {p.links.map((u) => (
                  <li key={u}>
                    <a href={u} target="_blank" rel="noopener noreferrer nofollow">
                      <LinkIcon />
                      <span>{hostOf(u)}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="app-cta">
            <p>리뷰·수정은 ANI:WHERE 앱에서</p>
            <a className="btn" href={`${APP_URL}/?cafe=${encodeURIComponent(p.id)}`} target="_blank" rel="noopener noreferrer">
              <EditIcon />
              앱에서 열기
            </a>
          </div>
        </div>
      </div>
    </article>
  );
}
