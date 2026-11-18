"use client";
import { useEffect, useState } from "react";
import { PLACEHOLDER_POSTER } from "@/lib/popup";
import { CloseIcon, SearchIcon } from "../Icons";

// 상세 이미지 슬라이드 (앱 components/gallery 모양): 회색 상자, 왼쪽 위 '눌러서 크게 보기', 오른쪽 위 '3 / 6',
// 양옆 ‹ ›, 아래 점. 몇 초마다 넘어가고, 누르면 크게 본다.
export default function Gallery({ images, alt }: { images: string[]; alt: string }) {
  const list = images.length ? images : [PLACEHOLDER_POSTER];
  const n = list.length;
  const [i, setI] = useState(0);
  const [big, setBig] = useState(false);
  const [paused, setPaused] = useState(false);

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

  const go = (d: number) => setI((k) => (k + d + n) % n);
  const fallback = (e: React.SyntheticEvent<HTMLImageElement>) => {
    if (!e.currentTarget.src.endsWith(PLACEHOLDER_POSTER)) e.currentTarget.src = PLACEHOLDER_POSTER;
  };

  return (
    <div className="gallery" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      <button type="button" className="g-zoom" onClick={() => setBig(true)}>
        <SearchIcon />
        눌러서 크게 보기
      </button>
      {n > 1 && (
        <span className="g-count">
          {i + 1} / {n}
        </span>
      )}
      <div className="g-stage">
        {list.map((src, k) => (
          <button
            key={`${src}-${k}`}
            type="button"
            className={`g-slide${k === i ? " on" : ""}`}
            onClick={() => setBig(true)}
            aria-label={`${alt} 이미지 ${k + 1} 크게 보기`}
            tabIndex={k === i ? 0 : -1}
          >
            <img src={src} alt={k === 0 ? alt : ""} loading={k === 0 ? "eager" : "lazy"} onError={fallback} />
          </button>
        ))}
      </div>
      {n > 1 && (
        <>
          <button type="button" className="aw-arrow l show big" aria-label="이전 이미지" onClick={() => go(-1)}>
            ‹
          </button>
          <button type="button" className="aw-arrow r show big" aria-label="다음 이미지" onClick={() => go(1)}>
            ›
          </button>
          <div className="g-dots">
            {list.map((src, k) => (
              <button
                key={`${src}-d${k}`}
                type="button"
                className={k === i ? "on" : undefined}
                aria-label={`이미지 ${k + 1}`}
                onClick={() => setI(k)}
              />
            ))}
          </div>
        </>
      )}
      {big && (
        <div className="lightbox" role="dialog" aria-label="이미지 크게 보기" onClick={() => setBig(false)}>
          <img src={list[i]} alt={alt} onError={fallback} />
          <button type="button" className="lb-x" aria-label="닫기" onClick={() => setBig(false)}>
            <CloseIcon />
          </button>
          {n > 1 && (
            <span className="lb-count">
              {i + 1} / {n}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
