"use client";
import { useEffect } from "react";

// 메뉴바 모션 (11/19 요청, 미리보기에서 고른 것):
//   로고 · 검색 · 알림 · 마이페이지(로그인) — 젤리: 흰 바탕이 생기며 살짝 기울었다 통통 (동그라미 모양은 그대로)
//   홈 · 지도로 보기 · 리스트로 보기 · 내 캘린더 — 말랑 알약: 흰 알약이 미끄러져 따라오고 늘었다가 출렁 멈춤
// PC 는 마우스를 올리면, 폰은 누르면 (폰은 1.2초 뒤 사라짐). '움직임 줄이기' 설정이면 CSS 에서 움직이지 않는다.
const PILL = ".gnb-tabs a";
const JELLY = ".gnb-search, .gnb-bell, .gnb-me, .gnb-login, .gnb-admin";
const LOGO = ".gnb-logo";

const restart = (el: Element, cls: string) => {
  el.classList.remove(cls);
  void (el as HTMLElement).offsetWidth;
  el.classList.add(cls);
};

export default function GnbMotion() {
  useEffect(() => {
    const gnb = document.querySelector<HTMLElement>(".gnb");
    if (!gnb) return;
    const blob = document.createElement("span");
    blob.className = "gnb-blob";
    blob.setAttribute("aria-hidden", "true");
    gnb.prepend(blob);
    let timer = 0;
    const hide = () => blob.classList.remove("show");

    const pillTo = (t: HTMLElement, touch: boolean) => {
      const g = gnb.getBoundingClientRect();
      const r = t.getBoundingClientRect();
      Object.assign(blob.style, {
        left: `${r.left - g.left - 2}px`,
        top: `${r.top - g.top - 2}px`,
        width: `${r.width + 4}px`,
        height: `${r.height + 4}px`,
      });
      blob.classList.add("show");
      restart(blob, "move");
      restart(t, "gnb-hit");
      clearTimeout(timer);
      if (touch) timer = window.setTimeout(hide, 1200);
    };
    const jelly = (t: HTMLElement, touch: boolean) => {
      hide();
      t.classList.add("gnb-on");
      restart(t, "gnb-jelly");
      if (touch) window.setTimeout(() => t.classList.remove("gnb-on"), 1200);
    };
    const pick = (
      e: PointerEvent,
    ): [HTMLElement | null, "pill" | "jelly" | "logo" | null] => {
      const el = e.target as HTMLElement | null;
      const p = el?.closest<HTMLElement>(PILL);
      if (p) return [p, "pill"];
      const j = el?.closest<HTMLElement>(JELLY);
      if (j) return [j, "jelly"];
      const l = el?.closest<HTMLElement>(LOGO);
      if (l) return [l, "logo"];
      return [null, null];
    };
    let last: HTMLElement | null = null;
    const over = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      const [t, kind] = pick(e);
      if (!t || t === last) return;
      if (last) last.classList.remove("gnb-on");
      last = t;
      if (kind === "pill") pillTo(t, false);
      else if (kind === "jelly") jelly(t, false);
      else if (kind === "logo") {
        hide();
        restart(t, "gnb-jelly");
      }
    };
    const out = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      const to = e.relatedTarget as HTMLElement | null;
      if (last && !last.contains(to)) {
        last.classList.remove("gnb-on");
        last = null;
      }
    };
    const down = (e: PointerEvent) => {
      if (e.pointerType === "mouse") return;
      const [t, kind] = pick(e);
      if (!t) return;
      if (kind === "pill") pillTo(t, true);
      else if (kind === "jelly") jelly(t, true);
      else if (kind === "logo") restart(t, "gnb-jelly");
    };
    const leave = (e: PointerEvent) => {
      if (e.pointerType === "mouse") hide();
    };
    gnb.addEventListener("pointerover", over);
    gnb.addEventListener("pointerout", out);
    gnb.addEventListener("pointerdown", down);
    gnb.addEventListener("pointerleave", leave);
    return () => {
      gnb.removeEventListener("pointerover", over);
      gnb.removeEventListener("pointerout", out);
      gnb.removeEventListener("pointerdown", down);
      gnb.removeEventListener("pointerleave", leave);
      clearTimeout(timer);
      blob.remove();
    };
  }, []);
  return null;
}
