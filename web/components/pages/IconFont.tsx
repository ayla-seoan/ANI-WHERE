import { ICON_NAMES } from "@/content/docs.gen";

// 튜토리얼 · 디자인 시스템 문서는 앱(Streamlit)처럼 <span class="mi">이름</span> 아이콘(Material Symbols Rounded)을 쓴다.
// 이 페이지에서만, 쓰는 아이콘 이름만 골라 글꼴을 받는다 (React 19 가 <head> 로 올려 준다).
export default function IconFont() {
  const href =
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,0,0" +
    `&icon_names=${ICON_NAMES.join(",")}&display=block`;
  return <link rel="stylesheet" href={href} precedence="default" />;
}
