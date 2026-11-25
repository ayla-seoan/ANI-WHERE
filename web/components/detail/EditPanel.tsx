"use client";
import { useRouter } from "next/navigation";
import { useMemo, useState, useTransition } from "react";
import { editSaveAction, takeDownAction } from "@/app/popup-actions";
import { addDays, ALWAYS_END, blockSensitive, isAlways, linksErrors, siteName, split, type Picked } from "@/lib/cafe-rules";
import type { HistoryCard } from "@/lib/server/cafe";
import DeleteRequestButton from "../admin/DeleteRequest";
import AddressField from "../edit/AddressField";
import EditImages, { imageErrors, type ImgState } from "../edit/EditImages";
import { ClearInput, IntroField, TagPills } from "../edit/Fields";
import WorkPicker from "../edit/WorkPicker";
import { goLogin, useMember } from "../member/MemberContext";
import { toast } from "../member/Toast";
import { ChipInput, chipValues, LinkRows } from "./EditInputs";
import HistoryList from "./HistoryList";

// 상세 '수정하기' 탭 (A-DetailEdit 시안 · 앱 render_edit). 누구나(회원) 고칠 수 있고, 기존 기록은 남기고 새 줄로 쌓여서
// 언제든 되돌릴 수 있다. 등록 7단계와 같은 순서로 묶음 7개, 바뀐 칸은 민트로 표시하고, 아래 고정 줄에서 저장한다.
// 오른쪽에는 '저장하면 이렇게 바뀌어요'(이전 → 이후)와 수정 이력(되돌리기).
// 고칠 수 있는 칸 = 서버(editSaveAction)가 받는 칸 전부. 서버가 받지 않는 칸(운영 시간 · 예약처 · 찾아가는 법 등)은 만들지 않는다.

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

type Diff = { k: string; before: string; after: string };

const none = (v: string) => v.trim() || "없음";
const cut = (v: string, n = 60) => ([...v].length <= n ? v : [...v].slice(0, n).join("") + "…");
const same = (a: string[], b: string[]) => a.length === b.length && a.every((x, i) => x === b[i]);
const day = (v: string) => (isAlways(v) ? "상시" : v || "없음");

function Mark({ on }: { on: boolean }) {
  return on ? <span className="ade-mark">수정함</span> : null;
}

