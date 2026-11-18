import { NextResponse } from "next/server";
import { getPopup } from "@/lib/data";
import { enabled, search, withThumbs, type Post } from "@/lib/server/blog";

// GET /api/blog/<팝업 id>[?thumbs=0] → 그 팝업의 네이버 블로그 후기 (앱 _blog_posts · _blog_list).
//   { enabled, posts: [{ title, link, desc, blogger, day, thumb }], count, error }
// 키(NAVER_BLOG_CLIENT_ID / _SECRET)가 없으면 { enabled: false, posts: [], count: 0 } — 화면은 '연결한 뒤에 보여요' 안내.
// 같은 팝업은 하루 한 번만 검색한다 (앱 st.cache_data(ttl=86400) 와 같게). 대표 사진은 thumbs=0 이 아닐 때만 가져온다.

export const dynamic = "force-dynamic";

const DAY = 86_400_000;
const LIMIT = 15; // 앱과 같게 최대 15건
type Found = { at: number; posts: Post[]; error: string };
const found = new Map<string, Found>();
const thumbs = new Map<string, { at: number; url: string }>();

async function postsFor(id: string): Promise<Found | null> {
  const hit = found.get(id);
  // 실패(연결 실패 · 한도)는 10분만 기억하고 다시 해 본다
  if (hit && Date.now() - hit.at < (hit.error ? 600_000 : DAY)) return hit;
  const p = await getPopup(id);
  if (!p) return null;
  const [posts, error] = await search(
    { work: p.work, cafe_name: p.name === "매장 미정" ? "" : p.name, start_date: p.start, address: p.address },
    LIMIT,
    true, // 한 달 호출 한도 안에서만
  );
  const f = { at: Date.now(), posts, error };
  found.set(id, f);
  if (found.size > 2000) found.delete(found.keys().next().value as string);
  return f;
}

async function thumbsFor(posts: Post[]): Promise<Record<string, string>> {
  const need = posts.filter((p) => {
    const t = thumbs.get(p.link);
    return !t || Date.now() - t.at > DAY;
  });
  for (const [p, url] of await withThumbs(need)) thumbs.set(p.link, { at: Date.now(), url });
  if (thumbs.size > 5000) thumbs.delete(thumbs.keys().next().value as string);
  return Object.fromEntries(posts.map((p) => [p.link, thumbs.get(p.link)?.url || ""]));
}

export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const wantThumbs = new URL(req.url).searchParams.get("thumbs") !== "0";
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
  const th = wantThumbs ? await thumbsFor(f.posts) : {};
  const posts = f.posts.map((p) => ({ ...p, thumb: th[p.link] || "" }));
  return NextResponse.json(
    { enabled: true, posts, count: posts.length, error: f.error },
    { headers: head(f.error ? 600 : 86_400) },
  );
}
