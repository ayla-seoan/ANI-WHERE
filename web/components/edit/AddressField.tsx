"use client";
import { useRef, useState } from "react";
import { postcodeAction } from "@/app/popup-actions";
import type { Picked } from "@/lib/cafe-rules";
import { ClearInput } from "./Fields";

// 주소 입력칸 + 카카오 우편번호 찾기 (앱 address_field · common/kakao_postcode.py · components/kakao_postcode).
// 우편번호 서비스는 키가 필요 없고 좌표를 주지 않아서, 고른 주소의 좌표는 서버(geo.ts)가 따로 찾는다.
// 팝업 창은 브라우저가 막을 수 있어 화면 안에 펼친다.

type PostcodeData = { roadAddress?: string; jibunAddress?: string; autoJibunAddress?: string; address?: string; buildingName?: string; zonecode?: string };
type PostcodeCtor = new (o: { width: string; height: string; oncomplete: (d: PostcodeData) => void }) => { embed: (el: HTMLElement) => void };
declare global {
  interface Window {
    daum?: { Postcode?: PostcodeCtor };
  }
}

const SDKS = [
  "https://t1.kakaocdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js",
  "https://t1.daumcdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js",
];
let sdk: Promise<PostcodeCtor> | null = null;

function ctor(): PostcodeCtor | undefined {
  const k = (window as unknown as { kakao?: { Postcode?: PostcodeCtor } }).kakao;
  return k?.Postcode || window.daum?.Postcode;
}

function loadSdk(): Promise<PostcodeCtor> {
  const have = ctor();
  if (have) return Promise.resolve(have);
  return (sdk ||= new Promise<PostcodeCtor>((resolve, reject) => {
    const tryAt = (i: number) => {
      if (i >= SDKS.length) {
        sdk = null;
        reject(new Error("load"));
        return;
      }
      const s = document.createElement("script");
      s.src = SDKS[i];
      s.async = true;
      s.onload = () => {
        const c = ctor();
        if (c) resolve(c);
        else tryAt(i + 1);
      };
      s.onerror = () => tryAt(i + 1);
      document.head.appendChild(s);
    };
    tryAt(0);
  }));
}

export default function AddressField({
  value,
  onChange,
  onPick,
  placeholder = "",
}: {
  value: string;
  onChange: (v: string) => void;
  onPick: (p: Picked & { name: string }) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  const close = () => {
    setOpen(false);
    if (box.current) box.current.innerHTML = "";
  };
  const toggle = () => {
    if (open) {
      close();
      return;
    }
    setOpen(true);
    setMsg("");
    loadSdk().then(
      (Postcode) => {
        if (!box.current) return;
        box.current.innerHTML = "";
        new Postcode({
          width: "100%",
          height: "100%",
          oncomplete: (d) => {
            const address = d.roadAddress || d.jibunAddress || d.address || "";
            const jibun = d.jibunAddress || d.autoJibunAddress || "";
            close();
            setBusy(true);
            // 건물 이름은 카페명과 다를 때가 많아 넘기지 않는다
            postcodeAction(address, jibun)
              .then((c) => onPick({ ...c, precision: c.precision || "none", name: "" }))
              .catch(() => onPick({ address, lat: 0, lng: 0, source: "카카오 우편번호", precision: "none", name: "" }))
              .finally(() => setBusy(false));
          },
        }).embed(box.current);
      },
      () => setMsg("카카오 우편번호 서비스를 불러오지 못했습니다. 인터넷 연결을 확인해 주세요."),
    );
  };

  return (
    <div className="ed-field">
      <label className="ed-label" htmlFor="ed-addr">
        주소
      </label>
      <ClearInput id="ed-addr" value={value} onChange={onChange} placeholder={placeholder} maxLength={200} />
      <button type="button" className="btn-line ed-post" onClick={toggle} disabled={busy}>
        {busy ? "주소 확인 중…" : open ? "닫기" : "우편번호로 주소 찾기"}
      </button>
      <div ref={box} className="ed-postbox" hidden={!open} />
      {open && msg && <div className="ed-cap">{msg}</div>}
    </div>
  );
}
