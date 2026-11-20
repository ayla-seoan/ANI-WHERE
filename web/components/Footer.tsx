import FootLink from "@/components/FootLink";

// 앱(Streamlit) 바닥글과 똑같이 (11/18 요청): © 연도 ANI:WHERE · 운영 · 문의 + 개인정보처리방침 · 사용자 튜토리얼 · 디자인 시스템.
// 문의 연락처는 바닥글에 그대로 쓰지 않고 개인정보처리방침 10절에만 둔다 (11/20: 공유할 때 개인 메일이 모든 화면에 보이지 않게, 앱과 같게).
// 처리방침 · 튜토리얼 · 디자인 시스템도 이 웹 안의 화면으로 연다 (Streamlit 으로 넘어가지 않게).
export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="aw-foot">
      <div>© {year} ANI:WHERE</div>
      <div>
        운영: ANI:WHERE · 문의: <FootLink href="/privacy">개인정보처리방침 10. 연락처</FootLink>
      </div>
      <div className="aw-foot-links">
        <FootLink href="/privacy">개인정보처리방침 · 이용약관</FootLink>
        <FootLink href="/guide">사용자 튜토리얼</FootLink>
        <FootLink href="/design">디자인 시스템</FootLink>
      </div>
    </footer>
  );
}
