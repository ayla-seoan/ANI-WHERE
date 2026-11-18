"use client";
import { useId, useMemo, useRef, useState } from "react";

// 작품 · 캐릭터 고르기 (앱 pick_work_and_characters): 작품을 고르면 그 작품의 캐릭터만 고를 수 있다.
// 둘 다 목록에 없으면 새로 입력 (작품: 입력하고 Enter, 캐릭터: 이름을 입력하고 Enter).
// 작품을 바꾸면 캐릭터는 비워진다 (처음 작품으로 돌아오면 처음 캐릭터가 다시 채워진다).

const norm = (s: string) => s.replace(/\s+/g, "").toLowerCase();

function Combo({
  options,
  value,
  onPick,
  placeholder,
  label,
}: {
  options: string[];
  value: string;
  onPick: (v: string) => void;
  placeholder: string;
  label: string;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hi, setHi] = useState(0);
  const id = useId();
  const list = useMemo(() => {
    const k = norm(q);
    const hits = k ? options.filter((o) => norm(o).includes(k)) : options;
    return hits.slice(0, 200);
  }, [options, q]);
  const fresh = q.trim() && !options.some((o) => o === q.trim()) ? q.trim() : "";
  const items = fresh ? [`__new__${fresh}`, ...list] : list;
  const choose = (v: string) => {
    onPick(v);
    setQ("");
    setOpen(false);
  };
  return (
    <div className="ed-combo">
      <input
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-label={label}
        value={open ? q : value}
        placeholder={open && value ? value : placeholder}
        onFocus={() => {
          setOpen(true);
          setQ("");
          setHi(0);
        }}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onChange={(e) => {
          setQ(e.target.value);
          setHi(0);
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setHi((h) => Math.min(items.length - 1, h + 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setHi((h) => Math.max(0, h - 1));
          } else if (e.key === "Enter") {
            e.preventDefault();
            const it = items[hi];
            if (it) choose(it.startsWith("__new__") ? it.slice(7) : it);
          } else if (e.key === "Escape") {
            setOpen(false);
            (e.target as HTMLInputElement).blur();
          }
        }}
      />
      {value && !open && (
        <button type="button" className="ed-x" aria-label={`${label} 지우기`} onClick={() => onPick("")}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" aria-hidden>
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
      )}
      <span className="ed-caret" aria-hidden />
      {open && (
        <ul className="ed-menu" role="listbox" id={`${id}-list`}>
          {items.length === 0 && <li className="ed-none">목록에 없어요. 이름을 입력하고 Enter</li>}
          {items.map((it, i) => (
            <li
              key={it}
              role="option"
              aria-selected={i === hi}
              className={i === hi ? "on" : ""}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(it.startsWith("__new__") ? it.slice(7) : it);
              }}
              onMouseEnter={() => setHi(i)}
            >
              {it.startsWith("__new__") ? (
                <>
                  <b>{it.slice(7)}</b> <span className="ed-new">새로 입력</span>
                </>
              ) : (
                it
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Multi({
  options,
  value,
  onChange,
  disabled,
  placeholder,
}: {
  options: string[];
  value: string[];
  onChange: (v: string[]) => void;
  disabled: boolean;
  placeholder: string;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hi, setHi] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const id = useId();
  const rest = options.filter((o) => !value.includes(o));
  const k = norm(q);
  const list = k ? rest.filter((o) => norm(o).includes(k)) : rest;
  const fresh = q.trim() && !options.includes(q.trim()) && !value.includes(q.trim()) ? q.trim() : "";
  const items = fresh ? [`__new__${fresh}`, ...list] : list;
  const add = (v: string) => {
    if (v && !value.includes(v)) onChange([...value, v]);
    setQ("");
    setHi(0);
  };
  return (
    <div className={`ed-multi${disabled ? " off" : ""}`} onClick={() => !disabled && input.current?.focus()}>
      {value.map((c) => (
        <span key={c} className="ed-chip">
          {c}
          <button
            type="button"
            aria-label={`${c} 빼기`}
            onClick={(e) => {
              e.stopPropagation();
              onChange(value.filter((x) => x !== c));
            }}
          >
            ×
          </button>
        </span>
      ))}
      <input
        ref={input}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-list`}
        aria-label="캐릭터"
        disabled={disabled}
        value={q}
        placeholder={value.length ? "" : placeholder}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onChange={(e) => {
          setQ(e.target.value);
          setHi(0);
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            const it = items[hi];
            if (it) add(it.startsWith("__new__") ? it.slice(7) : it);
          } else if (e.key === "ArrowDown") {
            e.preventDefault();
            setHi((h) => Math.min(items.length - 1, h + 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setHi((h) => Math.max(0, h - 1));
          } else if (e.key === "Backspace" && !q && value.length) {
            onChange(value.slice(0, -1));
          } else if (e.key === "Escape") setOpen(false);
        }}
      />
      {open && !disabled && items.length > 0 && (
        <ul className="ed-menu" role="listbox" id={`${id}-list`}>
          {items.map((it, i) => (
            <li
              key={it}
              role="option"
              aria-selected={i === hi}
              className={i === hi ? "on" : ""}
              onMouseDown={(e) => {
                e.preventDefault();
                add(it.startsWith("__new__") ? it.slice(7) : it);
              }}
              onMouseEnter={() => setHi(i)}
            >
              {it.startsWith("__new__") ? (
                <>
                  <b>{it.slice(7)}</b> <span className="ed-new">새로 입력</span>
                </>
              ) : (
                it
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function WorkPicker({
  byWork,
  work,
  characters,
  initialWork,
  initialChars,
  onChange,
}: {
  byWork: Record<string, string[]>;
  work: string;
  characters: string[];
  /** 처음 값 (작품을 바꿨다가 돌아오면 처음 캐릭터를 다시 채운다) */
  initialWork: string;
  initialChars: string[];
  onChange: (work: string, chars: string[]) => void;
}) {
  const works = useMemo(() => {
    const ws = Object.keys(byWork).sort();
    if (initialWork && !ws.includes(initialWork)) ws.push(initialWork);
    if (work && !ws.includes(work)) ws.push(work);
    return ws;
  }, [byWork, initialWork, work]);
  const options = useMemo(() => {
    const o = [...(byWork[work] || [])];
    for (const c of characters) if (!o.includes(c)) o.push(c);
    return o;
  }, [byWork, work, characters]);
  return (
    <>
      <div className="ed-field">
        <span className="ed-label">작품</span>
        <Combo
          label="작품"
          options={works}
          value={work}
          placeholder="작품명으로 찾기 · 없으면 새로 입력"
          onPick={(w) => onChange(w.trim(), w.trim() && w.trim() === initialWork ? initialChars : [])}
        />
      </div>
      <div className="ed-field">
        <span className="ed-label">캐릭터</span>
        <Multi
          key={work}
          options={options}
          value={characters}
          disabled={!work}
          placeholder={work ? "캐릭터 고르기 · 없으면 이름을 입력하고 Enter" : "작품을 먼저 골라주세요"}
          onChange={(c) => onChange(work, c)}
        />
      </div>
    </>
  );
}
