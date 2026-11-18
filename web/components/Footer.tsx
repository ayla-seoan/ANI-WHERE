import Link from "next/link";

// 앱(Streamlit) 바닥글과 똑같이 (11/18 요청): © 연도 ANI:WHERE · 운영 · 문의 + 개인정보처리방침 · 사용자 튜토리얼 · 디자인 시스템.
// 연락처는 앱(app_cafemap.py CONTACT_EMAIL)과 docs/privacy-policy.md 10절에 공개한 것과 같다.
// 처리방침 · 튜토리얼 · 디자인 시스템도 이 웹 안의 화면으로 연다 (Streamlit 으로 넘어가지 않게).
const CONTACT_EMAIL = "tjtek888@gmail.com";

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="aw-foot">
      <div>© {year} ANI:WHERE</div>
      <div>
        운영: ANI:WHERE · 문의: <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
      </div>
      <div className="aw-foot-links">
        <Link href="/privacy">개인정보처리방침 · 이용약관</Link>
        <Link href="/guide">사용자 튜토리얼</Link>
        <Link href="/design">디자인 시스템</Link>
      </div>
    </footer>
  );
}
