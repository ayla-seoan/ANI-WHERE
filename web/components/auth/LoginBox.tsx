"use client";
import { submitWith } from "@/lib/submit";
import { useActionState, useState } from "react";
import { loginAction, signupAction, type FormState } from "@/app/actions";
import Consent from "./Consent";

// 로그인 · 회원가입 (앱 _login_body): 가운데 좁은 칸, 위에 '로그인 | 회원가입' 고르기,
// 아이디·비밀번호 칸 아래에 카카오·네이버 간편 로그인 (같은 창에서 넘어간다 — 이 웹은 iframe 이 아니라 작은 창이 필요 없다).

export type SocialLinks = { kakao: string | null; naver: string | null };

const NICK_HELP =
  "입력하지 않으면 칸에 흐리게 보이는 닉네임(꾸밈말 + 애니 캐릭터 이름)으로 자동으로 정해져요. 2~10자, 다른 회원과 같은 닉네임 · 욕설·음란한 말 · 관리자·운영자처럼 보이는 이름은 쓸 수 없어요. 가입한 뒤 마이페이지에서 언제든 바꿀 수 있어요.";

function Err({ s }: { s: FormState }) {
  if (!s?.error) return null;
  return (
    <div className="auth-warn" role="alert">
      {s.error}
    </div>
  );
}

function Social({ links, verb }: { links: SocialLinks; verb: string }) {
  return (
    <>
      {(["kakao", "naver"] as const).map((p) => {
        const label = p === "kakao" ? "카카오" : "네이버";
        const href = links[p];
        return href ? (
          <a key={p} className={`auth-btn ${p}`} href={href}>
            {label}로 {verb}
          </a>
        ) : (
          <span key={p} className="auth-btn off">
            {label} {verb} 준비 중
          </span>
        );
      })}
    </>
  );
}

export default function LoginBox({
  links,
  suggest,
  next,
  error,
}: {
  links: SocialLinks;
  suggest: string;
  next: string;
  error: string;
}) {
  const [mode, setMode] = useState<"login" | "join">("login");
  const [ls, loginForm, loggingIn] = useActionState(loginAction, null);
  const [js, joinForm, joining] = useActionState(signupAction, null);
  return (
    <div className="auth-wrap">
      <div className="seg" role="tablist" aria-label="로그인 또는 회원가입">
        {(
          [
            ["login", "로그인"],
            ["join", "회원가입"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={mode === k}
            className={mode === k ? "on" : ""}
            onClick={() => setMode(k)}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <div className="auth-warn" role="alert">
          {error}
        </div>
      )}
      {mode === "login" ? (
        <>
          <div className="auth-title">환영합니다</div>
          <div className="auth-sub">아이디로 가입했다면 아래에, 카카오·네이버로 가입했다면 간편 로그인 가능해요.</div>
          <form onSubmit={submitWith(loginForm)} className="auth-form">
            <input type="hidden" name="next" value={next} />
            <label className="fl">
              <span>아이디</span>
              <input name="login_id" maxLength={20} autoComplete="username" required />
            </label>
            <label className="fl">
              <span>비밀번호</span>
              <input name="password" type="password" maxLength={72} autoComplete="current-password" required />
            </label>
            <Err s={ls} />
            <button type="submit" className="btn-main" disabled={loggingIn}>
              로그인
            </button>
          </form>
          <div className="auth-or">또는 간편 로그인</div>
          <Social links={links} verb="로그인" />
        </>
      ) : (
        <>
          <div className="auth-title">3초 만에 회원가입</div>
          <div className="auth-sub auth-guide">
            <b>아이디·비밀번호·닉네임</b>만 있으면 가입돼요. 이메일·전화번호는 받지 않아요.
            <br />
            카카오·네이버 계정이 있으면 아래 간편 가입으로 비밀번호 없이도 가입할 수 있어요.
            <br />
            가입하면 북마크·리뷰가 <b>어느 기기에서나</b> 내 것으로 남아요.
          </div>
          <form onSubmit={submitWith(joinForm)} className="auth-form">
            <label className="fl">
              <span>아이디 (필수)</span>
              <input
                name="login_id"
                maxLength={20}
                placeholder="영어 소문자·숫자·_ 4~20자"
                autoComplete="username"
                required
              />
            </label>
            <label className="fl">
              <span>비밀번호 (필수)</span>
              <input
                name="password"
                type="password"
                maxLength={72}
                placeholder="영문+숫자 8자 이상"
                autoComplete="new-password"
                required
              />
            </label>
            <label className="fl">
              <span>비밀번호 확인 (필수)</span>
              <input name="password2" type="password" maxLength={72} autoComplete="new-password" required />
            </label>
            <label className="fl">
              <span>
                닉네임 (선택)
                <span className="help" tabIndex={0}>
                  ?<span className="tip">{NICK_HELP}</span>
                </span>
              </span>
              <input name="nickname" maxLength={10} placeholder={suggest} />
            </label>
            <Consent kind="local" />
            <div className="auth-sub auth-guide">
              이메일·전화번호를 받지 않아서 <b>비밀번호를 잊으면 찾을 수 없어요.</b> 꼭 기억해 두세요. 프로필
              사진(선택)은 가입한 뒤 마이페이지에서 올릴 수 있어요.
            </div>
            <Err s={js} />
            <button type="submit" className="btn-main" disabled={joining}>
              가입하기
            </button>
          </form>
          <div className="auth-or">또는 간편 가입</div>
          <Social links={links} verb="가입하기" />
        </>
      )}
      <div className="auth-foot">
        로그인하지 않아도 팝업은 둘러볼 수 있어요.
        <br />
        받는 정보: <b>별명(닉네임)</b>과 계정 고유 번호뿐이에요. 고유 번호는 알아볼 수 없게 바꿔서(해시) 저장하고,
        이메일·전화번호·실명은 받지도 저장하지도 않아요.
      </div>
    </div>
  );
}
