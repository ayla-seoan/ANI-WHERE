"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { startTransition, useActionState, useEffect, useRef, useState, useTransition, type FormEvent } from "react";
import {
  decideAction,
  noticeDeleteAction,
  noticeSaveAction,
  refreshAction,
  ruleSaveAction,
  surveyReloadAction,
  type AdminState,
} from "@/app/admin-actions";
import { toast } from "@/components/member/Toast";
import { submitWith } from "@/lib/submit";
import { IcEdit, IcLeft, IcLess, IcRefresh, IcRight } from "./AdminIcons";

// 관리자 화면에서 누르는 부분 (서버 액션을 부르고, 끝나면 안내 + 화면 새로 읽기). 권한 확인은 서버 액션이 다시 한다.

/** 누른 버튼(name/value)까지 담아 보낸다 (React 19 폼 초기화를 막는 submitWith 와 같은 방식) */
function submitBtn(action: (fd: FormData) => void) {
  return (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget, (e.nativeEvent as SubmitEvent).submitter);
    startTransition(() => action(fd));
  };
}

/** 서버 액션 결과가 새로 오면 한 번: 안내를 띄우고 화면을 새로 읽는다 */
function useResult(s: AdminState, onOk?: () => void) {
  const router = useRouter();
  const seen = useRef(s);
  const ok = useRef(onOk);
  useEffect(() => {
    ok.current = onOk;
  });
  useEffect(() => {
    if (s === seen.current || !s) return;
    seen.current = s;
    if (s.ok) {
      toast(s.ok, "ok");
      ok.current?.();
      router.refresh();
    } else if (s.error) toast(s.error, "error");
  }, [s, router]);
}

// ------------------------------------------------------------------ 바로가기 줄 '데이터 새로 불러오기'
export function RefreshButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      className="adm-linkbtn"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        const res = await refreshAction();
        setBusy(false);
        if (res?.ok) toast(res.ok, "ok");
        else if (res?.error) toast(res.error, "error");
        router.refresh();
      }}
    >
      <IcRefresh />
      데이터 새로 불러오기
    </button>
  );
}

/** 사용자 테스트 '새로고침' */
export function SurveyReload({ className = "st-btn wide" }: { className?: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  return (
    <button
      type="button"
      className={className}
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        const res = await surveyReloadAction();
        setBusy(false);
        if (res?.error) toast(res.error, "error");
        router.refresh();
      }}
    >
      <IcRefresh />
      새로고침
    </button>
  );
}

