"use client";
import { submitWith } from "@/lib/submit";
import { useActionState } from "react";
import { socialJoinAction } from "@/app/actions";
import { avatarUrl } from "@/lib/avatar";
import Consent from "./Consent";

// 카카오·네이버로 처음 온 사람 (앱 _auth_body '거의 다 됐어요'): 닉네임 + 동의만 받고 가입을 끝낸다.
export default function SocialJoin({
  label,
  nick,
  avatar,
  suggest,
}: {
  label: string;
  nick: string;
  avatar: string;
  suggest: string;
}) {
  const [s, form, busy] = useActionState(socialJoinAction, null);
  return (
    <div className="auth-wrap">
      <div className="auth-title">거의 다 됐어요</div>
      <div className="auth-sub">{label} 계정으로 처음 오셨어요. 앱에서 쓸 닉네임만 정하면 가입이 끝나요.</div>
      <div className="auth-av">
        <img src={avatarUrl(avatar)} alt="" width={48} height={48} referrerPolicy="no-referrer" />
        {avatar
          ? `${label} 프로필 사진이 있어요. 아래 [선택] 항목에 동의하면 리뷰 옆에 보여요.`
          : "프로필 사진은 선택이에요. 마이페이지에서 언제든 바꿀 수 있어요."}
      </div>
      <form onSubmit={submitWith(form)} className="auth-form">
        <label className="fl">
          <span>닉네임 (선택)</span>
          <input name="nickname" defaultValue={nick.slice(0, 10)} maxLength={10} placeholder={suggest} />
        </label>
        <Consent
          kind="social"
          photoLabel={
            avatar
              ? `[선택] ${label} 프로필 사진을 불러와 리뷰 옆에 보여 줘요 (사진 주소 저장, 마이페이지에서 언제든 지울 수 있어요)`
              : undefined
          }
        />
        {s?.error && (
          <div className="auth-warn" role="alert">
            {s.error}
          </div>
        )}
        <button type="submit" className="btn-main" disabled={busy}>
          가입하고 시작하기
        </button>
      </form>
    </div>
  );
}
