"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { posterBg } from "../cards";
import { RankChip, RankStamp } from "../RankStamp";
import { TalkLine } from "./Icons2";
import SecHead from "./SecHead";

// 홈 맨 아래 '꿀팁 가득! 실시간 후기' (11/26 사용자 시안).
//  PC: 왼쪽 '오늘의 꿀팁' 큰 카드(가장 최근 사진 후기, 없으면 가장 최근 후기) + 오른쪽 종류 칩 · 최신순 타임라인
//  모바일: 대화창처럼 최근 후기 3개 → 오늘 후기 많은 팝업 칩 3개 → '다녀왔다면 후기 쓰고 도장 받기'
// 종류 칩은 실제 리뷰 종류(다녀온 후기 · 기대평 · 기타)로 — 시안의 꿀팁 · 웨이팅 · 굿즈는 예시이고 그런 분류는 저장돼 있지 않다.
// '후기 전체 보기' · '후기 더보기'는 두지 않는다 (사용자 요청).

export type FeedCard = {
  id: string;
  kind: string;
  name: string;
  avatar: string;
  lv: number;
  when: string;
  stars: number;
  body: string;
  photos: string[];
  popupId: string;
  popup: string;
  poster: string;
  place: string; // '마포 · ~ 12.15'
};
export type FeedPop = { id: string; name: string; poster: string; n: number; label: string };

const LIST_MAX = 6;
const MOBILE_MAX = 3;
const KIND_CLASS: Record<string, string> = { "다녀온 후기": "visit", 기대평: "hope", 기타: "etc" };
const two = (n: number) => String(n).padStart(2, "0");

/** 처음(서버와 같은 글자)엔 '11.25 14:30', 화면이 뜬 뒤에는 '10분 전' */
function whenText(stamp: string, now: number | null): string {
  const t = Date.parse(stamp);
  if (!t) return "";
  const k = new Date(t + 9 * 3600_000);
  const day = `${two(k.getUTCMonth() + 1)}.${two(k.getUTCDate())}`;
  if (now === null) return `${day} ${two(k.getUTCHours())}:${two(k.getUTCMinutes())}`;
  const min = Math.floor((now - t) / 60_000);
  if (min < 1) return "방금";
  if (min < 60) return `${min}분 전`;
  if (min < 60 * 24) return `${Math.floor(min / 60)}시간 전`;
  if (min < 60 * 24 * 7) return `${Math.floor(min / (60 * 24))}일 전`;
  return day;
}

const byNew = (a: FeedCard, b: FeedCard) => b.when.localeCompare(a.when);

function Kind({ k }: { k: string }) {
  return k ? <span className={`ah-fd-kind ${KIND_CLASS[k] ?? "etc"}`}>{k}</span> : null;
}

function Stars({ n }: { n: number }) {
  return n > 0 ? (
    <span className="ah-fd-stars" role="img" aria-label={`5점 만점에 ${n}점`}>
      {"★".repeat(n)}
      {"☆".repeat(5 - n)}
    </span>
  ) : null;
}

