"use client";
import Link from "next/link";
import { useState } from "react";
import { answer, MAX_QUESTION, needsLocation, type LatLng, type Query } from "@/lib/ask";
import { mask, scan } from "@/lib/guard";
import type { Item } from "@/lib/popup";
import { askAi } from "@/app/ask/actions";

// 물어보기 전체 화면 (앱 page_ask): 제목 · 예시 질문 · 입력칸 · [물어보기] → 읽은 조건 · 'AI 산출 / 규칙 기반 대체' 배지 · 답 ·
// 찾은 팝업 버튼(누르면 상세). 규칙 답(lib/ask.ts)은 브라우저에서 바로, 작품·지역·날짜 검색이면 서버가 AI 로 다듬는다
// (키가 없거나 실패하면 규칙 기반 대체). 질문 · 내 위치는 어디에도 저장하지 않는다.

const EXAMPLES = ["이번 주말 성수에서 하는 팝업 있어?", "주술회전 팝업 어디서 해?", "부산 팝업 알려줘", "12월에 시작하는 팝업"];
const TOP_K = 6;
const INTENT_MAX = 5;

type Shown = {
  cond: string;
  privacy: boolean;
  text: string;
  hits: Item[];
  used: Set<string>;
  source: "ai" | "fallback" | "rule";
  badge: string;
  confidence: "high" | "low";
  dropped: number;
};

/** 앱 ask.validate (개인정보는 가리고 계속 찾는다) */
function validate(q: string): string[] {
  const t = q.trim();
  const errors: string[] = [];
  if (!t) errors.push("질문을 입력해 주세요. 예: 이번 주말 성수에서 하는 팝업 있어?");
  else if ([...t].length < 2) errors.push("질문이 너무 짧아요. 작품 이름이나 지역을 함께 적어 주세요.");
  if ([...t].length > MAX_QUESTION) errors.push(`질문은 ${MAX_QUESTION}자까지 쓸 수 있어요. 지금 ${[...t].length}자예요.`);
  if (scan(t).length) errors.push("전화번호·이메일 같은 개인정보는 질문에 넣지 말아 주세요. 가린 뒤에 찾아요.");
  return errors;
}

function describe(q: Query): string {
  const parts: string[] = [];
  if (q.works.length) parts.push("작품 " + q.works.join(", "));
  if (q.characters.length) parts.push("캐릭터 " + q.characters.join(", "));
  if (q.places.length) parts.push("지역 " + q.places.join(", "));
  if (q.windowLabel) parts.push(q.windowLabel);
  return parts.join(" · ") || "조건 없음 (낱말로만 찾음)";
}

function hereOnce(): Promise<LatLng | null> {
  if (typeof navigator === "undefined" || !navigator.geolocation) return Promise.resolve(null);
  return new Promise((resolve) =>
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 },
    ),
  );
}

const SendIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinejoin="round" aria-hidden>
    <path d="M4 5l16 7-16 7 2.5-7L4 5z" />
    <path d="M6.5 12H12" strokeLinecap="round" />
  </svg>
);
const PinIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z" />
  </svg>
);
const WarnIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7.5v5.5M12 16.5v.01" strokeLinecap="round" />
  </svg>
);
const ShieldIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinejoin="round" aria-hidden>
    <path d="M12 3l7 3v5c0 4.5-3 8.3-7 10-4-1.7-7-5.5-7-10V6l7-3z" />
  </svg>
);

