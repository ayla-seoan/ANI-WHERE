"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { stateOf } from "@/lib/popup";
import { areaFill, posterBg } from "../cards";
import { RankStamp } from "../RankStamp";
import { RankCard } from "../mypage/RankBits";
import RankGuideLink from "../mypage/RankGuideLink";
import BookmarkButton from "./BookmarkButton";

// 내 캘린더 가운데 칸 (A-Cal · A-MCal · A-MVisited, 앱 render_box_view):
// 북마크 · 다녀온 팝업(내가 쓴 다녀온 후기 = 후기 도장) · 최근 본 팝업(이 브라우저).
export type KeepItem = {
  id: string;
  work: string;
  name: string;
  start: string;
  end: string;
  poster: string;
  /** 지역 칩 (11/20 요청: 지역마다 색) */
  area: string;
  city: string;
  /** 첫 번째 특전 (없으면 '') */
  perk: string;
};
type Visited = {
  item: KeepItem;
  reviews: { rating: number; body: string; when: string }[];
};
export type KeepTab = "fav" | "visited" | "recent";

export const RECENT_KEY = "aw_recent";
export const RECENT_MAX = 10;
const BOX_PAGE = 10; // 북마크 · 다녀온 팝업: 처음 10건, 더 있으면 '+N건 더보기' 로 10건씩 (앱 BOX_PAGE, 11/19 요청)

function More({ total, n, onMore }: { total: number; n: number; onMore: () => void }) {
  if (total <= n) return null;
  return (
    <button type="button" className="am-more" onClick={onMore}>
      +{total - n}건 더보기
    </button>
  );
}

/** 상세를 열 때 부른다: 최근 본 팝업 (이 브라우저에만, 최신 10개) */
export function rememberRecent(id: string) {
  try {
    const cur = (localStorage.getItem(RECENT_KEY) || "").split(",").filter((x) => x && x !== id);
    localStorage.setItem(RECENT_KEY, [id, ...cur].slice(0, RECENT_MAX).join(","));
  } catch {
    /* 저장이 막히면 기록하지 않는다 */
  }
}

const md = (s: string) => (s ? `${Number(s.slice(5, 7))}.${Number(s.slice(8, 10))}` : "");

function periodOf(p: KeepItem, today: string): string {
  if (!p.start) return "기간 확인 필요";
  if (p.end && p.end === today) return "오늘 종료";
  return `${md(p.start)} ~ ${p.end ? md(p.end) : "상시"}`;
}

function Card({
  p,
  today,
  bookmark,
  stampLv,
  children,
}: {
  p: KeepItem;
  today: string;
  bookmark?: boolean;
  /** 다녀온 팝업: 포스터 귀퉁이 40px 도장 (내 지금 랭크 색) */
  stampLv?: number;
  children?: React.ReactNode;
}) {
  const st = stateOf(p, today);
  return (
    <Link href={`/popup/${p.id}`} className="am-card">
      <span className="am-pst" style={posterBg(p.poster)}>
        {!!stampLv && (
          <span className="am-stamp">
            <RankStamp lv={stampLv} size={40} />
          </span>
        )}
      </span>
      <span className="am-body">
        <span className="am-chips">
          {children ? null : <span className={`am-st ${st.color}`}>{st.label}</span>}
          {p.area && (
            <span className="am-area" style={areaFill(p.city)}>
              {p.area}
            </span>
          )}
        </span>
        <span className="am-t">{p.work || p.name}</span>
        <span className="am-sub">
          {p.work ? `${p.name} · ` : ""}
          {periodOf(p, today)}
        </span>
        {children ?? (p.perk && <span className="am-perk">특전 · {p.perk}</span>)}
      </span>
      {bookmark && <BookmarkButton cafeId={p.id} variant="row" />}
    </Link>
  );
}

function Empty({ title, hint, children }: { title: string; hint: string; children?: React.ReactNode }) {
  return (
    <div className="am-empty">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} aria-hidden>
        <path d="M6 4h12v16l-6-4-6 4V4z" />
      </svg>
      <h3>{title}</h3>
      <p>{hint}</p>
      {children}
    </div>
  );
}