// ------------------------------------------------------------------ 주 고르기 (앱 _week_nav)
/** ‹ [달력] › : 달력에서 아무 날이나 고르면 그 날이 든 주(월~일)를 본다 */
export function WeekNav({
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
  hrefFor: Record<string, string>;
}) {
  const router = useRouter();
  const toOff = (ymd: string) => {
    const d = new Date(`${ymd}T00:00:00Z`);
    const dow = (d.getUTCDay() + 6) % 7;
    const m = new Date(d.getTime() - dow * 86400000);
    return Math.round((m.getTime() - Date.parse(`${thisMon}T00:00:00Z`)) / (7 * 86400000));
  };
  return (
    <div className="admwk">
      <Link className="st-icbtn" href={hrefFor.prev} scroll={false} aria-label="이전 주">
        <IcLeft />
      </Link>
      <input
        type="date"
        className="admwk-date"
        aria-label="주 고르기"
        value={mon}
        onChange={(e) => {
          if (!/^\d{4}-\d{2}-\d{2}$/.test(e.target.value)) return;
          const n = toOff(e.target.value);
          router.push(hrefFor.base.replace("__W__", String(n)), { scroll: false });
        }}
      />
      <Link className="st-icbtn" href={hrefFor.next} scroll={false} aria-label="다음 주">
        <IcRight />
      </Link>
      <span className="admwk-label">
        <b>{label}</b>
        {off === 0 ? " · 이번 주" : ""}
      </span>
      {off !== 0 && (
        <Link className="st-btn" href={hrefFor.now} scroll={false}>
          이번 주
        </Link>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ 삭제 요청 승인 / 거부 (앱 _admin_requests 한 줄)
export function DecideForm({ entryId }: { entryId: string }) {
  // 처리하면 이 줄이 목록에서 바로 빠지므로(화면 새로 읽기), 결과 안내는 액션을 부른 자리에서 바로 띄운다
  const router = useRouter();
  const [busy, start] = useTransition();
  const [reason, setReason] = useState("");
  const send = submitBtn((fd) => {
    start(async () => {
      const res = await decideAction(null, fd);
      if (res?.ok) {
        toast(res.ok, "ok");
        setReason("");
      } else if (res?.error) toast(res.error, "error");
      router.refresh();
    });
  });
  return (
    <form className="adm-decide" onSubmit={send}>
      <input type="hidden" name="entry_id" value={entryId} />
      <button type="submit" name="approve" value="1" className="st-btn primary wide" disabled={busy}>
        승인 (삭제)
      </button>
      <input
        name="admin_reason"
        className="st-input"
        placeholder="거부할 때 요청자에게 보낼 사유"
        aria-label="거부 사유"
        maxLength={300}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <button type="submit" name="approve" value="0" className="st-btn wide" disabled={busy}>
        거부
      </button>
    </form>
  );
}

// ------------------------------------------------------------------ 알림 규칙 고치기 (앱 _admin_rule_editor)
export type RuleView = {
  key: string;
  name: string;
  enabled: boolean;
  days: number | null;
  max_items: number | null;
  hasDays: boolean;
  hasMax: boolean;
};

export function RuleEditor({ rules }: { rules: RuleView[] }) {
  const [opened, setOpened] = useState(false);
  const [pick, setPick] = useState(rules[0]?.key || "");
  const [s, action, busy] = useActionState(ruleSaveAction, null);
  useResult(s);
  const cur = rules.find((r) => r.key === pick) || rules[0];
  return (
    <>
      <button type="button" className="st-btn danger" onClick={() => setOpened((o) => !o)}>
        {opened ? <IcLess /> : <IcEdit />}
        {opened ? "수정 닫기" : "수정하기"}
      </button>
      {opened && cur && (
        <form className="st-box adm-rule" onSubmit={submitBtn(action)} key={`${cur.key}:${cur.enabled}:${cur.days}:${cur.max_items}`}>
          <input type="hidden" name="rule" value={cur.key} />
          <label className="st-field">
            <span>고칠 규칙</span>
            <select className="st-input" value={pick} onChange={(e) => setPick(e.target.value)}>
              {rules.map((r) => (
                <option key={r.key} value={r.key}>
                  {r.name} ({r.enabled ? "켜짐" : "꺼짐"})
                </option>
              ))}
            </select>
          </label>
          <div className="adm-rule-nums">
            {cur.hasDays ? (
              <label className="st-field">
                <span>며칠 전부터 (공지는 며칠 동안)</span>
                <input
                  className="st-input"
                  type="number"
                  name="days"
                  min={0}
                  max={30}
                  step={1}
                  defaultValue={cur.days ?? 0}
                  required
                />
              </label>
            ) : (
              <div className="adm-empty">이 규칙은 일수가 없어요.</div>
            )}
            {cur.hasMax ? (
              <label className="st-field">
                <span>최대 노출 개수</span>
                <input
                  className="st-input"
                  type="number"
                  name="max_items"
                  min={1}
                  max={30}
                  step={1}
                  defaultValue={cur.max_items ?? 1}
                  required
                />
              </label>
            ) : (
              <div className="adm-empty">처리할 때마다 1건씩 가요.</div>
            )}
          </div>
          <div className="adm-rule-btns">
            <button type="submit" name="enabled" value="1" className="st-btn primary wide" disabled={busy}>
              {cur.enabled ? "저장" : "저장하고 다시 켜기"}
            </button>
            {cur.enabled && (
              <button type="submit" name="enabled" value="0" className="st-btn wide" disabled={busy}>
                이 알림 끄기 (삭제)
              </button>
            )}
          </div>
          <p className="st-cap">
            끈 규칙은 회원에게 더 이상 나가지 않아요. 기록은 남아서 언제든 다시 켤 수 있어요. 주간 브리핑 메일은 Apps
            Script 에서 고쳐요.
          </p>
        </form>
      )}
    </>
  );
}

// ------------------------------------------------------------------ 공지 알림 (앱 _admin_notices 아래 두 칸)
export type NoticeView = { id: string; title: string; body: string; when: string; edits: number };

export function NoticesPanel({ rows }: { rows: NoticeView[] }) {
  const router = useRouter();
  const [editing, setEditing] = useState<string | null>(null);
  const cur = editing ? rows.find((r) => r.id === editing) || null : null;
  return (
    <div className="adm-ntgrid">
      <div className="adm-ntlist">
        <div className="adm-panel-h">공지 알림 {rows.length}개</div>
        {!rows.length && <div className="adm-empty">아직 보낸 공지 알림이 없어요. 오른쪽에서 추가해 보세요.</div>}
        {rows.map((r) => (
          <div key={r.id} className="adm-ntitem">
            <div className="adm-req" style={{ ["--st" as string]: "#14B8A6" }}>
              <div className="rail" />
              <div>
                <div className="t">{r.title}</div>
                <div className="d">{r.body}</div>
                <div className="d">
                  {r.when} · 수정 {r.edits}회
                </div>
              </div>
            </div>
            <div className="adm-ntbtns">
              <button type="button" className="st-btn wide" onClick={() => setEditing(r.id)}>
                수정
              </button>
              <button
                type="button"
                className="st-btn wide"
                onClick={async () => {
                  const res = await noticeDeleteAction(r.id);
                  if (res?.ok) {
                    toast(res.ok, "ok");
                    if (editing === r.id) setEditing(null);
                  } else if (res?.error) toast(res.error, "error");
                  router.refresh();
                }}
              >
                삭제
              </button>
            </div>
          </div>
        ))}
      </div>
      <NoticeEditor key={cur?.id || "new"} cur={cur} onDone={() => setEditing(null)} />
    </div>
  );
}

function NoticeEditor({ cur, onDone }: { cur: NoticeView | null; onDone: () => void }) {
  const [title, setTitle] = useState(cur?.title || "");
  const [body, setBody] = useState(cur?.body || "");
  const [s, action, busy] = useActionState(noticeSaveAction, null);
  useResult(s, () => {
    setTitle(""); // 저장했으면 입력칸을 비운다
    setBody("");
    onDone();
  });
  return (
    <form className="adm-nted" onSubmit={submitWith(action)}>
      <div className="adm-panel-h">{cur ? "공지 수정" : "새 공지 추가"}</div>
      <input type="hidden" name="entry_id" value={cur?.id || ""} />
      <label className="st-field">
        <span>제목</span>
        <input className="st-input" name="title" maxLength={60} value={title} onChange={(e) => setTitle(e.target.value)} />
        <small className="st-count">
          {[...title].length}/60
        </small>
      </label>
      <label className="st-field">
        <span>내용</span>
        <textarea
          className="st-input"
          name="body"
          maxLength={500}
          rows={5}
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
        <small className="st-count">
          {[...body].length}/500
        </small>
      </label>
      <div className="adm-ntbtns two-up">
        <button type="submit" className="st-btn primary wide" disabled={busy}>
          저장
        </button>
        {cur && (
          <button type="button" className="st-btn wide" onClick={onDone}>
            취소
          </button>
        )}
      </div>
      <p className="st-cap">저장하면 모든 회원의 종 알림과 &apos;내 캘린더 &gt; 알림 받은 내역&apos;에 보여요.</p>
    </form>
  );
}
