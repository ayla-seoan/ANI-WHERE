"use client";
/* eslint-disable @typescript-eslint/no-explicit-any -- 카카오·Leaflet SDK 는 window 전역이라 타입 정의 없이 쓴다 */
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { periodDot, PLACEHOLDER_POSTER, type Item } from "@/lib/popup";
import { CloseIcon } from "../Icons";

// 지도 (앱 components/kakao_map 과 같은 모양): 물방울 핀, 커서를 올리면 포스터 카드, 누르면 지도 안 미리보기 창.
// 카카오 지도 JS 키(NEXT_PUBLIC_KAKAO_JS_KEY, 브라우저용 공개 키)가 있으면 카카오맵, 없거나 6초 안에 못 불러오면
// Leaflet + OpenStreetMap 으로 대신 그린다. 둘 다 실패해도 화면은 멈추지 않고 안내 글만 보인다.

import { homeBox } from "@/lib/locate";
import { toast } from "../member/Toast";

export type Bounds = { south: number; west: number; north: number; east: number };

const KAKAO_KEY = process.env.NEXT_PUBLIC_KAKAO_JS_KEY || "";
const LEAFLET = "https://unpkg.com/leaflet@1.9.4/dist/";
// 처음 화면 범위가 없을 때: 포천~제주
const MAINLAND_JEJU: Bounds = { south: 33.15, west: 126.1, north: 37.95, east: 129.45 };

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const old = document.querySelector<HTMLScriptElement>(`script[data-src="${src}"]`);
    if (old) {
      if (old.dataset.loaded === "1") return resolve();
      old.addEventListener("load", () => resolve());
      old.addEventListener("error", () => reject(new Error("load")));
      return;
    }
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.dataset.src = src;
    s.onload = () => {
      s.dataset.loaded = "1";
      resolve();
    };
    s.onerror = () => reject(new Error("load"));
    document.head.appendChild(s);
  });
}

function loadCss(href: string) {
  if (document.querySelector(`link[href="${href}"]`)) return;
  const l = document.createElement("link");
  l.rel = "stylesheet";
  l.href = href;
  document.head.appendChild(l);
}

async function loadKakao(key: string): Promise<any> {
  const w = window as any;
  if (!w.kakao?.maps?.LatLng) {
    await loadScript(`https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&appkey=${encodeURIComponent(key)}`);
    // 도메인이 등록되지 않으면 준비가 끝나지 않고 멈추기도 해서, 6초 안에 안 되면 실패로 본다 (앱과 같은 규칙)
    await new Promise<void>((resolve, reject) => {
      const t = setTimeout(() => reject(new Error("kakao maps timeout")), 6000);
      try {
        w.kakao.maps.load(() => {
          clearTimeout(t);
          resolve();
        });
      } catch (e) {
        clearTimeout(t);
        reject(e);
      }
    });
  }
  return w.kakao.maps;
}

async function loadLeaflet(): Promise<any> {
  const w = window as any;
  if (!w.L) {
    loadCss(`${LEAFLET}leaflet.css`);
    await loadScript(`${LEAFLET}leaflet.js`);
  }
  return w.L;
}

/** 커서를 올리면 뜨는 카드 (사용자가 쓴 글이라 textContent 로 넣는다) */
function tipCard(list: Item[]): HTMLElement {
  const card = document.createElement("div");
  card.className = "map-tip";
  list.slice(0, 3).forEach((q) => {
    const item = document.createElement("div");
    item.className = "item";
    const img = document.createElement("img");
    img.src = q.poster || PLACEHOLDER_POSTER;
    img.alt = "";
    img.onerror = () => {
      img.src = PLACEHOLDER_POSTER;
    };
    const box = document.createElement("div");
    (
      [
        ["w", q.work],
        ["c", q.name],
        ["a", q.address || "-"],
        ["d", periodDot(q)],
      ] as const
    ).forEach(([cls, text]) => {
      const d = document.createElement("div");
      d.className = cls;
      d.textContent = text;
      box.appendChild(d);
    });
    item.append(img, box);
    card.appendChild(item);
  });
  if (list.length > 3) {
    const m = document.createElement("div");
    m.className = "more";
    m.textContent = `+ 같은 곳에 ${list.length - 3}곳 더 · 눌러서 모두 보기`;
    card.appendChild(m);
  }
  return card;
}

