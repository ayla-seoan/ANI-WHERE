"use client";
import { useEffect, useState } from "react";

// '홈 화면에 추가' 안내. 안드로이드/크롬은 beforeinstallprompt 로 설치 버튼, iOS 사파리는 방법만 글로 보여 준다.
// 닫으면 localStorage 에 기억한다 (사생활 보호 모드 등에서 막히면 이번 방문만 숨김).

const KEY = "aniwhere.installHint.dismissed";

type BIPEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function wasDismissed(): boolean {
  try {
    return window.localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

function remember() {
  try {
    window.localStorage.setItem(KEY, "1");
  } catch {
    /* 저장이 막혀 있어도 동작은 계속 */
  }
}

function isStandalone(): boolean {
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return window.matchMedia?.("(display-mode: standalone)").matches || nav.standalone === true;
}

function isIOSSafari(): boolean {
  const ua = window.navigator.userAgent;
  const ios = /iphone|ipad|ipod/i.test(ua) || (/macintosh/i.test(ua) && navigator.maxTouchPoints > 1);
  const otherBrowser = /crios|fxios|edgios|kakaotalk|naver|instagram|fban|line\//i.test(ua);
  return ios && /safari/i.test(ua) && !otherBrowser;
}

export default function InstallHint() {
  const [mode, setMode] = useState<"none" | "prompt" | "ios">("none");
  const [evt, setEvt] = useState<BIPEvent | null>(null);

  useEffect(() => {
    if (isStandalone() || wasDismissed()) return;
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setEvt(e as BIPEvent);
      setMode("prompt");
    };
    const onInstalled = () => {
      setMode("none");
      remember();
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    let timer: ReturnType<typeof setTimeout> | undefined;
    if (isIOSSafari()) timer = setTimeout(() => setMode("ios"), 2500);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (mode === "none") return null;

  const close = () => {
    setMode("none");
    remember();
  };

  const install = async () => {
    if (!evt) return;
    try {
      await evt.prompt();
      const choice = await evt.userChoice;
      if (choice.outcome === "accepted") remember();
    } catch {
      /* 무시 */
    }
    setEvt(null);
    setMode("none");
  };

  return (
    <div className="install" role="dialog" aria-label="홈 화면에 추가 안내">
      <img src="/icons/icon-192.png" alt="" width={40} height={40} />
      <div className="txt">
        <b>홈 화면에 추가</b>
        {mode === "prompt" ? (
          <span>현장에서 앱처럼 바로 열어 보세요.</span>
        ) : (
          <span>
            사파리 아래쪽 <b style={{ display: "inline" }}>공유</b> 버튼 → <b style={{ display: "inline" }}>홈 화면에 추가</b>
          </span>
        )}
      </div>
      {mode === "prompt" && (
        <button type="button" className="btn" onClick={install}>
          설치
        </button>
      )}
      <button type="button" className="x" aria-label="안내 닫기" onClick={close}>
        ×
      </button>
    </div>
  );
}
