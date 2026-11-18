"use client";
import { usePathname, useRouter } from "next/navigation";
import { useActionState, useEffect, useRef, useState } from "react";
import { requestDeleteAction } from "@/app/admin-actions";
import { goLogin, useMember } from "@/components/member/MemberContext";
import { toast } from "@/components/member/Toast";
import { submitWith } from "@/lib/submit";

// 일반 회원의 게시글 삭제 요청 (앱 delete_request_dialog): '삭제 요청' 버튼 → 가운데 대화상자에서 이유를 적어 보낸다.
// 관리자가 '관리자 > 삭제 요청' 에서 승인/거부하고, 결과는 알림으로 간다. 손님이 누르면 로그인 화면으로.

const LABEL: Record<string, string> = { review: "리뷰", cafe: "팝업" };
const MAX_REASON = 300;

export default function DeleteRequestButton({
  targetType,
  targetId,
  title,
}: {
  targetType: "cafe" | "review";
  targetId: string;
  title: string;
}) {
  const { me } = useMember();
  const router = useRouter();
  const path = usePathname() || "/";
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        className="btn-line dr-btn"
        onClick={() => {
          if (!me) {
            goLogin(router, "로그인한 회원만 삭제를 요청할 수 있어요.", path);
            return;
          }
          setOpen(true);
        }}
      >
        삭제 요청
      </button>
      {open && (
        <RequestDialog
          targetType={targetType}
          targetId={targetId}
          title={title}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}

function RequestDialog({
  targetType,
  targetId,
  title,
  onClose,
}: {
  targetType: string;
  targetId: string;
  title: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const path = usePathname() || "/";
  const [s, action, busy] = useActionState(requestDeleteAction, null);
  const [reason, setReason] = useState("");
  const seen = useRef(s);
  const box = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (s === seen.current) return;
    seen.current = s;
    if (s?.ok) {
      toast(s.ok, "ok");
      onClose();
      router.refresh();
    } else if (s?.login) {
      goLogin(router, s.error || "로그인해 주세요.", path);
    }
  }, [s, onClose, router, path]);
  useEffect(() => {
    box.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", esc);
      document.body.style.overflow = prev;
    };
  }, [onClose]);
  return (
    <div className="dlg-bg" onClick={onClose}>
      <div className="dlg dr-dlg" role="dialog" aria-modal="true" aria-label="삭제 요청" onClick={(e) => e.stopPropagation()}>
        <div className="dr-head">
          <b className="dlg-t">삭제 요청</b>
          <button type="button" className="dr-x" onClick={onClose} aria-label="닫기">
            <svg viewBox="0 0 24 24" aria-hidden>
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <p className="dr-what">
          <b>{LABEL[targetType] || "게시글"}</b> · {[...title].slice(0, 60).join("")}
        </p>
        <form onSubmit={submitWith(action)} className="dr-form">
          <input type="hidden" name="target_type" value={targetType} />
          <input type="hidden" name="target_id" value={targetId} />
          <input type="hidden" name="title" value={title} />
          <label className="dr-label" htmlFor={`dr_reason_${targetId}`}>
            삭제를 요청하는 이유
          </label>
          <textarea
            ref={box}
            id={`dr_reason_${targetId}`}
            name="reason"
            maxLength={MAX_REASON}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="예: 잘못된 정보예요 / 광고·도배 글이에요 / 이미 끝난 행사예요"
            rows={4}
          />
          <div className="dr-count">
            {[...reason].length}/{MAX_REASON}
          </div>
          {s?.error && !s.login && (
            <div className="dr-warn" role="alert">
              <svg viewBox="0 0 24 24" aria-hidden>
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7.5v5.5M12 16.5v.1" />
              </svg>
              {s.error}
            </div>
          )}
          <button type="submit" className="btn-main" disabled={busy}>
            요청 보내기
          </button>
        </form>
      </div>
    </div>
  );
}
