import { NextResponse, type NextRequest } from "next/server";
import { oauthMock } from "@/lib/server/auth";

// 시험용 가짜 카카오·네이버 동의 화면 (WEB_STORAGE=local + WEB_OAUTH_MOCK=1 일 때만). 배포에서는 404.
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  if (!oauthMock()) return new NextResponse("Not found", { status: 404 });
  const q = req.nextUrl.searchParams;
  const uid = (q.get("uid") || "1").replace(/[^\w]/g, "").slice(0, 20) || "1";
  const url = new URL("/auth", req.nextUrl.origin);
  url.searchParams.set("code", `mock-${uid}`);
  url.searchParams.set("state", q.get("state") || "");
  return NextResponse.redirect(url);
}
