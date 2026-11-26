"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";
import { rawCsvAction } from "@/app/a-admin-actions";
import { decideAction, noticeDeleteAction, noticeSaveAction, refreshAction, ruleSaveAction } from "@/app/admin-actions";
import { toast } from "@/components/member/Toast";
import { IcLeft, IcRefresh, IcRight } from "./AdminIcons";

// 관리자 화면 A안에서 누르는 부분. 모두 기존 서버 액션(admin-actions.ts · a-admin-actions.ts)을 부르고,
// 권한은 서버 액션이 맨 앞에서 다시 확인한다. 끝나면 안내를 띄우고 화면을 새로 읽는다.

const MAX_REASON = 300;

/** 결과 안내 + 화면 새로 읽기 */
function useRun() {
  const router = useRouter();
  const [busy, start] = useTransition();
  const run = (job: () => Promise<{ ok?: string; error?: string } | null>, after?: (ok: boolean) => void) =>
    start(async () => {
      const res = await job();
      if (res?.ok) toast(res.ok, "ok");
      else if (res?.error) toast(res.error, "error");
      after?.(!!res?.ok);
      router.refresh();
    });
  return { busy, run, router };
}

const fd = (o: Record<string, string>) => {
  const f = new FormData();
  for (const [k, v] of Object.entries(o)) f.set(k, v);
  return f;
};

