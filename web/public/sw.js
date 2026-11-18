/* ANI:WHERE 서비스 워커 (직접 작성, 플러그인 없음)
 * - 정적 파일(/_next/static, /icons, 로고)·포스터 이미지: 캐시 먼저 (cache-first)
 * - 화면(HTML): 네트워크 먼저, 실패하면 저장된 화면 → 그것도 없으면 /offline
 * - 바꿀 때는 VERSION 을 올린다. activate 때 예전 캐시를 지운다.
 */
const VERSION = "v3"; // v3: 회원 기능 — 로그인·내 캘린더 화면은 저장하지 않는다 (v2: 앱과 같은 화면, 기본 포스터·로고 바뀜)
const STATIC_CACHE = `aniwhere-static-${VERSION}`;
const PAGE_CACHE = `aniwhere-pages-${VERSION}`;
const IMAGE_CACHE = `aniwhere-images-${VERSION}`;
const KEEP = [STATIC_CACHE, PAGE_CACHE, IMAGE_CACHE];
const OFFLINE_URL = "/offline";
const PRECACHE = [
  OFFLINE_URL,
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/logo_mint_sm.webp",
  "/default_poster.webp",
];
const MAX_IMAGES = 150;
const MAX_PAGES = 60;

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith("aniwhere-") && !KEEP.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function trim(cacheName, max) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - max; i++) await cache.delete(keys[i]);
}

async function cacheFirst(request, cacheName, max) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(request);
  if (hit) return hit;
  try {
    const res = await fetch(request);
    // 외부 이미지는 no-cors 로 오면 opaque(status 0) 다. 그래도 img 로 보여 줄 수 있어 저장한다.
    if (res.ok || res.type === "opaque") {
      cache.put(request, res.clone()).then(() => max && trim(cacheName, max));
    }
    return res;
  } catch (err) {
    if (request.destination === "image") {
      const ph = await caches.match("/default_poster.webp");
      if (ph) return ph;
    }
    throw err;
  }
}

async function networkFirstPage(request) {
  const cache = await caches.open(PAGE_CACHE);
  try {
    const res = await fetch(request);
    if (res.ok) cache.put(request, res.clone()).then(() => trim(PAGE_CACHE, MAX_PAGES));
    return res;
  } catch {
    const hit = (await cache.match(request)) || (await cache.match(request, { ignoreSearch: true }));
    if (hit) return hit;
    const offline = await caches.match(OFFLINE_URL);
    return offline || new Response("오프라인", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // 포스터 이미지 (GitHub raw 의 static/uploads)
  if (url.hostname === "raw.githubusercontent.com" && url.pathname.includes("/static/uploads/")) {
    event.respondWith(cacheFirst(request, IMAGE_CACHE, MAX_IMAGES));
    return;
  }
  if (url.origin !== self.location.origin) return;

  // 로그인 · 가입 · 내 캘린더는 회원 개인 화면이라 저장하지 않는다 (공용 기기에서 오프라인으로 남지 않게)
  if (request.mode === "navigate" && /^\/(login|auth|calendar)(\/|$)/.test(url.pathname)) return;

  // 화면 이동 (주소창·링크로 새 페이지 열기)
  if (request.mode === "navigate") {
    event.respondWith(networkFirstPage(request));
    return;
  }

  // Next.js 화면 데이터(RSC)는 저장하지 않는다. 실패하면 Next 가 일반 이동으로 바꾸고 위 규칙을 탄다.
  if (request.headers.get("RSC") || url.searchParams.has("_rsc")) return;

  // 이름에 해시가 붙은 정적 파일·아이콘·그림
  if (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname.startsWith("/icons/") ||
    /\.(png|svg|webp|jpg|jpeg|ico|woff2?)$/.test(url.pathname)
  ) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
  }
});