type Engine = {
  draw: (pts: Item[], selected: string) => void;
  focus: (p: Item) => void;
  /** 내 위치: 그 둘레로 화면을 옮기고 파란 점을 찍는다 (11/19, 앱 home_box). b 가 없으면 내 자리로 확대 */
  showMe: (me: { lat: number; lng: number }, b?: Bounds) => void;
  destroy: () => void;
};

function kakaoEngine(
  K: any,
  el: HTMLElement,
  home: Bounds | null,
  onPin: (p: Item) => void,
  onBlank: () => void,
): Engine {
  const box = (b: Bounds) => new K.LatLngBounds(new K.LatLng(b.south, b.west), new K.LatLng(b.north, b.east));
  const map = new K.Map(el, { center: new K.LatLng(36.3, 127.8), level: 12 });
  map.setMaxLevel(14);
  map.setBounds(box(MAINLAND_JEJU), 0, 0, 0, 0);
  map.setMaxLevel(map.getLevel());
  if (home) map.setBounds(box(home), 20, 20, 20, 20);
  map.addControl(new K.ZoomControl(), K.ControlPosition.RIGHT);
  let overlays: any[] = [];
  let tip: any = null;
  let meDot: any = null;
  let lastPin = 0;
  K.event.addListener(map, "click", () => {
    if (Date.now() - lastPin > 400) onBlank();
  });
  const onResize = () => map.relayout();
  window.addEventListener("resize", onResize);
  return {
    draw(pts, selected) {
      overlays.forEach((o) => o.setMap(null));
      overlays = [];
      if (tip) tip.setMap(null);
      tip = null;
      pts.forEach((p) => {
        const pos = new K.LatLng(p.lat, p.lng);
        const pin = document.createElement("div");
        pin.className = `pin${p.id === selected ? " sel" : ""}`;
        pin.setAttribute("role", "button");
        pin.setAttribute("aria-label", `${p.work} ${p.name}`);
        pin.onmousedown = () => {
          lastPin = Date.now();
        };
        pin.onclick = (e) => {
          lastPin = Date.now();
          e.stopPropagation();
          onPin(p);
        };
        pin.onmouseenter = () => {
          if (tip) tip.setMap(null);
          const here = pts.filter((q) => q.lat === p.lat && q.lng === p.lng);
          const card = tipCard([p, ...here.filter((q) => q.id !== p.id)]);
          card.classList.add("kcard");
          tip = new K.CustomOverlay({ position: pos, content: card, yAnchor: 1, zIndex: 3, clickable: false });
          tip.setMap(map);
          if (card.parentElement) card.parentElement.style.pointerEvents = "none";
        };
        pin.onmouseleave = () => {
          if (tip) tip.setMap(null);
          tip = null;
        };
        const o = new K.CustomOverlay({
          position: pos,
          content: pin,
          zIndex: p.id === selected ? 2 : 1,
          clickable: true,
          xAnchor: 0.5,
          yAnchor: 1.15,
        });
        o.setMap(map);
        overlays.push(o);
      });
    },
    focus(p) {
      if (map.getLevel() > 5) map.setLevel(5);
      map.panTo(new K.LatLng(p.lat, p.lng));
    },
    showMe(me, b) {
      const pos = new K.LatLng(me.lat, me.lng);
      if (b) map.setBounds(box(b), 20, 20, 20, 20);
      else {
        if (map.getLevel() > 5) map.setLevel(5);
        map.panTo(pos);
      }
      if (meDot) meDot.setPosition(pos);
      else {
        const dot = document.createElement("div");
        dot.className = "me-dot";
        dot.setAttribute("aria-label", "내 위치");
        meDot = new K.CustomOverlay({ position: pos, content: dot, zIndex: 4, clickable: false });
        meDot.setMap(map);
      }
    },
    destroy() {
      window.removeEventListener("resize", onResize);
      overlays.forEach((o) => o.setMap(null));
    },
  };
}

