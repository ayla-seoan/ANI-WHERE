"use client";
import { submitWith } from "@/lib/submit";
import { useRouter } from "next/navigation";
import { useActionState, useEffect, useRef, useState } from "react";
import { reviewCreateAction, reviewDeleteAction, reviewEditAction, type FormState } from "@/app/actions";
import { avatarUrl, uploadUrl } from "@/lib/avatar";
import { sensitiveWarning } from "@/lib/guard";
import { APP_URL } from "@/lib/popup";
import { goLogin } from "../member/MemberContext";
import { toast } from "../member/Toast";
import { ChatIcon, EditIcon, StarIcon } from "../Icons";

// 상세 오른쪽 '리뷰' (앱 render_detail_tabs · render_reviews · _review_card): 맨 위 리뷰 쓰기(회원만),
// 그 아래 '리뷰 후기 / 블로그 후기', 평균 별점, 종류별 보기, 원글 + 답글. 내 글만 ⋯ 로 수정·삭제.
// '수정하기'(팝업 정보 고치기) · 사진 첨부 · 블로그 후기는 ANI:WHERE 앱에서.

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
};
export type TView = { post: RView; replies: RView[] };

const KINDS = ["다녀온 후기", "기대평", "기타"];
const RATED = "다녀온 후기";
const KIND_COLOR: Record<string, string> = { "다녀온 후기": "green", 기대평: "blue", 기타: "gray" };

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

function useDone(s: FormState, after: () => void) {
  const router = useRouter();
  const seen = useRef<FormState>(null);
  useEffect(() => {
    if (!s || s === seen.current) return;
    seen.current = s;
    if (s.ok) {
      toast(s.ok);
      after();
      router.refresh();
    }
  }, [s, after, router]);
}

/** 글쓰기 칸. parentId 가 있으면 답글 칸 (칸을 누르면 등록·취소 버튼이 나온다) */
function WriteBox({
  cafeId,
  parentId = "",
  me,
}: {
  cafeId: string;
  parentId?: string;
  me: { nick: string; avatar: string };
}) {
  const [kind, setKind] = useState(KINDS[0]);
  const [rating, setRating] = useState<number | null>(null);
  const [body, setBody] = useState("");
  const [focus, setFocus] = useState(false);
  const [n, setN] = useState(0);
  const [s, action, busy] = useActionState(reviewCreateAction, null);
  useDone(s, () => {
    setBody("");
    setRating(null);
    setFocus(false);
    setN((k) => k + 1);
  });
  const warn = sensitiveWarning(body);
  const allowEmpty = !parentId && kind === RATED && rating !== null;
  const reply = !!parentId;
  return (
    <form
      onSubmit={submitWith(action)}
      className={`write${reply ? " reply" : ""}${focus || body ? " open" : ""}`}
      key={n}
    >
      <input type="hidden" name="cafe_id" value={cafeId} />
      <input type="hidden" name="parent_id" value={parentId} />
      <input type="hidden" name="kind" value={reply ? "" : kind} />
      <input type="hidden" name="rating" value={rating ?? ""} />
      {(!reply || focus || body) && (
        <div className="rv-me">
          <Av v={me.avatar} size={28} />
          <b>{me.nick}</b>
        </div>
      )}
      {!reply && (
        <div className="pills kind-pills" role="radiogroup" aria-label="종류">
          {KINDS.map((k) => (
            <button key={k} type="button" className="pill" aria-pressed={kind === k} onClick={() => setKind(k)}>
              {k}
            </button>
          ))}
        </div>
      )}
      {!reply && kind === RATED && (
        <div className="rate-box">
          <div className="rv-rate-q">이 팝업 방문하셨나요?</div>
          <div className="rv-rate-sub">방문 예정인 분들에게 도움이 되는 후기를 작성해주세요</div>
          <Stars value={rating} onChange={setRating} />
        </div>
      )}
      <textarea
        name="body"
        value={body}
        maxLength={1000}
        rows={reply ? 2 : 4}
        onFocus={() => setFocus(true)}
        onChange={(e) => setBody(e.target.value)}
        placeholder={
          reply ? "답글을 남겨 주세요" : "다녀온 후기나 기대하는 점을 남겨 주세요 (대기 시간, 특전 소진 여부 등)"
        }
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
      {!reply && (
        <p className="cap pic-note">
          + 사진 첨부는{" "}
          <a href={`${APP_URL}/?cafe=${encodeURIComponent(cafeId)}`} target="_blank" rel="noopener noreferrer">
            ANI:WHERE 앱
          </a>
          에서 할 수 있어요.
        </p>
      )}
      <div className={reply ? "two" : ""}>
        <button type="submit" className="btn-main" disabled={busy || !!warn || (!body.trim() && !allowEmpty)}>
          {reply ? "답글 등록" : "리뷰 등록"}
        </button>
        {reply && (
          <button
            type="button"
            className="btn-line"
            onClick={() => {
              setBody("");
              setFocus(false);
            }}
          >
            취소
          </button>
        )}
      </div>
    </form>
  );
}

