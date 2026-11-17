"use client";
import { useEffect } from "react";

/** 서비스 워커 등록. 개발 중(npm run dev)에는 캐시가 수정 확인을 방해하므로 production 빌드에서만. */
export default function SWRegister() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;
    const register = () => {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((err) => {
        console.warn("서비스 워커 등록 실패", err);
      });
    };
    if (document.readyState === "complete") register();
    else {
      window.addEventListener("load", register, { once: true });
      return () => window.removeEventListener("load", register);
    }
  }, []);
  return null;
}
