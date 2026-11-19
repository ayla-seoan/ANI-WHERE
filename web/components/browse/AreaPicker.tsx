"use client";
import { useEffect, useRef, useState } from "react";
import { ExpandMore } from "../Icons";

// 지역 고르기 — 여러 곳을 함께 고를 수 있다 (앱 st.multiselect '지역 고르기 (여러 곳 가능)', 11/19 요청).
// 값은 쉼표로 이은 글자 ('마포,송파', '' = 전체) — 주소창 ?area= 와 그대로 맞는다.
export const splitAreas = (v: string): string[] => v.split(",").map((x) => x.trim()).filter(Boolean);

export default function AreaPicker({
  value,
  areas,
  onChange,
  className = "",
}: {
  value: string;
  areas: string[];
  onChange: (v: string) => void;
  className?: string;
}) {
  const picked = splitAreas(value);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);
  const all = [...areas, ...picked.filter((a) => !areas.includes(a))];
  const toggle = (a: string) =>
    onChange((picked.includes(a) ? picked.filter((x) => x !== a) : [...picked, a]).join(","));
  const label = picked.length ? (picked.length <= 2 ? picked.join(", ") : `${picked[0]} 외 ${picked.length - 1}곳`) : "";
  return (
    <div className={`area-pick ${className}`} ref={box}>
      <button
        type="button"
        className={`area-pick-btn${picked.length ? " on" : ""}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="지역 고르기"
        onClick={() => setOpen((o) => !o)}
      >
        <span>{label || "지역 고르기 (여러 곳 가능)"}</span>
        <ExpandMore />
      </button>
      {open && (
        <div className="area-pick-pop" role="listbox" aria-multiselectable="true">
          <button type="button" className={`area-opt${picked.length ? "" : " on"}`} onClick={() => onChange("")}>
            전체
          </button>
          {all.map((a) => (
            <button
              key={a}
              type="button"
              role="option"
              aria-selected={picked.includes(a)}
              className={`area-opt${picked.includes(a) ? " on" : ""}`}
              onClick={() => toggle(a)}
            >
              {a}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