export default function EditPanel({
  entryId,
  data,
  byWork,
  history,
  histLv = {},
}: {
  entryId: string;
  data: EditData | null;
  byWork: Record<string, string[]>;
  history: HistoryCard[];
  /** 기록 번호 → 고친 회원의 후기 도장 랭크 (0 = 없음) */
  histLv?: Record<number, number>;
}) {
  const { me } = useMember();
  const router = useRouter();
  const [ver, setVer] = useState(0); // '되돌리기' = 고치던 내용을 버리고 처음 값으로
  if (!me || !data) {
    const msg = "팝업 정보 수정은 로그인하면 할 수 있어요.";
    return (
      <div className="ed-gate ade-gate">
        <div className="ntf-empty">{msg}</div>
        <button type="button" className="btn-main" onClick={() => goLogin(router, msg, `/popup/${entryId}?tab=edit`)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" width={16} height={16} aria-hidden>
            <path d="M14 4h4a2 2 0 012 2v12a2 2 0 01-2 2h-4M10 16l4-4-4-4M14 12H4" />
          </svg>
          로그인하고 계속하기
        </button>
      </div>
    );
  }
  return (
    <EditForm
      key={`${data.entryId}_${data.revision}_${ver}`}
      d={data}
      byWork={byWork}
      history={history}
      histLv={histLv}
      admin={me.admin}
      onReset={() => setVer((v) => v + 1)}
    />
  );
}

function EditForm({
  d,
  byWork,
  history,
  histLv,
  admin,
  onReset,
}: {
  d: EditData;
  byWork: Record<string, string[]>;
  history: HistoryCard[];
  histLv: Record<number, number>;
  admin: boolean;
  onReset: () => void;
}) {
  const router = useRouter();
  const wasAlways = isAlways(d.end);
  const init = useMemo(
    () => ({ perks: split(d.perks), goods: split(d.goods), links: d.links.split("\n").filter(Boolean) }),
    [d.perks, d.goods, d.links],
  );
  const [work, setWork] = useState(d.work);
  const [chars, setChars] = useState(d.characters);
  const [name, setName] = useState(d.cafeName);
  const [addr, setAddr] = useState(d.address);
  const [picked, setPicked] = useState<Picked | null>(null);
  const [start, setStart] = useState(d.start);
  const [always, setAlways] = useState(wasAlways);
  const [end, setEnd] = useState(wasAlways ? addDays(d.start, 30) : d.end);
  const [perks, setPerks] = useState(init.perks);
  const [perksDraft, setPerksDraft] = useState("");
  const [goods, setGoods] = useState(init.goods);
  const [goodsDraft, setGoodsDraft] = useState("");
  const [tags, setTags] = useState(d.tags);
  const [links, setLinks] = useState(init.links);
  const [intro, setIntro] = useState(d.intro);
  const [img, setImg] = useState<ImgState>({ removed: [], poster: null, extras: [] });
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, start_] = useTransition();
  const [askDel, setAskDel] = useState(false);
  const [delBusy, startDel] = useTransition();

  const perksAll = chipValues(perks, perksDraft);
  const goodsAll = chipValues(goods, goodsDraft);
  const linksAll = links.map((x) => x.trim()).filter(Boolean);
  const linksText = linksAll.join("\n");
  const endOut = always ? ALWAYS_END : end;

  const bad = blockSensitive(name, addr, perksAll.join(", "), goodsAll.join(", "), intro);
  const imgErr = useMemo(() => imageErrors(d.images, img), [d.images, img]);
  const linkErr = useMemo(() => linksErrors(linksText).errors, [linksText]);

  // ---- 바뀐 칸 (이전 → 이후) ----
  const keepN = d.images.filter((n) => !img.removed.includes(n)).length;
  const afterN = (img.poster ? 1 + Math.max(0, keepN - 1) : keepN) + img.extras.length;
  const imgNote = [
    img.poster ? "포스터 변경" : "",
    img.removed.length ? `${img.removed.length}장 삭제` : "",
    img.extras.length ? `${img.extras.length}장 추가` : "",
  ].filter(Boolean);
  const chg = {
    work: work !== d.work,
    chars: !same(chars, d.characters),
    name: name !== d.cafeName,
    addr: addr !== d.address,
    img: imgNote.length > 0,
    start: start !== d.start,
    end: always !== wasAlways || (!always && end !== d.end),
    perks: !same(perksAll, init.perks),
    goods: !same(goodsAll, init.goods),
    tags: !same([...tags].sort(), [...d.tags].sort()),
    links: !same(linksAll, init.links),
    intro: intro !== d.intro,
  };
  const diffs: Diff[] = [
    chg.work && { k: "작품", before: none(d.work), after: none(work) },
    chg.chars && { k: "캐릭터", before: none(d.characters.join(", ")), after: none(chars.join(", ")) },
    chg.name && { k: "카페명", before: none(d.cafeName), after: none(name) },
    chg.addr && { k: "주소", before: none(d.address), after: none(addr) },
    chg.img && { k: "이미지", before: `${d.images.length}장`, after: `${afterN}장 (${imgNote.join(" · ")})` },
    chg.start && { k: "시작일", before: day(d.start), after: day(start) },
    chg.end && { k: "종료일", before: day(d.end), after: day(endOut) },
    chg.perks && { k: "특전", before: none(init.perks.join(", ")), after: none(perksAll.join(", ")) },
    chg.goods && { k: "굿즈", before: none(init.goods.join(", ")), after: none(goodsAll.join(", ")) },
    chg.tags && { k: "이벤트", before: none(d.tags.join(", ")), after: none(tags.join(", ")) },
    chg.links && { k: "참고 웹사이트", before: none(init.links.map(siteName).join(", ")), after: none(linksAll.map(siteName).join(", ")) },
    chg.intro && { k: "팝업 소개", before: cut(none(d.intro)), after: cut(none(intro)) },
  ].filter(Boolean) as Diff[];
  const set = (...on: boolean[]) => (on.some(Boolean) ? " chg" : "");

  const save = () => {
    const fd = new FormData();
    fd.set("entry_id", d.entryId);
    fd.set("work", work);
    fd.set("characters", JSON.stringify(chars));
    fd.set("cafe_name", name);
    fd.set("address", addr);
    fd.set("picked", picked && picked.address === addr.trim() ? JSON.stringify(picked) : "");
    fd.set("start_date", start);
    fd.set("end_date", endOut);
    if (always) fd.set("always", "1");
    fd.set("perks", perksAll.join(", "));
    fd.set("goods", goodsAll.join(", "));
    for (const t of tags) fd.append("tags", t);
    fd.set("links", linksText);
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
      document.querySelector(".ad-tabs")?.scrollIntoView({ behavior: "smooth", block: "start" });
      router.refresh();
    });
  };

  return (
    <div className="ed-panel ade">
      <p className="ade-info">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" aria-hidden>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v5M12 16h.01" />
        </svg>
        <span>
          회원이면 누구나 모든 칸을 고칠 수 있어요. 기존 기록은 남기고 새 줄로 쌓여서, 잘못 고쳐도 <strong>수정 이력</strong>에서 언제든 되돌릴 수
          있어요.
        </span>
      </p>

      <div className="ade-cols">
        <div className="ade-form">
          <fieldset className={`ade-set${set(chg.work, chg.chars)}`}>
            <legend>
              1 · 작품 · 캐릭터 <Mark on={chg.work || chg.chars} />
            </legend>
            <div className={`ade-grid2 ade-work${chg.work ? " chg-a" : ""}${chg.chars ? " chg-b" : ""}`}>
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
            </div>
          </fieldset>

          <fieldset className={`ade-set${set(chg.name, chg.addr)}`}>
            <legend>
              2 · 카페 정보 <Mark on={chg.name || chg.addr} />
            </legend>
            <div className={`ade-f${set(chg.name)}`}>
              <label className="ed-field">
                <span className="ed-label">카페명 · 장소 이름</span>
                <ClearInput value={name} onChange={setName} maxLength={100} />
              </label>
            </div>
            <div className={`ade-f ade-addr${set(chg.addr)}`}>
              <AddressField
                value={addr}
                onChange={setAddr}
                onPick={(c) => {
                  setPicked({ address: c.address, lat: c.lat, lng: c.lng, source: c.source, precision: c.precision });
                  setAddr(c.address);
                }}
              />
            </div>
          </fieldset>

          <fieldset className={`ade-set${set(chg.img)}`}>
            <legend>
              3 · 이미지 <small>{afterN}장</small> <Mark on={chg.img} />
            </legend>
            <EditImages images={d.images} value={img} onChange={setImg} />
          </fieldset>

          <fieldset className={`ade-set${set(chg.start, chg.end)}`}>
            <legend>
              4 · 기간 <Mark on={chg.start || chg.end} />
            </legend>
            <div className="ade-grid2">
              <div className={`ade-f${set(chg.start)}`}>
                <label className="ed-field">
                  <span className="ed-label">시작일</span>
                  <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
                </label>
              </div>
              <div className={`ade-f${set(chg.end && !always)}`}>
                <label className="ed-field">
                  <span className="ed-label">종료일</span>
                  <input type="date" value={end} disabled={always} onChange={(e) => setEnd(e.target.value)} />
                </label>
              </div>
            </div>
            <label className={`ck ed-ck ade-ck${set(always !== wasAlways)}`}>
              <input type="checkbox" checked={always} onChange={(e) => setAlways(e.target.checked)} />
              <span>종료일 없음 (상시)</span>
            </label>
            {d.check && (
              <div className="auth-warn ed-warn">
                기간을 정확히 읽지 못한 팝업이에요
                {d.check.raw && !d.check.raw.startsWith("(") ? ` (원문: '${d.check.raw}')` : ""}. 공식 공지를 보고 시작·종료일을 고쳐 주세요.
              </div>
            )}
          </fieldset>

          <fieldset className={`ade-set${set(chg.perks, chg.goods, chg.tags)}`}>
            <legend>
              5 · 특전 · 굿즈 · 이벤트 <Mark on={chg.perks || chg.goods || chg.tags} />
            </legend>
            <div className={`ade-f${set(chg.perks)}`}>
              <ChipInput
                label="특전"
                items={perks}
                draft={perksDraft}
                onItems={setPerks}
                onDraft={setPerksDraft}
                placeholder="예: 랜덤 코스터 (쓰고 Enter)"
              />
            </div>
            <div className={`ade-f${set(chg.goods)}`}>
              <ChipInput
                label="굿즈"
                items={goods}
                draft={goodsDraft}
                onItems={setGoods}
                onDraft={setGoodsDraft}
                placeholder="예: 아크릴 스탠드 (쓰고 Enter)"
              />
            </div>
            <div className={`ade-f ade-tags${set(chg.tags)}`}>
              <TagPills value={tags} onChange={setTags} />
            </div>
          </fieldset>

          <fieldset className={`ade-set${set(chg.links)}`}>
            <legend>
              6 · 참고 웹사이트 <small>http:// 또는 https:// 로 시작하는 주소</small> <Mark on={chg.links} />
            </legend>
            <div className={`ade-f${set(chg.links)}`}>
              <LinkRows value={links} onChange={setLinks} errors={linkErr} />
            </div>
          </fieldset>

          <fieldset className={`ade-set${set(chg.intro)}`}>
            <legend>
              7 · 팝업 소개 <Mark on={chg.intro} />
            </legend>
            <div className={`ade-f${set(chg.intro)}`}>
              <IntroField value={intro} onChange={setIntro} hideLabel />
            </div>
            <p className="ed-cap">전화번호 · 이메일 · 계좌번호가 들어 있으면 저장되지 않아요.</p>
          </fieldset>

          {bad && <div className="ed-err">{bad}</div>}
          {errors.map((e) => (
            <div key={e} className="ed-err">
              {e}
            </div>
          ))}

          <div className="ade-bar">
            <span className="ade-bar-t" aria-live="polite">
              {diffs.length ? (
                <>
                  바뀐 칸 <strong>{diffs.length}곳</strong> · {diffs.map((x) => x.k).join(", ")}
                </>
              ) : (
                "아직 바꾼 칸이 없어요"
              )}
            </span>
            <button type="button" className="ade-reset" disabled={busy || !diffs.length} onClick={onReset}>
              되돌리기
            </button>
            <button
              type="button"
              className="ade-save"
              disabled={busy || !diffs.length || !!bad || imgErr.length > 0 || linkErr.length > 0}
              onClick={save}
            >
              {busy ? "저장 중…" : "저장하기"}
            </button>
          </div>

          <div className="ade-del">
            <span>끝난 팝업이거나 잘못 올라온 팝업인가요?</span>
            {admin ? (
              <button type="button" className="btn-line" onClick={() => setAskDel(true)}>
                지도에서 내리기 (관리자)
              </button>
            ) : (
              <DeleteRequestButton targetType="cafe" targetId={d.entryId} title={d.title} />
            )}
          </div>
        </div>

        <aside className="ade-side" aria-label="바뀌는 내용 · 수정 이력">
          <section className="ade-diff" aria-labelledby="ade-diff-h">
            <h2 id="ade-diff-h">저장하면 이렇게 바뀌어요</h2>
            {diffs.length ? (
              diffs.map((x) => (
                <div key={x.k} className="ade-diff-one">
                  <span>{x.k}</span>
                  <del>{x.before}</del>
                  <ins>→ {x.after}</ins>
                </div>
              ))
            ) : (
              <p className="ed-cap">칸을 고치면 이전 내용과 바뀐 내용을 여기에서 나란히 볼 수 있어요.</p>
            )}
          </section>
          <section className="ade-hist" aria-labelledby="ade-hist-h">
            <h2 id="ade-hist-h">
              수정 이력 <span>{history.length}</span>
            </h2>
            <HistoryList entryId={d.entryId} cards={history} lv={histLv} />
          </section>
        </aside>
      </div>

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
