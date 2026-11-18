"use client";
import { useEffect, useRef, useState } from "react";

// 상세 제목 줄의 공유 버튼 (앱 common/share.py + components/share/index.html 을 옮김).
// 처음에는 공유 아이콘만, 누르면 왼쪽으로 카카오톡 · 인스타그램 · 링크 복사가 펼쳐진다.
// 공유 주소는 웹 상세 주소 <이 사이트>/popup/<id> — 받은 사람이 누르면 이 팝업 상세가 바로 열린다.
// 카카오톡 카드 공유는 NEXT_PUBLIC_KAKAO_JS_KEY 가 있을 때만 (없으면 링크 복사 + 카카오톡 열기).

type KakaoSdk = {
  isInitialized(): boolean;
  init(key: string): void;
  Share: { sendDefault(o: unknown): void };
};
declare global {
  interface Window {
    Kakao?: KakaoSdk;
  }
}

const KAKAO_KEY = process.env.NEXT_PUBLIC_KAKAO_JS_KEY || "";
const KAKAO_SDK = "https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js";

let kakaoReady: Promise<void> | null = null;
function loadKakao(): Promise<void> {
  return (kakaoReady ||= new Promise<void>((resolve, reject) => {
    const done = () => {
      try {
        if (!window.Kakao) throw new Error("Kakao SDK 없음");
        if (!window.Kakao.isInitialized()) window.Kakao.init(KAKAO_KEY);
        resolve();
      } catch (e) {
        reject(e);
      }
    };
    if (window.Kakao) return done();
    const s = document.createElement("script");
    s.src = KAKAO_SDK;
    s.async = true;
    s.onload = done;
    s.onerror = () => {
      kakaoReady = null;
      reject(new Error("카카오 SDK 를 불러오지 못했어요"));
    };
    document.head.appendChild(s);
  }));
}

function shareUrl(id: string): string {
  return `${window.location.origin}/popup/${encodeURIComponent(id)}`;
}

async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    // 권한이 없으면 옛 방식으로 복사
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
}

const isMobile = () => /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
const isAndroid = () => /Android/i.test(navigator.userAgent);

/** 앱 열기: 휴대폰은 앱 주소(스킴)로, PC 는 새 탭으로. 누른 직후에 열어야 브라우저가 막지 않는다 */
function openApp(appUrl: string, androidIntent: string | null, webUrl: string | null) {
  if (isMobile()) window.location.href = isAndroid() && androidIntent ? androidIntent : appUrl;
  else if (webUrl) window.open(webUrl, "_blank", "noopener");
}