export default function AskPage({ items, today }: { items: Item[]; today: string }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [warns, setWarns] = useState<string[]>([]);
  const [shown, setShown] = useState<Shown | null>(null);
  const byId = new Map(items.map((i) => [i.id, i]));

  async function run(raw: string) {
    const errors = validate(raw);
    setShown(null);
    if (errors.some((e) => !e.includes("개인정보"))) {
      setWarns(errors);
      return;
    }
    setWarns([]);
    const privacy = errors.length > 0;
    const question = mask(raw.trim());
    setBusy(true);
    try {
      const loc = needsLocation(question, items, today) ? await hereOnce() : null;
      const res = answer(question, items, today, { loc });
      const base: Shown = {
        cond: describe(res.query),
        privacy,
        text: res.text,
        hits: [],
        used: new Set(),
        source: "rule",
        badge: "규칙 기반 대체",
        confidence: "low",
        dropped: 0,
      };
      if (res.guide || !res.hits.length) {
        setShown(base); // 0건 → 다음 할 일 안내
        return;
      }
      if (res.query.intent) {
        // 자주 묻는 질문(가까운 · 추천 · 곧 끝나는 …): 규칙 답, 찾은 팝업 모두 근거
        const hits = res.hits.slice(0, INTENT_MAX);
        setShown({ ...base, hits, used: new Set(hits.map((h) => h.id)), confidence: "high" });
        return;
      }
      // 작품·지역·날짜 검색: 서버에서 AI 로 다듬기 (실패하면 규칙 기반 대체)
      let ai = null;
      try {
        ai = await askAi(question);
      } catch {
        ai = null;
      }
      if (ai && ai.applies) {
        const hits = ai.hitIds.map((id) => byId.get(id)).filter((x): x is Item => Boolean(x));
        setShown({
          ...base,
          text: ai.text,
          hits: hits.length ? hits : res.hits.slice(0, TOP_K),
          used: new Set(ai.usedIds),
          source: ai.source,
          badge: ai.badge,
          confidence: ai.confidence,
          dropped: ai.dropped,
        });
      } else {
        const hits = res.hits.slice(0, TOP_K);
        setShown({ ...base, hits, used: new Set(hits.slice(0, 3).map((h) => h.id)), source: "fallback", confidence: "high" });
      }
    } finally {
      setBusy(false);
    }
  }

  const sorted = shown ? [...shown.hits].sort((a, b) => Number(!shown.used.has(a.id)) - Number(!shown.used.has(b.id))) : [];

  return (
    <div className="pg-ask">
      <div className="ask-q">팝업에게 물어보기</div>
      <div className="ask-sub">앱에 모인 팝업 정보 안에서만 찾아 답해요. 작품·지역·날짜를 함께 적으면 더 정확해요.</div>
      <div className="ask-exs">
        {EXAMPLES.map((ex) => (
          <button key={ex} type="button" onClick={() => setQ(ex)}>
            {ex}
          </button>
        ))}
      </div>
      <form
        className="ask-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (!busy) void run(q);
        }}
      >
        <input
          type="text"
          value={q}
          maxLength={MAX_QUESTION}
          onChange={(e) => setQ(e.target.value)}
          placeholder="예: 이번 주말 홍대 근처 주술회전 팝업 있어?"
          aria-label="질문"
          enterKeyHint="send"
          autoComplete="off"
        />
        <button type="submit" className="ask-send" disabled={busy}>
          <SendIcon />
          물어보기
        </button>
      </form>

      {warns.map((w) => (
        <div key={w} className="ask-note warn" role="alert">
          <WarnIcon />
          {w}
        </div>
      ))}
      {busy && <div className="ask-wait">팝업을 찾는 중이에요...</div>}

      {shown && !busy && (
        <div className="ask-result" aria-live="polite">
          {shown.privacy && (
            <div className="ask-note info">
              <ShieldIcon />
              전화번호·이메일 같은 개인정보는 질문에 넣지 말아 주세요. 가린 뒤에 찾아요.
            </div>
          )}
          <div className="ask-cond">질문에서 읽은 조건: {shown.cond}</div>
          {!shown.hits.length ? (
            // 0건일 때 빈 화면 대신 다음 할 일을 안내한다
            <div className="ask-answer ask-none">
              조건에 맞는 팝업을 찾지 못했어요.
              <br />· 작품 이름을 줄여서(예: <b>주술회전</b>) 다시 물어보거나
              <br />· 날짜·지역 조건을 하나 빼 보세요.
              <br />· 아직 등록되지 않은 팝업이라면 첫 화면 오른쪽 아래 <b>+</b> 로 직접 등록할 수 있어요.
            </div>
          ) : (
            <>
              <span className={shown.source === "ai" ? "ask-badge" : "ask-badge fb"}>{shown.badge}</span>
              {shown.confidence === "low" && <span className="ask-badge fb">딱 맞는 팝업은 없음</span>}
              <div className="ask-answer">{shown.text}</div>
              {shown.dropped > 0 && (
                <div className="ask-cap">AI 가 후보에 없는 팝업 {shown.dropped}건을 근거로 들어 지웠어요.</div>
              )}
              <div className="ask-found">
                <b>찾은 팝업</b> — 누르면 상세로 이동해요
              </div>
              {sorted.map((r) => (
                <Link
                  key={r.id}
                  href={`/popup/${r.id}`}
                  prefetch={false}
                  className={`ask-hit${shown.used.has(r.id) ? " on" : ""}`}
                >
                  <PinIcon />
                  {`${r.work} · ${r.name}  |  ${r.start} ~ ${r.end}  |  ${r.area || "지역 미상"}`}
                </Link>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
