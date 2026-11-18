import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "ANI:WHERE — 애니 팝업·콜라보 카페 찾기",
    short_name: "ANI:WHERE",
    description: "지금 열린 애니메이션 팝업스토어·콜라보 카페를 찾고 가기 전에 확인하는 지도",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#ffffff",
    theme_color: "#E9F7F2",
    lang: "ko",
    dir: "ltr",
    categories: ["entertainment", "lifestyle", "travel"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "지도로 보기", short_name: "지도", url: "/map" },
      { name: "리스트로 보기", short_name: "리스트", url: "/list" },
      { name: "이번 주 팝업", short_name: "이번 주", url: "/this-week" },
    ],
  };
}
