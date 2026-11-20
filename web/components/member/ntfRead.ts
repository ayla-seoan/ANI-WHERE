"use client";
import { useCallback, useMemo, useSyncExternalStore } from "react";

// 읽은 알림 번호 (앱 _ntf_read · _ntf_mark): 쿠키 aw_ntf_read_<회원 해시> 에 8자리 번호를 '.' 로 이어 둔다.
// 종과 내 캘린더 '알림 받은 내역' 이 같은 쿠키를 보므로 한쪽에서 읽으면 다른 쪽도 바로 '읽음'.
const EVT = "aw:ntf";
const MAX_AGE = 5184000; // 60일 (앱과 같게)

function cookieOf(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? m[1] : null;
}

function subscribe(cb: () => void) {
  window.addEventListener(EVT, cb);
  return () => window.removeEventListener(EVT, cb);
}

export type NtfRead = { read: Set<string>; mark: (ids: string[]) => void };

/** cookie = 쿠키 이름 (서버가 회원 번호로 만든다), initial = 서버가 읽어 둔 값 (첫 화면이 깜빡이지 않게) */
export function useNtfRead(cookie: string, initial: string): NtfRead {
  const raw = useSyncExternalStore(
    subscribe,
    () => cookieOf(cookie) ?? initial,
    () => initial,
  );
  const read = useMemo(() => new Set(raw.split(".").filter((x) => /^[0-9a-f]{8}$/.test(x))), [raw]);
  const mark = useCallback(
    (ids: string[]) => {
      const all = new Set([...read, ...ids.filter((x) => /^[0-9a-f]{8}$/.test(x))]);
      // 앱: '.'.join(sorted(read)[-200:])
      const v = [...all].sort().slice(-200).join(".");
      try {
        document.cookie = `${cookie}=${v}; path=/; max-age=${MAX_AGE}; SameSite=Lax`;
      } catch {
        /* 쿠키가 막혀도 이번 화면은 그대로 */
      }
      window.dispatchEvent(new Event(EVT));
    },
    [cookie, read],
  );
  return { read, mark };
}

// ---- '내 주변 추천' 위치 (브라우저 위치 권한을 허용했을 때만) ----
export type NearItem = {
  id: string;
  cafeId: string;
  dist: string;
  work: string;
  cafe: string;
  poster: string;
  area?: string; // 지역 칩 (11/20)
  city?: string;
};
export type Near = { state: "idle" | "asking" | "denied" | "off" | "done"; items: NearItem[] };

let pos: { lat: number; lng: number } | null | undefined;

/** 위치 권한이 이미 허용돼 있으면 묻지 않고 바로 (ask=false), 사용자가 눌렀으면 물어본다 (ask=true) */
export async function myPosition(ask: boolean): Promise<{ lat: number; lng: number } | null> {
  if (pos !== undefined) return pos;
  if (typeof navigator === "undefined" || !navigator.geolocation) return (pos = null);
  if (!ask) {
    try {
      const st = await navigator.permissions?.query({ name: "geolocation" as PermissionName });
      if (!st || st.state !== "granted") return null;
    } catch {
      return null;
    }
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (p) => resolve((pos = { lat: p.coords.latitude, lng: p.coords.longitude })),
      () => resolve((pos = null)),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    );
  });
}

export async function fetchNear(kind: "bell" | "cal", ask: boolean): Promise<Near> {
  const p = await myPosition(ask);
  if (!p) return { state: ask ? "denied" : "idle", items: [] };
  try {
    const res = await fetch(`/api/near?for=${kind}&lat=${p.lat.toFixed(5)}&lng=${p.lng.toFixed(5)}`, { cache: "no-store" });
    if (!res.ok) return { state: "denied", items: [] };
    const j = (await res.json()) as { enabled: boolean; items: NearItem[] };
    return { state: j.enabled ? "done" : "off", items: j.items || [] };
  } catch {
    return { state: "denied", items: [] };
  }
}