export default function ReviewFeed({
  cards,
  kinds,
  pops,
  writeHref,
}: {
  cards: FeedCard[];
  kinds: string[];
  pops: FeedPop[];
  writeHref: string;
}) {
  const [kind, setKind] = useState("전체");
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => setNow(Date.now()), []);

  const all = [...cards].sort(byNew);
  const list = kind === "전체" ? all : all.filter((c) => c.kind === kind);
  const top = list.find((c) => c.photos.length) ?? list[0];
  const rest = list.filter((c) => c !== top).slice(0, LIST_MAX);
  const mobile = all.slice(0, MOBILE_MAX);

  return (
    <section className="ah-sec ah-tip" aria-labelledby="ah-tip-h">
      <SecHead id="ah-tip-h" title="꿀팁 가득! 실시간 후기 모음" icon={<TalkLine />}>
        <span className="ah-fd-live" aria-label="실시간">
          <i aria-hidden />
          LIVE
        </span>
      </SecHead>

      {!cards.length ? (
        <div className="ah-empty">아직 후기가 없어요. 다녀온 팝업에 첫 후기를 남겨 보세요.</div>
      ) : (
        <>
          {/* ---------- PC: 큰 꿀팁 카드 + 오른쪽 타임라인 ---------- */}
          <div className="ah-fd pc-only">
            {top ? (
              <article className="ah-fd-top">
                <div className="ah-fd-hero" style={top.photos[0] ? undefined : posterBg(top.poster)}>
                  {top.photos[0] && <img src={top.photos[0]} alt="후기 사진" loading="lazy" referrerPolicy="no-referrer" />}
                  <span className="ah-fd-badge">
                    <img src="/mascot.png" alt="" />
                    오늘의 꿀팁
                  </span>
                  {top.photos.length > 1 && (
                    <span className="ah-fd-thumbs">
                      {top.photos.slice(1, 3).map((src, i) => (
                        <span key={src} className="ah-fd-th">
                          <img src={src} alt="" loading="lazy" referrerPolicy="no-referrer" />
                          {i === 1 && top.photos.length > 3 && <b>+{top.photos.length - 3}</b>}
                        </span>
                      ))}
                    </span>
                  )}
                </div>
                <div className="ah-fd-in">
                  <div className="ah-fd-meta">
                    <Kind k={top.kind} />
                    <Stars n={top.stars} />
                    <span className="ah-fd-who">
                      {top.lv > 0 ? <RankChip lv={top.lv} /> : null}
                      <strong>{top.name}</strong>
                    </span>
                    <span className="ah-fd-time" suppressHydrationWarning>
                      {whenText(top.when, now)}
                    </span>
                  </div>
                  <p className="ah-fd-body">{top.body}</p>
                  <Link href={`/popup/${top.popupId}`} className="ah-fd-pop" prefetch={false}>
                    <span className="ah-fd-pp" style={posterBg(top.poster)} />
                    <strong>{top.popup}</strong>
                    <span>{top.place}</span>
                  </Link>
                </div>
              </article>
            ) : (
              <div className="ah-empty ah-fd-top">아직 &apos;{kind}&apos; 후기가 없어요.</div>
            )}

            <div className="ah-fd-side">
              <div className="ah-chips" role="group" aria-label="후기 종류">
                {["전체", ...kinds].map((k) => (
                  <button key={k} type="button" className="ah-chip" aria-pressed={kind === k} onClick={() => setKind(k)}>
                    {k}
                  </button>
                ))}
              </div>
              {rest.length ? (
                <ol className="ah-fd-line">
                  {rest.map((c, i) => (
                    <li key={c.id} className={i === 0 ? "new" : undefined}>
                      <Link href={`/popup/${c.popupId}`} prefetch={false}>
                        <span
                          className="ah-fd-lth"
                          style={c.photos[0] ? { backgroundImage: `url("${c.photos[0]}")` } : posterBg(c.poster)}
                        />
                        <span className="ah-fd-ltx">
                          <span className="ah-fd-lmeta">
                            <Kind k={c.kind} />
                            <span suppressHydrationWarning>
                              {whenText(c.when, now)} · {c.popup}
                            </span>
                          </span>
                          <span className="ah-fd-lbody">{c.body}</span>
                        </span>
                      </Link>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="ah-fd-none">다른 후기가 아직 없어요.</p>
              )}
            </div>
          </div>

          {/* ---------- 모바일: 대화창 ---------- */}
          <div className="ah-fm m-only">
            <div className="ah-fm-chat">
              <div className="ah-fm-hi">
                <span className="ah-fm-bot">
                  <img src="/mascot.png" alt="" />
                </span>
                <span className="ah-fm-say">방금 올라온 꿀팁이에요!</span>
              </div>
              {mobile.map((c) => (
                <div key={c.id} className="ah-fm-msg">
                  <span className="ah-fm-av">
                    <img src={c.avatar} alt="" referrerPolicy="no-referrer" loading="lazy" />
                    {c.lv > 0 && (
                      <span className="ah-fm-rk">
                        <RankStamp lv={c.lv} size={20} />
                      </span>
                    )}
                  </span>
                  <div className="ah-fm-box">
                    <div className="ah-fm-who">
                      <strong>{c.name}</strong>
                      <span suppressHydrationWarning>{whenText(c.when, now)}</span>
                    </div>
                    <Link href={`/popup/${c.popupId}`} className="ah-fm-card" prefetch={false}>
                      <span className="ah-fm-tag">
                        <Kind k={c.kind} />
                        <strong>{c.popup}</strong>
                      </span>
                      <span className="ah-fm-body">{c.body}</span>
                      {c.photos.length > 0 && (
                        <span className="ah-fm-ph">
                          {c.photos.slice(0, 3).map((src) => (
                            <img key={src} src={src} alt="" loading="lazy" referrerPolicy="no-referrer" />
                          ))}
                        </span>
                      )}
                    </Link>
                  </div>
                </div>
              ))}
            </div>
            {pops.length > 0 && (
              <div className="ah-fm-pops">
                {pops.map((p) => (
                  <Link key={p.id} href={`/popup/${p.id}`} className="ah-fm-pop" prefetch={false}>
                    <span className="ah-fm-pp" style={posterBg(p.poster)} />
                    <span className="ah-fm-pt">
                      <strong>{p.name}</strong>
                      <span>
                        {p.label} {p.n}
                      </span>
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>
          <Link href={writeHref} className="ah-fd-cta m-only">
            <img src="/mascot.png" alt="" />
            다녀왔다면 후기 쓰고 도장 받기
          </Link>
        </>
      )}
    </section>
  );
}
