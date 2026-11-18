"use client";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, useTransition } from "react";
import { bookmarkSetAction } from "@/app/actions";
import { workKey } from "@/lib/popup";
import { posterBg } from "../cards";
import { AddIcon } from "../Icons";
import { useMember } from "./MemberContext";
import { toast } from "./Toast";

// '최애 추가하기' (앱 bookmark_pick_dialog): 검색칸 + 포스터 격자에서 팝업을 눌러 고르고, 저장하면 한 번에 북마크된다
// (내 캘린더 · 알림 · 북마크 팝업 줄에 반영). 고른 것이 앞으로 오고, 그다음 진행 중 → 예정, 시작일 순. 60개까지 보인다.

export type PickItem = { id: string; work: string; name: string; chars: string; poster: string; period: string; rank: number; start: string };


export default function BookmarkPicker({ items }: { items: PickItem[] }) {
  const router = useRouter();
  const { favs } = useMember();
  const [open, setOpen] = useState(false);
  const [pick, setPick] = useState<string[]>([]);
  const [q, setQ] = useState("");
  const [busy, start] = useTransition();
  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", esc);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", esc);
      document.body.style.overflow = "";
    };
  }, [open]);

  const shown = useMemo(() => {
    const k = workKey(q);
    const rows = [...items].sort(
      (a, b) =>
        Number(!pick.includes(a.id)) - Number(!pick.includes(b.id)) || a.rank - b.rank || a.start.localeCompare(b.start),
    );
    return (k ? rows.filter((r) => workKey(`${r.work}${r.name}${r.chars}`).includes(k)) : rows).slice(0, 60);
  }, [items, pick, q]);

  const toggle = (id: string) => setPick((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  const save = () =>
    start(async () => {
      const res = await bookmarkSetAction(pick);
      if (res?.error) {
        toast(res.error, "error");
        return;
      }
      setOpen(false);
      toast(res?.ok || "", "bookmark");
      router.refresh();
    });

  return (
    <>
      <button
        type="button"
        className="story add"
        onClick={() => {
          setPick([...favs].sort());
          setQ("");
          setOpen(true);
        }}
      >
        <span className="ring">
          <AddIcon />
        </span>
        <span className="nm">최애 추가하기</span>
      </button>
      {open && (
        <div className="dlg-bg fw-bg" onClick={() => setOpen(false)}>
          <div className="dlg fw-dlg" role="dialog" aria-label="최애 추가하기" onClick={(e) => e.stopPropagation()}>
            <div className="fw-top">
              <b className="dlg-t">최애 추가하기</b>
              <button type="button" className="fw-x" aria-label="닫기" onClick={() => setOpen(false)}>
                <svg viewBox="0 0 24 24" aria-hidden>
                  <path d="M6 6l12 12M18 6L6 18" />
                </svg>
              </button>
            </div>
            <div className="fw-title">놓치고 싶지 않은 팝업을 골라 주세요</div>
            <div className="fw-sub">
              북마크한 팝업은 내 캘린더와 알림으로 챙겨 드리고, 그 작품이 &apos;내가 관심있는 작품&apos; 맨 앞에 보여요.
            </div>
            <div className="fw-count">
              <b>{pick.length}</b>개 선택
            </div>
            <label className="fw-search">
              <svg viewBox="0 0 24 24" aria-hidden>
                <circle cx="11" cy="11" r="6.5" />
                <path d="M16 16l4.5 4.5" />
              </svg>
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="작품 · 카페 이름으로 검색"
                aria-label="팝업 검색"
              />
            </label>
            {!shown.length && <div className="ntf-empty fw-none">찾는 팝업이 없어요. 다른 이름으로 검색해 보세요.</div>}
            <div className="fw-grid">
              {shown.map((r) => {
                const on = pick.includes(r.id);
                return (
                  <button
                    key={r.id}
                    type="button"
                    className={`fwc${on ? " on" : ""}`}
                    aria-pressed={on}
                    onClick={() => toggle(r.id)}
                  >
                    <span className="fwp" style={posterBg(r.poster)}>
                      {on && (
                        <span className="fwchk">
                          <svg viewBox="0 0 24 24" aria-hidden>
                            <path d="M5 12.5l4.5 4.5L19 7.5" />
                          </svg>
                        </span>
                      )}
                    </span>
                    <span className="fwn">{r.work}</span>
                    <span className="fwm">{r.name}</span>
                    <span className="fwm">{r.period}</span>
                  </button>
                );
              })}
            </div>
            <div className="fw-foot">
              <button type="button" className="fw-skip" onClick={() => setOpen(false)}>
                다음에 할게요
              </button>
              <button type="button" className="btn-main fw-save" disabled={busy} onClick={save}>
                <svg viewBox="0 0 24 24" aria-hidden>
                  <circle cx="12" cy="12" r="9" />
                  <path d="M8 12.3l2.8 2.8L16.2 9.6" />
                </svg>
                저장하기
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
