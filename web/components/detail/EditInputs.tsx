"use client";
import { useRef } from "react";
import { MAX_LINKS, split } from "@/lib/cafe-rules";

// 상세 '수정하기' 탭 전용 입력칸 (A-DetailEdit 시안 5 · 6번 묶음). 등록하기(/add)의 입력칸(edit/Fields.tsx)은 그대로 둔다.
// 저장 값은 예전과 같다: 특전 · 굿즈 = 쉼표로 이은 글, 참고 웹사이트 = 한 줄에 하나.

const X = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" aria-hidden>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);

/** 칩 목록 + 쓰는 중인 글 → 저장할 목록 (쓰는 중인 글도 쉼표로 나눠 함께 저장된다) */
export const chipValues = (items: string[], draft: string) => [...items, ...split(draft).filter((x) => !items.includes(x))];

/** 특전 · 굿즈: 칩으로 보이고 ✕ 로 빼고, 입력칸에 쓰고 Enter(또는 쉼표)로 더한다 */
export function ChipInput({
  label,
  items,
  draft,
  onItems,
  onDraft,
  placeholder,
  maxLength = 500,
}: {
  label: string;
  items: string[];
  draft: string;
  onItems: (v: string[]) => void;
  onDraft: (v: string) => void;
  placeholder: string;
  maxLength?: number;
}) {
  const input = useRef<HTMLInputElement>(null);
  const commit = (text: string) => {
    const add = split(text).filter((x) => !items.includes(x));
    if (add.length) onItems([...items, ...add]);
    onDraft("");
  };
  return (
    <label className="ed-field ade-chipf">
      <span className="ed-label">{label}</span>
      <span className="ade-chips">
        {items.map((it) => (
          <span key={it} className="ade-chip">
            {it}
            <button
              type="button"
              aria-label={`${it} 빼기`}
              onClick={(e) => {
                e.preventDefault();
                onItems(items.filter((x) => x !== it));
                input.current?.focus();
              }}
            >
              {X}
            </button>
          </span>
        ))}
        <input
          ref={input}
          value={draft}
          maxLength={maxLength}
          placeholder={items.length ? "+ 추가" : placeholder}
          aria-label={`${label} 추가`}
          onChange={(e) => {
            const v = e.target.value;
            // 쉼표를 치면 그 앞까지를 칩으로
            if (/,\s*$/.test(v)) commit(v);
            else onDraft(v);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              if (draft.trim()) commit(draft);
            } else if (e.key === "Backspace" && !draft && items.length) {
              onItems(items.slice(0, -1));
            }
          }}
        />
      </span>
    </label>
  );
}

/** 참고 웹사이트: 한 줄에 주소 하나 + ✕, '+ 링크 추가' (최대 MAX_LINKS 개) */
export function LinkRows({ value, onChange, errors }: { value: string[]; onChange: (v: string[]) => void; errors: string[] }) {
  const rows = value.length ? value : [""];
  return (
    <div className="ade-links">
      {rows.map((u, i) => (
        <div key={i} className="ade-link">
          <input
            type="url"
            inputMode="url"
            value={u}
            maxLength={500}
            aria-label={`참고 웹사이트 주소 ${i + 1}`}
            placeholder="https://x.com/... (공지 트윗 · 인스타 · 공식 사이트)"
            onChange={(e) => onChange(rows.map((x, k) => (k === i ? e.target.value : x)))}
          />
          <button type="button" aria-label={`링크 ${i + 1} 빼기`} onClick={() => onChange(rows.filter((_, k) => k !== i))}>
            {X}
          </button>
        </div>
      ))}
      {rows.length < MAX_LINKS && (
        <button type="button" className="ade-add" onClick={() => onChange([...rows, ""])}>
          + 링크 추가
        </button>
      )}
      {errors.map((e) => (
        <div key={e} className="ed-err">
          {e}
        </div>
      ))}
    </div>
  );
}
