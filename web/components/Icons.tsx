// 작은 선 아이콘 (앱이 쓰는 Material Symbols Rounded 모양을 단순화한 인라인 SVG). 이모지 대신 쓴다.
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
const solid = { viewBox: "0 0 24 24", fill: "currentColor", "aria-hidden": true };

export const SearchIcon = (p: P) => (
  <svg {...base} strokeWidth={2.3} {...p}>
    <circle cx="10.5" cy="10.5" r="6.6" />
    <path d="M15.6 15.6L20 20" />
  </svg>
);
export const MapIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M12 21s-6-5.3-6-11a6 6 0 1112 0c0 5.7-6 11-6 11z" />
    <circle cx="12" cy="10" r="2.2" />
  </svg>
);
export const PinIcon = (p: P) => (
  <svg {...solid} {...p}>
    <path d="M12 2.5a7 7 0 00-7 7c0 5.1 6 11.3 6.3 11.6a1 1 0 001.4 0C13 20.8 19 14.6 19 9.5a7 7 0 00-7-7zm0 9.6a2.6 2.6 0 110-5.2 2.6 2.6 0 010 5.2z" />
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
export const ChevronRight = (p: P) => (
  <svg {...base} {...p}>
    <path d="M9 6l6 6-6 6" />
  </svg>
);
export const ExpandMore = (p: P) => (
  <svg {...base} {...p}>
    <path d="M6 9l6 6 6-6" />
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
export const CloseIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />
  </svg>
);
export const StoreIcon = (p: P) => (
  // Material 'local_cafe' 와 비슷한 컵 모양 (앱 카드의 매장 아이콘)
  <svg {...base} {...p}>
    <path d="M4 6h12v6a5 5 0 01-5 5H9a5 5 0 01-5-5V6z" />
    <path d="M16 8h1.5a2.5 2.5 0 010 5H16" />
    <path d="M4 20h13" />
  </svg>
);
export const TuneIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M4 7h9M17 7h3M4 17h3M11 17h9" />
    <circle cx="15" cy="7" r="2" />
    <circle cx="9" cy="17" r="2" />
  </svg>
);
export const ListIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M9 6h11M9 12h11M9 18h11" />
    <circle cx="4.5" cy="6" r="1" />
    <circle cx="4.5" cy="12" r="1" />
    <circle cx="4.5" cy="18" r="1" />
  </svg>
);
export const HelpIcon = (p: P) => (
  <svg {...base} strokeWidth={1.8} {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.6 9.4a2.5 2.5 0 014.8.9c0 1.7-2.4 2.1-2.4 3.6" />
    <path d="M12 17.2v.1" />
  </svg>
);
export const FireIcon = (p: P) => (
  <svg {...solid} {...p}>
    <path d="M12 2.5c.4 3-1.3 4.7-2.8 6.3C7.7 10.4 6 12.1 6 15a6 6 0 0012 0c0-2.3-1-4.1-2-5.4-.3 1.3-1 2.3-2 2.8.3-3.4-.8-7.2-2-9.9zm0 17.5a3 3 0 01-3-3c0-1.6 1.2-2.5 2.2-3.6.3 1.3 1 2 1.8 2.5.6.4 1 1 1 1.6a3 3 0 01-2 2.5z" />
  </svg>
);
export const NewIcon = (p: P) => (
  // Material 'fiber_new' (둥근 네모 안 NEW)
  <svg viewBox="0 0 24 24" aria-hidden {...p}>
    <rect x="2" y="5" width="20" height="14" rx="3" fill="currentColor" />
    <text
      x="12"
      y="15.2"
      textAnchor="middle"
      fontSize="7.2"
      fontWeight="900"
      fill="#fff"
      fontFamily="Arial, sans-serif"
    >
      NEW
    </text>
  </svg>
);
export const HourglassIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M6 3h12M6 21h12" />
    <path d="M7 3c0 4 5 6 5 9s-5 5-5 9M17 3c0 4-5 6-5 9s5 5 5 9" />
    <path d="M8.5 19.5h7l-3.5-3z" fill="currentColor" />
  </svg>
);
export const EventIcon = (p: P) => (
  <svg {...base} {...p}>
    <rect x="3.5" y="5" width="17" height="15" rx="2.5" />
    <path d="M3.5 10h17M8 3v4M16 3v4" />
    <path d="M9 15l2 2 4-4" />
  </svg>
);
export const CalendarIcon = (p: P) => (
  <svg {...base} {...p}>
    <rect x="3.5" y="5" width="17" height="15" rx="2.5" />
    <path d="M3.5 10h17M8 3v4M16 3v4" />
  </svg>
);
export const GiftIcon = (p: P) => (
  <svg {...base} {...p}>
    <rect x="3.5" y="8" width="17" height="4" rx="1" />
    <path d="M5 12v8h14v-8M12 8v12" />
    <path d="M12 8c-1.5-3-5-3.5-5-1.2C7 8 9 8 12 8zM12 8c1.5-3 5-3.5 5-1.2C17 8 15 8 12 8z" />
  </svg>
);
export const BagIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M5 8h14l-1 12H6L5 8z" />
    <path d="M9 10V7a3 3 0 016 0v3" />
  </svg>
);
export const PartyIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M4 20l4.5-12 7.5 7.5L4 20z" />
    <path d="M14 4v2M19 9h2M17.5 5.5l-1.5 1.5M13 9c1-1 2.5-1 3.5 0" />
  </svg>
);
export const SparkleIcon = (p: P) => (
  <svg {...solid} {...p}>
    <path d="M10 3l1.8 4.9L17 10l-5.2 2.1L10 17l-1.8-4.9L3 10l5.2-2.1L10 3zM18 13l.9 2.2 2.1.8-2.1.8L18 19l-.9-2.2L15 16l2.1-.8L18 13z" />
  </svg>
);
export const OpenIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M14 4h6v6M20 4l-9 9" />
    <path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5" />
  </svg>
);
export const BookmarkIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M6 4h12v16l-6-4-6 4V4z" />
  </svg>
);
export const ChatIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M4 5h12v9H8l-4 3V5z" />
    <path d="M16 9h4v9l-3-2h-7v-2" />
  </svg>
);
export const StarIcon = (p: P) => (
  <svg {...solid} {...p}>
    <path d="M12 3.5l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.8l-5.2 2.7 1-5.8-4.2-4.1 5.8-.8L12 3.5z" />
  </svg>
);
/** 후기 모음 (Material 'rate_review': 말풍선 + 별) */
export const RateReviewIcon = (p: P) => (
  <svg {...base} {...p}>
    <path d="M4 5.5A1.5 1.5 0 015.5 4h13A1.5 1.5 0 0120 5.5v9a1.5 1.5 0 01-1.5 1.5H9l-5 4V5.5z" />
    <path d="M12 7.2l.95 1.95 2.15.3-1.55 1.5.37 2.13L12 12.07l-1.92 1.01.37-2.13-1.55-1.5 2.15-.3z" />
  </svg>
);
