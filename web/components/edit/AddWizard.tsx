"use client";
import { useState, useTransition } from "react";
import { addAction, locateAction, quickReadAction, type QuickGot } from "@/app/popup-actions";
import {
  addDays,
  ALWAYS_END,
  askPh,
  blockSensitive,
  EVENT_TAGS,
  EXTRA_MB,
  isAlways,
  linksErrors,
  MAX_EXTRAS,
  objJosa,
  possibleDuplicates,
  POSTER_MB,
  split,
  TAG_ALWAYS,
  tooBig,
  validateCafe,
  type CafeEntry,
  type ExistingRow,
  type Picked,
} from "@/lib/cafe-rules";
import AddressField from "./AddressField";
import { ClearArea, ClearInput, Dropzone, Help, IntroField, LinksField, TagPills, useObjectUrls } from "./Fields";
import WorkPicker from "./WorkPicker";

// 등록하기 (앱 page_add): 한 화면에 한 단계씩 묻는다 — 단계 표시줄 + 가운데 카드 하나.
// 첫 단계의 '공지로 간편등록' 은 공지 글을 붙여넣어 한 화면에서 바로 등록한다 (AI 키가 있으면 AI, 없거나 실패하면 규칙 기반).
// 마지막 '등록 확인' 에서 앞에서 넣은 정보를 한눈에 보여 주고 등록하면 새 팝업 상세로 간다.

const STEPS: [string, string][] = [
  ["작품 · 캐릭터", "movie"],
  ["카페 정보", "local_cafe"],
  ["이미지", "image"],
  ["기간", "calendar_month"],
  ["특전 · 굿즈", "redeem"],
  ["팝업 소개", "article"],
  ["등록 확인", "task_alt"],
];

const ICON: Record<string, React.ReactNode> = {
  movie: <path d="M4 5h16v14H4zM4 9h16M8 5l2 4M13 5l2 4" />,
  task_alt: <path d="M21 11.1V12a9 9 0 11-5.3-8.2M21 4L12 13l-3-3" />,
  edit_note: <path d="M4 6h10M4 10h10M4 14h6M14 20h3l5-5-3-3-5 5v3z" />,
  check: <path d="M5 12.5l4.5 4.5L19 7.5" />,
  location_on: <path d="M12 21s-6-5.3-6-11a6 6 0 1112 0c0 5.7-6 11-6 11zM12 12a2 2 0 100-4 2 2 0 000 4z" />,
  schedule: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  festival: <path d="M12 3l8 6H4l8-6zM5 9v11M19 9v11M9 20v-5h6v5" />,
  build: <path d="M14.7 6.3a4 4 0 00-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 005.4-5.4l-2.6 2.6-2.4-.6-.6-2.4 2.6-2.6z" />,
  image: (
    <>
      <rect x="4" y="5" width="16" height="14" rx="2" />
      <path d="M4 16l4.5-4.5 4 4 3-3L20 17M15.5 9.5h.01" />
    </>
  ),
};
const Mi = ({ name, big = false }: { name: string; big?: boolean }) => (
  <svg
    className={big ? "wiz-svg" : "mi"}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={big ? 1.6 : 2}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    {ICON[name]}
  </svg>
);

const QUICK_PLACEHOLDER = `공지 내용을 그대로 붙여넣어 주세요.

SNS, 블로그, 공식 홈페이지 등 어디서 가져온 공지든 괜찮아요. 읽어오기를 누르면 행사 정보를 자동으로 정리해 드려요.

입력 예시)

명일방주 콜라보 카페 오픈!
기간: 2026.10.16 ~ 11.17
장소: 애니메이트 카페 홍대점
주소: 서울 마포구 양화로 188 AK&홍대 5층
구매 금액별 한정 특전 증정!

※ 정리된 정보는 등록 전에 확인하고 수정할 수 있어요.`;

