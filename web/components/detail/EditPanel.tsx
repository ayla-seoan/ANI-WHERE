"use client";
import { useRouter } from "next/navigation";
import { useMemo, useState, useTransition } from "react";
import { editSaveAction, takeDownAction } from "@/app/popup-actions";
import { addDays, ALWAYS_END, blockSensitive, isAlways, linksErrors, type Picked } from "@/lib/cafe-rules";
import type { HistoryCard } from "@/lib/server/cafe";
import DeleteRequestButton from "../admin/DeleteRequest";
import AddressField from "../edit/AddressField";
import EditImages, { imageErrors, type ImgState } from "../edit/EditImages";
import { ClearInput, Help, IntroField, LinksField, TagPills } from "../edit/Fields";
import WorkPicker from "../edit/WorkPicker";
import { goLogin, useMember } from "../member/MemberContext";
import { toast } from "../member/Toast";
import HistoryList from "./HistoryList";

// 상세 오른쪽 '수정하기' 탭 (앱 render_edit). 누구나(회원) 고칠 수 있고, 기존 기록은 남기고 새 줄로 쌓여서
// 언제든 되돌릴 수 있다. 저장하면 상세에 그대로 머물고 맨 위로 올라가 바뀐 내용을 보여 준다.

export type EditData = {
  entryId: string;
  revision: number;
  work: string;
  characters: string[];
  cafeName: string;
  address: string;
  start: string;
  end: string;
  tags: string[];
  perks: string;
  goods: string;
  links: string;
  intro: string;
  images: string[];
  /** '기간 확인 필요' 표시가 있으면 원문 (없으면 null) */
  check: { raw: string } | null;
  title: string;
};

export default function EditPanel({
  entryId,
  data,
  byWork,
  history,
}: {
  entryId: string;
  data: EditData | null;
  byWork: Record<string, string[]>;
  history: HistoryCard[];
}) {
  const { me } = useMember();
  const router = useRouter();
  if (!me || !data) {
    const msg = "팝업 정보 수정은 로그인하면 할 수 있어요.";
    return (
      <div className="ed-gate">
        <div className="ntf-empty" style={{ padding: "10px 2px" }}>
          {msg}
        </div>
        <button
          type="button"
          className="side-cta"
          onClick={() => goLogin(router, msg, `/popup/${entryId}?tab=edit`)}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={16} height={16} aria-hidden>
            <path d="M14 4h4a2 2 0 012 2v12a2 2 0 01-2 2h-4M10 16l4-4-4-4M14 12H4" />
          </svg>
          로그인하고 계속하기
        </button>
      </div>
    );
  }
  return <EditForm key={`${data.entryId}_${data.revision}`} d={data} byWork={byWork} history={history} admin={me.admin} />;
}

