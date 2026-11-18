"use client";
import { useEffect } from "react";
import { rememberRecent } from "./KeepBox";

/** 상세를 열면 '최근 본 팝업'에 남긴다 (이 브라우저에만) */
export default function RememberRecent({ id }: { id: string }) {
  useEffect(() => rememberRecent(id), [id]);
  return null;
}
