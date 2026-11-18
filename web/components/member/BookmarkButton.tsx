"use client";
import { useMember } from "./MemberContext";

// 북마크 버튼 (앱 _heart): 아직이면 흰 바탕 '북마크+', 북마크했으면 포인트 색으로 채운 체크 북마크.
// 손님이 누르면 로그인 화면으로. 카드 안에서는 카드 링크로 넘어가지 않게 막는다.
export default function BookmarkButton({
  cafeId,
  variant = "card",
}: {
  cafeId: string;
  variant?: "card" | "detail" | "row";
}) {
  const { favs, toggle } = useMember();
  const on = favs.has(cafeId);
  return (
    <button
      type="button"
      className={`bm bm-${variant}${on ? " on" : ""}`}
      aria-pressed={on}
      aria-label={on ? "북마크 해제" : "북마크하기"}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        toggle(cafeId);
      }}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        {on ? (
          <>
            <path d="M6 4h12v16l-6-4-6 4V4z" fill="currentColor" stroke="none" />
            <path d="M9 10.2l2 2 4-4" stroke="#fff" />
          </>
        ) : (
          <>
            <path d="M6 4h12v16l-6-4-6 4V4z" />
            <path d="M12 7.5v5M9.5 10h5" />
          </>
        )}
      </svg>
    </button>
  );
}
