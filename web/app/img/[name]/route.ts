import { NextResponse, type NextRequest } from "next/server";
import { RAW_ROOT, rawHeaders } from "@/lib/server/github";

// /img/<파일 이름> → 예전에 앱에서 올린 사진 (저장소 static/uploads). 11/20 요청: 브라우저에 깃허브 주소가 보이지 않게
// 서버가 대신 받아 준다. 파일 이름이 내용 해시라 같은 이름이면 늘 같은 그림 → CDN 에 오래 둔다.
const TYPES: Record<string, string> = {
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  webp: "image/webp",
  gif: "image/gif",
  avif: "image/avif",
};

export async function GET(_: NextRequest, { params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  const m = /^[\w.-]+\.(png|jpe?g|webp|gif|avif)$/i.exec(name);
  if (!m || name.includes("..")) return new NextResponse("Not found", { status: 404 });
  let res: Response;
  try {
    res = await fetch(`${RAW_ROOT}/static/uploads/${encodeURIComponent(name)}`, {
      headers: rawHeaders(),
      cache: "no-store", // 그림은 아래 CDN 캐시가 맡는다 (데이터 캐시는 2MB 넘는 그림을 못 담음)
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return new NextResponse("Not found", { status: 404, headers: { "Cache-Control": "public, s-maxage=60" } });
  }
  if (!res.ok) return new NextResponse("Not found", { status: 404, headers: { "Cache-Control": "public, s-maxage=300" } });
  return new NextResponse(res.body, {
    headers: {
      "Content-Type": TYPES[m[1].toLowerCase()],
      "Cache-Control": "public, max-age=86400, s-maxage=31536000, immutable",
    },
  });
}
