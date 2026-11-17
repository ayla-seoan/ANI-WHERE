"use client";
import { useEffect, useMemo, useState } from "react";
import { statusOf } from "@/lib/popup";
import PopupCard, { type CardData } from "./PopupCard";
import EmptyState from "./EmptyState";
import { SearchIcon } from "./Icons";

export type BrowserItem = CardData & { text: string };

type Tab = "ongoing" | "upcoming" | "all";
const TABS: { key: Tab; label: string }[] = [
  { key: "ongoing", label: "진행 중" },
  { key: "upcoming", label: "예정" },
  { key: "all", label: "전체" },
];
const ALL = "전체";

function inTab(p: CardData, tab: Tab, today: string) {
  if (tab === "all") return true;
  return statusOf(p, today) === tab; // 날짜 없는 행은 진행 중·예정에서 빠진다
}

function matches(text: string, words: string[]) {
  return words.every((w) => text.includes(w));
}

export default function PopupBrowser({ items, today }: { items: BrowserItem[]; today: string }) {
  const [q, setQ] = useState("");
  const [region, setRegion] = useState(ALL);
  const [tab, setTab] = useState<Tab>("ongoing");
  const [ready, setReady] = useState(false);

  // 상세에서 뒤로 왔을 때 조건을 되살린다 (주소창 ?q=&r=&t=)
  useEffect(() => {
    try {
      const sp = new URLSearchParams(window.location.search);
      const t = sp.get("t");
      if (t === "ongoing" || t === "upcoming" || t === "all") setTab(t);
      const qq = sp.get("q");
      if (qq) setQ(qq.slice(0, 60));
      const r = sp.get("r");
      if (r) setRegion(r.slice(0, 20));
    } catch {
      /* 무시 */
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    const sp = new URLSearchParams();
    if (q.trim()) sp.set("q", q.trim());
    if (region !== ALL) sp.set("r", region);
    if (tab !== "ongoing") sp.set("t", tab);
    const qs = sp.toString();
    window.history.replaceState(window.history.state, "", qs ? `/?${qs}` : "/");
  }, [q, region, tab, ready]);

  const words = useMemo(() => q.trim().toLowerCase().split(/\s+/).filter(Boolean), [q]);

  // 지역 칩: 지금 탭·검색어 기준 개수, 많은 순
  const regions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of items) {
      if (!inTab(p, tab, today) || !matches(p.text, words)) continue;
      counts.set(p.region, (counts.get(p.region) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "ko"));
  }, [items, tab, today, words]);

  const tabCounts = useMemo(() => {
    const c: Record<Tab, number> = { ongoing: 0, upcoming: 0, all: 0 };
    for (const p of items) {
      if (!matches(p.text, words)) continue;
      if (region !== ALL && p.region !== region) continue;
      c.all++;
      const s = statusOf(p, today);
      if (s === "ongoing") c.ongoing++;
      if (s === "upcoming") c.upcoming++;
    }
    return c;
  }, [items, today, words, region]);

  const shown = useMemo(
    () => items.filter((p) => inTab(p, tab, today) && (region === ALL || p.region === region) && matches(p.text, words)),
    [items, tab, today, region, words],
  );
  const filtered = q.trim() !== "" || region !== ALL;
  const reset = () => {
    setQ("");
    setRegion(ALL);
    setTab("ongoing");
  };
  const tabLabel = TABS.find((t) => t.key === tab)?.label ?? "";

  return (
    <section aria-label="팝업 찾기">
      <form className="search" role="search" onSubmit={(e) => e.preventDefault()}>
        <SearchIcon />
        <input
          type="search"
          inputMode="search"
          enterKeyHint="search"
          placeholder="작품 · 캐릭터 · 매장 · 주소"
          aria-label="작품, 캐릭터, 매장, 주소로 검색"
          value={q}
          maxLength={60}
          onChange={(e) => setQ(e.target.value)}
        />
        {q && (
          <button type="button" className="clear" aria-label="검색어 지우기" onClick={() => setQ("")}>
            ×
          </button>
        )}
      </form>

      <div className="tabs" role="tablist" aria-label="진행 상태">
        {TABS.map((t) => (
          <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}>
            {t.label}
            <span className="count">{tabCounts[t.key]}</span>
          </button>
        ))}
      </div>

      <div className="chips" role="group" aria-label="지역">
        <button type="button" className="chip" aria-pressed={region === ALL} onClick={() => setRegion(ALL)}>
          전체
        </button>
        {regions.map(([r, n]) => (
          <button key={r} type="button" className="chip" aria-pressed={region === r} onClick={() => setRegion(r)}>
            {r}
            <small>{n}</small>
          </button>
        ))}
        {region !== ALL && !regions.some(([r]) => r === region) && (
          <button type="button" className="chip" aria-pressed onClick={() => setRegion(ALL)}>
            {region}
            <small>0</small>
          </button>
        )}
      </div>

      {shown.length > 0 ? (
        <>
          <p className="result-line" aria-live="polite">
            {tabLabel} {shown.length}곳{filtered ? " 찾음" : ""}
          </p>
          <div className="grid">
            {shown.map((p, i) => (
              <PopupCard key={p.id} p={p} today={today} eager={i < 4} />
            ))}
          </div>
        </>
      ) : (
        <EmptyState
          hint={
            tab !== "all" && tabCounts.all > 0
              ? `'${tabLabel}' 대신 '전체' 탭을 보거나 조건을 줄여 보세요.`
              : "검색어나 지역 조건을 줄여 보세요."
          }
          onReset={filtered || tab !== "ongoing" ? reset : undefined}
        />
      )}
    </section>
  );
}
