"use client";
import { useCallback, useEffect, useRef, useState } from "react";

// 옆으로 넘기는 줄 (앱 _DRAG_JS 와 같은 동작): 넘길 게 있으면 양옆에 ‹ › 버튼, PC 에서는 끌어서 넘긴다.
export default function HScroll({
  className,
  children,
  label,
}: {
  className: string;
  children: React.ReactNode;
  label?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [left, setLeft] = useState(false);
  const [right, setRight] = useState(false);

  const update = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    setLeft(el.scrollLeft > 4);
    setRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  }, []);

  useEffect(() => {
    update();
    const el = ref.current;
    if (!el) return;
    el.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    // 끌어서 넘기기 (마우스만. 터치는 브라우저 기본 스크롤)
    let down = false;
    let moved = false;
    let x0 = 0;
    let s0 = 0;
    const onDown = (e: PointerEvent) => {
      if (e.pointerType !== "mouse" || e.button !== 0) return;
      down = true;
      moved = false;
      x0 = e.clientX;
      s0 = el.scrollLeft;
    };
    const onMove = (e: PointerEvent) => {
      if (!down) return;
      const dx = e.clientX - x0;
      if (Math.abs(dx) > 5) {
        moved = true;
        el.classList.add("aw-dragging");
      }
      if (moved) el.scrollLeft = s0 - dx;
    };
    const onUp = () => {
      down = false;
      setTimeout(() => el.classList.remove("aw-dragging"), 0);
    };
    // 끌고 난 뒤의 클릭은 링크로 넘어가지 않게
    const onClick = (e: MouseEvent) => {
      if (moved) {
        e.preventDefault();
        e.stopPropagation();
        moved = false;
      }
    };
    el.addEventListener("pointerdown", onDown);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    el.addEventListener("click", onClick, true);
    return () => {
      el.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
      el.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      el.removeEventListener("click", onClick, true);
    };
  }, [update]);

  const go = (dir: number) => {
    const el = ref.current;
    if (el) el.scrollBy({ left: dir * Math.max(200, el.clientWidth * 0.8), behavior: "smooth" });
  };

  return (
    <div className="hs-wrap">
      <div ref={ref} className={`hs ${className}`} role={label ? "region" : undefined} aria-label={label}>
        {children}
      </div>
      <button type="button" className={`aw-arrow l${left ? " show" : ""}`} aria-label="이전" onClick={() => go(-1)}>
        ‹
      </button>
      <button type="button" className={`aw-arrow r${right ? " show" : ""}`} aria-label="다음" onClick={() => go(1)}>
        ›
      </button>
    </div>
  );
}
