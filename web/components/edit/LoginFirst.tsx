"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { goLogin } from "../member/MemberContext";

// 손님이 회원만 쓰는 화면에 바로 들어왔을 때: 안내를 남기고 로그인 화면으로 (앱 page_add 의 flash + go("login"))
export default function LoginFirst({ msg, next }: { msg: string; next: string }) {
  const router = useRouter();
  useEffect(() => {
    goLogin(router, msg, next);
  }, [router, msg, next]);
  return (
    <div className="ed-gate wiz-gate">
      <div className="ntf-empty">{msg}</div>
      <button type="button" className="side-cta" onClick={() => goLogin(router, msg, next)}>
        로그인하고 계속하기
      </button>
    </div>
  );
}
