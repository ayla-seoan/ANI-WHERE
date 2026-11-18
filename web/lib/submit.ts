"use client";
import { startTransition, type FormEvent } from "react";

// 서버 액션 폼 보내기. <form action={...}> 은 보낸 뒤 입력칸을 모두 비워서(React 19 폼 초기화),
// 틀린 비밀번호 · 동의 빠짐 같은 안내가 뜰 때 쓴 내용이 사라졌다 → 기본 제출을 막고 직접 보낸다 (입력은 그대로 남는다).
export function submitWith(action: (fd: FormData) => void) {
  return (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    startTransition(() => action(fd));
  };
}
