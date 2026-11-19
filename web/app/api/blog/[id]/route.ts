import { NextResponse } from "next/server";
import { getPopup } from "@/lib/data";
import { enabled, refresh, type SavedPost } from "@/lib/server/blog";

// GET /api/blog/<팝업 id>[?thumbs=0] → 그 팝업의 네이버 블로그 후기 (앱 _blog_list).
//   { enabled, posts: [{ title, link, desc, blogger, day, thumb }], count, error }
// 키(NAVER_BLOG_CLIENT_ID / _SECRET)가 없으면 { enabled: false, posts: [], count: 0 } — 화면은 '연결한 뒤에 보여요' 안내.
// 11/19 요청: 찾은 글은 blog_posts 표에 저장해 두고 여기서 바로 읽는다. 네이버는 팝업마다 하루 한 번만 물어 새 글만 더한다
// (blog.refresh, 앱과 같은 표). 대표 사진도 저장해 둬서 thumbs=0 이어도 같이 온다.

export const dynamic = "force-dynamic";

type Found = { at: number; posts: SavedPost[]; error: string };
const found = new Map<string, Found>(); // 같은 서버에서 잠깐(1분 · 실패는 10분) 기억 — 표 읽기도 줄인다

async function postsFor(id: string): Promise<Found | null> {
  const hit = found.get(id);
  if (hit && Date.now() - hit.at < (hit.error ? 600_000 : 60_000)) return hit;
  const p = await getPopup(id);
  if (!p) return null;
  const [posts, error] = await refresh(id, {
    work: p.work,
    cafe_name: p.name === "매장 미정" ? "" : p.name,
    start_date: p.start,
    address: p.address,
  });
  const f = { at: Date.now(), posts, error };
  found.set(id, f);
  if (found.size > 2000) found.delete(found.keys().next().value as string);
  return f;
}

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const head = (sec: number) => ({ "Cache-Control": `public, max-age=0, s-maxage=${sec}, stale-while-revalidate=600` });
  if (!enabled()) return NextResponse.json({ enabled: false, posts: [], count: 0, error: "off" }, { headers: head(600) });
  if (!/^[\w-]{1,64}$/.test(id)) return NextResponse.json({ error: "잘못된 주소" }, { status: 400 });
  let f: Found | null;
  try {
    f = await postsFor(id);
  } catch {
    f = { at: Date.now(), posts: [], error: "검색 실패" };
  }
  if (!f) return NextResponse.json({ enabled: true, posts: [], count: 0, error: "팝업 없음" }, { status: 404 });
  // 저장해 둔 글이 있으면 실패 표시는 보내지 않는다 (화면은 저장된 글을 보여 준다)
  const error = f.posts.length ? "" : f.error;
  return NextResponse.json(
    { enabled: true, posts: f.posts, count: f.posts.length, error },
    { headers: head(error ? 300 : 600) },
  );
}
