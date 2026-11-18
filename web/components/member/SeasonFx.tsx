"use client";
import { useEffect, useState } from "react";

// 내 캘린더 계절 배경 (앱 _season_fx · common/season.py 와 같게, 11/19 요청):
// 3~5월 꽃잎 · 6~8월 잎사귀 · 9~11월 단풍 · 12~2월 눈. 화면 위에서 천천히 떨어진다.
// 클릭을 막지 않고(pointer-events: none), 운영체제 '동작 줄이기' 를 켰으면 보이지 않는다.
const NS = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"';
const LEAF = "M10 1L12 6L16 4L15 9L19 10L15 12L16 16L11 14L10 19L9 14L4 16L5 12L1 10L5 9L4 4L8 6Z";
const SVGS: Record<string, string[]> = {
  spring: [
    `<svg ${NS}><path d="M10 1C14 5 15 11 10 19C5 11 6 5 10 1Z" fill="#F7B6C8"/><path d="M10 4V16" stroke="#EE93AE" stroke-width=".8"/></svg>`,
    `<svg ${NS}><path d="M10 2C15 4 16 10 10 18C4 10 5 4 10 2Z" fill="#FBD3DE"/><path d="M8 2L10 5L12 2" fill="#fff"/></svg>`,
  ],
  summer: [
    `<svg ${NS}><path d="M3 17C3 8 9 3 18 2C17 11 12 17 3 17Z" fill="#7CCB8C"/><path d="M3 17L14 6" stroke="#4FA766" stroke-width="1"/></svg>`,
    `<svg ${NS}><path d="M3 17C3 8 9 3 18 2C17 11 12 17 3 17Z" fill="#A6DDA0"/><path d="M3 17L14 6" stroke="#6CBF6F" stroke-width="1"/></svg>`,
  ],
  autumn: [
    `<svg ${NS}><path d="${LEAF}" fill="#E0674A"/></svg>`,
    `<svg ${NS}><path d="${LEAF}" fill="#F2A541"/></svg>`,
    `<svg ${NS}><path d="M3 17C3 8 9 3 18 2C17 11 12 17 3 17Z" fill="#E9C46A"/><path d="M3 17L14 6" stroke="#C99A3A" stroke-width="1"/></svg>`,
  ],
  winter: [
    `<svg ${NS}><circle cx="10" cy="10" r="7" fill="#CFE3F2"/></svg>`,
    `<svg ${NS}><g stroke="#B9D6EC" stroke-width="1.6" stroke-linecap="round"><path d="M10 2V18M3 6L17 14M3 14L17 6"/></g></svg>`,
  ],
};

function seasonOf(month: number): string {
  if (month >= 3 && month <= 5) return "spring";
  if (month >= 6 && month <= 8) return "summer";
  if (month >= 9 && month <= 11) return "autumn";
  return "winter";
}

type Piece = { left: number; size: number; url: string; opacity: number; fall: number; sway: number; delay: number; rot: number };

export default function SeasonFx() {
  const [pieces, setPieces] = useState<Piece[]>([]);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    // 한국 시간 기준 달 (앱 TODAY 와 같게)
    const month = Number(new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(5, 7));
    const season = seasonOf(month);
    const urls = SVGS[season].map((s) => `data:image/svg+xml;utf8,${encodeURIComponent(s)}`);
    const n = window.innerWidth <= 640 ? 7 : 14;
    const winter = season === "winter";
    setPieces(
      Array.from({ length: n }, (_, k) => {
        const fall = 12 + Math.random() * 12;
        return {
          left: Math.random() * 100,
          size: (winter ? 9 : 22) + Math.random() * (winter ? 9 : 14),
          url: urls[k % urls.length],
          opacity: 0.55 + Math.random() * 0.35,
          fall,
          sway: 3 + Math.random() * 3,
          delay: Math.random() * fall,
          rot: (Math.random() > 0.5 ? 1 : -1) * (180 + Math.random() * 360),
        };
      }),
    );
  }, []);
  if (!pieces.length) return null;
  return (
    <div className="aw-season" aria-hidden="true">
      {pieces.map((p, k) => (
        <i
          key={k}
          style={
            {
              left: `${p.left}%`,
              width: p.size,
              height: p.size,
              backgroundImage: `url("${p.url}")`,
              opacity: p.opacity,
              animationDuration: `${p.fall}s, ${p.sway}s`,
              animationDelay: `-${p.delay}s, 0s`,
              "--r": `${p.rot}deg`,
            } as React.CSSProperties
          }
        />
      ))}
    </div>
  );
}