type W = {
  step: number;
  quick: boolean;
  work: string;
  characters: string[];
  cafe_name: string;
  address: string;
  picked: Picked | null;
  start: string;
  end: string;
  perks: string;
  goods: string;
  poster: File | null;
  extras: File[];
  tags: string[];
  links: string;
  intro: string;
  raw: string;
  got: QuickGot | null;
  badge: string;
  v: number;
};

function Thumbs({ files }: { files: File[] }) {
  const urls = useObjectUrls(files);
  return (
    <div className="ed-thumbs">
      {urls.map((u, i) => (
         
        <img key={u} src={u} alt={`추가 이미지 ${i + 1}`} />
      ))}
    </div>
  );
}

function Errs({ list }: { list: string[] }) {
  return (
    <>
      {list.map((e) => (
        <div key={e} className="ed-err">
          {e}
        </div>
      ))}
    </>
  );
}
function Warns({ list }: { list: string[] }) {
  return (
    <>
      {list.map((e) => (
        <div key={e} className="auth-warn ed-warn">
          {e}
        </div>
      ))}
    </>
  );
}

export default function AddWizard({ byWork, existing, today }: { byWork: Record<string, string[]>; existing: ExistingRow[]; today: string }) {
  const [w, setW] = useState<W>({
    step: 0,
    quick: false,
    work: "",
    characters: [],
    cafe_name: "",
    address: "",
    picked: null,
    start: today,
    end: addDays(today, 27), // 팝업은 보통 몇 주 간다
    perks: "",
    goods: "",
    poster: null,
    extras: [],
    tags: [],
    links: "",
    intro: "",
    raw: "",
    got: null,
    badge: "",
    v: 0,
  });
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, start] = useTransition();
  const up = (p: Partial<W>) => setW((x) => ({ ...x, ...p }));
  const move = (d: number) => {
    setErrors([]);
    setW((x) => ({ ...x, step: Math.max(0, Math.min(STEPS.length - 1, x.step + d)) }));
    window.scrollTo({ top: 0 });
  };
  const pickedFor = () => (w.picked && w.picked.address === w.address.trim() ? w.picked : null);

  const submit = (mode: "quick" | "wizard") => {
    const fd = new FormData();
    fd.set("mode", mode);
    fd.set("work", w.work);
    fd.set("characters", JSON.stringify(w.characters));
    fd.set("cafe_name", w.cafe_name.trim());
    fd.set("address", w.address.trim());
    const pk = pickedFor();
    fd.set("picked", pk ? JSON.stringify(pk) : "");
    fd.set("start_date", w.start);
    fd.set("end_date", w.end);
    fd.set("perks", w.perks);
    fd.set("goods", w.goods);
    for (const t of w.tags) fd.append("tags", t);
    fd.set("links", w.links);
    fd.set("intro", w.intro);
    if (w.poster) fd.set("poster", w.poster);
    for (const f of w.extras) fd.append("extras", f);
    setErrors([]);
    setErr("");
    start(async () => {
      const r = await addAction(null, fd);
      if (r?.error) setErr(r.error);
      if (r?.errors?.length) setErrors(r.errors);
    });
  };

  const nav = (label: string, ok: boolean, onNext?: () => void | Promise<boolean | void>) => {
    const next = (
      <button
        type="button"
        className="btn-main"
        disabled={!ok || busy}
        onClick={() => {
          if (!onNext) return move(1);
          const r = onNext();
          if (r instanceof Promise) r.then((go) => go !== false && move(1));
          else move(1);
        }}
      >
        {label}
      </button>
    );
    return w.step > 0 ? (
      <div className="two wiz-nav">
        <button type="button" className="btn-line" onClick={() => move(-1)}>
          이전
        </button>
        {next}
      </div>
    ) : (
      <div className="wiz-nav">{next}</div>
    );
  };

  // ---------------- 단계별 ----------------
  const stepWork = () => {
    const bad = blockSensitive(w.work, ...w.characters);
    return (
      <>
        <WorkPicker
          byWork={byWork}
          work={w.work}
          characters={w.characters}
          initialWork=""
          initialChars={[]}
          onChange={(work, characters) => up({ work, characters })}
        />
        <p className="ed-cap">캐릭터는 모르면 비워 두세요.</p>
        {bad && <div className="ed-err">{bad}</div>}
        {nav("다음", !!w.work && !bad)}
        <hr className="wiz-hr" />
        <p className="ed-cap">공지 글이 있나요? 붙여넣기만 하면 한 화면에서 바로 등록할 수 있어요.</p>
        <button type="button" className="btn-line wiz-quick" onClick={() => up({ quick: true })}>
          <Mi name="edit_note" />
          공지로 간편등록
        </button>
      </>
    );
  };

  const stepCafe = () => {
    const bad = blockSensitive(w.cafe_name, w.address);
    return (
      <>
        <label className="ed-field">
          <span className="ed-label">카페명</span>
          <ClearInput value={w.cafe_name} onChange={(v) => up({ cafe_name: v })} placeholder={askPh("카페명")} maxLength={100} />
        </label>
        <AddressField
          value={w.address}
          onChange={(v) => up({ address: v })}
          placeholder={`${askPh("주소")} (예: 서울 마포구 ...)`}
          onPick={(c) =>
            up({
              cafe_name: w.cafe_name.trim() || c.name,
              address: c.address,
              picked: { address: c.address, lat: c.lat, lng: c.lng, source: c.source, precision: c.precision },
            })
          }
        />
        {bad && <div className="ed-err">{bad}</div>}
        {nav("다음", !!(w.cafe_name.trim() && w.address.trim()) && !bad, async () => {
          up({ cafe_name: w.cafe_name.trim(), address: w.address.trim() });
          const g = await locateAction(w.address.trim(), pickedFor());
          if (!g.ok) {
            setErr(g.note);
            return false;
          }
          setErr("");
          setNote(g.note);
        })}
      </>
    );
  };

  const stepImages = () => {
    const errs: string[] = [];
    if (w.extras.length > MAX_EXTRAS) errs.push(`추가 이미지는 ${MAX_EXTRAS}장까지 올릴 수 있습니다.`);
    if (w.extras.some((f) => tooBig(f.size, EXTRA_MB))) errs.push(`추가 이미지는 한 장에 ${EXTRA_MB} MB 까지 올릴 수 있습니다.`);
    return (
      <StepImages
        w={w}
        up={up}
        errs={errs}
        nav={(posterErr) => nav("다음", !errs.length && !posterErr)}
      />
    );
  };

  const always = isAlways(w.end);
  const stepDates = () => (
    <>
      <div className="ed-two">
        <label className="ed-field">
          <span className="ed-label">시작</span>
          <input type="date" value={w.start} onChange={(e) => up({ start: e.target.value })} />
        </label>
        <label className="ed-field">
          <span className="ed-label">종료</span>
          <input
            type="date"
            value={always ? addDays(w.start || today, 30) : w.end}
            disabled={always}
            onChange={(e) => up({ end: e.target.value })}
          />
        </label>
      </div>
      <label className="ck ed-ck">
        <input
          type="checkbox"
          checked={always}
          onChange={(e) =>
            up({
              end: e.target.checked ? ALWAYS_END : addDays(w.start || today, 30),
              tags: [...w.tags.filter((t) => t !== TAG_ALWAYS), ...(e.target.checked ? [TAG_ALWAYS] : [])],
            })
          }
        />
        <span>종료일 없음 (상시)</span>
      </label>
      {w.start && w.end && w.end < w.start && <p className="ed-cap">종료일이 시작일보다 빠릅니다.</p>}
      {nav("다음", !!w.start && !!w.end && w.end >= w.start)}
    </>
  );

  const stepExtras = () => {
    const bad = blockSensitive(w.perks, w.goods);
    const badLinks = linksErrors(w.links).errors.length > 0;
    return (
      <>
        <label className="ed-field">
          <span className="ed-label">
            특전
            <Help>쉼표로 구분</Help>
          </span>
          <ClearInput value={w.perks} onChange={(v) => up({ perks: v })} placeholder={`${askPh("특전")} (예: 랜덤 코스터, 포토카드)`} maxLength={500} />
        </label>
        <label className="ed-field">
          <span className="ed-label">
            굿즈
            <Help>쉼표로 구분</Help>
          </span>
          <ClearInput value={w.goods} onChange={(v) => up({ goods: v })} placeholder={`${askPh("굿즈")} (예: 아크릴 스탠드, 캔뱃지)`} maxLength={500} />
        </label>
        <b className="ed-sub">이벤트 추가 정보</b>
        <div className="wiz-checks">
          {EVENT_TAGS.map((t) => (
            <label key={t} className="ck">
              <input
                type="checkbox"
                checked={w.tags.includes(t)}
                onChange={(e) => up({ tags: e.target.checked ? [...w.tags, t] : w.tags.filter((x) => x !== t) })}
              />
              <span>{t}</span>
            </label>
          ))}
        </div>
        <LinksField value={w.links} onChange={(v) => up({ links: v })} />
        {bad && <div className="ed-err">{bad}</div>}
        {nav("다음", !bad && !badLinks)}
      </>
    );
  };

  const stepIntro = () => {
    const bad = blockSensitive(w.intro);
    return (
      <>
        <IntroField value={w.intro} onChange={(v) => up({ intro: v })} hideLabel />
        <p className="ed-cap">비워 둬도 괜찮아요. 쓴 내용은 상세 화면에 &apos;팝업 소개&apos; 로 보여요.</p>
        {bad && <div className="ed-err">{bad}</div>}
        {nav("다음", !bad)}
      </>
    );
  };

  const entryOf = (): CafeEntry => ({
    cafe_name: w.cafe_name.trim(),
    work: w.work,
    characters: w.characters,
    address: w.address.trim(),
    start_date: w.start,
    end_date: w.end,
    perks: split(w.perks),
    goods: split(w.goods),
    confidence: "high",
  });

  const stepConfirm = () => {
    const fmt = (s: string) => s.replace(/-/g, ".");
    const rows: [string, string][] = [
      ["작품", w.work],
      ["캐릭터", w.characters.join(", ")],
      ["카페명", w.cafe_name],
      ["주소", w.address],
      ["기간", `${fmt(w.start)} ~ ${fmt(w.end)}`],
      ["특전", w.perks],
      ["굿즈", w.goods],
      ["이벤트", w.tags.join(" · ")],
      ["이미지", `${(w.poster ? 1 : 0) + w.extras.length}장`],
      ["팝업 소개", [...w.intro].length > 60 ? [...w.intro].slice(0, 60).join("") + "…" : w.intro],
    ];
    const v = validateCafe(entryOf(), today, existing);
    return (
      <>
        <div className="wiz-sum">
          {rows
            .filter(([, x]) => x)
            .map(([k, x]) => (
              <div key={k}>
                <b>{k}</b> · {x}
              </div>
            ))}
        </div>
        <p className="ed-cap">고칠 곳이 있으면 &apos;이전&apos; 으로 돌아가 바꿔 주세요.</p>
        <Warns list={v.warnings} />
        <Errs list={v.errors} />
        <Errs list={errors} />
        {nav(busy ? "등록 중…" : "등록하기", v.ok, () => {
          submit("wizard");
          return Promise.resolve(false);
        })}
      </>
    );
  };

  // ---------------- 간편등록 ----------------
  const quick = () => {
    const got = w.got;
    const read = () => {
      start(async () => {
        setErr("");
        const r = await quickReadAction(w.raw);
        if (r.error || !r.got) {
          setErr(r.error || "공지를 읽지 못했어요.");
          return;
        }
        const g = r.got;
        // 못 찾은 칸은 비워 둔다 (오늘 날짜 같은 값으로 채우지 않는다 — 추측 금지)
        setW((x) => ({
          ...x,
          work: g.work || "",
          characters: g.characters,
          cafe_name: g.cafe_name || "",
          address: g.address || "",
          picked: null,
          start: g.start_date || "",
          end: g.end_date || "",
          perks: g.perks.join(", "),
          goods: g.goods.join(", "),
          tags: g.tags,
          links: g.links.join("\n"),
          intro: x.raw.trim(), // 붙여넣은 공지 그대로를 팝업 소개로
          got: g,
          badge: r.badge || "",
          v: x.v + 1,
        }));
      });
    };
    return (
      <>
        <ClearArea
          value={w.raw}
          onChange={(v) => up({ raw: v })}
          aria-label="공지"
          placeholder={QUICK_PLACEHOLDER}
          style={{ height: 300 }}
          maxLength={20000}
        />
        {!got && blockSensitive(w.raw) && <div className="ed-err">{blockSensitive(w.raw)}</div>}
        <button type="button" className="btn-main wiz-read" disabled={!w.raw.trim() || busy} onClick={read}>
          {busy && !got ? "읽는 중…" : "읽어오기"}
        </button>
        {got && <QuickBody key={w.v} w={w} up={up} byWork={byWork} existing={existing} today={today} busy={busy} errors={errors} onSave={() => submit("quick")} />}
      </>
    );
  };

  const steps = [stepWork, stepCafe, stepImages, stepDates, stepExtras, stepIntro, stepConfirm];
  const [title, icon] = STEPS[w.step];

  return (
    <div className="wiz">
      <div className="wiz-head">
        <div className="wiz-back">
          {!w.quick && w.step > 0 && (
            <button type="button" className="btn-line" onClick={() => move(-1)}>
              돌아가기
            </button>
          )}
        </div>
        <h1 className="add-title">팝업 카페 등록하기</h1>
        <div />
      </div>
      <div className="wiz-mid">
        {w.quick ? (
          <section className="wiz-card">
            <div className="wiz-title">공지로 간편등록</div>
            <div className="wiz-icon">
              <Mi name="edit_note" big />
            </div>
            {err && <div className="ed-err">{err}</div>}
            {quick()}
            <button
              type="button"
              className="btn-line wiz-off"
              onClick={() => {
                setErr("");
                setErrors([]);
                setW((x) => ({ ...x, quick: false, step: 0, v: x.v + 1 }));
              }}
            >
              단계별로 등록하기
            </button>
          </section>
        ) : (
          <>
            <ol className="wiz-steps">
              {STEPS.map(([name], i) => {
                const st = i < w.step ? "done" : i === w.step ? "now" : "todo";
                return (
                  <li key={name} className={`ws-${st}`}>
                    <span className="ws-dot">{st === "done" ? <Mi name="check" /> : i + 1}</span>
                    <span className="ws-name">{name}</span>
                  </li>
                );
              })}
            </ol>
            <section className="wiz-card">
              <div className="wiz-title">{title}</div>
              {(w.step === 0 || w.step === STEPS.length - 1) && (
                <div className="wiz-icon">
                  <Mi name={icon} big />
                </div>
              )}
              {err && <div className="ed-err">{err}</div>}
              {note && w.step === 2 && (
                <p className="ed-cap">
                  <Mi name="location_on" />
                  {note}
                </p>
              )}
              {steps[w.step]()}
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function StepImages({
  w,
  up,
  errs,
  nav,
}: {
  w: W;
  up: (p: Partial<W>) => void;
  errs: string[];
  nav: (posterErr: boolean) => React.ReactNode;
}) {
  const [changing, setChanging] = useState(false);
  const [posterErr, setPosterErr] = useState("");
  const posterUrl = useObjectUrls(w.poster ? [w.poster] : []);
  return (
    <>
      <b className="ed-sub">
        메인 이미지 (포스터) <span className="ed-gray">(1장만)</span>
      </b>
      {w.poster && !changing ? (
        <div className="wiz-poster">
          { }
          <img src={posterUrl[0]} alt="포스터 미리보기" />
          <div>
            <p className="ed-cap">포스터 미리보기</p>
            <button type="button" className="btn-line ed-sm" onClick={() => setChanging(true)}>
              변경
            </button>
          </div>
        </div>
      ) : (
        <>
          <Dropzone
            label={`메인 이미지 (1장, ~ ${POSTER_MB} MB)`}
            hint={`PNG · JPG · JPEG · WEBP · GIF · ~ ${POSTER_MB} MB`}
            onFiles={([f]) => {
              if (tooBig(f.size, POSTER_MB)) {
                setPosterErr(`메인 이미지는 ${POSTER_MB} MB 까지 올릴 수 있습니다.`);
                return;
              }
              setPosterErr("");
              up({ poster: f });
              setChanging(false);
            }}
          />
          {changing ? (
            <button type="button" className="btn-line ed-sm" onClick={() => setChanging(false)}>
              취소
            </button>
          ) : (
            !w.poster && <p className="ed-cap">포스터가 없어도 등록할 수 있어요. 있으면 목록에서 훨씬 눈에 띄어요!</p>
          )}
        </>
      )}
      <b className="ed-sub">
        이미지 추가 등록 <span className="ed-gray">(최대 {MAX_EXTRAS}장)</span>
      </b>
      <Dropzone
        label={`추가 이미지 (~ ${EXTRA_MB} MB)`}
        multiple
        hint={`PNG · JPG · JPEG · WEBP · GIF · 한 장에 ~ ${EXTRA_MB} MB`}
        onFiles={(fs) => up({ extras: fs })}
      />
      {w.extras.length > 0 && (
        <>
          <p className="ed-cap">추가 이미지 미리보기 ({w.extras.length}장)</p>
          <Thumbs files={w.extras.slice(0, MAX_EXTRAS)} />
        </>
      )}
      {posterErr && <div className="ed-err">{posterErr}</div>}
      <Errs list={errs} />
      {nav(!!posterErr)}
    </>
  );
}

function QuickBody({
  w,
  up,
  byWork,
  existing,
  today,
  busy,
  errors,
  onSave,
}: {
  w: W;
  up: (p: Partial<W>) => void;
  byWork: Record<string, string[]>;
  existing: ExistingRow[];
  today: string;
  busy: boolean;
  errors: string[];
  onSave: () => void;
}) {
  const got = w.got as QuickGot;
  const [initial] = useState({ work: w.work, chars: w.characters });
  const fields: [string, unknown][] = [
    ["작품명", got.work],
    ["카페명", got.cafe_name],
    ["주소", got.address],
    ["기간", got.start_date && got.end_date],
    ["캐릭터", got.characters.length],
    ["특전", got.perks.length],
    ["굿즈", got.goods.length],
    ["이벤트", got.tags.length],
    ["참고 웹사이트", got.links.length],
  ];
  const found = fields.filter(([, v]) => v).map(([n]) => n);
  const readMsg = found.length ? (
    <>
      {found.map((n, i) => (
        <span key={n}>
          {i > 0 && ", "}
          <span className="ed-hl">{n}</span>
        </span>
      ))}
      {objJosa(found[found.length - 1])} 읽어왔어요
    </>
  ) : (
    <>읽어 온 항목이 없어요. 칸을 직접 채워 주세요</>
  );
  const extra = [
    got.area ? (["location_on", `지역 ${got.area}`] as const) : null,
    got.hours ? (["schedule", `운영시간 ${got.hours}`] as const) : null,
    got.events.length ? (["festival", `그 밖의 이벤트 ${got.events.join(", ")}`] as const) : null,
  ].filter(Boolean) as (readonly [string, string])[];

  const posterUrl = useObjectUrls(w.poster ? [w.poster] : []);
  const imgErr: string[] = [];
  if (w.poster && tooBig(w.poster.size, POSTER_MB)) imgErr.push(`메인 이미지는 ${POSTER_MB} MB 까지 올릴 수 있습니다.`);
  if (w.extras.length > MAX_EXTRAS) imgErr.push(`추가 이미지는 ${MAX_EXTRAS}장까지 올릴 수 있습니다.`);
  if (w.extras.some((f) => tooBig(f.size, EXTRA_MB))) imgErr.push(`추가 이미지는 한 장에 ${EXTRA_MB} MB 까지 올릴 수 있습니다.`);
  const badLinks = linksErrors(w.links).errors.length > 0;

  let ready = !!(w.work && w.cafe_name.trim() && w.address.trim() && w.start && w.end);
  let dupes: ExistingRow[] = [];
  let v = { ok: true, errors: [] as string[], warnings: [] as string[] };
  if (ready) {
    // 작품 + 장소 + 기간이 모두 같은 카페가 이미 있으면 알려 준다 (막지는 않는다)
    dupes = possibleDuplicates({ work: w.work, cafe_name: w.cafe_name.trim(), area: got.area, start_date: w.start, end_date: w.end }, existing);
    v = validateCafe(
      {
        cafe_name: w.cafe_name.trim(),
        work: w.work,
        characters: w.characters,
        address: w.address.trim(),
        start_date: w.start,
        end_date: w.end,
        perks: split(w.perks),
        goods: split(w.goods),
        confidence: "high",
      },
      today,
      existing,
    );
    ready = v.ok;
  }
  const bad = blockSensitive(w.cafe_name, w.address, w.perks, w.goods, w.intro);
  const ai = w.badge === "AI 산출";

  return (
    <div className="quick-body">
      <p className="ed-cap quick-src">
        <span className={`ai-badge${ai ? " ai" : ""}`}>
          <Mi name={ai ? "task_alt" : "build"} />
          {w.badge || "규칙 기반 대체"}
        </span>
        {ai ? "AI 로 읽었어요." : "규칙 기반으로 읽었어요 (AI 아님)."} 비었거나 틀린 칸은 직접 고쳐 주세요.
      </p>
      {got.status === "자동등록" ? (
        <div className="auth-ok quick-ok">
          <b>{readMsg}</b>
          {!got.cafe_name && (
            <ul>
              <li>
                공지에 가게 이름이 없어요. <b>카페명</b>만 직접 넣어 주세요
              </li>
            </ul>
          )}
        </div>
      ) : (
        <div className="auth-warn quick-warn">
          <b>{readMsg}</b>
          {got.reasons.length > 0 && (
            <ul>
              {got.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {extra.length > 0 && (
        <p className="ed-cap">
          {extra.map(([ic, t], i) => (
            <span key={t}>
              {i > 0 && " · "}
              <Mi name={ic} />
              {t}
            </span>
          ))}{" "}
          (저장 칸이 없어 참고로만 보여 줘요)
        </p>
      )}

      <WorkPicker
        byWork={byWork}
        work={w.work}
        characters={w.characters}
        initialWork={initial.work}
        initialChars={initial.chars}
        onChange={(work, characters) => up({ work, characters })}
      />
      <label className="ed-field">
        <span className="ed-label">카페명</span>
        <ClearInput value={w.cafe_name} onChange={(x) => up({ cafe_name: x })} placeholder={askPh("카페명")} maxLength={100} />
      </label>
      <AddressField
        value={w.address}
        onChange={(x) => up({ address: x })}
        placeholder={got.area && !w.address ? `주소를 찾지 못했어요 · 지역: ${got.area}` : `${askPh("주소")} (예: 서울 마포구 ...)`}
        onPick={(c) =>
          up({
            cafe_name: w.cafe_name.trim() || c.name,
            address: c.address,
            picked: { address: c.address, lat: c.lat, lng: c.lng, source: c.source, precision: c.precision },
          })
        }
      />
      <div className="ed-two">
        <label className="ed-field">
          <span className="ed-label">시작</span>
          <input type="date" value={w.start} onChange={(e) => up({ start: e.target.value })} />
        </label>
        <label className="ed-field">
          <span className="ed-label">종료</span>
          <input type="date" value={w.end} onChange={(e) => up({ end: e.target.value })} />
        </label>
      </div>
      <label className="ed-field">
        <span className="ed-label">
          특전
          <Help>쉼표로 구분</Help>
        </span>
        <ClearInput value={w.perks} onChange={(x) => up({ perks: x })} maxLength={500} />
      </label>
      <label className="ed-field">
        <span className="ed-label">
          굿즈
          <Help>쉼표로 구분</Help>
        </span>
        <ClearInput value={w.goods} onChange={(x) => up({ goods: x })} maxLength={500} />
      </label>
      <TagPills value={w.tags} onChange={(t) => up({ tags: t })} />
      <LinksField value={w.links} onChange={(x) => up({ links: x })} />
      <IntroField value={w.intro} onChange={(x) => up({ intro: x })} />
      <p className="ed-cap">붙여넣은 공지가 그대로 팝업 소개로 보여요. 필요하면 고쳐 주세요.</p>

      <b className="ed-sub">
        <Mi name="image" />
        메인 이미지 (포스터) <span className="ed-gray">(1장만)</span>
      </b>
      <Dropzone label={`메인 이미지 (1장, ~ ${POSTER_MB} MB)`} hint={`PNG · JPG · JPEG · WEBP · GIF · ~ ${POSTER_MB} MB`} onFiles={([f]) => up({ poster: f })} />
      {w.poster ? (
        <div className="wiz-poster">
          { }
          <img src={posterUrl[0]} alt="포스터 미리보기" />
          <div>
            <p className="ed-cap">{w.poster.name}</p>
            <button type="button" className="btn-line ed-sm" onClick={() => up({ poster: null })}>
              빼기
            </button>
          </div>
        </div>
      ) : (
        <p className="ed-cap">포스터가 없어도 등록할 수 있어요. 있으면 목록에서 훨씬 눈에 띄어요!</p>
      )}
      <b className="ed-sub">
        이미지 추가 등록 <span className="ed-gray">(최대 {MAX_EXTRAS}장)</span>
      </b>
      <Dropzone
        label={`추가 이미지 (~ ${EXTRA_MB} MB)`}
        multiple
        hint={`PNG · JPG · JPEG · WEBP · GIF · 한 장에 ~ ${EXTRA_MB} MB`}
        onFiles={(fs) => up({ extras: fs })}
      />
      {w.extras.length > 0 && (
        <>
          <p className="ed-cap">추가 이미지 미리보기 ({w.extras.length}장)</p>
          <Thumbs files={w.extras.slice(0, MAX_EXTRAS)} />
        </>
      )}
      <Errs list={imgErr} />

      {w.work && w.cafe_name.trim() && w.address.trim() && w.start && w.end ? (
        <>
          {dupes.length > 0 && (
            <div className="auth-warn ed-warn">
              같은 작품·장소·기간의 카페가 이미 있어요: {dupes.slice(0, 3).map((d) => `${d.work} · ${d.cafe_name}`).join(", ")}
            </div>
          )}
          <Warns list={v.warnings} />
          <Errs list={v.errors} />
        </>
      ) : (
        <p className="ed-cap">작품 · 카페명 · 주소 · 기간을 채우면 등록할 수 있어요.</p>
      )}
      {bad && <div className="ed-err">{bad}</div>}
      <Errs list={errors} />
      <button type="button" className="btn-main wiz-save" disabled={!ready || !!bad || badLinks || imgErr.length > 0 || busy} onClick={onSave}>
        {busy ? "등록 중…" : "등록하기"}
      </button>
    </div>
  );
}
