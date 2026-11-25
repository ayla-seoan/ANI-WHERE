"use client";
import { submitWith } from "@/lib/submit";
import { useRouter } from "next/navigation";
import { startTransition, useActionState, useEffect, useRef, useState } from "react";
import { reviewCreateAction, reviewDeleteAction, reviewEditAction, type FormState } from "@/app/actions";
import { avatarUrl, uploadUrl } from "@/lib/avatar";
import { sensitiveWarning } from "@/lib/guard";
import { goLogin, useMember } from "../member/MemberContext";
import { toast } from "../member/Toast";
import { nextTier, tierOf } from "@/lib/stamp";
import { CloseIcon } from "../Icons";
import { RankChip, RankStamp } from "../RankStamp";
import { useObjectUrls } from "../edit/Fields";

// 상세 '리뷰' 탭 (A-Detail 시안 · 앱 render_reviews · _review_card): 왼쪽 리뷰 쓰기(회원만 — 종류 · 별점 · 사진 4장 · 내 후기 도장),
// 오른쪽 평균 별점 · 점수 분포 · 사진 모아 보기 · 종류별 보기 · 리뷰 카드(닉네임 옆 랭크, 사진 120px, 답글).
// 내 글은 ⋯ 로 수정·삭제, 관리자는 모든 글을 사유를 적고 삭제 (쓴 회원에게 알림). 탭 머리 · 블로그 후기 탭은 SideTabs 가 그린다.
const MAX_IMAGES = 4; // review.MAX_IMAGES
const IMAGE_MB = 10; // review.IMAGE_MB

export type RView = {
  id: string;
  kind: string;
  name: string;
  avatar: string;
  body: string;
  rating: number | null;
  images: string[];
  when: string;
  edited: boolean;
  mine: boolean;
  /** 글쓴이 후기 도장 랭크 (0 · 없음 = 도장 없음) */
  lv?: number;
};
export type TView = { post: RView; replies: RView[] };

const KINDS = ["다녀온 후기", "기대평", "기타"];
const RATED = "다녀온 후기";
const KIND_COLOR: Record<string, string> = { "다녀온 후기": "green", 기대평: "blue", 기타: "gray" };
const PAGE = 8; // 처음 보여 주는 리뷰 수 ('리뷰 더보기' 로 이만큼씩 더)
const PHOTO_NOTE = "얼굴·영수증·연락처가 보이는 사진은 올리지 말아 주세요. 사진의 위치 정보는 지우고 저장해요.";

