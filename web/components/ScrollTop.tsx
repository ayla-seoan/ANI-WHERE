"use client";
import { useEffect, useState } from "react";
import { ExpandMore } from "./Icons";

// 스크롤하면 화면 아래 가운데에 뜨는 '맨 위로' (앱 #aw-top)
export default function ScrollTop() {
  const [on, setOn] = useState(false);
  useEffect(() => {
    const f = () => setOn(window.scrollY > 600);
    f();
    window.addEventListener("scroll", f, { passive: true });
    return () => window.removeEventListener("scroll", f);
  }, []);
  if (!on) return null;
  return (
    <button
      type="button"
      id="aw-top"
      aria-label="맨 위로"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
    >
      <ExpandMore className="up" />
    </button>
  );
}
