"use client";
import { useEffect, useRef, useState } from "react";
import { PLACEHOLDER_POSTER } from "@/lib/popup";
import { CloseIcon, SearchIcon } from "../Icons";

// 상세 사진 (A-Detail 시안 왼쪽 칸): 3:4 큰 사진(민트 테두리) + 양옆 ‹ › + 아래 작은 사진 줄(한 줄 4칸, 더 많으면 옆으로 넘김).
// 몇 초마다 넘어가고, 큰 사진을 누르면 크게 본다 (앱 components/gallery 의 '눌러서 크게 보기' 그대로).
export default function Gallery({ images, alt }: { images: string[]; alt: string }) {
  const list = images.length ? images : [PLACEHOLDER_POSTER];
  const n = list.length;
  const [i, setI] = useState(0);
  const [big, setBig] = useState(false);
  const [paused, setPaused] = useState(false);
  const thumbs = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (n < 2 || paused || big) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => setI((k) => (k + 1) % n), 4000);
    return () => clearInterval(id);
  }, [n, paused, big]);

  useEffect(() => {
    if (!big) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setBig(false);
      if (e.key === "ArrowRight") setI((k) => (k + 1) % n);
      if (e.key === "ArrowLeft") setI((k) => (k - 1 + n) % n);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [big, n]);

  // 지금 사진의 작은 그림이 줄 안에 보이게 (줄만 옆으로 민다 — 화면은 움직이지 않는다)
  useEffect(() => {
    const row = thumbs.current;
    const cur = row?.children[i] as HTMLElement | undefined;
    if (!row || !cur) return;
    const left = cur.offsetLeft - row.offsetLeft;
    if (left < row.scrollLeft || left + cur.offsetWidth > row.scrollLeft + row.clientWidth)
      row.scrollTo({ left: Math.max(0, left - cur.offsetWidth), behavior: "smooth" });
  }, [i]);

  const go = (d: number) => setI((k) => (k + d + n) % n);
  const fallback = (e: React.SyntheticEvent<HTMLImageElement>) => {
    if (!e.currentTarget.src.endsWith(PLACEHOLDER_POSTER)) e.currentTarget.src = PLACEHOLDER_POSTER;
  };

  return (
    <div className="ad-gal" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      <div className="ad-gal-stage">
        {list.map((src, k) => (
          <button
            key={`${src}-${k}`}
            type="button"
            className={`ad-gal-slide${k === i ? " on" : ""}`}
            onClick={() => setBig(true)}
            aria-label={`${alt} 이미지 ${k + 1} 크게 보기`}
            tabIndex={k === i ? 0 : -1}
          >
            <img src={src} alt={k === 0 ? alt : ""} loading={k === 0 ? "eager" : "lazy"} onError={fallback} />
          </button>
        ))}
        <span className="ad-gal-zoom" aria-hidden>
          <SearchIcon />
          눌러서 크게 보기
        </span>
        {n > 1 && (
          <>
            <span className="ad-gal-count">
              {i + 1} / {n}
            </span>
            <button type="button" className="ad-gal-arrow l" aria-label="이전 사진" onClick={() => go(-1)}>
              ‹
            </button>
            <button type="button" className="ad-gal-arrow r" aria-label="다음 사진" onClick={() => go(1)}>
              ›
            </button>
          </>
        )}
      </div>
      {n > 1 && (
        <div className="ad-gal-thumbs" ref={thumbs}>
          {list.map((src, k) => (
            <button
              key={`${src}-t${k}`}
              type="button"
              className={k === i ? "on" : undefined}
              aria-label={`사진 ${k + 1}`}
              aria-current={k === i}
              onClick={() => setI(k)}
            >
              <img src={src} alt="" loading="lazy" onError={fallback} />
            </button>
          ))}
        </div>
      )}
      {big && (
        <div className="lightbox" role="dialog" aria-label="이미지 크게 보기" onClick={() => setBig(false)}>
          <img src={list[i]} alt={alt} onError={fallback} />
          <button type="button" className="lb-x" aria-label="닫기" onClick={() => setBig(false)}>
            <CloseIcon />
          </button>
          {n > 1 && (
            <>
              <span className="lb-count">
                {i + 1} / {n}
              </span>
              <button
                type="button"
                className="ad-gal-arrow l"
                aria-label="이전 사진"
                onClick={(e) => {
                  e.stopPropagation();
                  go(-1);
                }}
              >
                ‹
              </button>
              <button
                type="button"
                className="ad-gal-arrow r"
                aria-label="다음 사진"
                onClick={(e) => {
                  e.stopPropagation();
                  go(1);
                }}
              >
                ›
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
