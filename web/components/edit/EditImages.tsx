"use client";
import { useState } from "react";
import { uploadUrl } from "@/lib/avatar";
import { EXTRA_MB, MAX_EXTRAS, POSTER_MB, tooBig } from "@/lib/cafe-rules";
import { Dropzone, useObjectUrls } from "./Fields";

// 수정하기의 이미지 칸 (앱 _edit_images · _poster_upload · _confirm_poster).
// 지금 이미지를 보여 주고 '삭제'(수정 저장을 눌러야 반영) · 포스터 바꾸기(이미 있으면 바꿀지 묻는다) · 이미지 추가.
// 첫 번째가 포스터. 저장할 때는 [새 포스터 + 남긴 이미지 2장째부터] 또는 [남긴 이미지] 뒤에 추가 이미지.

export type ImgState = { removed: string[]; poster: File | null; extras: File[] };

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

  return (
    <div className="ed-field">
      <b className="ed-sub">이미지</b>
      {keep.length ? (
        <>
          <p className="ed-cap">첫 번째가 포스터예요.</p>
          <div className="ed-grid">
            {keep.map((n) => (
              <div key={n} className="ed-cell">
                <Thumb src={uploadUrl(n)} />
                <button type="button" className="btn-line ed-sm" onClick={() => onChange({ ...value, removed: [...value.removed, n] })}>
                  삭제
                </button>
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="ed-cap">아직 이미지가 없어요.</p>
      )}
      {value.removed.length > 0 && (
        <div className="ed-undo">
          <span className="ed-cap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
            </svg>
            {value.removed.length}장 삭제 예정 · <b>수정 저장</b>을 눌러야 반영돼요.
          </span>
          <button type="button" className="btn-line ed-sm" onClick={() => onChange({ ...value, removed: [] })}>
            삭제 취소
          </button>
        </div>
      )}

      <span className="ed-label">
        포스터 바꾸기 (1장, ~ {POSTER_MB} MB)
        <span className="help" tabIndex={0} aria-label="도움말">
          ?<span className="tip">포스터는 한 장만 올릴 수 있어요</span>
        </span>
      </span>
      <Dropzone
        label="포스터 바꾸기"
        hint={`PNG · JPG · JPEG · WEBP · GIF · ~ ${POSTER_MB} MB`}
        resetKey={ver}
        onFiles={([f]) => {
          // 포스터는 한 장: 이미 있으면 바꿀지 묻는다
          if (keep.length) setAsk(f);
          else onChange({ ...value, poster: f });
        }}
      />
      {value.poster && (
        <div className="ed-newposter">
          <span className="ed-cap ok">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <circle cx="12" cy="12" r="9" />
              <path d="M8 12.3l2.8 2.8L16.2 9.6" />
            </svg>
            새 포스터로 변경돼요. <b>수정 저장</b>을 눌러야 반영돼요.
          </span>
          { }
          <img src={posterUrl[0]} alt="새 포스터 미리보기" width={160} />
          <button type="button" className="btn-line ed-sm" onClick={() => onChange({ ...value, poster: null })}>
            취소
          </button>
        </div>
      )}

      <span className="ed-label">이미지 추가</span>
      <Dropzone
        label="이미지 추가"
        multiple
        hint={`PNG · JPG · JPEG · WEBP · GIF · 한 장에 ~ ${EXTRA_MB} MB`}
        onFiles={(fs) => onChange({ ...value, extras: [...value.extras, ...fs] })}
      />
      {value.extras.length > 0 && (
        <ul className="ed-files">
          {value.extras.map((f, i) => (
            <li key={`${f.name}-${i}`}>
              { }
              <img src={extraUrls[i]} alt="" />
              <span>{f.name}</span>
              <button
                type="button"
                aria-label={`${f.name} 빼기`}
                onClick={() => onChange({ ...value, extras: value.extras.filter((_, k) => k !== i) })}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
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
            { }
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
