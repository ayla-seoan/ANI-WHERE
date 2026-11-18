"use client";
import { useState } from "react";

// 가입 동의 (앱 _consent_boxes): 필수(만 14세 이상 · 이용약관 · 개인정보 수집·이용)와 선택(프로필 사진)을 따로.
// 무엇을·왜·얼마나 보관하는지 표로 먼저 보여 주고, '약관 전체 동의' 로 한 번에 켤 수 있다.
const PRIVACY_TABLE = {
  local: "아이디 · 일방향 암호화한 비밀번호 · 닉네임 · 동의 시각",
  social: "로그인 수단 · 계정 번호를 되돌릴 수 없게 바꾼 값 · 닉네임 · 동의 시각",
};

export default function Consent({ kind, photoLabel }: { kind: "local" | "social"; photoLabel?: string }) {
  const keys = ["age", "terms", "privacy", ...(photoLabel ? ["photo"] : [])];
  const [on, setOn] = useState<Record<string, boolean>>({});
  const all = keys.every((k) => on[k]);
  const set = (k: string, v: boolean) => setOn((o) => ({ ...o, [k]: v }));
  const box = (k: string, label: string) => (
    <label className="ck">
      <input type="checkbox" name={k} checked={!!on[k]} onChange={(e) => set(k, e.target.checked)} />
      <span>{label}</span>
    </label>
  );
  return (
    <>
      <div className="consent-box">
        <b>개인정보 수집·이용 안내</b>
        <table>
          <tbody>
            <tr>
              <th>항목</th>
              <td>{PRIVACY_TABLE[kind]}</td>
            </tr>
            <tr>
              <th>목적</th>
              <td>회원 식별·로그인, 리뷰 작성자 표시, 북마크·알림</td>
            </tr>
            <tr>
              <th>보관</th>
              <td>
                <b>탈퇴할 때까지</b> (탈퇴하면 지난 기록까지 바로 지워요)
              </td>
            </tr>
          </tbody>
        </table>
        <span>
          이메일·전화번호·실명은 받지 않아요. 동의하지 않으면 가입할 수 없지만, 로그인 없이도 둘러볼 수 있어요.
        </span>
      </div>
      <div className="ck-all">
        <label className="ck">
          <input
            type="checkbox"
            checked={all}
            onChange={(e) => setOn(Object.fromEntries(keys.map((k) => [k, e.target.checked])))}
          />
          <span>약관 전체 동의{photoLabel ? " (선택 항목 포함)" : ""}</span>
        </label>
      </div>
      {box("age", "[필수] 만 14세 이상이에요")}
      {box("terms", "[필수] 이용약관에 동의해요")}
      {box("privacy", "[필수] 위 개인정보 수집·이용에 동의해요")}
      {photoLabel && box("photo", photoLabel)}
      <div className="consent-link consent-note">
        전문 보기:{" "}
        <a href="/privacy" target="_blank" rel="noopener">
          개인정보처리방침 · 이용약관
        </a>{" "}
        · 만 14세 미만은 가입할 수 없어요 (법정대리인 동의 절차를 갖추지 않았어요)
      </div>
    </>
  );
}