function EditBox({ r, isReply, onClose }: { r: RView; isReply: boolean; onClose: () => void }) {
  const [kind, setKind] = useState(r.kind || KINDS[0]);
  const [rating, setRating] = useState<number | null>(r.rating);
  const [body, setBody] = useState(r.body);
  const [s, action, busy] = useActionState(reviewEditAction, null);
  useDone(s, onClose);
  const warn = sensitiveWarning(body);
  return (
    <form onSubmit={submitWith(action)} className="write edit">
      <input type="hidden" name="entry_id" value={r.id} />
      <input type="hidden" name="kind" value={isReply ? "" : kind} />
      <input type="hidden" name="rating" value={rating ?? ""} />
      {!isReply && (
        <div className="pills kind-pills">
          {KINDS.map((k) => (
            <button key={k} type="button" className="pill" aria-pressed={kind === k} onClick={() => setKind(k)}>
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
      {s?.error && <div className="auth-warn">{s.error}</div>}
      <div className="two">
        <button type="button" className="btn-line" onClick={onClose}>
          취소
        </button>
        <button type="submit" className="btn-main" disabled={busy || !!warn}>
          저장
        </button>
      </div>
    </form>
  );
}

function Card({ r, reply = false, replies = 0 }: { r: RView; reply?: boolean; replies?: number }) {
  const router = useRouter();
  const [menu, setMenu] = useState(false);
  const [editing, setEditing] = useState(false);
  const [asking, setAsking] = useState(false);
  return (
    <div className={`rv-card${reply ? " is-reply" : ""}`}>
      <div className="rv-head">
        {reply && <span className="kb gray">답글</span>}
        {r.kind && <span className={`kb ${KIND_COLOR[r.kind] || "gray"}`}>{r.kind}</span>}
        <Av v={r.avatar} size={26} />
        <b>{r.name}</b>
        <span className="rv-when">
          · {whenText(r.when)}
          {r.edited ? " (수정됨)" : ""}
        </span>
        {r.mine && (
          <span className="rv-more">
            <button type="button" aria-label="내 글 수정·삭제" onClick={() => setMenu((m) => !m)}>
              ⋯
            </button>
            {menu && (
              <span className="rv-menu">
                <button
                  type="button"
                  onClick={() => {
                    setEditing(true);
                    setMenu(false);
                  }}
                >
                  수정
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAsking(true);
                    setMenu(false);
                  }}
                >
                  삭제
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
        r.body.trim() && <p className="rv-body">{r.body}</p>
      )}
      {r.images.length > 0 && (
        <div className="rv-pics">
          {r.images.map((x) => (
            <a key={x} href={uploadUrl(x)} target="_blank" rel="noopener noreferrer">
              <img src={uploadUrl(x)} alt="리뷰 사진" loading="lazy" />
            </a>
          ))}
        </div>
      )}
      {asking && (
        <div className="dlg-bg" onClick={() => setAsking(false)}>
          <div className="dlg" role="dialog" aria-label="리뷰 삭제" onClick={(e) => e.stopPropagation()}>
            <b className="dlg-t">리뷰 삭제</b>
            <p>
              이 글을 삭제할까요? 삭제하면 다시 볼 수 없어요.
              {replies ? ` 달린 답글 ${replies}개도 함께 안 보이게 돼요.` : ""}
            </p>
            <div className="two">
              <button type="button" className="btn-line" onClick={() => setAsking(false)}>
                취소
              </button>
              <button
                type="button"
                className="btn-main"
                onClick={async () => {
                  setAsking(false);
                  const res = await reviewDeleteAction(r.id);
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
}: {
  cafeId: string;
  threads: TView[];
  me: { nick: string; avatar: string } | null;
}) {
  const router = useRouter();
  const [sub, setSub] = useState<"review" | "blog">("review");
  const [pick, setPick] = useState("전체");
  const n = threads.reduce((a, t) => a + 1 + t.replies.length, 0);
  const rated = threads.filter((t) => t.post.kind === RATED && t.post.rating).map((t) => t.post.rating as number);
  const avg = rated.length ? Math.round((rated.reduce((a, b) => a + b, 0) / rated.length) * 10) / 10 : 0;
  const count = Object.fromEntries(KINDS.map((k) => [k, threads.filter((t) => t.post.kind === k).length]));
  const shown = threads.filter((t) => pick === "전체" || t.post.kind === pick);

  return (
    <aside className="detail-side" aria-label="리뷰">
      <div className="side-tabs">
        <span className="on">
          <ChatIcon />
          리뷰 {n}
        </span>
        <a href={`${APP_URL}/?cafe=${encodeURIComponent(cafeId)}`} target="_blank" rel="noopener noreferrer">
          <EditIcon />
          수정하기
        </a>
      </div>
      <div className="side-box rvbox">
        {me ? (
          <WriteBox cafeId={cafeId} me={me} />
        ) : (
          <>
            <p className="side-note">리뷰는 로그인하면 쓸 수 있어요.</p>
            <button
              type="button"
              className="side-cta"
              onClick={() => goLogin(router, "리뷰는 로그인하면 쓸 수 있어요.", `/popup/${cafeId}`)}
            >
              로그인하고 계속하기
            </button>
          </>
        )}
      </div>
      <div className="rv-subtabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={sub === "review"}
          className={sub === "review" ? "on" : ""}
          onClick={() => setSub("review")}
        >
          리뷰 후기 ({n})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={sub === "blog"}
          className={sub === "blog" ? "on" : ""}
          onClick={() => setSub("blog")}
        >
          블로그 후기
        </button>
      </div>
      {sub === "blog" ? (
        <div className="blog-empty">
          네이버 블로그 후기는{" "}
          <a href={`${APP_URL}/?cafe=${encodeURIComponent(cafeId)}`} target="_blank" rel="noopener noreferrer">
            ANI:WHERE 앱
          </a>
          에서 볼 수 있어요.
        </div>
      ) : !threads.length ? (
        <p className="rv-none">아직 리뷰가 없습니다. 다녀온 후기나 기대하는 점을 처음으로 남겨 보세요.</p>
      ) : (
        <>
          {rated.length > 0 && (
            <div className="rv-avg">
              <span className="rv-avg-num">{avg.toFixed(1)}</span>
              <span className="rv-avg-stars" aria-label={`5점 만점에 ${avg.toFixed(1)}점`}>
                <span className="rv-avg-bg">
                  {[0, 1, 2, 3, 4].map((k) => (
                    <StarIcon key={k} />
                  ))}
                </span>
                <span className="rv-avg-fg" style={{ width: `${(avg / 5) * 100}%` }}>
                  {[0, 1, 2, 3, 4].map((k) => (
                    <StarIcon key={k} />
                  ))}
                </span>
              </span>
              <span className="rv-avg-cnt">다녀온 후기 {rated.length}개 평균</span>
            </div>
          )}
          <div className="seg small" role="tablist" aria-label="리뷰 보기">
            {["전체", ...KINDS].map((k) => (
              <button key={k} type="button" className={pick === k ? "on" : ""} onClick={() => setPick(k)}>
                {k} {k === "전체" ? threads.length : count[k]}
              </button>
            ))}
          </div>
          {!shown.length && (
            <p className="rv-none">
              아직 {pick}
              {pick === "기대평" ? "이" : "가"} 없어요. 위에서 처음으로 남겨 보세요.
            </p>
          )}
          {shown.map((t) => (
            <div key={t.post.id} className="rv-thread">
              <Card r={t.post} replies={t.replies.length} />
              {t.replies.map((r) => (
                <Card key={r.id} r={r} reply />
              ))}
              {me && <WriteBox cafeId={cafeId} parentId={t.post.id} me={me} />}
            </div>
          ))}
        </>
      )}
    </aside>
  );
}
