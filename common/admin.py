"""관리자 대시보드 · 삭제 요청 · 알림 · 접속 기록 (화면과 상관없는 계산만).

저장소는 모두 append-only (common/storage.py) 다. 처리·수정·삭제도 새 행을 쌓는다.
  - del_requests : 일반 회원의 게시글 삭제 요청 → 관리자가 승인/거부
  - notices      : 회원에게 가는 알림 (target = 회원 번호, 또는 'all' = 전체 공지)
  - visits       : 회원이 접속한 날 (회원 번호 × 날짜 1행) — 일별 접속 회원 수
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd

from . import mycal
from .guard import scan

REQ_HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at",
               "target_type", "target_id", "target_title", "reason", "requester", "requester_nick",
               "decision", "admin_reason", "decided_at"]
NOTICE_HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at",
                  "target", "kind", "title", "body"]
VISIT_HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at", "member", "day"]

TARGET_LABEL = {"review": "리뷰", "cafe": "팝업"}
MAX_REASON = 300


def _day(v) -> date | None:
    """날짜 칸('2026-11-18') 또는 기록 시각(updated_at, UTC). 시각은 한국 시간 날짜로 바꾼다."""
    text = str(v or "")
    if "T" in text:
        try:
            ts = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if ts.tzinfo is not None:
                return (ts + timedelta(hours=9) - ts.utcoffset()).date() if ts.utcoffset() is not None else ts.date()
        except ValueError:
            pass
    return mycal._day(text[:10])


def week_of(d: date) -> tuple[date, date]:
    """그 날이 든 주의 월요일 ~ 일요일."""
    mon = d - timedelta(days=d.weekday())
    return mon, mon + timedelta(days=6)


# ------------------------------------------------------------------ 팝업 현황 (주 단위 칸반)
def popup_board(all_rows: list[dict], week_start: date) -> dict[str, list[dict]]:
    """고른 주(월~일) 기준 네 칸.
    새로 생성 = 그 주에 처음 등록된 팝업 / 예정 = 그 주가 끝난 뒤 4주 안에 시작 /
    진행 = 그 주에 열려 있고 그 주 뒤에도 이어짐 / 종료 = 그 주 안에 끝남."""
    mon, sun = week_start, week_start + timedelta(days=6)
    first_seen: dict[str, date] = {}
    for r in all_rows:
        d = _day(r.get("updated_at"))
        eid = str(r.get("entry_id"))
        if d and (eid not in first_seen or d < first_seen[eid]):
            first_seen[eid] = d
    board: dict[str, list[dict]] = {"새로 생성": [], "예정": [], "진행": [], "종료": []}
    for r in mycal.latest_rows(all_rows):
        if r.get("status") == "deleted" and r.get("source") != "기간 종료":
            continue                          # 관리자가 내린 것은 빼고, 기간이 끝나 내려간 것은 센다
        eid = str(r.get("entry_id"))
        s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        if first_seen.get(eid) and mon <= first_seen[eid] <= sun:
            board["새로 생성"].append(r)
        if not (s and e):
            continue
        if sun < s <= sun + timedelta(days=28):
            board["예정"].append(r)
        elif mon <= e <= sun:
            board["종료"].append(r)
        elif s <= sun and e > sun:
            board["진행"].append(r)
    for k in board:
        board[k].sort(key=lambda r: str(r.get("start_date") or ""))
    return board


# ------------------------------------------------------------------ 이용 지표
def member_events(member_rows: list[dict]) -> pd.DataFrame:
    """회원 가입(revision 1)·탈퇴(status deleted) 날짜."""
    recs = []
    for r in member_rows:
        d = _day(r.get("updated_at"))
        if not d:
            continue
        if int(r.get("revision") or 0) == 1:
            recs.append({"day": d, "event": "가입"})
        if r.get("status") == "deleted":
            recs.append({"day": d, "event": "탈퇴"})
    return pd.DataFrame(recs, columns=["day", "event"])


def weekly_counts(events: pd.DataFrame, event: str, today: date, weeks: int = 8) -> pd.DataFrame:
    """최근 weeks 주의 주별 수 (월요일 날짜를 '11/10 주' 로)."""
    mon_now, _ = week_of(today)
    labels, counts = [], []
    for i in range(weeks - 1, -1, -1):
        mon = mon_now - timedelta(weeks=i)
        sun = mon + timedelta(days=6)
        n = 0 if events.empty else int(((events["event"] == event) & (events["day"] >= mon) & (events["day"] <= sun)).sum())
        labels.append(f"{mon.month}/{mon.day} 주")
        counts.append(n)
    return pd.DataFrame({"주": labels, "명": counts})


def daily_active(visit_rows: list[dict], week_start: date) -> pd.DataFrame:
    """고른 주의 요일별 접속 회원 수 (같은 날 여러 번 와도 1명)."""
    days = [week_start + timedelta(days=i) for i in range(7)]
    seen: dict[date, set] = {d: set() for d in days}
    for r in visit_rows:
        d = _day(r.get("day"))
        if d in seen:
            seen[d].add(str(r.get("member")))
    wd = "월화수목금토일"
    return pd.DataFrame({"날": [f"{d.month}/{d.day}({wd[d.weekday()]})" for d in days],
                         "접속 회원": [len(seen[d]) for d in days]})


def last_visit(visit_rows: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for r in visit_rows:
        m, d = str(r.get("member")), str(r.get("day") or "")
        if d > out.get(m, ""):
            out[m] = d
    return out


def log_visit(visit_store, member_key: str, today: date) -> None:
    """회원이 오늘 처음 들어왔을 때 한 줄 (회원 번호 × 날짜)."""
    visit_store.append({"member": member_key, "day": today.isoformat()},
                       entry_id=f"{member_key}:{today.isoformat()}")


# ------------------------------------------------------------------ 삭제 요청
def validate_reason(reason: str) -> list[str]:
    r = " ".join(str(reason or "").split())
    errors = []
    if len(r) < 5:
        errors.append("삭제를 요청하는 이유를 5자 이상 적어 주세요.")
    if len(r) > MAX_REASON:
        errors.append(f"이유는 {MAX_REASON}자까지 적을 수 있어요.")
    if scan(r):
        errors.append("이유에 전화번호·이메일 같은 개인정보는 넣지 말아 주세요.")
    return errors


def request_delete(req_store, target_type: str, target_id: str, title: str, reason: str,
                   requester: str, requester_nick: str) -> dict:
    return req_store.append({
        "target_type": target_type, "target_id": str(target_id), "target_title": title[:80],
        "reason": " ".join(str(reason).split()), "requester": requester, "requester_nick": requester_nick,
        "decision": "pending", "admin_reason": "", "decided_at": "",
    })


def pending_for(req_rows: list[dict], target_id: str, requester: str) -> bool:
    """같은 사람이 같은 글에 아직 처리 안 된 요청이 있는가 (중복 요청 막기)."""
    return any(str(r.get("target_id")) == str(target_id) and str(r.get("requester")) == requester
               and r.get("decision") == "pending" for r in req_rows)


def decide(req_store, notice_store, req: dict, approve: bool, admin_reason: str = "") -> dict:
    """승인/거부 기록을 쌓고, 요청한 회원에게 알림을 보낸다. 게시글 삭제는 부르는 쪽(화면)이 한다."""
    payload = {k: req.get(k, "") for k in REQ_HEADERS if k not in ("row_id", "entry_id", "revision", "status", "updated_at")}
    payload.update({"decision": "approved" if approve else "rejected",
                    "admin_reason": " ".join(str(admin_reason or "").split()),
                    "decided_at": datetime.now().isoformat(timespec="seconds")})
    row = req_store.append(payload, entry_id=str(req["entry_id"]))
    what = f'{TARGET_LABEL.get(req.get("target_type"), "게시글")} \'{req.get("target_title", "")}\''
    if approve:
        send(notice_store, str(req.get("requester")), "삭제 승인", "삭제 요청이 승인되었어요",
             f"요청하신 {what} 이(가) 승인되어 게시글이 삭제되었습니다.")
    else:
        send(notice_store, str(req.get("requester")), "삭제 거부", "삭제 요청이 거부되었어요",
             f"요청하신 {what} 삭제가 거부되었어요. 사유: {payload['admin_reason'] or '(사유 없음)'}")
    return row


# ------------------------------------------------------------------ 알림
def send(notice_store, target: str, kind: str, title: str, body: str, entry_id: str | None = None) -> dict:
    return notice_store.append({"target": target, "kind": kind, "title": title[:60], "body": body[:500]},
                               entry_id=entry_id)


def notices_for(notice_rows: list[dict], member_key: str, days: int = 60, today: date | None = None) -> list[dict]:
    """이 회원이 받을 알림 (전체 공지 + 나에게 온 것), 최신순. notice_rows 는 current_rows()."""
    today = today or date.today()
    out = []
    for r in notice_rows:
        if str(r.get("target")) not in ("all", member_key):
            continue
        d = _day(r.get("updated_at"))
        if d and (today - d).days > days:
            continue
        out.append(r)
    return sorted(out, key=lambda r: str(r.get("updated_at", "")), reverse=True)