export default function ShareButtons({
  id,
  title,
  text,
  image,
}: {
  id: string;
  title: string;
  text: string;
  image: string;
}) {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 안내 문구는 3초 보였다가 사라진다 (앱과 같게)
  const say = (t: string) => {
    setMsg(t);
    if (timer.current) clearTimeout(timer.current);
    if (t) timer.current = setTimeout(() => setMsg(""), 3000);
  };
  useEffect(() => () => void (timer.current && clearTimeout(timer.current)), []);

  const copy = async (okText: string) => {
    await copyText(shareUrl(id));
    say(okText);
  };

  const onKakao = async () => {
    // 1) 카카오 키가 있으면 카카오톡 공유 창 → 친구를 고르면 포스터 카드로 보낸다
    let why = KAKAO_KEY ? "" : "카카오 JavaScript 키가 설정되지 않았어요";
    if (KAKAO_KEY) {
      try {
        await loadKakao();
        const url = shareUrl(id);
        window.Kakao!.Share.sendDefault({
          objectType: "feed",
          content: {
            title,
            description: text,
            imageUrl: new URL(image, window.location.href).href,
            link: { mobileWebUrl: url, webUrl: url },
          },
          buttons: [{ title: "자세히 보기", link: { mobileWebUrl: url, webUrl: url } }],
        });
        say("카카오톡 공유 창을 열었어요");
        return;
      } catch (e) {
        const m = e instanceof Error ? e.message : String(e);
        why =
          `카카오 공유 창을 못 열었어요 (${m}) — 카카오 콘솔의 Web 사이트 도메인에 ` +
          `${window.location.origin} 이 그대로 등록돼 있는지 확인해 주세요`;
        console.warn("[ANI:WHERE] Kakao share failed:", e, "origin:", window.location.origin);
      }
    }
    // 2) 키가 없거나 공유 창을 못 열면: 링크를 복사하고 카카오톡을 연다 (채팅방에 붙여 넣으면 된다)
    await copy(
      (why ? why + " · " : "") +
        (isMobile()
          ? "링크를 복사했어요. 카카오톡이 열리면 채팅방에 붙여 넣어 주세요"
          : "링크를 복사했어요. 카카오톡 PC 에서 채팅방에 붙여 넣어 주세요"),
    );
    openApp("kakaotalk://launch", "intent://launch#Intent;scheme=kakaotalk;package=com.kakao.talk;end", null);
  };

  const onInsta = async () => {
    // 인스타그램에는 웹에서 DM 창을 바로 여는 주소가 없다. 휴대폰은 기기 공유 창(navigator.share)을 열어
    // 거기서 인스타그램을 고르게 한다. PC · 공유 창이 없으면 링크를 복사하고 인스타 DM 을 연다.
    const data = { title, text: `${title}\n${text}`, url: shareUrl(id) };
    let why = "";
    if (isMobile()) {
      if (navigator.share) {
        try {
          await navigator.share(data);
          say("공유 창을 열었어요. 인스타그램을 고르면 DM 으로 보낼 수 있어요");
          return;
        } catch (e) {
          if (e instanceof Error && e.name === "AbortError") {
            say("");
            return;
          }
          why = e instanceof Error ? e.name || e.message : String(e);
          console.warn("[ANI:WHERE] share sheet failed:", e);
        }
      }
      why = why
        ? `공유 창을 열 수 없었어요 (${why})`
        : "이 브라우저는 공유 창을 지원하지 않아요 (앱 안의 브라우저라면 크롬·사파리로 열어 주세요)";
    }
    await copy((why ? why + " · " : "") + "링크를 복사했어요. 인스타그램 DM 에 붙여 넣어 보내 주세요");
    openApp(
      "instagram://direct-inbox",
      "intent://direct-inbox#Intent;scheme=instagram;package=com.instagram.android;end",
      "https://www.instagram.com/direct/new/",
    );
  };

  return (
    <div className={`shr${open ? " open" : ""}`}>
      <div className="shr-row">
        <button
          type="button"
          className={`shr-main${open ? " open" : ""}`}
          aria-label="공유하기"
          aria-expanded={open}
          onClick={() => {
            setOpen(!open);
            if (open) say("");
          }}
        >
          {/* 공유 아이콘 (점 세 개를 잇는 모양) */}
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="#26302D"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden
          >
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <path d="M8.6 13.5l6.8 4" />
            <path d="M15.4 6.5l-6.8 4" />
          </svg>
        </button>
        {open && (
          <div className="shr-panel">
            <button type="button" className="shr-kakao" aria-label="카카오톡으로 공유" onClick={onKakao}>
              <svg viewBox="0 0 24 24" aria-hidden>
                <circle cx="12" cy="12" r="11" fill="#FEE500" />
                <path
                  d="M12 6.5c-3.6 0-6.5 2.2-6.5 5 0 1.8 1.2 3.4 3 4.3l-.7 2.6 3-2c.4.1.8.1 1.2.1 3.6 0 6.5-2.2 6.5-5s-2.9-5-6.5-5z"
                  fill="#3C1E1E"
                />
              </svg>
            </button>
            <button type="button" className="shr-insta" aria-label="인스타그램으로 공유" onClick={onInsta}>
              <svg viewBox="0 0 24 24" aria-hidden>
                <defs>
                  <linearGradient id={`ig-${id}`} x1="0" y1="1" x2="1" y2="0">
                    <stop offset="0" stopColor="#f9ce34" />
                    <stop offset=".5" stopColor="#ee2a7b" />
                    <stop offset="1" stopColor="#6228d7" />
                  </linearGradient>
                </defs>
                <rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke={`url(#ig-${id})`} strokeWidth="2.2" />
                <circle cx="12" cy="12" r="4" fill="none" stroke={`url(#ig-${id})`} strokeWidth="2.2" />
                <circle cx="17.3" cy="6.7" r="1.3" fill="#ee2a7b" />
              </svg>
            </button>
            <button
              type="button"
              className="shr-copy"
              aria-label="링크 복사"
              onClick={() => void copy("링크를 복사했어요")}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="#2E9C82"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
                <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
              </svg>
            </button>
          </div>
        )}
      </div>
      {msg && (
        <div className="shr-msg" role="status">
          {msg}
        </div>
      )}
    </div>
  );
}
