"""내 캘린더: 찜한 팝업을 달력에 막대로 그리고, 곧 있는 팝업 목록을 만든다.

연속된 날짜는 한 막대로 묶는다. 한 주(일~토)를 넘어가면 주마다 막대를 끊어서 그리고,
같은 주에서 겹치는 막대는 아래 줄(lane)로 내려 쌓는다.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass
class Event:
    cafe_id: str
    work: str
    cafe_name: str
    start: date
    end: date
    images: str = ""
    address: str = ""


@dataclass
class Bar:
    event: Event
    col: int          # 0=일 … 6=토
    span: int         # 며칠 칸을 차지하는지
    lane: int         # 같은 주에서 몇 번째 줄인지 (0 부터)
    cont_left: bool   # 지난주에서 이어지는 막대
    cont_right: bool  # 다음 주로 이어지는 막대


@dataclass
class Week:
    days: list[date]
    bars: list[Bar]

    @property
    def lanes(self) -> int:
        return max((b.lane for b in self.bars), default=-1) + 1


def _day(value) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def latest_rows(all_rows: list[dict]) -> list[dict]:
    """entry_id 별 최신 행 (지도에서 내린 것도 포함). 종료돼 내려간 찜도 지난 달력에 남기려고 쓴다."""
    latest: dict[str, dict] = {}
    for row in all_rows:
        eid = str(row.get("entry_id"))
        prev = latest.get(eid)
        if prev is None or int(row.get("revision", 0) or 0) >= int(prev.get("revision", 0) or 0):
            latest[eid] = row
    return list(latest.values())


def fav_events(rows: list[dict], fav_ids: set[str], today: date) -> list[Event]:
    """찜한 카페들의 일정. 내려간(deleted) 카페는 기간이 끝나서 내려간 것만 남긴다 (직접 지운 건 뺀다)."""
    out = []
    for r in rows:
        cid = str(r.get("entry_id"))
        if cid not in fav_ids:
            continue
        start, end = _day(r.get("start_date")), _day(r.get("end_date"))
        if not start or not end:
            continue
        if end < start:
            start, end = end, start
        if r.get("status") == "deleted" and end >= today:
            continue
        out.append(Event(cid, str(r.get("work") or ""), str(r.get("cafe_name") or ""),
                         start, end, str(r.get("images") or ""), str(r.get("address") or "")))
    return sorted(out, key=lambda e: (e.start, e.end, e.work))


def month_weeks(year: int, month: int, events: list[Event]) -> list[Week]:
    """그 달의 주들(일요일 시작). 주마다 걸치는 일정을 막대로 나누고 겹치면 줄을 바꾼다."""
    weeks = []
    for days in calendar.Calendar(firstweekday=6).monthdatescalendar(year, month):
        first, last = days[0], days[-1]
        segs = []
        for e in events:
            if e.end < first or e.start > last:
                continue
            s, t = max(e.start, first), min(e.end, last)
            segs.append((e, (s - first).days, (t - s).days + 1, e.start < first, e.end > last))
        # 먼저 시작하고, 같은 날이면 긴 막대부터 위 줄에 둔다
        segs.sort(key=lambda x: (x[1], -x[2]))
        lanes_end: list[int] = []      # 줄마다 마지막으로 차지한 칸
        bars = []
        for e, col, span, cl, cr in segs:
            lane = next((i for i, end in enumerate(lanes_end) if end < col), len(lanes_end))
            if lane == len(lanes_end):
                lanes_end.append(col + span - 1)
            else:
                lanes_end[lane] = col + span - 1
            bars.append(Bar(e, col, span, lane, cl, cr))
        weeks.append(Week(days, bars))
    return weeks


def upcoming(events: list[Event], today: date, limit: int = 10) -> list[Event]:
    """아직 끝나지 않은 일정: 진행 중인 것부터, 그다음 시작일이 가까운 순."""
    live = [e for e in events if e.end >= today]
    return sorted(live, key=lambda e: (e.start > today, e.start, e.end))[:limit]


def status(e: Event, today: date) -> tuple[str, str]:
    """(배지 글자, 색 이름). 진행 중 / 오늘 시작 / D-n / 종료."""
    if e.end < today:
        return "종료", "gray"
    if e.start > today:
        return f"D-{(e.start - today).days}", "blue"
    if e.start == today:
        return "오늘 시작", "green"
    if e.end == today:
        return "오늘 종료", "red"
    return "진행 중", "green"
