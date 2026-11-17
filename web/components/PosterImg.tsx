"use client";
import { useState } from "react";
import { PLACEHOLDER_POSTER } from "@/lib/popup";

/** 포스터 이미지. 주소가 없거나 깨지면 기본 그림으로 바꾼다. 외부(GitHub raw) 이미지라 일반 img 를 쓴다. */
export default function PosterImg({ src, alt, eager = false }: { src?: string; alt: string; eager?: boolean }) {
  const [broken, setBroken] = useState(false);
  return (
    <img
      src={!src || broken ? PLACEHOLDER_POSTER : src}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
      onError={() => setBroken(true)}
    />
  );
}
