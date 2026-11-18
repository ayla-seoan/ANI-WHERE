// 관리자 화면 작은 선 아이콘 (앱의 :material/...: 아이콘을 단순화한 인라인 SVG). 이모지 대신 쓴다.
type P = { className?: string };
const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  className: "ai",
};

const make = (d: React.ReactNode) =>
  function Icon(p: P) {
    return (
      <svg {...base} {...p} className={`ai${p.className ? ` ${p.className}` : ""}`}>
        {d}
      </svg>
    );
  };

export const IcLeft = make(<path d="M15 18l-6-6 6-6" />);
export const IcRight = make(<path d="M9 6l6 6-6 6" />);
export const IcMore = make(<path d="M6 9l6 6 6-6" />);
export const IcLess = make(<path d="M6 15l6-6 6 6" />);
export const IcClose = make(<path d="M6 6l12 12M18 6L6 18" />);
export const IcRefresh = make(
  <>
    <path d="M20 11a8 8 0 10-2.3 5.7" />
    <path d="M20 4v7h-7" />
  </>,
);
export const IcSchedule = make(
  <>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </>,
);
export const IcDatabase = make(
  <>
    <ellipse cx="12" cy="6" rx="7" ry="2.8" />
    <path d="M5 6v12c0 1.5 3.1 2.8 7 2.8s7-1.3 7-2.8V6M5 12c0 1.5 3.1 2.8 7 2.8s7-1.3 7-2.8" />
  </>,
);
export const IcForm = make(
  <>
    <rect x="5" y="4" width="14" height="17" rx="2" />
    <path d="M9 4.5V3h6v1.5M8.5 10h7M8.5 14h7M8.5 18h4" />
  </>,
);
export const IcEditNote = make(
  <>
    <path d="M4 6h10M4 10h10M4 14h6" />
    <path d="M14.5 19.5l5.8-5.8a1.5 1.5 0 00-2.1-2.1l-5.8 5.8-.6 2.7z" />
  </>,
);
export const IcEdit = make(<path d="M4 20h4L19 9a2.8 2.8 0 00-4-4L4 16v4z" />);
export const IcTable = make(
  <>
    <rect x="3.5" y="4.5" width="17" height="15" rx="2" />
    <path d="M3.5 9.5h17M3.5 14.5h17M9.5 9.5v10" />
  </>,
);
export const IcFlow = make(
  <>
    <rect x="3" y="3.5" width="7" height="5" rx="1" />
    <rect x="14" y="15.5" width="7" height="5" rx="1" />
    <path d="M6.5 8.5V18h7.5M14 6h3.5v9.5" />
  </>,
);
export const IcLogin = make(
  <>
    <path d="M14 4h4a2 2 0 012 2v12a2 2 0 01-2 2h-4" />
    <path d="M10 16l4-4-4-4M14 12H4" />
  </>,
);
export const IcInfo = make(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5.5M12 7.5v.1" />
  </>,
);
export const IcError = make(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v5.5M12 16.5v.1" />
  </>,
);
export const IcLinkOff = make(
  <>
    <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1" />
    <path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1" />
    <path d="M4 4l16 16" />
  </>,
);
export const IcHourglass = make(<path d="M7 3.5h10M7 20.5h10M8 3.5c0 4.5 8 4.5 8 8.5s-8 4-8 8.5M16 3.5c0 2-1.5 3.2-3 4.3" />);
export const IcCompare = make(<path d="M7 4L3.5 7.5 7 11M3.5 7.5H15M17 13l3.5 3.5L17 20M20.5 16.5H9" />);
