"use client";
import { useEffect } from "react";

// 튜토리얼 '처음 3단계' 배너: 끌어서 넘기기 + 양옆 ‹ › (앱 _DRAG_JS 의 .g-slides 부분을 옮김).
// 문서(HTML)는 서버에서 그대로 그리고, 이 조각은 화면에 붙은 뒤 버튼과 끌기만 더한다.
export default function GuideSlides() {
  useEffect(() => {
    const row = document.querySelector<HTMLElement>(".pg-guide .g-slides");
    const box = row?.parentElement;
    if (!row || !box) return;
    if (getComputedStyle(box).position === "static") box.style.position = "relative";
    const mk = (cls: string, txt: string, label: string) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `aw-arrow ${cls}`;
      b.textContent = txt;
      b.setAttribute("aria-label", label);
      box.appendChild(b);
      return b;
    };
    const l = mk("l", "‹", "이전");
    const r = mk("r", "›", "다음");
    l.onclick = () => row.scrollBy({ left: -row.clientWidth * 0.8 });
    r.onclick = () => row.scrollBy({ left: row.clientWidth * 0.8 });
    const place = () => {
      const top = row.getBoundingClientRect().top - box.getBoundingClientRect().top + 140 - (l.offsetHeight || 28) / 2;
      l.style.top = r.style.top = `${top}px`;
      l.classList.toggle("show", row.scrollLeft > 4);
      r.classList.toggle("show", row.scrollLeft + row.clientWidth < row.scrollWidth - 4);
    };
    // 마우스로 끌기 (손가락은 기본 가로 스크롤)
    let down = false;
    let x0 = 0;
    let s0 = 0;
    let moved = 0;
    const onDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      down = true;
      moved = 0;
      x0 = e.pageX;
      s0 = row.scrollLeft;
    };
    const onMove = (e: MouseEvent) => {
      if (!down) return;
      const dx = e.pageX - x0;
      moved = Math.max(moved, Math.abs(dx));
      if (moved > 5) {
        row.classList.add("aw-dragging");
        row.scrollLeft = s0 - dx;
        e.preventDefault();
      }
    };
    const onUp = () => {
      down = false;
      setTimeout(() => row.classList.remove("aw-dragging"), 0);
    };
    const onClick = (e: MouseEvent) => {
      if (moved > 5) {
        e.preventDefault();
        e.stopPropagation();
        moved = 0;
      }
    };
    const noDrag = (e: Event) => e.preventDefault();
    row.addEventListener("mousedown", onDown);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    row.addEventListener("click", onClick, true);
    row.addEventListener("dragstart", noDrag);
    row.addEventListener("scroll", place, { passive: true });
    window.addEventListener("resize", place);
    place();
    const t = setTimeout(place, 400);
    // 주소 끝 #add 같은 칸으로 (그림이 늦게 그려져도 맞는 자리로 한 번 더)
    const id = decodeURIComponent(location.hash.slice(1));
    const t2 = id ? setTimeout(() => document.getElementById(id)?.scrollIntoView({ block: "start" }), 300) : undefined;
    return () => {
      clearTimeout(t);
      if (t2) clearTimeout(t2);
      row.removeEventListener("mousedown", onDown);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      row.removeEventListener("click", onClick, true);
      row.removeEventListener("dragstart", noDrag);
      row.removeEventListener("scroll", place);
      window.removeEventListener("resize", place);
      l.remove();
      r.remove();
    };
  }, []);
  return null;
}
