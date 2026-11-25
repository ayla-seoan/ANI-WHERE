"use client";
import { useMember } from "../member/MemberContext";
import { BellLine, CheckLine } from "./Icons2";

// 사전예약 타임라인의 알림 버튼 (A-Home '예약 오픈 알림'). 새 알림 체계를 만들지 않고 기존 북마크에 잇는다 —
// 북마크한 팝업은 오픈 3일 전부터 종 알림이 온다. 그래서 글자도 실제 동작대로 '북마크하고 오픈 알림 받기'.
// 손님이 누르면 로그인 화면으로 (MemberContext.toggle).
export default function ReserveAlert({ cafeId, name }: { cafeId: string; name: string }) {
  const { favs, toggle } = useMember();
  const on = favs.has(cafeId);
  return (
    <button
      type="button"
      className={`ah-pre-btn${on ? " on" : ""}`}
      aria-pressed={on}
      aria-label={on ? `${name} 북마크 해제 (오픈 알림 끄기)` : `${name} 북마크하고 오픈 알림 받기`}
      onClick={() => toggle(cafeId)}
    >
      {on ? <CheckLine /> : <BellLine />}
      <span>{on ? "오픈 알림 받는 중" : "북마크하고 오픈 알림 받기"}</span>
    </button>
  );
}
