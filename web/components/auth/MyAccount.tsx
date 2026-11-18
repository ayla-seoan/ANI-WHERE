"use client";
import { submitWith } from "@/lib/submit";
import { startTransition, useActionState, useState } from "react";
import {
  avatarDefaultAction,
  changePasswordAction,
  logoutAction,
  renameAction,
  withdrawAction,
  type FormState,
} from "@/app/actions";
import { avatarUrl } from "@/lib/avatar";
import { APP_URL } from "@/lib/popup";

// 마이페이지 '내 계정' (앱 _my_account): 프로필 사진 · 닉네임 · 로그인 수단 · 가입일 · 회원 번호,
// 닉네임 바꾸기 + 로그아웃, (아이디 가입) 비밀번호 바꾸기, 개인정보처리방침, 탈퇴하기.
// 사진 올리기는 파일 저장소가 있는 ANI:WHERE 앱에서 (이 웹 서버에는 파일을 둘 곳이 없다).

export type Account = {
  nick: string;
  avatar: string;
  provider: string;
  providerLabel: string;
  agreed: string;
  key: string;
  admin: boolean;
};

function Msg({ s }: { s: FormState }) {
  if (s?.error)
    return (
      <div className="auth-warn" role="alert">
        {s.error}
      </div>
    );
  if (s?.ok)
    return (
      <div className="auth-ok" role="status">
        {s.ok}
      </div>
    );
  return null;
}

export default function MyAccount({ a, suggest }: { a: Account; suggest: string }) {
  const [rs, renameForm, renaming] = useActionState(renameAction, null);
  const [ps, pwForm] = useActionState(changePasswordAction, null);
  const [ws, withdrawForm] = useActionState(withdrawAction, null);
  const [avs, setAvs] = useState<FormState>(null);
  const [openPhoto, setOpenPhoto] = useState(false);
  const [openPw, setOpenPw] = useState(false);
  const [openOut, setOpenOut] = useState(false);
  const local = a.provider === "local";
  return (
    <div className="auth-wrap">
      <div className="auth-title">내 계정</div>
      <div className="auth-card me-card">
        <img
          className="me-avimg"
          src={avatarUrl(a.avatar)}
          alt=""
          width={72}
          height={72}
          referrerPolicy="no-referrer"
          onError={(e) => {
            e.currentTarget.src = avatarUrl("");
          }}
        />
        <div className="me-info">
          <b>{a.nick}</b>
          <br />
          <span className="auth-note">
            {a.providerLabel} 계정으로 로그인 중 · 가입 {a.agreed.slice(0, 10)}
            <br />
            회원 번호 <code>{a.key}</code>
            {a.admin ? " · 관리자" : ""}
          </span>
        </div>
      </div>

      <details className="exp" open={openPhoto} onToggle={(e) => setOpenPhoto((e.target as HTMLDetailsElement).open)}>
        <summary>프로필 사진 바꾸기</summary>
        <p className="cap">
          리뷰 옆에 동그랗게 보여요. 선택이에요 — 없으면 기본 그림이 보여요. 사람 얼굴·개인정보가 든 사진은 피해 주세요.
        </p>
        <p className="cap">
          사진 올리기는 ANI:WHERE 앱에서 할 수 있어요 (이 웹에는 사진 파일을 저장할 곳이 없어요). 같은 계정이라 올린
          사진이 여기에도 보여요.
        </p>
        <div className="two">
          <a className="btn-line" href={`${APP_URL}/login`} target="_blank" rel="noopener noreferrer">
            앱에서 사진 올리기
          </a>
          <button
            type="button"
            className="btn-line"
            onClick={async () => {
              setAvs(await avatarDefaultAction());
            }}
          >
            기본 사진 설정
          </button>
        </div>
        <Msg s={avs} />
      </details>

      <form onSubmit={submitWith(renameForm)} className="auth-form">
        <label className="fl">
          <span>닉네임 바꾸기</span>
          <input
            name="nickname"
            aria-label="닉네임 바꾸기"
            defaultValue={a.nick.slice(0, 10)}
            maxLength={10}
            placeholder={suggest}
          />
        </label>
        <p className="cap">칸을 비워 두고 저장하면 흐리게 보이는 랜덤 닉네임으로 바꿔요 (가입할 때와 같게)</p>
        <Msg s={rs} />
        <div className="two">
          <button type="submit" className="btn-main" disabled={renaming}>
            저장
          </button>
          <button type="button" className="btn-line" onClick={() => startTransition(() => logoutAction())}>
            로그아웃
          </button>
        </div>
      </form>

      {local && (
        <details className="exp" open={openPw} onToggle={(e) => setOpenPw((e.target as HTMLDetailsElement).open)}>
          <summary>비밀번호 바꾸기</summary>
          <form onSubmit={submitWith(pwForm)} className="auth-form">
            <label className="fl">
              <span>아이디</span>
              <input name="login_id" maxLength={20} autoComplete="username" />
            </label>
            <label className="fl">
              <span>지금 비밀번호</span>
              <input name="old" type="password" autoComplete="current-password" />
            </label>
            <label className="fl">
              <span>새 비밀번호</span>
              <input name="new" type="password" placeholder="영문+숫자 8자 이상" autoComplete="new-password" />
            </label>
            <label className="fl">
              <span>새 비밀번호 확인</span>
              <input name="new2" type="password" autoComplete="new-password" />
            </label>
            <Msg s={ps} />
            <button type="submit" className="btn-line">
              바꾸기
            </button>
          </form>
        </details>
      )}

      <div className="consent-link">
        <a href={`${APP_URL}/privacy`} target="_blank" rel="noopener noreferrer">
          개인정보처리방침 · 이용약관
        </a>
      </div>
      <div className="withdraw">
        <button type="button" className="withdraw-btn" onClick={() => setOpenOut((o) => !o)}>
          탈퇴하기
        </button>
        {openOut && (
          <form onSubmit={submitWith(withdrawForm)} className="withdraw-pop">
            <p>
              닉네임·프로필 사진·아이디와 비밀번호·접속 기록을 <b>지난 기록까지 바로 지워요</b>. 쓴 리뷰는 다른 이용자를
              위해 &apos;탈퇴한 회원&apos;으로 남아요 (지우고 싶은 글은 먼저 삭제해 주세요).
            </p>
            {local && (
              <>
                <p className="cap">
                  아이디로 가입했다면 확인을 위해 아이디·비밀번호를 넣어 주세요. 비밀번호 기록도 지워요.
                </p>
                <input name="login_id" placeholder="아이디" autoComplete="username" />
                <input name="password" type="password" placeholder="비밀번호" autoComplete="current-password" />
              </>
            )}
            <Msg s={ws} />
            <button type="submit" className="btn-main">
              탈퇴할게요
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
