"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { posterBg } from "../cards";
import { RankChip } from "../RankStamp";
import { TalkLine } from "./Icons2";
import SecHead from "./SecHead";

// 후기 모음 (A-Home): 높이가 제각각인 3단(모바일 2단) 카드. 제목 오른쪽 칩은 실제 리뷰 종류(다녀온 후기 · 기대평 · 기타)로 거른다 —
// 시안의 '꿀팁 · 웨이팅 · 특전 소진 · 굿즈'는 예시이고 그런 분류는 저장돼 있지 않다. '후기 더보기'는 받아 둔 것을 6개씩 더 펼친다.

export type WallCard = {
  id: string;
  kind: string;
  name: string;
  avatar: string;
  lv: number;
  when: string;
  stars: number;
  body: string;
  photo: string;
  more: number;
  popupId: string;
  popup: string;
  poster: string;
  state: string;
  stateColor: string;
};

const STEP = 6;
const KIND_CLASS: Record<string, string> = { "다녀온 후기": "visit", 기대평: "hope", 기타: "etc" };
const two = (n: number) => String(n).padStart(2, "0");

/** 서버와 브라우저가 같은 글자를 내도록 처음엔 날짜('11.25 14:30', 한국 시간), 화면이 뜬 뒤에는 '10분 전' */
function whenText(stamp: string, now: number | null): string {
  const t = Date.parse(stamp);
  if (!t) return "";
  const k = new Date(t + 9 * 3600_000);
  const day = `${two(k.getUTCMonth() + 1)}.${two(k.getUTCDate())}`;
  if (now === null) return `${day} ${two(k.getUTCHours())}:${two(k.getUTCMinutes())}`;
  const min = Math.floor((now - t) / 60_000);
  if (min < 1) return "방금 전";
  if (min < 60) return `${min}분 전`;
  if (min < 60 * 24) return `${Math.floor(min / 60)}시간 전`;
  if (min < 60 * 24 * 7) return `${Math.floor(min / (60 * 24))}일 전`;
  return day;
}

export default function ReviewWall({ cards, kinds }: { cards: WallCard[]; kinds: string[] }) {
  const [kind, setKind] = useState("전체");
  const [n, setN] = useState(STEP);
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => setNow(Date.now()), []);

  const list = kind === "전체" ? cards : cards.filter((c) => c.kind === kind);
  const shown = list.slice(0, n);
  return (
    <section className="ah-sec ah-tip" aria-labelledby="ah-tip-h">
      <SecHead id="ah-tip-h" title="꿀팁 가득! 실시간 후기 모음" icon={<TalkLine />}>
        {cards.length > 0 && (
          <div className="ah-chips" role="group" aria-label="후기 종류">
            {["전체", ...kinds].map((k) => (
              <button
                key={k}
                type="button"
                className="ah-chip"
                aria-pressed={kind === k}
                onClick={() => {
                  setKind(k);
                  setN(STEP);
                }}
              >
                {k}
              </button>
            ))}
          </div>
        )}
      </SecHead>
      {!cards.length ? (
        <div className="ah-empty">아직 후기가 없어요. 다녀온 팝업에 첫 후기를 남겨 보세요.</div>
      ) : !list.length ? (
        <div className="ah-empty">아직 &apos;{kind}&apos; 후기가 없어요.</div>
      ) : (
        <div className="ah-wall">
          {shown.map((c) => (
            <article key={c.id} className="ah-rv">
              {c.photo && (
                <div className="ah-rv-ph">
                  <img src={c.photo} alt="후기 사진" loading="lazy" referrerPolicy="no-referrer" />
                  {c.more > 0 && <span className="ah-rv-cnt">+{c.more}</span>}
                </div>
              )}
              <div className="ah-rv-in">
                {c.kind && <span className={`ah-rv-kind ${KIND_CLASS[c.kind] ?? "etc"}`}>{c.kind}</span>}
                <div className="ah-rv-who">
                  <img
                    className="ah-rv-av"
                    src={c.avatar}
                    alt=""
                    width={26}
                    height={26}
                    referrerPolicy="no-referrer"
                    loading="lazy"
                  />
                  <strong>{c.name}</strong>
                  <RankChip lv={c.lv} />
                  <span className="ah-rv-time" suppressHydrationWarning>
                    {whenText(c.when, now)}
                  </span>
                </div>
                {c.stars > 0 && (
                  <span className="ah-rv-stars" role="img" aria-label={`5점 만점에 ${c.stars}점`}>
                    {"★".repeat(c.stars)}
                    {"☆".repeat(5 - c.stars)}
                  </span>
                )}
                <p className="ah-rv-body">{c.body}</p>
                <Link href={`/popup/${c.popupId}`} className="ah-rv-pop" prefetch={false}>
                  <span className="ah-rv-pp" style={posterBg(c.poster)} />
                  <span className="ah-rv-pn">{c.popup}</span>
                  <span className={`ah-st ${c.stateColor}`}>{c.state}</span>
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
      {list.length > n && (
        <button type="button" className="ah-morebtn" onClick={() => setN((v) => v + STEP)}>
          후기 더보기
        </button>
      )}
    </section>
  );
}
