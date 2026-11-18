"use client";
import { useEffect, useMemo, useRef, type ReactNode } from "react";
import { EVENT_TAGS, IMAGE_ACCEPT, linksErrors, MAX_INTRO, MAX_LINKS } from "@/lib/cafe-rules";
import { LinkIcon } from "../Icons";

// 등록하기 · 수정하기가 같이 쓰는 입력칸 (앱 _links_field · _intro_field · pills · _clear_buttons · 입력칸 옆 ? 안내).

/** 입력칸 이름 옆 ? (커서를 올리거나 누르면 안내) — 버튼·링크 title 대신 */
export function Help({ children }: { children: ReactNode }) {
  return (
    <span className="help" tabIndex={0} aria-label="도움말">
      ?<span className="tip">{children}</span>
    </span>
  );
}

const X = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" aria-hidden>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);

/** 글자 입력칸 + 오른쪽 안의 × (내용이 있을 때만, 누르면 한 번에 비움 — 앱 _clear_buttons) */
export function ClearInput({
  value,
  onChange,
  ...rest
}: { value: string; onChange: (v: string) => void } & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <span className="ed-clear">
      <input {...rest} ref={ref} value={value} onChange={(e) => onChange(e.target.value)} />
      {value && !rest.disabled && (
        <button
          type="button"
          className="ed-x"
          aria-label="입력 내용 지우기"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            onChange("");
            ref.current?.focus();
          }}
        >
          {X}
        </button>
      )}
    </span>
  );
}

export function ClearArea({
  value,
  onChange,
  ...rest
}: { value: string; onChange: (v: string) => void } & Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, "value" | "onChange">) {
  const ref = useRef<HTMLTextAreaElement>(null);
  return (
    <span className="ed-clear ta">
      <textarea {...rest} ref={ref} value={value} onChange={(e) => onChange(e.target.value)} />
      {value && (
        <button
          type="button"
          className="ed-x"
          aria-label="입력 내용 지우기"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            onChange("");
            ref.current?.focus();
          }}
        >
          {X}
        </button>
      )}
    </span>
  );
}

/** 이벤트 추가 정보 (앱 st.pills · cafe.EVENT_TAGS) */
export function TagPills({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="ed-field">
      <span className="ed-label">이벤트 추가 정보</span>
      <div className="pills ed-pills">
        {EVENT_TAGS.map((t) => {
          const on = value.includes(t);
          return (
            <button
              key={t}
              type="button"
              className="pill"
              aria-pressed={on}
              onClick={() => onChange(on ? value.filter((x) => x !== t) : [...value, t])}
            >
              {t}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** 참고 웹사이트 (앱 _links_field): 한 줄에 하나. 잘못된 주소·개수 초과면 아래에 오류 */
export function LinksField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { errors } = useMemo(() => linksErrors(value), [value]);
  return (
    <label className="ed-field">
      <span className="ed-label">
        <LinkIcon className="ed-li" />
        참고 웹사이트
        <Help>http:// 또는 https:// 로 시작하는 주소를 최대 {MAX_LINKS}개까지</Help>
      </span>
      <ClearArea
        value={value}
        onChange={onChange}
        rows={3}
        style={{ height: 90 }}
        placeholder="https://x.com/... (공지 트윗·인스타·공식 사이트, 한 줄에 하나)"
      />
      {errors.map((e) => (
        <div key={e} className="ed-err">
          {e}
        </div>
      ))}
    </label>
  );
}

/** 팝업 소개 (앱 _intro_field): 최대 3000자 */
export function IntroField({
  value,
  onChange,
  hideLabel = false,
}: {
  value: string;
  onChange: (v: string) => void;
  hideLabel?: boolean;
}) {
  return (
    <label className="ed-field">
      <span className={hideLabel ? "sr-only" : "ed-label"}>
        팝업 소개
        {!hideLabel && <Help>상세 화면의 &apos;팝업 소개&apos; 에 그대로 보여요. 비워 둬도 등록할 수 있어요</Help>}
      </span>
      <ClearArea
        value={value}
        onChange={(v) => onChange([...v].slice(0, MAX_INTRO).join(""))}
        maxLength={MAX_INTRO}
        style={{ height: 220 }}
        placeholder="어떤 팝업인지 자유롭게 소개해 주세요 (콘셉트, 메뉴, 운영 방식, 입장 방법 등)"
      />
      <span className="ed-count">
        {[...value].length}/{MAX_INTRO}
      </span>
    </label>
  );
}

/** 이미지 올리는 칸 (회색 상자 + 민트 점선, 끌어다 놓기 · 눌러서 고르기) */
export function Dropzone({
  label,
  hint,
  multiple = false,
  onFiles,
  resetKey,
}: {
  label: string;
  hint: string;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
  resetKey?: number;
}) {
  return (
    <label className="ed-drop" key={resetKey}>
      <input
        type="file"
        accept={IMAGE_ACCEPT}
        multiple={multiple}
        aria-label={label}
        onChange={(e) => {
          const fs = Array.from(e.target.files || []);
          if (fs.length) onFiles(fs);
          e.target.value = "";
        }}
      />
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" />
      </svg>
      <b>여기에 끌어다 놓거나 눌러서 고르기</b>
      <span>{hint}</span>
    </label>
  );
}

/** 고른 파일의 미리보기 주소 (화면을 떠나면 놓아 준다) */
export function useObjectUrls(files: File[]): string[] {
  const urls = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => urls.forEach((u) => URL.revokeObjectURL(u)), [urls]);
  return urls;
}
