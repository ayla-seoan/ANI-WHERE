"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { PLACEHOLDER_POSTER } from "@/lib/popup";
import { ExpandMore } from "../Icons";

// 내 캘린더 가운데 칸 (앱 render_box_view): 북마크 · 다녀온 팝업(내가 쓴 다녀온 후기) · 최근 본 팝업(이 브라우저).
export type KeepItem = {
  id: string;
  work: string;
  name: string;
  start: string;
  end: string;
  poster: string;
};
type Visited = {
  item: KeepItem;
  reviews: { rating: number; body: string; when: string }[];
};

export const RECENT_KEY = "aw_recent";
export const RECENT_MAX = 10;
const BOX_PAGE = 10; // 북마크 · 다녀온 팝업: 처음 10건, 더 있으면 '+N건 더보기' 로 10건씩 (앱 BOX_PAGE, 11/19 요청)

function More({
  total,
  n,
  onMore,
}: {
  total: number;
  n: number;
  onMore: () => void;
}) {
  if (total <= n) return null;
  return (
    <div className="list-more bx-more">
      <button type="button" onClick={onMore}>
        <ExpandMore />+{total - n}건 더보기
      </button>
    </div>
  );
}

/** 상세를 열 때 부른다: 최근 본 팝업 (이 브라우저에만, 최신 10개) */
export function rememberRecent(id: string) {
  try {
    const cur = (localStorage.getItem(RECENT_KEY) || "")
      .split(",")
      .filter((x) => x && x !== id);
    localStorage.setItem(
      RECENT_KEY,
      [id, ...cur].slice(0, RECENT_MAX).join(","),
    );
  } catch {
    /* 저장이 막히면 기록하지 않는다 */
  }
}

const md = (s: string) =>
  s ? `${Number(s.slice(5, 7))}.${Number(s.slice(8, 10))}` : "";

function Card({
  p,
  today,
  children,
}: {
  p: KeepItem;
  today: string;
  children?: React.ReactNode;
}) {
  const state = !p.start
    ? ""
    : p.end && p.end < today
      ? "종료"
      : p.start > today
        ? "예정"
        : "진행 중";
  return (
    <Link href={`/popup/${p.id}`} className="bx-link">
      <div className={`bxc${state === "예정" ? " soon" : ""}`}>
        <img
          className="pst"
          src={p.poster || PLACEHOLDER_POSTER}
          alt=""
          loading="lazy"
          onError={(e) => {
            e.currentTarget.src = PLACEHOLDER_POSTER;
          }}
        />
        <div className="t">
          <span className={`st${state === "종료" ? " end" : ""}`}>{state}</span>
          <div className="w">{p.work}</div>
          <div className="c">{p.name}</div>
          <div className="d">
            {p.start
              ? `${md(p.start)} ~ ${p.end ? md(p.end) : "상시"}`
              : "기간 확인 필요"}
          </div>
        </div>
      </div>
      {children}
    </Link>
  );
}

function Empty({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="bx-empty">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.6}
        aria-hidden
      >
        <path d="M6 4h12v16l-6-4-6 4V4z" />
      </svg>
      <h4>{title}</h4>
      <p>{hint}</p>
    </div>
  );
}

export default function KeepBox({
  favs,
  visited,
  all,
  today,
}: {
  favs: KeepItem[];
  visited: Visited[];
  all: KeepItem[];
  today: string;
}) {
  const [tab, setTab] = useState<"fav" | "visited" | "recent">("fav");
  const [recent, setRecent] = useState<KeepItem[]>([]);
  const [nFav, setNFav] = useState(BOX_PAGE);
  const [nVisited, setNVisited] = useState(BOX_PAGE);
  useEffect(() => {
    try {
      const ids = (localStorage.getItem(RECENT_KEY) || "")
        .split(",")
        .filter(Boolean);
      setRecent(
        ids
          .map((id) => all.find((p) => p.id === id))
          .filter((p): p is KeepItem => !!p),
      );
    } catch {
      setRecent([]);
    }
  }, [all]);
  return (
    <>
      <div className="box-tabs" role="tablist">
        {(
          [
            ["fav", "북마크"],
            ["visited", "다녀온 팝업"],
            ["recent", "최근 본 팝업"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={tab === k}
            className={tab === k ? "on" : ""}
            onClick={() => setTab(k)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "fav" && (
        <>
          <div className="bx-tip">
            북마크한 팝업은 오픈·종료 3일 전부터 알림으로 알려 드려요.
          </div>
          {favs.length ? (
            <>
              {favs.slice(0, nFav).map((p) => (
                <Card key={p.id} p={p} today={today} />
              ))}
              <More
                total={favs.length}
                n={nFav}
                onMore={() => setNFav(nFav + BOX_PAGE)}
              />
            </>
          ) : (
            <Empty
              title="아직 북마크한 팝업이 없어요"
              hint="리스트나 상세에서 북마크 아이콘을 누르면 여기에 모여요."
            />
          )}
        </>
      )}
      {tab === "visited" && (
        <>
          <div className="bx-tip">
            &apos;다녀온 후기&apos;를 쓴 팝업이 여기에 모여요. 쓴 후기도 함께
            보여요.
          </div>
          {visited.length ? (
            <>
              {visited.slice(0, nVisited).map((v) => (
                <Card key={v.item.id} p={v.item} today={today}>
                  {v.reviews.map((r, i) => (
                    <div key={i} className="bxr">
                      <span className="stars">
                        {r.rating
                          ? "★".repeat(r.rating) + "☆".repeat(5 - r.rating)
                          : ""}
                      </span>
                      <div>{r.body}</div>
                    </div>
                  ))}
                </Card>
              ))}
              <More
                total={visited.length}
                n={nVisited}
                onMore={() => setNVisited(nVisited + BOX_PAGE)}
              />
            </>
          ) : (
            <Empty
              title="다녀온 팝업이 없어요"
              hint="팝업 상세의 리뷰에서 '다녀온 후기'를 쓰면 여기에 기록돼요."
            />
          )}
        </>
      )}
      {tab === "recent" && (
        <>
          <div className="bx-tip">
            이 브라우저에서 최근에 연 팝업 상세예요 (최대 {RECENT_MAX}개).
          </div>
          {recent.length ? (
            recent.map((p) => <Card key={p.id} p={p} today={today} />)
          ) : (
            <Empty
              title="최근 본 팝업이 없어요"
              hint="리스트나 지도에서 팝업을 눌러 상세를 열면 여기에 남아요."
            />
          )}
        </>
      )}
    </>
  );
}
