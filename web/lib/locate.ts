"use client";
import { useEffect, useState } from "react";

// 내 위치 (앱 common/locate.py 와 같은 규칙, 11/19 요청: 지도로 보기에 위치 기반 서비스).
// 위치는 이 브라우저 안에서만 쓰고 서버 · 저장소 어디에도 보내거나 저장하지 않는다.
export type LatLng = { lat: number; lng: number };

/** 브라우저에 위치를 한 번 묻는다. 거절 · 실패면 null (화면은 위치 없이 그대로 돈다) */
export function useMyLocation(): LatLng | null {
  const [me, setMe] = useState<LatLng | null>(null);
  useEffect(() => {
    if (typeof navigator === "undefined" || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (p) => setMe({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => setMe(null),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    );
  }, []);
  return me;
}

/** 두 좌표 사이 거리(km). 지역 순서 · 처음 화면을 정하는 데만 쓰니 구면 근사로 충분하다 (locate._km) */
export function km(a: LatLng, b: LatLng): number {
  const r = Math.PI / 180;
  const h =
    Math.sin(((b.lat - a.lat) * r) / 2) ** 2 +
    Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((b.lng - a.lng) * r) / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(h));
}

/** 지도 처음 화면: 나를 가운데 두고 가장 가까운 팝업 k 곳이 들어오는 범위 (locate.home_box, 반경 3~40km) */
export function homeBox(me: LatLng, points: LatLng[], k = 3) {
  const near = points.map((p) => km(me, p)).sort((a, b) => a - b).slice(0, k);
  const rKm = Math.min(Math.max((near.length ? near[near.length - 1] : 5) * 1.15, 3), 40);
  const dLat = rKm / 111;
  const dLng = rKm / (111 * Math.max(Math.cos((me.lat * Math.PI) / 180), 0.2));
  return { south: me.lat - dLat, north: me.lat + dLat, west: me.lng - dLng, east: me.lng + dLng };
}

/** 지역 이름들을 내 위치에서 가까운 순으로 (지역마다 팝업들의 가운데를 잰다, locate.areas_by_distance) */
export function areasByDistance(me: LatLng, points: { area: string; lat: number; lng: number }[]): string[] {
  const sums = new Map<string, [number, number, number]>();
  for (const p of points) {
    const s = sums.get(p.area) ?? [0, 0, 0];
    sums.set(p.area, [s[0] + p.lat, s[1] + p.lng, s[2] + 1]);
  }
  return [...sums.entries()]
    .map(([a, s]) => [a, km(me, { lat: s[0] / s[2], lng: s[1] / s[2] })] as const)
    .sort((x, y) => x[1] - y[1])
    .map(([a]) => a);
}
