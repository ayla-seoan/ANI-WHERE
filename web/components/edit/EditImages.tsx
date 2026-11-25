"use client";
import { useState } from "react";
import { uploadUrl } from "@/lib/avatar";
import { EXTRA_MB, IMAGE_ACCEPT, MAX_EXTRAS, POSTER_MB, tooBig } from "@/lib/cafe-rules";
import { useObjectUrls } from "./Fields";

// 수정하기의 이미지 칸 (A-DetailEdit 시안 3번 묶음 · 앱 _edit_images · _poster_upload · _confirm_poster).
// 3:4 작은 사진 칸이 한 줄로 서고 첫 번째에 '대표'. ✕ 로 빼기(저장을 눌러야 반영) · 대표 사진 바꾸기(이미 있으면 바꿀지 묻는다) · + 로 추가.
// 저장할 때는 [새 포스터 + 남긴 이미지 2장째부터] 또는 [남긴 이미지] 뒤에 추가 이미지.

export type ImgState = { removed: string[]; poster: File | null; extras: File[] };

const X = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" aria-hidden>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);

function Thumb({ src }: { src: string }) {
  const [bad, setBad] = useState(false);
  return bad ? (
    <span className="ed-nofile">(파일 없음)</span>
  ) : (
    <img src={src} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setBad(true)} />
  );
}

/** 지금 상태에서 생기는 오류 (앱과 같은 문구) */
export function imageErrors(images: string[], s: ImgState): string[] {
  const keep = images.filter((n) => !s.removed.includes(n));
  const errors: string[] = [];
  if (s.poster && tooBig(s.poster.size, POSTER_MB)) errors.push(`포스터는 ${POSTER_MB} MB 까지 올릴 수 있습니다.`);
  if (s.extras.some((f) => tooBig(f.size, EXTRA_MB))) errors.push(`추가 이미지는 한 장에 ${EXTRA_MB} MB 까지 올릴 수 있습니다.`);
  const total = (s.poster ? 1 + Math.max(0, keep.length - 1) : keep.length) + s.extras.length;
  if (total - 1 > MAX_EXTRAS) errors.push(`추가 이미지는 ${MAX_EXTRAS}장까지 둘 수 있습니다. 몇 장 지워 주세요.`);
  return errors;
}

export default function EditImages({ images, value, onChange }: { images: string[]; value: ImgState; onChange: (s: ImgState) => void }) {
  const [ask, setAsk] = useState<File | null>(null);
  const [ver, setVer] = useState(0);
  const keep = images.filter((n) => !value.removed.includes(n));
  const posterUrl = useObjectUrls(value.poster ? [value.poster] : []);
  const askUrl = useObjectUrls(ask ? [ask] : []);
  const extraUrls = useObjectUrls(value.extras);
  const errors = imageErrors(images, value);
  // 새 포스터를 고르면 지금 첫 장 자리에 들어간다 (남긴 이미지는 2장째부터)
  const old = value.poster ? keep.slice(1) : keep;

  return (
    <div className="ade-imgf">
      <div className="ade-imgs">
        {value.poster && (
          <span className="ade-img is-poster is-new">
            {posterUrl[0] && <img src={posterUrl[0]} alt="새 포스터 미리보기" />}
            <span className="ade-tag">새 대표</span>
            <button type="button" aria-label="새 포스터 취소" onClick={() => onChange({ ...value, poster: null })}>
              {X}
            </button>
          </span>
        )}
        {old.map((n, i) => (
          <span key={n} className={`ade-img${!value.poster && i === 0 ? " is-poster" : ""}`}>
            <Thumb src={uploadUrl(n)} />
            {!value.poster && i === 0 && <span className="ade-tag">대표</span>}
            <button type="button" aria-label={`이미지 ${i + 1} 빼기`} onClick={() => onChange({ ...value, removed: [...value.removed, n] })}>
              {X}
            </button>
          </span>
        ))}
        {value.extras.map((f, i) => (
          <span key={`${f.name}-${i}`} className="ade-img is-new is-extra">
            {extraUrls[i] && <img src={extraUrls[i]} alt="" />}
            <span className="ade-tag">새 사진</span>
            <button
              type="button"
              aria-label={`${f.name} 빼기`}
              onClick={() => onChange({ ...value, extras: value.extras.filter((_, k) => k !== i) })}
            >
              {X}
            </button>
          </span>
        ))}
        <label className="ade-img ade-img-add">
          <span className="sr-only">이미지 추가</span>
          <input
            type="file"
            accept={IMAGE_ACCEPT}
            multiple
            aria-label="이미지 추가"
            onChange={(e) => {
              const fs = Array.from(e.target.files || []);
              e.target.value = "";
              if (fs.length) onChange({ ...value, extras: [...value.extras, ...fs] });
            }}
          />
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" aria-hidden>
            <path d="M12 5v14M5 12h14" />
          </svg>
        </label>
      </div>
      <div className="ade-img-foot">
        <label className="ade-poster-btn" key={ver}>
          <input
            type="file"
            accept={IMAGE_ACCEPT}
            aria-label="포스터 바꾸기"
            onChange={(e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (!f) return;
              // 포스터는 한 장: 이미 있으면 바꿀지 묻는다
              if (keep.length) setAsk(f);
              else onChange({ ...value, poster: f });
            }}
          />
          대표 사진 바꾸기
        </label>
        <span className="ed-cap">
          첫 번째 사진이 포스터로 보여요. 포스터 ~ {POSTER_MB} MB · 추가 이미지 한 장 ~ {EXTRA_MB} MB, {MAX_EXTRAS}장까지. 사진의 위치 정보는
          지우고 저장해요.
        </span>
      </div>
      {!keep.length && !value.poster && !value.extras.length && <p className="ed-cap">아직 이미지가 없어요.</p>}
      {value.poster && (
        <p className="ed-cap ok ed-newposter">
          새 포스터로 변경돼요. <b>저장하기</b>를 눌러야 반영돼요.
        </p>
      )}
      {value.removed.length > 0 && (
        <div className="ed-undo">
          <span className="ed-cap">
            {value.removed.length}장 삭제 예정 · <b>저장하기</b>를 눌러야 반영돼요.
          </span>
          <button type="button" className="btn-line ed-sm" onClick={() => onChange({ ...value, removed: [] })}>
            삭제 취소
          </button>
        </div>
      )}
      {errors.map((e) => (
        <div key={e} className="ed-err">
          {e}
        </div>
      ))}

      {ask && (
        <div className="dlg-bg" role="dialog" aria-modal="true" aria-label="포스터 변경">
          <div className="dlg">
            <b className="dlg-t">포스터 변경</b>
            <p>
              포스터는 한 장만 올릴 수 있어요. 새 포스터로 <b>변경하시겠습니까?</b>
            </p>
            <img src={askUrl[0]} alt="" width={220} className="ed-askimg" />
            <div className="two">
              <button
                type="button"
                className="btn-line"
                onClick={() => {
                  setAsk(null);
                  setVer((v) => v + 1);
                }}
              >
                취소
              </button>
              <button
                type="button"
                className="btn-main"
                onClick={() => {
                  onChange({ ...value, poster: ask });
                  setAsk(null);
                }}
              >
                변경
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
