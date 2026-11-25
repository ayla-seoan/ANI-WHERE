// 홈 A안(docs/design/handoff/screens/A-Home) 섹션 제목 · 버튼 아이콘. 시안의 선 아이콘 모양 그대로 (이모지 대신 SVG).
type P = { className?: string };
const line = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2.2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export const BookmarkLine = (p: P) => (
  <svg {...line} {...p}>
    <path d="M7 4h10v16l-5-3.5L7 20z" />
  </svg>
);
export const SparkLine = (p: P) => (
  <svg {...line} {...p}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6" />
  </svg>
);
export const ClockLine = (p: P) => (
  <svg {...line} {...p}>
    <path d="M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3 2" />
  </svg>
);
export const ReserveLine = (p: P) => (
  <svg {...line} {...p}>
    <path d="M4 6h16v14H4zM4 10h16M8 3v4M16 3v4M9 15l2 2 4-4" />
  </svg>
);
export const TalkLine = (p: P) => (
  <svg {...line} {...p}>
    <path d="M4 5h16v11H9l-5 4z" />
  </svg>
);
export const BellLine = (p: P) => (
  <svg {...line} {...p}>
    <path d="M6 16v-5a6 6 0 1112 0v5l1.5 2h-15zM10 20a2 2 0 004 0" />
  </svg>
);
export const CheckLine = (p: P) => (
  <svg {...line} {...p}>
    <path d="M5 12.5l4.5 4.5L19 7.5" />
  </svg>
);
export const PlusLine = (p: P) => (
  <svg {...line} strokeWidth={2.4} {...p}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);
