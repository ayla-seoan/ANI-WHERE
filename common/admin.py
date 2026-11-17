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


def decide(req_store, notice_store, req: dict, approve: bool, admin_reason: str = "", notify: bool = True) -> dict:
    """승인/거부 기록을 쌓고, 요청한 회원에게 알림을 보낸다. 게시글 삭제는 부르는 쪽(화면)이 한다."""
    payload = {k: req.get(k, "") for k in REQ_HEADERS if k not in ("row_id", "entry_id", "revision", "status", "updated_at")}
    payload.update({"decision": "approved" if approve else "rejected",
                    "admin_reason": " ".join(str(admin_reason or "").split()),
                    "decided_at": datetime.now().isoformat(timespec="seconds")})
    row = req_store.append(payload, entry_id=str(req["entry_id"]))
    if not notify:                          # 관리자가 이 알림 규칙을 꺼 두었으면 처리 기록만 남긴다
        return row
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


def daily_events(events: pd.DataFrame, event: str, week_start: date) -> pd.DataFrame:
    """고른 주의 요일별 가입·탈퇴 수."""
    days = [week_start + timedelta(days=i) for i in range(7)]
    wd = "월화수목금토일"
    counts = [0 if events.empty else int(((events["event"] == event) & (events["day"] == d)).sum()) for d in days]
    return pd.DataFrame({"날": [f"{d.month}/{d.day}({wd[d.weekday()]})" for d in days], "명": counts})


def gantt_rows(all_rows: list[dict], start: date, end: date, limit: int = 60) -> list[dict]:
    """간트 차트용: [start, end] 기간에 걸친 팝업 (기간 종료로 내려간 것 포함, 관리자 삭제 제외), 시작일 순."""
    out = []
    for r in mycal.latest_rows(all_rows):
        if r.get("status") == "deleted" and r.get("source") != "기간 종료":
            continue
        s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        if s and e and s <= end and e >= start:
            out.append(r)
    out.sort(key=lambda r: (str(r.get("start_date") or ""), str(r.get("end_date") or "")))
    return out[:limit]


# ------------------------------------------------------------------ 자동 알림 규칙 (관리자 '알림 관리' 에서 고친다)
RULE_HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at", "rule", "enabled", "days", "max_items"]

# 규칙 번호 → 기본값. days = 며칠 전부터(또는 며칠 동안) / max_items = 한 번에 보이는 최대 개수. None 이면 고칠 수 없는 칸
RULES = {
    "open":   {"name": "북마크한 팝업 오픈", "when": "오픈 {days}일 전부터 오픈 당일까지 매일", "who": "그 팝업을 북마크한 회원",
               "where": "종 알림 · 내 캘린더 알림 내역", "days": 3, "max_items": 8, "why": "북마크한 팝업이 곧 열려요 (오픈 {days}일 전부터 알려 드려요)"},
    "end":    {"name": "북마크한 팝업 종료", "when": "종료 {days}일 전부터 종료 당일까지 매일 (진행 중일 때)", "who": "그 팝업을 북마크한 회원",
               "where": "종 알림 · 내 캘린더 알림 내역", "days": 3, "max_items": 8, "why": "북마크한 팝업이 곧 끝나요 (종료 {days}일 전부터 알려 드려요)"},
    "near":   {"name": "내 주변 추천", "when": "위치를 허용했을 때, 지금 열려 있는 가까운 팝업 (북마크한 곳 제외)", "who": "로그인한 회원",
               "where": "종 알림", "days": None, "max_items": 3, "why": "내 위치에서 가까운 곳에 지금 열려 있어요"},
    "del_ok": {"name": "삭제 요청 승인", "when": "관리자가 삭제 요청을 승인하고 게시글이 삭제됐을 때", "who": "요청한 회원",
               "where": "종 알림 · 내 캘린더 알림 내역", "days": None, "max_items": None, "why": "내가 보낸 삭제 요청이 처리됐어요"},
    "del_no": {"name": "삭제 요청 거부", "when": "관리자가 거부 사유를 적어 거부했을 때 (사유 포함)", "who": "요청한 회원",
               "where": "종 알림 · 내 캘린더 알림 내역", "days": None, "max_items": None, "why": "내가 보낸 삭제 요청이 처리됐어요"},
    "notice": {"name": "관리자 공지", "when": "관리자가 공지를 추가·수정했을 때 ({days}일간 종에 보임)", "who": "모든 회원",
               "where": "종 알림 · 내 캘린더 알림 내역", "days": 14, "max_items": 5, "why": "ANI:WHERE 운영 공지예요"},
}
KIND_RULE = {"공지": "notice", "삭제 승인": "del_ok", "삭제 거부": "del_no"}


def rule_settings(rule_rows: list[dict]) -> dict[str, dict]:
    """규칙마다 지금 값 (기본값 + 관리자가 고친 최신 기록). '삭제'(status=deleted) 한 규칙은 꺼진 것."""
    out = {k: {"enabled": True, "days": v["days"], "max_items": v["max_items"]} for k, v in RULES.items()}
    for r in mycal.latest_rows(rule_rows):
        k = str(r.get("entry_id"))
        if k not in out:
            continue
        cur = out[k]
        cur["enabled"] = r.get("status") != "deleted" and str(r.get("enabled", "1")) not in ("0", "false", "False")
        for f in ("days", "max_items"):
            if RULES[k][f] is not None and str(r.get(f) or "").strip().isdigit():
                cur[f] = max(0, int(r.get(f)))
    return out


def save_rule(rule_store, key: str, enabled: bool, days: int | None, max_items: int | None) -> dict:
    d = RULES[key]
    return rule_store.append({"rule": key, "enabled": "1" if enabled else "0",
                              "days": "" if d["days"] is None or days is None else str(int(days)),
                              "max_items": "" if d["max_items"] is None or max_items is None else str(int(max_items))},
                             entry_id=key)


def rules_table(settings: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for k, d in RULES.items():
        cur = settings[k]
        rows.append({"알림": d["name"], "상태": "켜짐" if cur["enabled"] else "꺼짐",
                     "언제": d["when"].format(days=cur["days"]),
                     "최대 개수": "-" if d["max_items"] is None else f'{cur["max_items"]}개',
                     "누구에게": d["who"], "어디에": d["where"]})
    rows.append({"알림": "주간 브리핑 메일", "상태": "켜짐", "언제": "매주 월요일 11:00", "최대 개수": "-",
                 "누구에게": "운영자 본인 메일", "어디에": "메일 (automation/weekly_briefing.gs) — 앱에서 못 고침"})
    return pd.DataFrame(rows)


def why(key: str, settings: dict[str, dict] | None = None) -> str:
    """이 알림이 왜 왔는지 한 줄."""
    d = RULES.get(key)
    if not d:
        return ""
    days = (settings or {}).get(key, {}).get("days", d["days"])
    return d["why"].format(days=days)
