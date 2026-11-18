"use client";
import Link from "next/link";
import { Fragment, useEffect, useRef, useState } from "react";
import { DEFAULT_CHIPS, GUIDE_EXAMPLES, MAX_QUESTION } from "@/lib/ask";
import { PLACEHOLDER_POSTER, type Item } from "@/lib/popup";
import { OpenIcon } from "../Icons";
import { send, useChat, type BotMsg } from "./store";

// 물어보기 대화창 (앱 _ask_chat_body 모양): 대화 기록 · 예시 칩 · 입력칸.
// PC 오른쪽 칸(AskPanel)과 모바일 아래 시트(AskFab)가 같은 기록을 쓴다.

/** 답 속 숫자만 굵은 민트로 (앱 _ask_nums) */
function Nums({ text }: { text: string }) {
  const parts = text.split(/(\d[\d,./:]*\d|\d)/);
  return (
    <>
      {parts.map((p, i) =>
        i % 2 ? (
          <b key={i} className="apn-num">
            {p}
          </b>
        ) : (
          <Fragment key={i}>{p}</Fragment>
        ),
      )}
    </>
  );
}

function Bot({ children }: { children: React.ReactNode }) {
  return (
    <div className="apn-row">
      <img className="apn-ava" src="/ask_avatar.png" alt="ANI:WHERE" width={38} height={38} />
      <div className="apn-col">
        <div className="apn-name">ANI:WHERE</div>
        <div className="apn-bot">{children}</div>
      </div>
    </div>
  );
}

/** 앱 _period 기본 모양 '11.5 ~ 12.20' (내 주변 질문이면 앞에 거리) */
function cardDates(p: Item, km?: number): string {
  const f = (s: string) => `${Number(s.slice(5, 7))}.${Number(s.slice(8, 10))}`;
  const dates = p.start ? `${f(p.start)} ~ ${p.end ? f(p.end) : "상시"}` : "기간 확인 필요";
  if (km === undefined) return dates;
  return `${km < 1 ? `${Math.round(km * 1000)}m` : `${km.toFixed(1)}km`} · ${dates}`;
}

function BotAnswer({
  m,
  onAsk,
  onShowAll,
  onOpen,
}: {
  m: BotMsg;
  onAsk: (q: string) => void;
  onShowAll?: (ids: string[], label: string) => void;
  onOpen?: () => void;
}) {
  return (
    <>
      {m.cards.length ? (
        <Bot>
          <Nums text={m.text} />
          {m.head ? (
            <>
              {" · "}
              <Nums text={m.head} />
            </>
          ) : null}
        </Bot>
      ) : m.guide ? (
        <Bot>
          말씀을 못 알아들었어요. <b>작품 이름 · 장소 · 날짜</b>를 넣어서 물어봐 주세요.
          <div className="apn-exbox">
            <b>이렇게 물어보세요</b>
            {GUIDE_EXAMPLES.map((x) => (
              <button key={x} type="button" className="apn-ex" onClick={() => onAsk(x)}>
                {x}
              </button>
            ))}
          </div>
        </Bot>
      ) : (
        <Bot>
          <Nums text={m.text} />
          {m.links.length > 0 && (
            <div className="apn-links">
              {m.links.map(([t, u]) => (
                <a key={u} className="apn-link" href={u} target="_blank" rel="noopener noreferrer">
                  <OpenIcon />
                  {t}
                </a>
              ))}
            </div>
          )}
        </Bot>
      )}
      {m.cards.map((p) => (
        <Link key={p.id} href={`/popup/${p.id}`} className="apc" prefetch={false} onClick={onOpen}>
          <img
            src={p.poster || PLACEHOLDER_POSTER}
            alt=""
            loading="lazy"
            onError={(e) => {
              if (!e.currentTarget.src.endsWith(PLACEHOLDER_POSTER)) e.currentTarget.src = PLACEHOLDER_POSTER;
            }}
          />
          <span className="apc-txt">
            <span className="apc-work">{p.work}</span>
            <span className="apc-cafe">{p.name}</span>
            <span className="apc-addr">{p.address}</span>
            <span className="apc-date">{cardDates(p, m.distances[p.id])}</span>
          </span>
        </Link>
      ))}
      {m.more &&
        (onShowAll ? (
          <button type="button" className="apn-more" onClick={() => onShowAll(m.more!.ids, m.more!.label)}>
            + {m.more.ids.length - m.cards.length}건 더보기 · 리스트로 보기
          </button>
        ) : (
          <Link
            className="apn-more"
            href={`/list?ids=${m.more.ids.join(",")}&ask=${encodeURIComponent(m.more.label)}`}
            onClick={onOpen}
          >
            + {m.more.ids.length - m.cards.length}건 더보기 · 리스트로 보기
          </Link>
        ))}
    </>
  );
}

export default function AskChat({
  items,
  today,
  onShowAll,
  onOpen,
}: {
  items: Item[];
  today: string;
  /** 리스트로 보기 화면 안에서는 주소 이동 대신 바로 조건을 바꾼다 */
  onShowAll?: (ids: string[], label: string) => void;
  /** 카드·더보기를 눌러 다른 화면으로 갈 때 (모바일 시트 닫기) */
  onOpen?: () => void;
}) {
  const chat = useChat();
  const [q, setQ] = useState("");
  const log = useRef<HTMLDivElement>(null);
  const ask = (text: string) => void send(text, items, today);

  // 새 답이 생기면 방금 한 질문이 대화창 맨 위에 오게 내린다 (앱과 같게)
  useEffect(() => {
    const box = log.current;
    if (!box) return;
    const mark = [...box.querySelectorAll(".apn-me")].pop() as HTMLElement | undefined;
    if (mark) box.scrollTop += mark.getBoundingClientRect().top - box.getBoundingClientRect().top - 6;
    else box.scrollTop = box.scrollHeight;
  }, [chat.length]);

  return (
    <div className="apn">
      <div className="apn-log" ref={log}>
        <Bot>
          안녕하세요 궁금하신 팝업에서 찾아 드릴게요!
          <br />
          <b>작품 · 지역 · 날짜</b>로 물어보면 더 정확하게 찾을 수 있어요!
        </Bot>
        {chat.map((m, i) =>
          m.role === "me" ? (
            <div key={i} className="apn-me">
              <span>{m.text}</span>
            </div>
          ) : m.role === "wait" ? (
            <Bot key={i}>내 위치를 확인하고 있어요…</Bot>
          ) : (
            <BotAnswer key={i} m={m} onAsk={ask} onShowAll={onShowAll} onOpen={onOpen} />
          ),
        )}
      </div>
      <div className="apn-chips">
        {DEFAULT_CHIPS.map((c) => (
          <button key={c} type="button" onClick={() => ask(c)}>
            {c}
          </button>
        ))}
      </div>
      <form
        className="apn-form"
        onSubmit={(e) => {
          e.preventDefault();
          ask(q);
          setQ("");
        }}
      >
        <input
          type="text"
          value={q}
          maxLength={MAX_QUESTION}
          onChange={(e) => setQ(e.target.value)}
          placeholder="예: 이번 주말 홍대 근처 팝업 있어?"
          aria-label="질문"
          enterKeyHint="send"
          autoComplete="off"
        />
        <button type="submit">보내기</button>
      </form>
    </div>
  );
}
