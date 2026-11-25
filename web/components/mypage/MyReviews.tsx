"use client";
import Link from "next/link";
import { useState } from "react";
import { posterBg } from "../cards";
import { RankStamp } from "../RankStamp";

// 마이페이지 '내가 쓴 후기' (A-MyPage): 누르면 그 팝업 상세로. 도장을 받은 후기(팝업마다 다녀온 후기 1개)에는 40px 도장.
export type MyReviewItem = {
  id: string;
  cafeId: string;
  title: string;
  poster: string;
  kind: string;
  rating: number;
  body: string;
  date: string; // '11.23'
  photos: number;
  stamp: boolean;
};

const PAGE = 5;

export default function MyReviews({ items, lv }: { items: MyReviewItem[]; lv: number }) {
  const [n, setN] = useState(PAGE);
  if (!items.length)
    return (
      <div className="mp-rv-empty">
        <img src="/mascot.png" alt="" />
        <p>
          아직 쓴 후기가 없어요. 팝업 상세의 리뷰에서 <b>다녀온 후기</b>를 쓰면 도장을 하나 받아요.
        </p>
        <Link href="/list" className="am-cta">
          팝업 찾아보기
        </Link>
      </div>
    );
  return (
    <>
      {items.slice(0, n).map((r) => (
        <Link key={r.id} href={`/popup/${r.cafeId}`} className="mp-rv">
          <span className="mp-rv-pst" style={posterBg(r.poster)} />
          <span className="mp-rv-body">
            <span className="mp-rv-t">{r.title}</span>
            <span className="mp-rv-meta">
              {r.rating ? <span className="stars">{"★".repeat(r.rating) + "☆".repeat(5 - r.rating)}</span> : <span className="kind">{r.kind}</span>}
              <span className="when">
                {" · "}
                {r.date}
                {r.photos ? ` · 사진 ${r.photos}장` : ""}
              </span>
            </span>
            {r.body ? <span className="mp-rv-txt">{r.body}</span> : <span className="mp-rv-txt none">별점만 남긴 후기예요</span>}
          </span>
          {r.stamp && (
            <span className="mp-rv-stamp">
              <RankStamp lv={lv || 1} size={40} />
            </span>
          )}
        </Link>
      ))}
      {items.length > n && (
        <button type="button" className="am-more" onClick={() => setN(n + PAGE)}>
          +{items.length - n}건 더보기
        </button>
      )}
    </>
  );
}