const XMark = (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" aria-hidden>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);

function whenText(stamp: string): string {
  const t = Date.parse(stamp);
  if (!t) return "";
  const k = new Date(t + 9 * 3600_000); // 한국 시간
  const two = (n: number) => String(n).padStart(2, "0");
  return `${two(k.getUTCMonth() + 1)}/${two(k.getUTCDate())} ${two(k.getUTCHours())}:${two(k.getUTCMinutes())}`;
}

function Av({ v, size }: { v: string; size: number }) {
  return (
    <img
      className="rv-av"
      src={avatarUrl(v)}
      alt=""
      width={size}
      height={size}
      referrerPolicy="no-referrer"
      loading="lazy"
      onError={(e) => {
        e.currentTarget.src = avatarUrl("");
      }}
    />
  );
}

function Stars({ value, onChange }: { value: number | null; onChange: (n: number) => void }) {
  const [hover, setHover] = useState(0);
  const show = hover || value || 0;
  return (
    <div className="rate-stars" role="radiogroup" aria-label="별점" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n}점`}
          className={n <= show ? "on" : ""}
          onMouseEnter={() => setHover(n)}
          onClick={() => onChange(n)}
        >
          ★
        </button>
      ))}
    </div>
  );
}

/** 저장이 끝나면 알림 → 칸 비우기 → 뒤에서 화면 맞추기 (11/20 등록 속도: 서버는 화면을 다시 그리지 않고 바로 답하고,
 *  router.refresh() 는 기다리지 않는다. 그 사이 새 글은 Reviews 의 pending 으로 먼저 보인다) */
function useDone(s: FormState, after: () => void) {
  const router = useRouter();
  const seen = useRef<FormState>(null);
  useEffect(() => {
    if (!s || s === seen.current) return;
    seen.current = s;
    if (s.ok) {
      toast(s.ok);
      after();
      startTransition(() => router.refresh());
    }
  }, [s, after, router]);
}

/** 사진 주소: 방금 고른 사진(blob:)은 그대로, 저장된 사진은 우리 주소로 */
const picSrc = (x: string) => (x.startsWith("blob:") ? x : uploadUrl(x));

type Posted = { parentId: string; view: RView };

/** 글쓰기 칸. parentId 가 있으면 답글 칸 (칸을 누르면 등록·취소 · 사진 첨부가 나온다) */
function WriteBox({
  cafeId,
  parentId = "",
  me,
  onPosted,
  onClose,
  stamps = 0,
  stampedHere = false,
}: {
  cafeId: string;
  parentId?: string;
  me: { nick: string; avatar: string };
  onPosted?: (p: Posted) => void;
  /** 답글 칸: '취소' 를 누르거나 등록이 끝나면 칸을 닫는다 */
  onClose?: () => void;
  /** 내 후기 도장 수 · 이 팝업에서 이미 도장을 받았는지 (리뷰 쓰기 칸) */
  stamps?: number;
  stampedHere?: boolean;
}) {
  const [kind, setKind] = useState(KINDS[0]);
  const [rating, setRating] = useState<number | null>(null);
  const [body, setBody] = useState("");
  const [focus, setFocus] = useState(false);
  const [n, setN] = useState(0);
  const [picOpen, setPicOpen] = useState(false);
  const [pics, setPics] = useState<File[]>([]);
  const [s, action, busy] = useActionState(reviewCreateAction, null);
  const sent = useRef<Posted | null>(null); // 보낸 내용 (저장되면 목록에 먼저 붙인다)
  useDone(s, () => {
    if (sent.current) onPosted?.(sent.current);
    sent.current = null;
    setBody("");
    setRating(null);
    setFocus(false);
    setPicOpen(false);
    setPics([]);
    setN((k) => k + 1);
    onClose?.();
  });
  const urls = useObjectUrls(pics);
  const tier = tierOf(stamps);
  const next = nextTier(stamps);
  const warn = sensitiveWarning(body);
  const heavy = pics.filter((p) => p.size > IMAGE_MB * 1024 * 1024).map((p) => p.name);
  const allowEmpty = !parentId && kind === RATED && (rating !== null || pics.length > 0);
  const reply = !!parentId;
  return (
    <form
      onSubmit={submitWith((fd) => {
        fd.delete("photos");
        const send = pics.slice(0, MAX_IMAGES);
        for (const p of send) fd.append("photos", p);
        sent.current = {
          parentId,
          view: {
            id: `pending-${Date.now()}`,
            kind: reply ? "" : kind,
            name: me.nick,
            avatar: me.avatar,
            body: body.trim(),
            rating: !reply && kind === RATED ? rating : null,
            images: send.map((p) => URL.createObjectURL(p)),
            when: new Date().toISOString(),
            edited: false,
            mine: true,
          },
        };
        action(fd);
      })}
      className={`write${reply ? " reply open" : " ad-write"}${!reply && (focus || body || pics.length) ? " open" : ""}`}
      key={n}
    >
      <input type="hidden" name="cafe_id" value={cafeId} />
      <input type="hidden" name="parent_id" value={parentId} />
      <input type="hidden" name="kind" value={reply ? "" : kind} />
      <input type="hidden" name="rating" value={rating ?? ""} />
      {reply ? (
        <div className="rv-me">
          <Av v={me.avatar} size={28} />
          <b>{me.nick}</b>
        </div>
      ) : (
        // 작성자 줄: 내 32px 후기 도장 + 닉네임 · 랭크 · 다음 랭크까지 남은 수
        <div className="ad-me">
          {tier ? (
            <RankStamp lv={tier.lv} size={32} />
          ) : (
            <span className="ad-nostamp" aria-hidden>
              <img src="/mascot.png" alt="" />
            </span>
          )}
          <span className="ad-me-t">
            <span>
              <b>{me.nick}</b>
              <strong>{tier ? `내 도장 Lv.${tier.lv} ${tier.name}` : "아직 도장이 없어요"}</strong>
            </span>
            <span>
              {stampedHere ? "이 팝업 도장은 이미 받았어요" : "다녀온 후기를 남기면 도장 +1"}
              {next ? ` · Lv.${next.tier.lv}까지 ${next.left}개` : " · 가장 높은 랭크예요"}
            </span>
          </span>
        </div>
      )}
      {!reply && (
        <div className="ad-seg" role="radiogroup" aria-label="리뷰 종류">
          {KINDS.map((k) => (
            <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}>
              {k}
            </button>
          ))}
        </div>
      )}
      {!reply && kind === RATED && (
        <div className="ad-rate">
          <Stars value={rating} onChange={setRating} />
          <span>별점만 골라도 등록돼요</span>
        </div>
      )}
      <textarea
        name="body"
        value={body}
        maxLength={1000}
        rows={reply ? 2 : 4}
        autoFocus={reply}
        onFocus={() => setFocus(true)}
        onChange={(e) => setBody(e.target.value)}
        placeholder={reply ? "답글을 남겨 주세요" : "웨이팅, 특전 남은 수, 굿즈 꿀팁을 알려 주세요"}
        aria-label={reply ? "답글" : "리뷰 내용"}
      />
      {warn && (
        <div className="auth-warn" role="alert">
          {warn}
        </div>
      )}
      {s?.error && (
        <div className="auth-warn" role="alert">
          {s.error}
        </div>
      )}
      {/* 사진: 리뷰 쓰기는 네 칸이 늘 보이고(시안), 답글은 '+ 사진 첨부' 를 눌러 연다 (11/20) */}
      {!reply ? (
        <div className="ad-pics">
          <span className="ad-pics-t">
            사진{" "}
            <span>
              {pics.length} / {MAX_IMAGES} · 한 장 {IMAGE_MB}MB
            </span>
          </span>
          <div className="ad-pics-grid">
            {pics.map((f, i) => (
              <span key={`${f.name}-${i}`} className="pic-one">
                {urls[i] && <img src={urls[i]} alt="" />}
                <button type="button" aria-label={`사진 ${i + 1} 빼기`} onClick={() => setPics(pics.filter((_, j) => j !== i))}>
                  {XMark}
                </button>
              </span>
            ))}
            {pics.length < MAX_IMAGES && (
              <label className="pic-drop ad-pic-add">
                <span className="sr-only">사진 추가</span>
                <input
                  type="file"
                  multiple
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  onChange={(e) => {
                    const add = Array.from(e.target.files || []);
                    e.target.value = "";
                    if (pics.length + add.length > MAX_IMAGES) toast(`사진은 ${MAX_IMAGES}장까지 올릴 수 있어요.`, "error");
                    setPics([...pics, ...add].slice(0, MAX_IMAGES));
                  }}
                />
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" aria-hidden>
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </label>
            )}
            {Array.from({ length: Math.max(0, MAX_IMAGES - pics.length - 1) }, (_, k) => (
              <span key={k} className="ad-pic-empty" />
            ))}
          </div>
          <span className="ad-pics-note">{PHOTO_NOTE}</span>
        </div>
      ) : !picOpen ? (
          <button
            type="button"
            className="pic-btn"
            onMouseDown={(e) => e.preventDefault() /* 답글 칸이 닫히지 않게 입력칸 포커스를 그대로 둔다 */}
            onClick={() => {
              setFocus(true);
              setPicOpen(true);
            }}
          >
            + 사진 첨부
          </button>
        ) : (
          <PicPicker
            label={`최대 ${MAX_IMAGES}장 · 한 장 ${IMAGE_MB}MB · ${PHOTO_NOTE}`}
            room={MAX_IMAGES}
            files={pics}
            onChange={setPics}
          />
        )}
      {heavy.length > 0 && (
        <p className="cap pic-err">
          {IMAGE_MB}MB 를 넘는 사진은 올릴 수 없어요: {heavy.join(", ")}
        </p>
      )}
      <div className={reply ? "two" : ""}>
        <button
          type="submit"
          className="btn-main"
          disabled={busy || !!warn || heavy.length > 0 || (!body.trim() && !allowEmpty)}
        >
          {reply ? "답글 등록" : kind === RATED && !stampedHere ? "등록하고 도장 받기" : "리뷰 등록"}
        </button>
        {reply && (
          <button
            type="button"
            className="btn-line"
            onClick={() => {
              setBody("");
              setFocus(false);
              setPics([]);
              setPicOpen(false);
              onClose?.();
            }}
          >
            취소
          </button>
        )}
      </div>
    </form>
  );
}

/** 사진 고르기 칸 (앱 st.file_uploader 여러 장): 고른 사진은 작은 그림으로 보이고 하나씩 뺄 수 있다 */
function PicPicker({
  label,
  room,
  files,
  onChange,
}: {
  label: string;
  room: number;
  files: File[];
  onChange: (f: File[]) => void;
}) {
  const [urls, setUrls] = useState<string[]>([]);
  useEffect(() => {
    const u = files.map((f) => URL.createObjectURL(f));
    setUrls(u);
    return () => u.forEach((x) => URL.revokeObjectURL(x));
  }, [files]);
  return (
    <div className="pic-pick">
      <label className="pic-drop">
        <span className="pic-label">{label}</span>
        <input
          type="file"
          multiple
          accept="image/png,image/jpeg,image/webp,image/gif"
          onChange={(e) => {
            const add = Array.from(e.target.files || []);
            e.target.value = "";
            onChange([...files, ...add]);
          }}
        />
        <span className="pic-go">사진 고르기</span>
      </label>
      {files.length > room && (
        <p className="cap pic-err">
          사진은 {room}장까지 올릴 수 있어요. 앞의 {room}장만 올라갑니다.
        </p>
      )}
      {files.length > 0 && (
        <div className="pic-list">
          {files.map((f, i) => (
            <span key={`${f.name}-${i}`} className="pic-one">
              {urls[i] && <img src={urls[i]} alt="" />}
              <button type="button" aria-label={`${f.name} 빼기`} onClick={() => onChange(files.filter((_, j) => j !== i))}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function EditBox({ r, isReply, onClose }: { r: RView; isReply: boolean; onClose: () => void }) {
  const [kind, setKind] = useState(r.kind || KINDS[0]);
  const [rating, setRating] = useState<number | null>(r.rating);
  const [body, setBody] = useState(r.body);
  const [keep, setKeep] = useState<string[]>(r.images);
  const [pics, setPics] = useState<File[]>([]);
  const [s, action, busy] = useActionState(reviewEditAction, null);
  useDone(s, onClose);
  const warn = sensitiveWarning(body);
  const room = MAX_IMAGES - keep.length;
  const heavy = pics.filter((p) => p.size > IMAGE_MB * 1024 * 1024).map((p) => p.name);
  return (
    <form
      onSubmit={submitWith((fd) => {
        fd.delete("photos");
        fd.delete("keep");
        for (const k of keep) fd.append("keep", k);
        for (const p of pics.slice(0, Math.max(0, room))) fd.append("photos", p);
        action(fd);
      })}
      className="write edit"
    >
      <input type="hidden" name="entry_id" value={r.id} />
      <input type="hidden" name="kind" value={isReply ? "" : kind} />
      <input type="hidden" name="rating" value={rating ?? ""} />
      {!isReply && (
        <div className="ad-seg" role="radiogroup" aria-label="리뷰 종류">
          {KINDS.map((k) => (
            <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}>
              {k}
            </button>
          ))}
        </div>
      )}
      {!isReply && kind === RATED && <Stars value={rating} onChange={setRating} />}
      <textarea
        name="body"
        value={body}
        maxLength={1000}
        rows={3}
        onChange={(e) => setBody(e.target.value)}
        aria-label="고칠 내용"
      />
      {warn && <div className="auth-warn">{warn}</div>}
      {r.images.length > 0 && (
        <>
          <p className="cap">붙어 있는 사진 (뺄 사진은 체크를 풀어요)</p>
          <div className="rv-keep">
            {r.images.map((x) => (
              <label key={x} className="rv-keep-one">
                <img src={uploadUrl(x)} alt="" loading="lazy" />
                <span className="ck">
                  <input
                    type="checkbox"
                    checked={keep.includes(x)}
                    onChange={(e) => setKeep((cur) => (e.target.checked ? [...cur, x] : cur.filter((y) => y !== x)))}
                  />
                  <span>남기기</span>
                </span>
              </label>
            ))}
          </div>
        </>
      )}
      {room > 0 && (
        <PicPicker label={`사진 추가 (최대 ${room}장 · 한 장 ${IMAGE_MB}MB)`} room={room} files={pics} onChange={setPics} />
      )}
      {heavy.length > 0 && (
        <p className="cap pic-err">
          {IMAGE_MB}MB 가 넘는 사진은 올릴 수 없어요: {heavy.join(", ")}
        </p>
      )}
      {s?.error && <div className="auth-warn">{s.error}</div>}
      <div className="two">
        <button type="button" className="btn-line" onClick={onClose}>
          취소
        </button>
        <button type="submit" className="btn-main" disabled={busy || !!warn || heavy.length > 0}>
          저장
        </button>
      </div>
    </form>
  );
}

function Card({
  r,
  reply = false,
  replies = 0,
  onZoom,
}: {
  r: RView;
  reply?: boolean;
  replies?: number;
  onZoom: (list: string[], i: number) => void;
}) {
  const router = useRouter();
  const { me } = useMember();
  const admin = !!me?.admin && !r.mine; // 관리자가 남의 글을 지울 땐 사유를 적는다
  const [menu, setMenu] = useState(false);
  const [editing, setEditing] = useState(false);
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState("");
  return (
    <div className={`rv-card${reply ? " is-reply" : ""}${r.id.startsWith("pending-") ? " is-pending" : ""}`}>
      <div className="rv-head">
        {/* 대댓글 표시 (11/20 요청): 앞에 'ㄴ' — 위 댓글에 단 답글 (앱 .rv-re 와 같게) */}
        {reply && (
          <span className="rv-re" aria-label="답글">
            ㄴ
          </span>
        )}
        <Av v={r.avatar} size={reply ? 28 : 34} />
        <b>{r.name}</b>
        <RankChip lv={r.lv ?? 0} />
        <span className="rv-when">
          {whenText(r.when)}
          {r.edited ? " (수정됨)" : ""}
        </span>
        {r.kind && <span className={`kb ${KIND_COLOR[r.kind] || "gray"}`}>{r.kind}</span>}
        {(r.mine || admin) && !r.id.startsWith("pending-") && (
          <span className="rv-more">
            <button type="button" aria-label={r.mine ? "내 글 수정·삭제" : "글 삭제 (관리자)"} onClick={() => setMenu((m) => !m)}>
              ⋯
            </button>
            {menu && (
              <span className="rv-menu">
                {r.mine && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditing(true);
                      setMenu(false);
                    }}
                  >
                    수정
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setAsking(true);
                    setMenu(false);
                  }}
                >
                  {r.mine ? "삭제" : "삭제 (관리자)"}
                </button>
              </span>
            )}
          </span>
        )}
      </div>
      {r.kind === RATED && r.rating && !editing && (
        <div className="rv-stars">{"★".repeat(r.rating) + "☆".repeat(5 - r.rating)}</div>
      )}
      {editing ? (
        <EditBox r={r} isReply={reply} onClose={() => setEditing(false)} />
      ) : (
        <>
          {r.body.trim() && <p className="rv-body">{r.body}</p>}
          {/* 사진: 120px 로 최대 4장, 더 있으면 넷째 칸에 +N. 누르면 크게 본다 */}
          {r.images.length > 0 && (
            <div className="rv-pics">
              {r.images.slice(0, MAX_IMAGES).map((x, k) => (
                <button key={x} type="button" aria-label={`사진 ${k + 1} 크게 보기`} onClick={() => onZoom(r.images.map(picSrc), k)}>
                  <img src={picSrc(x)} alt="리뷰 사진" loading="lazy" />
                  {k === MAX_IMAGES - 1 && r.images.length > MAX_IMAGES && <span>+{r.images.length - MAX_IMAGES}</span>}
                </button>
              ))}
            </div>
          )}
        </>
      )}
      {asking && (
        <div className="dlg-bg" onClick={() => setAsking(false)}>
          <div className="dlg" role="dialog" aria-label="리뷰 삭제" onClick={(e) => e.stopPropagation()}>
            <b className="dlg-t">리뷰 삭제</b>
            <p>
              이 글을 삭제할까요? 삭제하면 다시 볼 수 없어요.
              {replies ? ` 달린 답글 ${replies}개도 함께 안 보이게 돼요.` : ""}
            </p>
            {admin && (
              <label className="fl">
                <span>삭제 사유 (쓴 사람에게 알림으로 가요)</span>
                <textarea
                  value={reason}
                  maxLength={200}
                  rows={3}
                  placeholder="예: 다른 팝업과 관계없는 광고 글이에요"
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
            )}
            <div className="two">
              <button type="button" className="btn-line" onClick={() => setAsking(false)}>
                취소
              </button>
              <button
                type="button"
                className="btn-main"
                onClick={async () => {
                  if (admin && reason.split(/\s+/).join(" ").trim().length < 2) {
                    toast("삭제 사유를 두 글자 이상 적어 주세요. 쓴 사람에게 알림으로 가요.", "error");
                    return;
                  }
                  setAsking(false);
                  const res = await reviewDeleteAction(r.id, admin ? reason : "");
                  toast(res?.ok || res?.error || "", res?.ok ? "ok" : "error");
                  router.refresh();
                }}
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

export default function Reviews({
  cafeId,
  threads,
  me,
  stamps = 0,
}: {
  cafeId: string;
  threads: TView[];
  me: { nick: string; avatar: string } | null;
  /** 내 후기 도장 수 (lib/server/stamp.ts myStamps) */
  stamps?: number;
}) {
  const router = useRouter();
  const [pick, setPick] = useState("전체");
  const [sort, setSort] = useState<"new" | "star">("new");
  const [limit, setLimit] = useState(PAGE);
  // 방금 쓴 글: 서버가 저장했다고 답하면 바로 붙여 보여 주고, 새 목록(router.refresh)이 오면 비운다 (11/20 등록 속도)
  const [pending, setPending] = useState<Posted[]>([]);
  // 답글은 처음엔 접어 두고 '댓글 N개' 로 펼친다 (11/20 요청). 방금 답글을 단 글은 펼쳐 둔다
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [replyTo, setReplyTo] = useState("");
  const [zoom, setZoom] = useState<{ list: string[]; i: number } | null>(null);
  useEffect(() => {
    setPending((cur) => {
      cur.forEach((p) => p.view.images.forEach((x) => x.startsWith("blob:") && URL.revokeObjectURL(x)));
      return cur.length ? [] : cur;
    });
  }, [threads]);
  useEffect(() => {
    if (!zoom) return;
    const n = zoom.list.length;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setZoom(null);
      if (e.key === "ArrowRight") setZoom((z) => z && { ...z, i: (z.i + 1) % n });
      if (e.key === "ArrowLeft") setZoom((z) => z && { ...z, i: (z.i - 1 + n) % n });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoom]);
  const posted = (p: Posted) => {
    setPending((cur) => [...cur, p]);
    if (p.parentId) setOpen((o) => ({ ...o, [p.parentId]: true }));
  };
  const onZoom = (list: string[], i: number) => setZoom({ list, i });
  const all: TView[] = [
    ...pending.filter((p) => !p.parentId).map((p) => ({ post: p.view, replies: [] as RView[] })).reverse(),
    ...threads.map((t) => {
      const more = pending.filter((p) => p.parentId === t.post.id).map((p) => p.view);
      return more.length ? { ...t, replies: [...t.replies, ...more] } : t;
    }),
  ];
  const rated = all.filter((t) => t.post.kind === RATED && t.post.rating).map((t) => t.post.rating as number);
  const avg = rated.length ? Math.round((rated.reduce((a, b) => a + b, 0) / rated.length) * 10) / 10 : 0;
  const dist = [5, 4, 3, 2, 1].map((s) => ({ s, n: rated.filter((x) => x === s).length }));
  const count = Object.fromEntries(KINDS.map((k) => [k, all.filter((t) => t.post.kind === k).length]));
  const withPhoto = all.filter((t) => t.post.images.length > 0);
  const photos = withPhoto.flatMap((t) => t.post.images.map(picSrc));
  // 도장은 같은 팝업에 1개: 이 팝업에 내 '다녀온 후기'가 이미 있으면 더 받지 않는다
  const stampedHere = all.some((t) => t.post.mine && t.post.kind === RATED);
  const chips: [string, number][] = [
    ["전체", all.length],
    ["사진 후기만", withPhoto.length],
    ...KINDS.map((k) => [k, count[k]] as [string, number]),
  ];
  const filtered = all.filter((t) => pick === "전체" || (pick === "사진 후기만" ? t.post.images.length > 0 : t.post.kind === pick));
  const sorted =
    sort === "star"
      ? filtered
          .map((t, i) => ({ t, i }))
          .sort((a, b) => (b.t.post.rating ?? 0) - (a.t.post.rating ?? 0) || a.i - b.i)
          .map((x) => x.t)
      : filtered;
  const shown = sorted.slice(0, limit);

  return (
    <div className="rv-pane ad-rv">
      <section className="rvbox ad-rv-write" aria-labelledby="ad-write-h">
        <h2 id="ad-write-h">리뷰 쓰기</h2>
        {me ? (
          <WriteBox cafeId={cafeId} me={me} onPosted={posted} stamps={stamps} stampedHere={stampedHere} />
        ) : (
          <>
            <p className="side-note">리뷰는 로그인하면 쓸 수 있어요. 다녀온 후기를 남기면 후기 도장도 받아요.</p>
            <button
              type="button"
              className="btn-main"
              onClick={() => goLogin(router, "리뷰는 로그인하면 쓸 수 있어요.", `/popup/${cafeId}`)}
            >
              로그인하고 계속하기
            </button>
          </>
        )}
      </section>

      <section className="ad-rv-list" aria-labelledby="ad-list-h">
        <h2 id="ad-list-h" className="sr-only">
          리뷰 목록
        </h2>
        {!all.length ? (
          <p className="rv-none center">아직 리뷰가 없습니다. 다녀온 후기나 기대하는 점을 처음으로 남겨 보세요.</p>
        ) : (
          <>
            {(rated.length > 0 || photos.length > 0) && (
              <div className="ad-sum">
                {rated.length > 0 && (
                  <>
                    <div className="ad-sum-avg">
                      <span className="rv-avg-num">{avg.toFixed(1)}</span>
                      <span className="ad-stars" role="img" aria-label={`5점 만점에 ${avg.toFixed(1)}점`}>
                        <span>★★★★★</span>
                        <span style={{ width: `${(avg / 5) * 100}%` }}>★★★★★</span>
                      </span>
                      <span className="rv-avg-cnt">다녀온 후기 {rated.length}개 평균</span>
                    </div>
                    <div className="ad-sum-dist" aria-label="점수 분포">
                      {dist.map((b) => (
                        <div key={b.s}>
                          <span>{b.s}점</span>
                          <span className="ad-bar">
                            <span style={{ width: `${(b.n / rated.length) * 100}%` }} />
                          </span>
                          <span>{b.n}</span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
                {photos.length > 0 && (
                  <div className="ad-sum-pics" aria-label="사진 후기 모아 보기">
                    {photos.slice(0, 3).map((x, k) => (
                      <button key={`${x}-${k}`} type="button" aria-label={`사진 후기 ${k + 1} 크게 보기`} onClick={() => onZoom(photos, k)}>
                        <img src={x} alt="" loading="lazy" />
                        {k === 2 && photos.length > 3 && <span>+{photos.length - 3}</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="ad-filter">
              <div className="ad-fchips" role="group" aria-label="리뷰 보기">
                {chips.map(([k, n]) => (
                  <button
                    key={k}
                    type="button"
                    aria-pressed={pick === k}
                    className={pick === k ? "on" : ""}
                    onClick={() => {
                      setPick(k);
                      setLimit(PAGE);
                    }}
                  >
                    {k} {n}
                  </button>
                ))}
              </div>
              <label className="ad-sort">
                정렬
                <select value={sort} onChange={(e) => setSort(e.target.value === "star" ? "star" : "new")}>
                  <option value="new">최신순</option>
                  <option value="star">별점 높은 순</option>
                </select>
              </label>
            </div>
            {!shown.length && (
              <p className="rv-none center">
                {pick === "사진 후기만" ? "아직 사진 후기가 없어요." : `아직 ${pick}${pick === "기대평" ? "이" : "가"} 없어요.`} 처음으로 남겨 보세요.
              </p>
            )}
            {shown.map((t) => (
              <article key={t.post.id} className="rv-thread">
                <Card r={t.post} replies={t.replies.length} onZoom={onZoom} />
                {(t.replies.length > 0 || (me && !t.post.id.startsWith("pending-"))) && (
                  <div className="ad-rv-foot">
                    {t.replies.length > 0 && (
                      <button
                        type="button"
                        className="ad-rv-replies"
                        aria-expanded={!!open[t.post.id]}
                        onClick={() => setOpen((o) => ({ ...o, [t.post.id]: !o[t.post.id] }))}
                      >
                        {open[t.post.id] ? "댓글 접기" : `ㄴ 댓글 ${t.replies.length}개`}
                      </button>
                    )}
                    {me && !t.post.id.startsWith("pending-") && (
                      <button
                        type="button"
                        className="ad-rv-reply"
                        aria-expanded={replyTo === t.post.id}
                        onClick={() => setReplyTo((cur) => (cur === t.post.id ? "" : t.post.id))}
                      >
                        답글 쓰기
                      </button>
                    )}
                  </div>
                )}
                {open[t.post.id] && t.replies.map((r) => <Card key={r.id} r={r} reply onZoom={onZoom} />)}
                {me && replyTo === t.post.id && (
                  <WriteBox cafeId={cafeId} parentId={t.post.id} me={me} onPosted={posted} onClose={() => setReplyTo("")} />
                )}
              </article>
            ))}
            {sorted.length > limit && (
              <button type="button" className="ad-more" onClick={() => setLimit((n) => n + PAGE)}>
                리뷰 더보기
              </button>
            )}
          </>
        )}
      </section>

      {zoom && (
        <div className="lightbox" role="dialog" aria-label="사진 크게 보기" onClick={() => setZoom(null)}>
          <img src={zoom.list[zoom.i]} alt="리뷰 사진" />
          <button type="button" className="lb-x" aria-label="닫기" onClick={() => setZoom(null)}>
            <CloseIcon />
          </button>
          {zoom.list.length > 1 && (
            <>
              <span className="lb-count">
                {zoom.i + 1} / {zoom.list.length}
              </span>
              <button
                type="button"
                className="ad-gal-arrow l"
                aria-label="이전 사진"
                onClick={(e) => {
                  e.stopPropagation();
                  setZoom({ ...zoom, i: (zoom.i - 1 + zoom.list.length) % zoom.list.length });
                }}
              >
                ‹
              </button>
              <button
                type="button"
                className="ad-gal-arrow r"
                aria-label="다음 사진"
                onClick={(e) => {
                  e.stopPropagation();
                  setZoom({ ...zoom, i: (zoom.i + 1) % zoom.list.length });
                }}
              >
                ›
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
