import type { Metadata } from "next";
import { GUIDE_CSS, GUIDE_HTML } from "@/content/docs.gen";
import IconFont from "@/components/pages/IconFont";
import GuideSlides from "@/components/pages/GuideSlides";

// 사용자 튜토리얼 (앱 page_guide). 물어보기의 '사용법 알려줘' 가 /guide#map 같은 칸으로 안내한다.
// 내용은 docs/guide.md, 꾸밈은 static/guide/guide.css, 그림은 static/guide/*.png — scripts/sync_docs.mjs 가 옮겨 온다.
// 칸 id: home · map · list · bookmark · cal · add · edit · delete · login · ask · mobile
export const metadata: Metadata = {
  title: "사용자 튜토리얼",
  description: "ANI:WHERE 사용법: 홈 · 지도 · 리스트 · 북마크 · 내 캘린더 · 등록 · 수정 · 삭제 요청 · 로그인 · 물어보기.",
  alternates: { canonical: "/guide" },
};

export default function GuidePage() {
  return (
    <>
      <IconFont />
      <style dangerouslySetInnerHTML={{ __html: GUIDE_CSS }} />
      <div className="pg-wrap pg-guide" dangerouslySetInnerHTML={{ __html: GUIDE_HTML }} />
      <GuideSlides />
    </>
  );
}
