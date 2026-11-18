import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 여러 작업을 동시에 시험할 때 빌드 폴더를 나눈다 (기본 .next). 배포에서는 쓰지 않는다
  distDir: process.env.NEXT_DIST_DIR || ".next",
  poweredByHeader: false,
  // 사진 올리기(서버 액션)는 포스터 20MB 까지
  experimental: { serverActions: { bodySizeLimit: "60mb" } },
  // 물어보기 AI 프롬프트 파일(content/prompts)을 배포본에 꼭 넣는다 (서버가 실행 중에 fs 로 읽는다)
  outputFileTracingIncludes: { "/ask": ["./content/prompts/**"], "/add": ["./content/prompts/**"] },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
      {
        // 서비스 워커 파일은 항상 새로 받아야 VERSION 을 올린 것이 바로 반영된다
        source: "/sw.js",
        headers: [
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
          { key: "Service-Worker-Allowed", value: "/" },
        ],
      },
    ];
  },
};

export default nextConfig;
