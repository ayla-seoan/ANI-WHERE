import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";
import { NextResponse, type NextRequest } from "next/server";

// 팝업 목록 캐시(10분, lib/data.ts 의 'popups' 꼬리표)를 바로 비운다 (11/25).
// Streamlit 앱이나 GitHub Actions 가 Notion 에서 새 팝업을 Supabase 에 넣어도 이 웹은 그 사실을 몰라서,
// 10분 캐시가 지나고도 한 번 더 열어야 보였다. 가져오기가 끝나면 그쪽에서 이 주소를 부른다 (common/web_refresh.py).
// 하는 일은 캐시 비우기 하나뿐이고 데이터를 읽거나 쓰지 않는다. 비밀값(WEB_REVALIDATE_SECRET)은 서버 환경변수에만 둔다.
export const dynamic = "force-dynamic";

const NO_STORE = { "Cache-Control": "no-store" };

function same(a: string, b: string): boolean {
  const x = Buffer.from(a, "utf8");
  const y = Buffer.from(b, "utf8");
  return x.length === y.length && timingSafeEqual(x, y);
}

export async function POST(req: NextRequest) {
  const secret = (process.env.WEB_REVALIDATE_SECRET || "").trim();
  if (secret.length < 16) return NextResponse.json({ ok: false, error: "설정되지 않음" }, { status: 503, headers: NO_STORE });
  const given = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "").trim();
  if (!given || !same(given, secret)) return NextResponse.json({ ok: false }, { status: 401, headers: NO_STORE });
  revalidateTag("popups");
  return NextResponse.json({ ok: true }, { headers: NO_STORE });
}
