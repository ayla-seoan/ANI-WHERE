"""홈 '실시간 인기 급상승 랭킹' 점수와 순서 (11/20: Streamlit · 공개 웹이 같은 결과를 내도록 한곳에 모음).

규칙 (웹 `web/lib/rank.ts` 와 한 글자도 다르지 않게 맞춘다 — 바꾸면 두 곳을 같이 바꾸고
`samples/rank_cases.json` 으로 두 쪽을 다 돌려 본다: `python -X utf8 -m pytest tests/test_rank.py` · `cd web && npm run test:rank`)

  ① 최근 7일 점수 = 최근 7일 북마크 수 × 2 + 최근 7일 리뷰 · 답글 수
  ② 같으면 전체 기간의 같은 점수
  ③ 같으면 오픈이 빠른 순 (점수 0인 팝업도 이 순서로 채움)
  ④ 같으면 팝업 번호(entry_id) 순 — 같은 날 여는 팝업끼리 두 사이트 순서가 달라지지 않게

- 북마크 · 리뷰는 지금 살아 있는 기록(`current_rows`)만 받는다.
- 리뷰는 화면에 보이는 것만 센다 (원글이 지워져 함께 숨겨진 답글은 뺌). 보이는지는 **전체 기록**으로 판단한 뒤
  7일을 거른다 — 오래된 원글에 최근 단 답글도 최근 7일 점수에 들어간다.
- '최근 7일' 은 시각을 날짜 · 시간으로 읽어 비교한다 (글자 비교는 +09:00 · +00:00 이 섞이면 9시간 어긋남).
  시간대가 없는 시각은 UTC 로 본다.
- '오늘' 은 한국 시간 (`today_kst`). 서버(Streamlit Cloud 는 UTC)의 날짜를 쓰면 00~09시에 어제 끝난 팝업이 남는다.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

RANK_DAYS = 7
TOP_N = 5
KST = timezone(timedelta(hours=9))

Score = tuple[int, int]          # (최근 7일 점수, 전체 기간 점수)


def today_kst() -> date:
    return datetime.now(KST).date()


def _ts(value) -> datetime | None:
    s = str(value or "").strip()
    if not s:
        return None
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _ymd(value) -> str:
    """여러 모양의 날짜 → YYYY-MM-DD (웹 lib/data.ts ymd 와 같은 규칙). 못 읽으면 ''"""
    m = re.search(r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})", str(value or ""))
    if not m:
        return ""
    y, mo, d = int(m[1]), int(m[2]), int(m[3])
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return ""


def visible_reviews(rows: list[dict]) -> list[dict]:
    """화면에 보이는 리뷰만: 원글이거나, 답글을 따라 올라가 원글에 닿는 것 (review.threads 와 같음)."""
    by_id = {str(r.get("entry_id")): r for r in rows}

    def alive(r: dict) -> bool:
        seen: set[str] = set()
        cur: dict | None = r
        while cur is not None and str(cur.get("parent_id") or ""):
            eid = str(cur.get("entry_id"))
            if eid in seen:
                return False
            seen.add(eid)
            cur = by_id.get(str(cur.get("parent_id")))
        return cur is not None

    return [r for r in rows if alive(r)]


def _count(rows: Iterable[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        k = str(r.get("cafe_id") or "")
        if k:
            out[k] = out.get(k, 0) + 1
    return out


def scores(fav_rows: list[dict], review_rows: list[dict], now: datetime | None = None) -> dict[str, Score]:
    """팝업 id → (최근 7일 점수, 전체 기간 점수). 받는 행은 current_rows (지금 살아 있는 기록)."""
    since = (now or datetime.now(timezone.utc)) - timedelta(days=RANK_DAYS)
    revs = visible_reviews(review_rows)

    def recent(rows: list[dict]) -> list[dict]:
        return [r for r in rows if (t := _ts(r.get("updated_at"))) is not None and t >= since]

    f7, r7, fa, ra = _count(recent(fav_rows)), _count(recent(revs)), _count(fav_rows), _count(revs)
    return {k: (f7.get(k, 0) * 2 + r7.get(k, 0), fa.get(k, 0) * 2 + ra.get(k, 0)) for k in set(fa) | set(ra)}


def order(live: list[dict], score: dict[str, Score]) -> list[dict]:
    """진행 중 · 오픈 예정 팝업을 랭킹 순서로 (전부 돌려준다. 화면은 앞 TOP_N 개)."""
    def key(r: dict):
        eid = str(r.get("entry_id"))
        week, total = score.get(eid, (0, 0))
        return (-week, -total, _ymd(r.get("start_date")), eid)
    return sorted(live, key=key)