// ------------------------------------------------------------------ 주 이동 ‹ 11.23 – 11.29 ›
/** 지금 관리자 화면과 같은 동작: 이전/다음 주 링크 · 가운데를 누르면 달력(그 날이 든 주로) · 다른 주면 '이번 주' */
export function AxWeek({
  off,
  mon,
  label,
  thisMon,
  hrefFor,
}: {
  off: number;
  mon: string;
  label: string;
  thisMon: string;
  hrefFor: { prev: string; next: string; now: string; base: string };
}) {
  const router = useRouter();
  const date = useRef<HTMLInputElement>(null);
  const toOff = (ymd: string) => {
    const d = new Date(`${ymd}T00:00:00Z`);
    const dow = (d.getUTCDay() + 6) % 7;
    const m = new Date(d.getTime() - dow * 86400000);
    return Math.round((m.getTime() - Date.parse(`${thisMon}T00:00:00Z`)) / (7 * 86400000));
  };
  return (
    <div className="ax-week-wrap">
      <div className="ax-week">
        <Link className="ax-wk-btn" href={hrefFor.prev} scroll={false} aria-label="이전 주">
          <IcLeft />
        </Link>
        <button
          type="button"
          className="ax-wk-label"
          aria-label={`${label}${off === 0 ? " 이번 주" : ""} · 달력에서 주 고르기`}
          onClick={() => {
            const el = date.current;
            if (!el) return;
            try {
              el.showPicker();
            } catch {
              el.focus();
              el.click();
            }
          }}
        >
          {label}
          {off === 0 && <small>이번 주</small>}
        </button>
        <input
          ref={date}
          type="date"
          className="ax-wk-date"
          tabIndex={-1}
          aria-hidden
          value={mon}
          onChange={(e) => {
            if (!/^\d{4}-\d{2}-\d{2}$/.test(e.target.value)) return;
            router.push(hrefFor.base.replace("__W__", String(toOff(e.target.value))), { scroll: false });
          }}
        />
        <Link className="ax-wk-btn" href={hrefFor.next} scroll={false} aria-label="다음 주">
          <IcRight />
        </Link>
      </div>
      {off !== 0 && (
        <Link className="ax-btn line sm" href={hrefFor.now} scroll={false}>
          이번 주
        </Link>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ 데이터 새로 불러오기
export function AxRefresh() {
  const { busy, run } = useRun();
  return (
    <button type="button" className="ax-btn mint" disabled={busy} onClick={() => run(() => refreshAction())}>
      <IcRefresh />
      데이터 새로 불러오기
    </button>
  );
}

// ------------------------------------------------------------------ 한눈에 보기 '처리할 일' 의 삭제 요청: 그 자리에서 승인/거부
export function TodoDecide({ entryId, title }: { entryId: string; title: string }) {
  const { busy, run } = useRun();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  if (rejecting)
    return (
      <form
        className="ax-todo-rej"
        onSubmit={(e) => {
          e.preventDefault();
          run(() => decideAction(null, fd({ entry_id: entryId, approve: "0", admin_reason: reason })), (ok) => ok && setRejecting(false));
        }}
      >
        <input
          className="ax-input"
          name="admin_reason"
          value={reason}
          maxLength={MAX_REASON}
          onChange={(e) => setReason(e.target.value)}
          placeholder="요청자에게 보낼 거부 사유"
          aria-label={`${title} 거부 사유`}
          autoFocus
        />
        <button type="button" className="ax-btn line sm" onClick={() => setRejecting(false)} disabled={busy}>
          취소
        </button>
        <button type="submit" className="ax-btn dark sm" disabled={busy}>
          거부 보내기
        </button>
      </form>
    );
  return (
    <div className="ax-todo-btns">
      <button type="button" className="ax-btn line sm" disabled={busy} onClick={() => setRejecting(true)}>
        거부
      </button>
      <button
        type="button"
        className="ax-btn dark sm"
        disabled={busy}
        onClick={() => run(() => decideAction(null, fd({ entry_id: entryId, approve: "1", admin_reason: "" })))}
      >
        승인
      </button>
    </div>
  );
}

// ------------------------------------------------------------------ 삭제 요청 페이지: 펼친 요청 카드의 처리
/** 처리 사유 · 승인 / 거부 / 기간만 고치기 (= 거부로 기록하고 그 팝업의 수정 화면으로) */
export function RequestDecide({
  entryId,
  approveLabel,
  editHref,
}: {
  entryId: string;
  approveLabel: string;
  editHref: string | null;
}) {
  const { busy, run, router } = useRun();
  const [reason, setReason] = useState("");
  const decide = (approve: boolean, text: string, after?: (ok: boolean) => void) =>
    run(() => decideAction(null, fd({ entry_id: entryId, approve: approve ? "1" : "0", admin_reason: text })), after);
  return (
    <form className="ax-req-form" onSubmit={(e) => e.preventDefault()}>
      <label className="ax-field">
        <span>처리 사유 (요청자에게 알림으로 가요 · 거부할 때는 꼭)</span>
        <textarea
          className="ax-input"
          name="admin_reason"
          rows={2}
          maxLength={MAX_REASON}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="예: 공식 공지를 확인해 보니 진행 중인 행사라 유지해요"
        />
      </label>
      <div className="ax-req-btns">
        <button type="button" className="ax-btn dark lg" disabled={busy} onClick={() => decide(true, reason, (ok) => ok && setReason(""))}>
          {approveLabel}
        </button>
        <button type="button" className="ax-btn line lg" disabled={busy} onClick={() => decide(false, reason, (ok) => ok && setReason(""))}>
          거부
        </button>
        {editHref && (
          <button
            type="button"
            className="ax-btn ghost"
            disabled={busy}
            onClick={() => {
              const text = reason.trim() ? `기간만 고치기로 처리 — ${reason.trim()}` : "기간만 고치기로 처리";
              decide(false, text.slice(0, MAX_REASON), (ok) => ok && router.push(editHref));
            }}
          >
            기간만 고치기 →
          </button>
        )}
      </div>
    </form>
  );
}

// ------------------------------------------------------------------ 알림 관리: 규칙 한 줄 (며칠 · 최대 개수 · 켜기)
export type RuleRowView = {
  key: string;
  name: string;
  why: string;
  when: string;
  where: string;
  who: string;
  enabled: boolean;
  days: number | null;
  max_items: number | null;
  hasDays: boolean;
  hasMax: boolean;
  dayUnit: string;
};

export function RuleRow({ r }: { r: RuleRowView }) {
  const { busy, run } = useRun();
  const [days, setDays] = useState(String(r.days ?? ""));
  const [mx, setMx] = useState(String(r.max_items ?? ""));
  const dirty = (r.hasDays && days !== String(r.days ?? "")) || (r.hasMax && mx !== String(r.max_items ?? ""));
  const send = (enabled: boolean) => {
    const f: Record<string, string> = { rule: r.key, enabled: enabled ? "1" : "0" };
    if (r.hasDays) f.days = days;
    if (r.hasMax) f.max_items = mx;
    run(() => ruleSaveAction(null, fd(f)));
  };
  return (
    <tr className={r.enabled ? undefined : "off"} data-rule={r.key}>
      <td>
        <b className="ax-rule-n">{r.name}</b>
        <small>{r.why}</small>
        <small className="ax-rule-when">
          {r.when} · {r.where}
        </small>
      </td>
      <td>{r.who}</td>
      <td>
        {r.hasDays ? (
          <span className="ax-num">
            <input
              className="ax-input"
              type="number"
              inputMode="numeric"
              name="days"
              min={0}
              max={30}
              value={days}
              aria-label={`${r.name} 며칠`}
              onChange={(e) => setDays(e.target.value)}
            />
            <small>{r.dayUnit}</small>
          </span>
        ) : (
          <span className="ax-dash">—</span>
        )}
      </td>
      <td>
        {r.hasMax ? (
          <span className="ax-num">
            <input
              className="ax-input"
              type="number"
              inputMode="numeric"
              name="max_items"
              min={1}
              max={30}
              value={mx}
              aria-label={`${r.name} 최대 개수`}
              onChange={(e) => setMx(e.target.value)}
            />
            <small>개</small>
          </span>
        ) : (
          <span className="ax-dash">—</span>
        )}
      </td>
      <td>
        <span className="ax-sw-cell">
          <button
            type="button"
            role="switch"
            aria-checked={r.enabled}
            aria-label={`${r.name} 켜기`}
            className="ax-switch"
            disabled={busy}
            onClick={() => send(!r.enabled)}
          >
            <i />
          </button>
          <span className="ax-sw-t">{r.enabled ? "켜짐" : "꺼짐"}</span>
        </span>
      </td>
      <td>
        <button type="button" className="ax-btn mint sm" disabled={busy || !dirty} onClick={() => send(true)}>
          {r.enabled ? "저장" : "저장하고 켜기"}
        </button>
      </td>
    </tr>
  );
}

// ------------------------------------------------------------------ 알림 관리: 새 공지 · 보낸 공지
export type NoticeItem = { id: string; title: string; body: string; when: string; edits: number; shown: boolean };

export function AxNotices({ rows, days }: { rows: NoticeItem[]; days: number }) {
  const [editing, setEditing] = useState<string | null>(null);
  const cur = editing ? rows.find((r) => r.id === editing) || null : null;
  const { busy, run } = useRun();
  return (
    <div className="ax-row ax-nt">
      <NoticeForm key={cur?.id || "new"} cur={cur} days={days} onDone={() => setEditing(null)} />
      <section className="ax-card ax-grow" aria-labelledby="ax-nlist-h">
        <div className="ax-card-h">
          <h2 id="ax-nlist-h">보낸 공지 {rows.length}개</h2>
        </div>
        {!rows.length && <div className="ax-empty">아직 보낸 공지가 없어요. 왼쪽에서 첫 공지를 보내 보세요.</div>}
        {rows.map((r) => (
          <div key={r.id} className={`ax-nitem${editing === r.id ? " on" : ""}`}>
            <span className={`ax-tag ${r.shown ? "t-mint" : "t-gray"}`}>{r.shown ? "보이는 중" : "종에서 내려감"}</span>
            <div className="ax-nitem-b">
              <strong>{r.title}</strong>
              <p>{r.body}</p>
              <small>
                {r.when} · 수정 {r.edits}회
              </small>
            </div>
            <div className="ax-nitem-btns">
              <button type="button" className="ax-btn line sm" onClick={() => setEditing(r.id)}>
                수정
              </button>
              <button
                type="button"
                className="ax-btn text-red sm"
                disabled={busy}
                onClick={() => run(() => noticeDeleteAction(r.id), (ok) => ok && editing === r.id && setEditing(null))}
              >
                삭제
              </button>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}

function NoticeForm({ cur, days, onDone }: { cur: NoticeItem | null; days: number; onDone: () => void }) {
  const [title, setTitle] = useState(cur?.title || "");
  const [body, setBody] = useState(cur?.body || "");
  const { busy, run } = useRun();
  return (
    <form
      className="ax-card ax-nform"
      aria-labelledby="ax-nform-h"
      onSubmit={(e) => {
        e.preventDefault();
        run(
          () => noticeSaveAction(null, fd({ entry_id: cur?.id || "", title, body })),
          (ok) => {
            if (!ok) return;
            setTitle("");
            setBody("");
            onDone();
          },
        );
      }}
    >
      <h2 id="ax-nform-h" className="ax-nform-h">
        {cur ? "공지 수정" : "새 공지 보내기"}
      </h2>
      <label className="ax-field">
        <span>제목</span>
        <input
          className="ax-input"
          name="title"
          maxLength={60}
          value={title}
          placeholder="예: 12월 점검 안내"
          onChange={(e) => setTitle(e.target.value)}
        />
        <small className="ax-count">{[...title].length}/60</small>
      </label>
      <label className="ax-field">
        <span>내용</span>
        <textarea className="ax-input" name="body" rows={4} maxLength={500} value={body} onChange={(e) => setBody(e.target.value)} />
        <small className="ax-count">{[...body].length}/500</small>
      </label>
      <p className="ax-cap">받는 사람: 모든 회원 · 종 알림에 {days}일 동안 보여요 (기간은 위 &apos;관리자 공지&apos; 규칙에서 바꿔요).</p>
      <div className="ax-nform-btns">
        <button type="submit" className="ax-btn mint lg" disabled={busy}>
          {cur ? "수정 저장" : "공지 보내기"}
        </button>
        {cur && (
          <button type="button" className="ax-btn line lg" onClick={onDone}>
            취소
          </button>
        )}
      </div>
    </form>
  );
}

// ------------------------------------------------------------------ 원본 데이터 'CSV 내려받기'
export function CsvButton({ table, onlyNow, q }: { table: string; onlyNow: boolean; q: string }) {
  const [busy, start] = useTransition();
  return (
    <button
      type="button"
      className="ax-btn line"
      disabled={busy}
      onClick={() =>
        start(async () => {
          const res = await rawCsvAction(table, onlyNow, q);
          if (!res.csv) {
            toast(res.error || "내려받지 못했어요.", "error");
            return;
          }
          const url = URL.createObjectURL(new Blob([res.csv], { type: "text/csv;charset=utf-8" }));
          const a = document.createElement("a");
          a.href = url;
          a.download = res.name || `${table}.csv`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          setTimeout(() => URL.revokeObjectURL(url), 2000);
          if (res.ok) toast(res.ok, "ok");
        })
      }
    >
      CSV 내려받기
    </button>
  );
}

// ------------------------------------------------------------------ 모바일 가로 메뉴: 고른 메뉴가 보이게 (세로 스크롤은 건드리지 않음)
export function AxMenuScroll() {
  useEffect(() => {
    const on = document.querySelector<HTMLElement>(".ax-menu a.on");
    const bar = on?.parentElement;
    if (!on || !bar || bar.scrollWidth <= bar.clientWidth) return;
    bar.scrollLeft = on.offsetLeft - (bar.clientWidth - on.offsetWidth) / 2;
  });
  return null;
}
