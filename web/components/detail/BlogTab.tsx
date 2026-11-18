"use client";
import { useEffect, useState } from "react";

// 상세 '블로그 후기' 탭 (앱 _render_blog_tab · _bcard). 서버 /api/blog/<id> 가 네이버 블로그를 찾아 준다.
//   안내 한 줄 + 카드 (제목 · 요약 2줄 · 블로거 · 날짜, 오른쪽 대표 사진). 누르면 원문 새 탭.
// useBlogCount(id) 는 서브탭 이름 '블로그 후기 (n)' 의 숫자 (대표 사진 없이 가볍게 센다). 모르면 null.

export type BlogPost = { title: string; link: string; desc: string; blogger: string; day: string; thumb: string };
type BlogData = { enabled: boolean; posts: BlogPost[]; count: number; error?: string };

const OFF: BlogData = { enabled: false, posts: [], count: 0 };
const full = new Map<string, Promise<BlogData>>();
const light = new Map<string, Promise<BlogData>>();

function load(cafeId: string, thumbs: boolean): Promise<BlogData> {
  const box = thumbs ? full : light;
  let p = box.get(cafeId);
  if (!p) {
    p = fetch(`/api/blog/${encodeURIComponent(cafeId)}${thumbs ? "" : "?thumbs=0"}`)
      .then(async (r) => {
        const j = (await r.json()) as Partial<BlogData>;
        return {
          enabled: Boolean(j.enabled),
          posts: Array.isArray(j.posts) ? j.posts : [],
          count: Number(j.count) || 0,
          error: j.error,
        };
      })
      .catch(() => {
        box.delete(cafeId); // 다음에 다시 해 본다
        return { ...OFF, enabled: true, error: "연결 실패" };
      });
    box.set(cafeId, p);
  }
  return p;
}

/** 서브탭 '블로그 후기 (n)' 숫자. 세는 중이면 null, 연결 전·못 찾음은 0 (앱 n_blog or 0) */
export function useBlogCount(cafeId: string): number | null {
  const [n, setN] = useState<{ id: string; n: number } | null>(null);
  useEffect(() => {
    let live = true;
    // 탭을 이미 열어 대표 사진까지 받았으면 그것을 쓴다
    (full.get(cafeId) ?? load(cafeId, false)).then((d) => live && setN({ id: cafeId, n: d.count }));
    return () => {
      live = false;
    };
  }, [cafeId]);
  return n && n.id === cafeId ? n.n : null;
}

/** 'YYYY-MM-DD' → 'YYYY. MM. DD' (앱 f'{day:%Y. %m. %d}') */
const dayText = (d: string) => (/^\d{4}-\d{2}-\d{2}$/.test(d) ? d.replace(/-/g, ". ") : "");

function Note() {
  return (
    <div className="blog-note">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} aria-hidden>
        <circle cx="12" cy="12" r="9" />
        <path d="M8 12.3l2.7 2.7L16.2 9.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      네이버 블로그 검색 결과예요. 부정확한 결과가 포함될 수 있으니 참고로만 봐 주세요.
    </div>
  );
}

export default function BlogTab({ cafeId }: { cafeId: string }) {
  const [data, setData] = useState<{ id: string; d: BlogData } | null>(null);
  useEffect(() => {
    let live = true;
    load(cafeId, true).then((d) => live && setData({ id: cafeId, d }));
    return () => {
      live = false;
    };
  }, [cafeId]);
  const d = data && data.id === cafeId ? data.d : null;

  return (
    <div className="blog-tab">
      <Note />
      {!d ? (
        <div className="blog-empty">블로그 후기를 찾고 있어요…</div>
      ) : !d.enabled ? (
        <div className="blog-empty">블로그 후기는 네이버 검색을 연결한 뒤에 보여요.</div>
      ) : !d.posts.length ? (
        <div className="blog-empty">아직 이 팝업의 블로그 후기를 찾지 못했어요.</div>
      ) : (
        <div className="bcards">
          {d.posts.map((p) => (
            <a key={p.link} className="bcard" href={p.link} target="_blank" rel="noopener noreferrer">
              <div className="bcard-txt">
                <div className="bcard-t">{p.title}</div>
                <div className="bcard-d">{p.desc}</div>
                <div className="bcard-m">
                  <span>{p.blogger || "블로그"}</span>
                  <span>{dayText(p.day)}</span>
                </div>
              </div>
              {p.thumb && (
                <img
                  className="bcard-img"
                  src={p.thumb}
                  alt=""
                  loading="lazy"
                  referrerPolicy="no-referrer"
                  onError={(e) => {
                    e.currentTarget.style.display = "none"; // 사진이 안 열리면 깨진 그림 대신 칸을 비운다
                  }}
                />
              )}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
