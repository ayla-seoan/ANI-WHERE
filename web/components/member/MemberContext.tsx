"use client";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useState } from "react";
import { toggleFavAction } from "@/app/actions";
import { toast } from "./Toast";

// 로그인한 회원 · 내 북마크를 화면 어디서나 (레이아웃이 서버에서 읽어 넘겨준다).
export type MeLite = { nick: string; avatar: string; admin: boolean; key4: string } | null;
type Ctx = { me: MeLite; favs: Set<string>; toggle: (cafeId: string) => void };

const MemberCtx = createContext<Ctx>({ me: null, favs: new Set(), toggle: () => {} });

/** 손님이 회원 기능을 누름 → 로그인 화면으로 (앱 _need_login 처럼 안내를 함께) */
export function goLogin(router: ReturnType<typeof useRouter>, msg: string, next: string) {
  try {
    document.cookie = `aw_flash=${encodeURIComponent(msg)}; path=/; max-age=30; SameSite=Lax`;
  } catch {
    /* 무시 */
  }
  router.push(`/login?next=${encodeURIComponent(next)}`);
}

export function MemberProvider({ me, favIds, children }: { me: MeLite; favIds: string[]; children: React.ReactNode }) {
  const [favs, setFavs] = useState(() => new Set(favIds));
  const [prevIds, setPrevIds] = useState(favIds);
  if (prevIds !== favIds) {
    // 서버에서 새로 읽어 왔으면 (로그인·로그아웃·다른 화면) 그 값으로
    setPrevIds(favIds);
    setFavs(new Set(favIds));
  }
  const router = useRouter();
  const path = usePathname() || "/";
  const toggle = useCallback(
    (cafeId: string) => {
      if (!me) {
        goLogin(router, "북마크는 로그인하면 쓸 수 있어요.", path);
        return;
      }
      const on = !favs.has(cafeId);
      const flip = (want: boolean) =>
        setFavs((cur) => {
          const n = new Set(cur);
          if (want) n.add(cafeId);
          else n.delete(cafeId);
          return n;
        });
      flip(on); // 누르자마자 바뀌고, 저장이 실패하면 되돌린다
      toggleFavAction(cafeId, on).then((res) => {
        if (!res.ok) {
          flip(!on);
          if (res.login) goLogin(router, res.error || "로그인해 주세요.", path);
          else toast(res.error || "북마크를 저장하지 못했어요. 잠시 뒤 다시 눌러 주세요.", "error");
          return;
        }
        toast(
          on ? "북마크했어요. 내 캘린더에서 볼 수 있어요." : "북마크를 해제했어요.",
          on ? "bookmark" : "unbookmark",
        );
      });
    },
    [me, favs, router, path],
  );
  return <MemberCtx.Provider value={{ me, favs, toggle }}>{children}</MemberCtx.Provider>;
}

export const useMember = () => useContext(MemberCtx);