export default function KeepBox({
  favs,
  visited,
  all,
  today,
  stamps,
  lv,
  initialTab = "fav",
}: {
  favs: KeepItem[];
  visited: Visited[];
  all: KeepItem[];
  today: string;
  /** 내 후기 도장 수 · 지금 랭크 단계 (0 = 없음) */
  stamps: number;
  lv: number;
  initialTab?: KeepTab;
}) {
  const [tab, setTab] = useState<KeepTab>(initialTab);
  const [recent, setRecent] = useState<KeepItem[]>([]);
  const [nFav, setNFav] = useState(BOX_PAGE);
  const [nVisited, setNVisited] = useState(BOX_PAGE);
  useEffect(() => {
    try {
      const ids = (localStorage.getItem(RECENT_KEY) || "").split(",").filter(Boolean);
      setRecent(ids.map((id) => all.find((p) => p.id === id)).filter((p): p is KeepItem => !!p));
    } catch {
      setRecent([]);
    }
  }, [all]);
  const tabs: [KeepTab, string][] = [
    ["fav", `북마크 ${favs.length}`],
    ["visited", `다녀온 팝업 ${visited.length}`],
    ["recent", "최근 본"],
  ];
  return (
    <>
      <h2 className="sr-only">내 팝업 목록</h2>
      <div className="am-tabs" role="tablist">
        {tabs.map(([k, label]) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </div>
      {tab === "fav" &&
        (favs.length ? (
          <>
            {favs.slice(0, nFav).map((p) => (
              <Card key={p.id} p={p} today={today} bookmark />
            ))}
            <More total={favs.length} n={nFav} onMore={() => setNFav(nFav + BOX_PAGE)} />
          </>
        ) : (
          <Empty title="아직 북마크한 팝업이 없어요" hint="리스트나 상세에서 북마크 아이콘을 누르면 여기에 모여요.">
            <Link href="/list" className="am-cta">
              리스트에서 찾아보기
            </Link>
          </Empty>
        ))}
      {tab === "visited" && (
        <>
          {/* 도장 · 랭크 · 진행 막대만 (11/27 요청: 끝난 팝업 안내 줄은 두지 않는다) */}
          <RankCard stamps={stamps} />
          {visited.length ? (
            <>
              {visited.slice(0, nVisited).map((v) => {
                const top = v.reviews[0];
                return (
                  <Card key={v.item.id} p={v.item} today={today} stampLv={lv || 1}>
                    <span className="am-got">
                      {top?.rating ? <span className="am-stars">{"★".repeat(top.rating) + "☆".repeat(5 - top.rating)}</span> : null}
                      {top?.rating ? " · " : ""}
                      도장 받았어요
                      {top?.when ? <span className="am-when"> · {md(top.when.slice(0, 10))} 후기</span> : null}
                    </span>
                    {v.reviews
                      .filter((r) => r.body)
                      .map((r, i) => (
                        <span key={i} className="am-rv">
                          {r.body}
                        </span>
                      ))}
                  </Card>
                );
              })}
              <More total={visited.length} n={nVisited} onMore={() => setNVisited(nVisited + BOX_PAGE)} />
            </>
          ) : (
            <Empty
              title="다녀온 팝업이 없어요"
              hint="팝업 상세의 리뷰에서 '다녀온 후기'를 쓰면 도장을 받고 여기에 기록돼요."
            >
              <RankGuideLink stamps={stamps} className="am-cta">
                후기 도장 랭크 안내
              </RankGuideLink>
            </Empty>
          )}
        </>
      )}
      {tab === "recent" && (
        <>
          <p className="am-tip">이 브라우저에서 최근에 연 팝업 상세예요 (최대 {RECENT_MAX}개).</p>
          {recent.length ? (
            recent.map((p) => <Card key={p.id} p={p} today={today} bookmark />)
          ) : (
            <Empty title="최근 본 팝업이 없어요" hint="리스트나 지도에서 팝업을 눌러 상세를 열면 여기에 남아요." />
          )}
        </>
      )}
    </>
  );
}