function EditForm({ d, byWork, history, admin }: { d: EditData; byWork: Record<string, string[]>; history: HistoryCard[]; admin: boolean }) {
  const router = useRouter();
  const wasAlways = isAlways(d.end);
  const [work, setWork] = useState(d.work);
  const [chars, setChars] = useState(d.characters);
  const [name, setName] = useState(d.cafeName);
  const [addr, setAddr] = useState(d.address);
  const [picked, setPicked] = useState<Picked | null>(null);
  const [start, setStart] = useState(d.start);
  const [always, setAlways] = useState(wasAlways);
  const [end, setEnd] = useState(wasAlways ? addDays(d.start, 30) : d.end);
  const [perks, setPerks] = useState(d.perks);
  const [goods, setGoods] = useState(d.goods);
  const [tags, setTags] = useState(d.tags);
  const [links, setLinks] = useState(d.links);
  const [intro, setIntro] = useState(d.intro);
  const [img, setImg] = useState<ImgState>({ removed: [], poster: null, extras: [] });
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, start_] = useTransition();
  const [askDel, setAskDel] = useState(false);
  const [delBusy, startDel] = useTransition();

  const bad = blockSensitive(name, addr, perks, goods, intro);
  const imgErr = useMemo(() => imageErrors(d.images, img), [d.images, img]);
  const badLinks = linksErrors(links).errors.length > 0;

  const save = () => {
    const fd = new FormData();
    fd.set("entry_id", d.entryId);
    fd.set("work", work);
    fd.set("characters", JSON.stringify(chars));
    fd.set("cafe_name", name);
    fd.set("address", addr);
    fd.set("picked", picked && picked.address === addr.trim() ? JSON.stringify(picked) : "");
    fd.set("start_date", start);
    fd.set("end_date", always ? ALWAYS_END : end);
    if (always) fd.set("always", "1");
    fd.set("perks", perks);
    fd.set("goods", goods);
    for (const t of tags) fd.append("tags", t);
    fd.set("links", links);
    fd.set("intro", intro);
    fd.set("keep", JSON.stringify(d.images.filter((n) => !img.removed.includes(n))));
    if (img.poster) fd.set("poster", img.poster);
    for (const f of img.extras) fd.append("extras", f);
    setErrors([]);
    start_(async () => {
      const r = await editSaveAction(null, fd);
      if (!r || r.error || r.errors?.length) {
        setErrors(r?.errors?.length ? r.errors : [r?.error || "저장하지 못했어요."]);
        return;
      }
      toast(r.ok || "수정했습니다.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      router.refresh();
    });
  };

  return (
    <div className="ed-panel">
      <p className="ed-cap">누구나 수정할 수 있습니다. 기존 기록은 남기고 새 줄로 쌓여서 언제든 되돌릴 수 있습니다.</p>
      <WorkPicker
        byWork={byWork}
        work={work}
        characters={chars}
        initialWork={d.work}
        initialChars={d.characters}
        onChange={(w, c) => {
          setWork(w);
          setChars(c);
        }}
      />
      <label className="ed-field">
        <span className="ed-label">카페명</span>
        <ClearInput value={name} onChange={setName} maxLength={100} />
      </label>
      <AddressField
        value={addr}
        onChange={setAddr}
        onPick={(c) => {
          setPicked({ address: c.address, lat: c.lat, lng: c.lng, source: c.source, precision: c.precision });
          setAddr(c.address);
        }}
      />
      <div className="ed-two">
        <label className="ed-field">
          <span className="ed-label">시작</span>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="ed-field">
          <span className="ed-label">종료</span>
          <input type="date" value={end} disabled={always} onChange={(e) => setEnd(e.target.value)} />
        </label>
      </div>
      <label className="ck ed-ck">
        <input type="checkbox" checked={always} onChange={(e) => setAlways(e.target.checked)} />
        <span>종료일 없음 (상시)</span>
      </label>
      {d.check && (
        <div className="auth-warn ed-warn">
          기간을 정확히 읽지 못한 팝업이에요
          {d.check.raw && !d.check.raw.startsWith("(") ? ` (원문: '${d.check.raw}')` : ""}. 공식 공지를 보고 시작·종료일을 고쳐 주세요.
        </div>
      )}
      <label className="ed-field">
        <span className="ed-label">
          특전
          <Help>쉼표로 구분</Help>
        </span>
        <ClearInput value={perks} onChange={setPerks} maxLength={500} />
      </label>
      <label className="ed-field">
        <span className="ed-label">
          굿즈
          <Help>쉼표로 구분</Help>
        </span>
        <ClearInput value={goods} onChange={setGoods} maxLength={500} />
      </label>
      <TagPills value={tags} onChange={setTags} />
      <LinksField value={links} onChange={setLinks} />
      <IntroField value={intro} onChange={setIntro} />
      <EditImages images={d.images} value={img} onChange={setImg} />
      {bad && <div className="ed-err">{bad}</div>}
      {/* 수정 저장 · 지도에서 내리기(관리자) / 삭제 요청을 한 줄에 (모바일에서도 세로로 쌓이지 않는다) */}
      <div className="ed-btns">
        <button type="button" className="btn-main" disabled={busy || !!bad || imgErr.length > 0 || badLinks} onClick={save}>
          {busy ? "저장 중…" : "수정 저장"}
        </button>
        {admin ? (
          <button type="button" className="btn-line" onClick={() => setAskDel(true)}>
            지도에서 내리기 (관리자)
          </button>
        ) : (
          <DeleteRequestButton targetType="cafe" targetId={d.entryId} title={d.title} />
        )}
      </div>
      {errors.map((e) => (
        <div key={e} className="ed-err">
          {e}
        </div>
      ))}

      <details className="exp hx-exp">
        <summary>수정 이력</summary>
        <HistoryList entryId={d.entryId} cards={history} />
      </details>

      {askDel && (
        <div className="dlg-bg" role="dialog" aria-modal="true" aria-label="지도에서 내리기">
          <div className="dlg">
            <b className="dlg-t">지도에서 내리기</b>
            <p>정말로 지도에서 삭제하시겠습니까? 완전히 삭제 됩니다.</p>
            <div className="two">
              <button type="button" className="btn-line" onClick={() => setAskDel(false)}>
                취소
              </button>
              <button
                type="button"
                className="btn-main"
                disabled={delBusy}
                onClick={() =>
                  startDel(async () => {
                    const r = await takeDownAction(d.entryId);
                    if (r?.error) {
                      toast(r.error, "error");
                      setAskDel(false);
                    }
                  })
                }
              >
                삭제
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
