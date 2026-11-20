"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { periodDot, stateOf, type Item } from "@/lib/popup";
import { areaFill, posterBg } from "../cards";
import { FireIcon } from "../Icons";

// 실시간 인기 급상승 랭킹 (앱 _home_slide · _home_rank_rows 모양):
// 왼쪽 큰 배너(‹ › 로 넘김 · 5초마다 넘어감 · 아래 점) + 오른쪽(PC) / 아래(모바일) 1~5위 목록. 목록 줄을 누르면 배너가 그 순위로.
export default function RankBanner({ items, today }: { items: Item[]; today: string }) {
  const [i, setI] = useState(0);
  const [paused, setPaused] = useState(false);
  const track = useRef<HTMLDivElement>(null);
  const n = items.length;

  // 배너 줄을 i 번째 장으로 (가로 스크롤 + scroll-snap)
  useEffect(() => {
    const el = track.current;
    if (el) el.scrollTo({ left: el.clientWidth * i, behavior: "smooth" });
  }, [i]);

  // 손가락으로 넘긴 경우 i 를 맞춘다
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    let t: ReturnType<typeof setTimeout> | undefined;
    const onScroll = () => {
      if (t) clearTimeout(t);
      t = setTimeout(() => {
        const k = Math.round(el.scrollLeft / Math.max(1, el.clientWidth));
        setI((cur) => (cur === k ? cur : k));
      }, 120);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // 5초마다 다음 장 (커서를 올리면 멈춤, 움직임 줄이기 설정이면 넘기지 않음)
  useEffect(() => {
    if (paused || n < 2) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => setI((k) => (k + 1) % n), 5000);
    return () => clearInterval(id);
  }, [paused, n]);

  if (!n) return null;
  const go = (d: number) => setI((k) => (k + d + n) % n);

  return (
    <div className="rank">
      <div className="rank-banner" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
        <div className="hb-track" ref={track}>
          {items.map((p, k) => {
            const s = stateOf(p, today);
            return (
              <Link key={p.id} href={`/popup/${p.id}`} className="hb" prefetch={false} tabIndex={k === i ? 0 : -1}>
                <div className="hbbg" style={posterBg(p.poster)} />
                <div className="hbpic" style={posterBg(p.poster)} />
                <div className="hbtitle">
                  <FireIcon />
                  실시간 인기 급상승 랭킹
                </div>
                <div className="hbtxt">
                  <div className="hbrank">
                    {k + 1}
                    <small>위</small>
                  </div>
                  <div className="hbt">{p.work}</div>
                  <div className="hbd">
                    {p.name} · {periodDot(p)}
                  </div>
                  <div className="hbchips">
                    {p.area && <span style={areaFill(p.city)}>{p.area}</span>}
                    <span>{s.label}</span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
        {n > 1 && (
          <>
            <button type="button" className="aw-arrow l show big" aria-label="이전 순위" onClick={() => go(-1)}>
              ‹
            </button>
            <button type="button" className="aw-arrow r show big" aria-label="다음 순위" onClick={() => go(1)}>
              ›
            </button>
            <div className="aw-dots" role="tablist" aria-label="순위 고르기">
              {items.map((p, k) => (
                <button
                  key={p.id}
                  type="button"
                  role="tab"
                  aria-selected={k === i}
                  aria-label={`${k + 1}위`}
                  className={k === i ? "on" : undefined}
                  onClick={() => setI(k)}
                />
              ))}
            </div>
          </>
        )}
      </div>
      <div className="rank-list">
        <div className="hls-wrap">
          {items.map((p, k) => {
            const s = stateOf(p, today);
            return (
              <button key={p.id} type="button" className={`hl${k === i ? " on" : ""}`} onClick={() => setI(k)}>
                <b className="hln">{k + 1}</b>
                <span className="hlb">
                  <span className="hlt">{p.work}</span>
                  <span className="hls">{p.name}</span>
                </span>
                <span className={`hlst ${s.color}`}>{s.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