function leafletEngine(
  L: any,
  el: HTMLElement,
  home: Bounds | null,
  onPin: (p: Item) => void,
  onBlank: () => void,
): Engine {
  const b = home || MAINLAND_JEJU;
  const map = L.map(el, {
    zoomControl: false,
    attributionControl: true,
    minZoom: 6,
    maxBounds: [
      [-11, 60],
      [56, 150],
    ],
  });
  map.fitBounds([
    [b.south, b.west],
    [b.north, b.east],
  ]);
  L.control.zoom({ position: "topright" }).addTo(map);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap",
    maxZoom: 19,
    className: "tiles-base",
  }).addTo(map);
  let lastPin = 0;
  map.on("click", () => {
    if (Date.now() - lastPin > 400) onBlank();
  });
  const layer = L.layerGroup().addTo(map);
  let meMark: any = null;
  const ro = new ResizeObserver(() => map.invalidateSize());
  ro.observe(el);
  return {
    draw(pts, selected) {
      layer.clearLayers();
      pts.forEach((p) => {
        const sel = p.id === selected;
        const icon = L.divIcon({
          className: "pin-wrap",
          html: `<div class="pin${sel ? " sel" : ""}"></div>`,
          iconSize: sel ? [34, 34] : [26, 26],
          iconAnchor: sel ? [17, 40] : [13, 31],
        });
        const m = L.marker([p.lat, p.lng], {
          icon,
          zIndexOffset: sel ? 1000 : 0,
          keyboard: true,
          title: `${p.work} ${p.name}`,
        });
        const here = pts.filter((q) => q.lat === p.lat && q.lng === p.lng);
        m.bindTooltip(() => tipCard([p, ...here.filter((q) => q.id !== p.id)]), {
          direction: "top",
          offset: [0, -30],
          className: "tip-l",
          opacity: 1,
        });
        m.on("click", () => {
          lastPin = Date.now();
          onPin(p);
        });
        m.addTo(layer);
      });
    },
    focus(p) {
      map.setView([p.lat, p.lng], Math.max(map.getZoom(), 14));
    },
    showMe(me, b) {
      if (b)
        map.fitBounds([
          [b.south, b.west],
          [b.north, b.east],
        ]);
      else map.setView([me.lat, me.lng], Math.max(map.getZoom(), 15));
      if (meMark) meMark.setLatLng([me.lat, me.lng]);
      else
        meMark = L.marker([me.lat, me.lng], {
          icon: L.divIcon({ className: "me-wrap", html: '<div class="me-dot"></div>', iconSize: [16, 16], iconAnchor: [8, 8] }),
          keyboard: false,
          interactive: false,
          zIndexOffset: 2000,
        }).addTo(map);
    },
    destroy() {
      ro.disconnect();
      map.remove();
    },
  };
}

