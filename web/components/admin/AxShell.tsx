import Link from "next/link";
import { AxMenuScroll } from "./AxClient";

// 관리자 화면 A안 공통 틀 (docs/design/admin-handoff, AdmX-*): 왼쪽 어두운 사이드바 + 페이지 머리.
// 모바일(640px 이하)은 a-admin.css 에서 사이드바를 위쪽 가로 메뉴 줄로 바꾼다.

/** [주소 ?tab= 값, 메뉴 이름, 아이콘 선] — 시안 순서. 'home' 이 새 첫 화면(/data) */
export const AX_PAGES: [string, string, string][] = [
  ["home", "한눈에 보기", "M4 11l8-7 8 7v9h-5v-6H9v6H4z"],
  ["board", "팝업 현황", "M8 6h12 M8 12h12 M8 18h12 M4 6h.01 M4 12h.01 M4 18h.01"],
  ["usage", "이용 지표", "M5 20V10 M12 20V4 M19 20v-7"],
  ["requests", "삭제 요청", "M5 7h14 M10 7V4h4v3 M7 7l1 13h8l1-13"],
  ["notices", "알림 관리", "M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15z M10 20a2 2 0 0 0 4 0"],
  ["members", "회원 정보", "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21c1-4 4.5-6 8-6s7 2 8 6"],
  ["raw", "원본 데이터", "M4 6c0-2 16-2 16 0v12c0 2-16 2-16 0z M4 6c0 2 16 2 16 0 M4 12c0 2 16 2 16 0"],
  ["survey", "사용자 테스트", "M9 3h6 M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"],
];

export function AxIcon({ d, size = 18 }: { d: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d={d} />
    </svg>
  );
}

export function AxNav({
  tab,
  pend,
  hrefOf,
  routineUrl,
  supabaseUrl,
}: {
  tab: string;
  pend: number;
  hrefOf: (t: string) => string;
  routineUrl: string;
  supabaseUrl: string;
}) {
  return (
    <nav className="ax-side" aria-label="관리자 메뉴">
      <Link href="/" className="ax-logo" aria-label="ANI:WHERE 홈">
        <img src="/logo_sm.webp" alt="" />
      </Link>
      <span className="ax-side-h">관리자</span>
      <div className="ax-menu">
        {AX_PAGES.map(([t, label, d]) => {
          const on = t === tab;
          const badge = t === "requests" && pend > 0;
          return (
            <Link
              key={t}
              href={hrefOf(t)}
              scroll={false}
              className={on ? "on" : undefined}
              aria-current={on ? "page" : undefined}
              aria-label={badge ? `${label} (대기 ${pend}건)` : undefined}
            >
              <AxIcon d={d} />
              <span className="ax-menu-t">{label}</span>
              {badge && (
                <b className="ax-badge" aria-hidden>
                  {pend}
                </b>
              )}
            </Link>
          );
        })}
      </div>
      <AxMenuScroll />
      <div className="ax-side-foot">
        <a href={routineUrl} target="_blank" rel="noopener noreferrer">
          Claude 예약 작업 ↗
        </a>
        <a href={supabaseUrl} target="_blank" rel="noopener noreferrer">
          Supabase 데이터 보기 ↗
        </a>
        <Link href="/" className="ax-back">
          ← 서비스로 돌아가기
        </Link>
      </div>
    </nav>
  );
}

/** 페이지 머리: 작은 이름 · 큰 제목(Jua 30px) · 오른쪽 도구 */
export function AxHead({
  eyebrow,
  title,
  sub,
  right,
}: {
  eyebrow: string;
  title: React.ReactNode;
  sub?: React.ReactNode;
  right?: React.ReactNode;
}) {
  return (
    <div className="ax-head">
      <div className="ax-head-l">
        <span className="ax-eyebrow">{eyebrow}</span>
        <h1 className="ax-h1">{title}</h1>
        {sub && <p className="ax-sub">{sub}</p>}
      </div>
      {right && <div className="ax-head-r">{right}</div>}
    </div>
  );
}

/** 흰 카드 (시안의 section: 흰 바탕 · 20px 모서리 · 20px 안쪽 여백) */
export function AxCard({
  title,
  right,
  id,
  className = "",
  children,
}: {
  title?: React.ReactNode;
  right?: React.ReactNode;
  id?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={`ax-card ${className}`.trim()} aria-labelledby={title && id ? `${id}-h` : undefined} id={id}>
      {(title || right) && (
        <div className="ax-card-h">
          {title && <h2 id={id ? `${id}-h` : undefined}>{title}</h2>}
          {right && <div className="ax-card-hr">{right}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

/** 알약 꼬리표 (처리할 일 · 최근 활동 · 상태) */
export function AxTag({ tone, children }: { tone: string; children: React.ReactNode }) {
  return <span className={`ax-tag t-${tone}`}>{children}</span>;
}

/** 데이터가 없을 때 (빈 표 대신 다음에 할 일) */
export function AxEmpty({ children }: { children: React.ReactNode }) {
  return <div className="ax-empty">{children}</div>;
}
