// 작은 선 아이콘 (Material Symbols 모양을 단순화). 이모지 대신 쓴다.
type P = { className?: string };
const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export const SearchIcon = (p: P) => (
  <svg {...base} {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  </svg>
);
export const MapIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M12 21s-6-5.3-6-11a6 6 0 1112 0c0 5.7-6 11-6 11z" />
    <circle cx="12" cy="10" r="2.2" />
  </svg>
);
export const LinkIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1" />
    <path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1" />
  </svg>
);
export const BackIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M15 18l-6-6 6-6" />
  </svg>
);
export const EditIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M4 20h4L19 9l-4-4L4 16v4z" />
  </svg>
);
export const AddIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);
export const StoreIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M4 9l1.5-4h13L20 9" />
    <path d="M4 9h16v1.5a2.5 2.5 0 01-5 0 2.5 2.5 0 01-5 0 2.5 2.5 0 01-5 0z" />
    <path d="M5 13v7h14v-7" />
  </svg>
);
export const MapOutlineIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2z" />
    <path d="M9 4v14M15 6v14" />
  </svg>
);
export const ChatIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M4 5h12v9H8l-4 3V5z" />
    <path d="M16 9h4v9l-3-2h-7v-2" />
  </svg>
);