export default function MapCanvas({
  points,
  home,
  focus,
  me = null,
  onMe,
}: {
  points: Item[];
  home: Bounds | null;
  /** 내 위치 (허용했을 때만). 처음 한 번 그 둘레로 화면을 옮긴다 */
  me?: { lat: number; lng: number } | null;
  /** '내 위치' 버튼으로 새 위치를 받았을 때 (데일리 노트도 가까운 지역부터 다시) */
  onMe?: (me: { lat: number; lng: number }) => void;
  /** 바깥(데일리 노트·목록)에서 고른 팝업: 그 자리로 옮기고 미리보기 창을 연다. n 이 바뀔 때마다 다시 */
  focus: { id: string; n: number } | null;
}) {
  const el = useRef<HTMLDivElement>(null);
  const engine = useRef<Engine | null>(null);
  const [kind, setKind] = useState<"loading" | "kakao" | "leaflet" | "error">("loading");
  const [spot, setSpot] = useState<Item[] | null>(null);
  const [selected, setSelected] = useState("");
  const pts = points.filter((p) => p.lat !== null && p.lng !== null);
  const ptsRef = useRef(pts);
  ptsRef.current = pts;

  const openSpot = (p: Item) => {
    const here = ptsRef.current.filter((q) => q.lat === p.lat && q.lng === p.lng);
    setSpot([p, ...here.filter((q) => q.id !== p.id)]);
    setSelected(p.id);
  };

  // 지도 만들기 (처음 한 번)
  useEffect(() => {
    let dead = false;
    const node = el.current;
    if (!node) return;
    const onPin = (p: Item) => openSpot(p);
    const onBlank = () => setSpot(null);
    (async () => {
      if (KAKAO_KEY) {
        try {
          const K = await loadKakao(KAKAO_KEY);
          if (dead) return;
          engine.current = kakaoEngine(K, node, home, onPin, onBlank);
          setKind("kakao");
          return;
        } catch (e) {
          console.warn(
            "카카오 지도를 불러오지 못해 OpenStreetMap 으로 표시합니다. 카카오 개발자 콘솔 > 플랫폼 > Web 에 이 사이트 도메인이 등록됐는지 확인해 주세요.",
            e,
          );
          node.innerHTML = "";
        }
      }
      try {
        const L = await loadLeaflet();
        if (dead) return;
        engine.current = leafletEngine(L, node, home, onPin, onBlank);
        setKind("leaflet");
      } catch {
        if (!dead) setKind("error");
      }
    })();
    return () => {
      dead = true;
      engine.current?.destroy();
      engine.current = null;
    };
    // 지도는 처음 한 번만 만든다 (home 은 처음 화면 범위)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 내 위치가 오면 한 번만 그 둘레로 (앱: 지도 처음 화면을 내 주변으로, 가까운 팝업 3곳이 들어오게)
  const meDone = useRef(false);
  useEffect(() => {
    if (!me || meDone.current || !engine.current) return;
    meDone.current = true;
    engine.current.showMe(me, homeBox(me, ptsRef.current as { lat: number; lng: number }[]));
  }, [me, kind]);

  // '내 위치' 버튼 (11/19 요청): 누를 때마다 지금 위치를 다시 받아 내 자리로 확대해 옮긴다
  const [locating, setLocating] = useState(false);
  const goMe = () => {
    if (!navigator.geolocation) {
      toast("이 브라우저는 위치를 알려 주지 않아요.", "error");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setLocating(false);
        meDone.current = true;
        const here = { lat: p.coords.latitude, lng: p.coords.longitude };
        engine.current?.showMe(here);
        onMe?.(here);
      },
      () => {
        setLocating(false);
        toast("위치를 알 수 없어요. 브라우저 주소창의 위치 권한을 허용해 주세요.", "error");
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  };

  // 점 다시 그리기
  const sig = pts.map((p) => p.id).join(",");
  useEffect(() => {
    if (engine.current) engine.current.draw(ptsRef.current, selected);
  }, [sig, selected, kind]);

  // 바깥에서 고른 팝업으로 옮기기
  useEffect(() => {
    if (!focus || !engine.current) return;
    const p = ptsRef.current.find((q) => q.id === focus.id);
    if (!p) return;
    engine.current.focus(p);
    openSpot(p);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus?.n, kind]);

  return (
    <div className="map-box">
      <div ref={el} className="map-canvas" />
      {(kind === "kakao" || kind === "leaflet") && (
        <button
          type="button"
          className={`map-me${locating ? " busy" : ""}${kind === "leaflet" ? " leaf" : ""}`}
          aria-label="내 현재 위치로"
          onClick={goMe}
          disabled={locating}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
            <circle cx="12" cy="12" r="8" />
          </svg>
        </button>
      )}
      {kind === "loading" && <div className="map-msg">지도를 불러오는 중…</div>}
      {kind === "error" && (
        <div className="map-msg">
          지금은 지도를 불러오지 못했어요.
          <br />
          왼쪽 데일리 팝업 노트나 리스트로 보기에서 팝업을 찾아보세요.
        </div>
      )}
      {spot && (
        <div className="map-spot" role="dialog" aria-label="팝업 미리보기">
          <div className="head">
            <span>{spot.length > 1 ? `이 자리의 팝업 ${spot.length}곳` : "팝업 미리보기"}</span>
            <button type="button" className="x" aria-label="닫기" onClick={() => setSpot(null)}>
              <CloseIcon />
            </button>
          </div>
          {spot.map((q) => (
            <Link key={q.id} href={`/popup/${q.id}`} className="item" prefetch={false}>
              <img
                src={q.poster || PLACEHOLDER_POSTER}
                alt=""
                loading="lazy"
                onError={(e) => {
                  if (!e.currentTarget.src.endsWith(PLACEHOLDER_POSTER)) e.currentTarget.src = PLACEHOLDER_POSTER;
                }}
              />
              <div>
                <div className="w">{q.work}</div>
                <div className="c">{q.name}</div>
                <div className="a">{q.address}</div>
                <div className="d">{periodDot(q)}</div>
              </div>
              <span className="go" aria-hidden>
                ›
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
