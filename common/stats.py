"""PO 지표 · 데이터 분석. /stats 화면과 docs/metrics.md 가 같은 숫자를 쓰도록 계산을 한곳에 둔다.

여기서 다루는 것:
  1. 방문 전 정보 완결률 — 사용자가 '가도 되는지' 판단하는 데 필요한 5가지(기간·주소·좌표·참고 링크·포스터)가
     모두 있는 팝업의 비율. PRD 의 북극성 지표.
  2. 개선 전후 비교 — 어느 시점(cutoff) 까지 쌓인 기록만으로 같은 지표를 다시 계산한다.
     저장소가 append-only 라서 과거 시점의 상태를 그대로 되살릴 수 있다.
  3. 팝업 통계 — 지역·작품·월별 팝업 수, 평균 진행 기간, 별점·북마크 분포.

화면(Streamlit)에 의존하지 않는다. 표준 라이브러리와 pandas 만 쓴다.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from . import geo, mycal

# 방문 전에 꼭 있어야 하는 정보 (칸 이름 → 화면 이름)
VISIT_FIELDS: dict[str, str] = {
    "start_date": "기간",
    "address": "주소",
    "lat": "지도 좌표",
    "links": "참고 링크",
    "images": "포스터",
}
# 있으면 좋은 정보 (완결률에는 넣지 않고 따로 본다)
EXTRA_FIELDS: dict[str, str] = {
    "intro": "팝업 소개",
    "perks": "특전",
    "goods": "굿즈",
}

# Notion 주간 가져오기(11/2 첫 실행) 를 넣기 직전. 개선 전후 비교의 기준 시점
NOTION_CUTOFF = "2026-10-30"


def _filled(row: dict, col: str) -> bool:
    value = row.get(col)
    if col == "start_date":       # 기간은 시작·종료가 둘 다 있어야 한다
        return bool(mycal._day(row.get("start_date"))) and bool(mycal._day(row.get("end_date")))
    return bool(str(value if value is not None else "").strip())


def popups(all_rows: list[dict], until: str | None = None) -> list[dict]:
    """entry_id 별 최신 행. until('YYYY-MM-DD') 을 주면 그날 전까지 쌓인 기록만으로 본다.

    삭제한 것은 빼고, '기간 종료'로 지도에서 내린 것은 포함한다 (그때 실제로 있던 팝업이므로).
    """
    rows = [r for r in all_rows if until is None or str(r.get("updated_at", ""))[:10] < until]
    out = []
    for r in mycal.latest_rows(rows):
        if r.get("status") == "deleted" and r.get("source") != "기간 종료":
            continue
        out.append(r)
    return out


def completeness(rows: list[dict]) -> dict:
    """칸별 채움 비율(%)과 방문 전 정보 완결률(%)."""
    n = len(rows)
    if n == 0:
        return {"n": 0, "fields": {}, "complete": 0.0}
    fields = {name: round(sum(_filled(r, col) for r in rows) / n * 100, 1)
              for col, name in {**VISIT_FIELDS, **EXTRA_FIELDS}.items()}
    complete = sum(all(_filled(r, c) for c in VISIT_FIELDS) for r in rows) / n * 100
    return {"n": n, "fields": fields, "complete": round(complete, 1)}


def before_after(all_rows: list[dict], cutoff: str = NOTION_CUTOFF) -> pd.DataFrame:
    """칸별 채움 비율을 '이전(cutoff 전)' 과 '지금' 으로 나란히. 긴 형식(항목·시점·비율)."""
    before = completeness(popups(all_rows, until=cutoff))
    now = completeness(popups(all_rows))
    recs = []
    for label, snap in (("이전", before), ("지금", now)):
        recs.append({"항목": "방문 전 정보 모두", "시점": label, "비율": snap["complete"]})
        for name, pct in snap["fields"].items():
            recs.append({"항목": name, "시점": label, "비율": pct})
    return pd.DataFrame(recs)


def status_counts(rows: list[dict], today: date) -> dict[str, int]:
    """진행 중 · 예정 · 종료 팝업 수."""
    out = {"진행 중": 0, "예정": 0, "종료": 0}
    for r in rows:
        s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        if not s or not e:
            continue
        out["종료" if e < today else "예정" if s > today else "진행 중"] += 1
    return out


def starting_within(rows: list[dict], today: date, days: int = 7) -> int:
    """오늘부터 days 일 안에 시작하는 팝업 수."""
    n = 0
    for r in rows:
        s = mycal._day(r.get("start_date"))
        if s and 0 <= (s - today).days < days:
            n += 1
    return n


def by_city(rows: list[dict], top: int = 10) -> pd.DataFrame:
    c = Counter(geo.city_name(str(r.get("address") or "")) or "지역 미상" for r in rows)
    return _top(c, "지역", top)


def by_work(rows: list[dict], top: int = 10) -> pd.DataFrame:
    c = Counter(str(r.get("work") or "").strip() or "작품 미상" for r in rows)
    return _top(c, "작품", top)


def by_month(rows: list[dict]) -> pd.DataFrame:
    """시작 월별 팝업 수 (빈 달도 0 으로 채워 시간 축이 끊기지 않게)."""
    months = [d.strftime("%Y-%m") for d in (mycal._day(r.get("start_date")) for r in rows) if d]
    if not months:
        return pd.DataFrame(columns=["월", "팝업 수"])
    idx = pd.period_range(min(months), max(months), freq="M").astype(str)
    c = Counter(months)
    return pd.DataFrame({"월": list(idx), "팝업 수": [c.get(m, 0) for m in idx]})


def durations(rows: list[dict]) -> list[int]:
    """팝업 진행 일수 (시작·종료 포함)."""
    out = []
    for r in rows:
        s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        if s and e and e >= s:
            out.append((e - s).days + 1)
    return out


def duration_buckets(days: list[int]) -> pd.DataFrame:
    bins = [("1~7일", 1, 7), ("8~14일", 8, 14), ("15~30일", 15, 30), ("31~60일", 31, 60), ("61일 이상", 61, 10**6)]
    return pd.DataFrame({"기간": [b[0] for b in bins],
                         "팝업 수": [sum(lo <= d <= hi for d in days) for _, lo, hi in bins]})


def rating_dist(review_rows: list[dict]) -> pd.DataFrame:
    """별점 1~5 분포 (다녀온 후기의 최신 행만)."""
    c: Counter = Counter()
    for r in review_rows:
        try:
            n = int(r.get("rating"))
        except (TypeError, ValueError):
            continue
        if 1 <= n <= 5:
            c[n] += 1
    return pd.DataFrame({"별점": [f"{i}점" for i in range(1, 6)], "후기 수": [c.get(i, 0) for i in range(1, 6)]})


def engagement(fav_rows: list[dict], review_rows: list[dict]) -> dict:
    """북마크·리뷰 참여 현황. fav_rows / review_rows 는 current_rows()."""
    fav_users = Counter(str(r.get("user")) for r in fav_rows)
    review_people = {str(r.get("nickname", "")).rsplit("#", 1)[-1] for r in review_rows if r.get("nickname")}
    return {
        "북마크 수": len(fav_rows),
        "북마크한 사람": len(fav_users),
        "1인당 북마크": round(len(fav_rows) / len(fav_users), 1) if fav_users else 0.0,
        "리뷰 수": len(review_rows),
        "리뷰 쓴 사람": len(review_people),
    }


def top_bookmarked(fav_rows: list[dict], cafe_rows: list[dict], top: int = 5) -> pd.DataFrame:
    names = {str(r.get("entry_id")): f'{r.get("work") or ""} · {r.get("cafe_name") or ""}'.strip(" ·")
             for r in cafe_rows}
    c = Counter(str(r.get("cafe_id")) for r in fav_rows)
    recs = [{"팝업": names.get(cid, "(내려간 팝업)"), "북마크": n} for cid, n in c.most_common(top)]
    return pd.DataFrame(recs, columns=["팝업", "북마크"])


def _top(c: Counter, label: str, top: int) -> pd.DataFrame:
    items = c.most_common()
    head, rest = items[:top], items[top:]
    if rest:
        head.append(("그 외", sum(n for _, n in rest)))
    return pd.DataFrame(head, columns=[label, "팝업 수"])


# ------------------------------------------------------------------ 사용자 테스트 설문 (11/18, n8n 이 쌓은 '정리' 탭)
# 폼: automation/n8n/create_form.gs — 참여자가 직접 써 보고 내는 설문. A = 평소 방법, B = ANI:WHERE (같은 사람이 둘 다 답함)
SURVEY_TARGET = {"success": 80.0, "q1": 60.0}     # PRD 사용자 지표: 과업 성공률 80% 이상, 첫 과제 평균 60초 이하
SURVEY_TASKS = {"질문 1": "이번 주말 서울 팝업 찾기", "질문 2": "작품 팝업 북마크", "질문 3": "내 캘린더에서 확인",
                "질문 4": "공식 공지 열기"}
SURVEY_OK = ("해냈어요", "어렵게 해냈어요")


def _nums(values) -> list[float]:
    out = []
    for v in values:
        try:
            x = float(str(v).strip())
        except (TypeError, ValueError):
            continue
        if x > 0:
            out.append(x)
    return out


def _avg(values) -> float | None:
    xs = _nums(values)
    return round(sum(xs) / len(xs), 1) if xs else None


def survey_summary(rows: list[dict]) -> dict:
    """'정리' 탭 → 응답자 · A/B 시간 · 과제별 성공률 · 만족도 · 문제 정의(불편한 점 · 정보 출처) 집계.
    automation/n8n/code/summarize.js 와 같은 규칙 (성공 = 해냈어요 + 어렵게 해냈어요, 평균 시간 = 성공한 줄만).
    사람 단위 값(방문 빈도 · 불편한 점 …)은 '질문 1' 줄에만 있다."""
    rows = [r for r in rows if str(r.get("닉네임") or "").strip() and str(r.get("과제") or "").strip()]
    people = [r for r in rows if r.get("과제") == "질문 1"]

    def ok(r) -> bool:
        return str(r.get("결과")) in SURVEY_OK

    def pct(a: int, b: int) -> float | None:
        return round(a / b * 100, 1) if b else None

    tasks = {}
    for t in SURVEY_TASKS:
        ts = [r for r in rows if r.get("과제") == t]
        tasks[t] = {"명": len(ts), "성공률": pct(sum(ok(r) for r in ts), len(ts)),
                    "평균초": _avg(r.get("걸린시간초") for r in ts if ok(r)),
                    "결과": Counter(str(r.get("결과") or "응답 없음") for r in ts)}

    def multi(key: str) -> list[tuple[str, int]]:
        c: Counter = Counter()
        for r in people:
            for x in str(r.get(key) or "").split(","):
                if x.strip():
                    c[x.strip()] += 1
        return c.most_common()

    blocks = Counter(f'{r.get("과제")} · {str(r.get("막힌 지점")).strip()}' for r in rows if str(r.get("막힌 지점") or "").strip())
    return {
        "응답자": len(people),
        "성공률": pct(sum(ok(r) for r in rows), len(rows)),
        "평소초": _avg(r.get("평소걸린시간초") for r in people),
        "질문1초": tasks["질문 1"]["평균초"],
        "비교": _avg(r.get("비교") for r in people),
        "만족도": _avg(r.get("만족도") for r in people),
        "다시쓸의향": pct(sum(str(r.get("다시쓸의향")) == "있어요" for r in people), len(people)),
        "과제별": tasks,
        "불편한점": multi("불편한점"),
        "정보출처": multi("정보출처"),
        "방문빈도": Counter(str(r.get("방문빈도") or "") for r in people if r.get("방문빈도")).most_common(),
        "만족도분포": Counter(str(r.get("만족도")) for r in people if str(r.get("만족도") or "").strip()),
        "막힌곳": blocks.most_common(5),
        "바라는점": [str(r.get("바라는점")).strip() for r in people if str(r.get("바라는점") or "").strip()],
    }


# ---- 응답 검증 (11/20, 1차 강사 코멘트 "실측이면 참가자 · 측정 방법 · 원자료 공개") --------------------------------
# 11/26 사용자 결정: 예전처럼 **'정리' 탭의 응답을 모두 센다** (1차 응답 탭이 비어 있어 1차 15명이 통째로 빠졌다).
# 구글 폼 응답 탭(1차 응답 · 2차 응답)과의 대조는 빼는 데 쓰지 않고, 화면 · 보고서에 '폼 응답 탭에서 확인된 수 / 없는 수' 를 참고로만 보여 준다.
# 지난 규칙: 11/20 ~ 11/25 폼 응답 탭에 있고 받은 시각이 과거인 응답만, 11/25 ~ 11/26 폼 응답 탭에 있는 응답만 (받은 시각 무관).
SURVEY_FORM_TABS = {"1차": "1차 응답", "2차": "2차 응답"}
_FORM_TIME = re.compile(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*(오전|오후)?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?")
_KST = timezone(timedelta(hours=9))


def parse_form_time(text) -> datetime | None:
    """구글 폼 타임스탬프 ('2026. 11. 19 오후 9:22:00' · '2026-11-19 21:22:00') → 한국 시각 (시간대 없는 값)."""
    t = str(text or "").strip()
    m = _FORM_TIME.search(t)
    if m:
        y, mo, d, ampm, h, mi, sec = m.groups()
        h = int(h)
        if ampm == "오후" and h < 12:
            h += 12
        if ampm == "오전" and h == 12:
            h = 0
        try:
            return datetime(int(y), int(mo), int(d), h, int(mi), int(sec or 0))
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(t.replace("/", "-")).replace(tzinfo=None) if t else None
    except ValueError:
        return None


def survey_verify(rows: list[dict], forms: dict[str, list[dict]], now: datetime | None = None) -> tuple[list[dict], dict]:
    """(셀 '정리' 줄 = 닉네임이 있는 모든 줄, 설명). forms = {'1차': 1차 응답 탭 줄들, '2차': ...}.
    11/26 부터 빼지 않는다: '검증' = 폼 응답 탭에서 확인된 사람 수, '폼에 없음' = 확인 안 된 사람 수, '제외' = 늘 0.
    '폼 응답 미래 시각' · '폼 응답 시각 없음' 도 참고 건수다."""
    now = now or datetime.now(_KST).replace(tzinfo=None)
    ok: set[tuple[str, str]] = set()
    future = no_time = 0
    for ver, rs in forms.items():
        for r in rs:
            nick = str(r.get("닉네임") or "").strip()
            t = parse_form_time(r.get("타임스탬프"))
            if not nick:
                continue
            ok.add((ver, nick))            # 시각과 상관없이 센다 (11/25)
            if t is None:
                no_time += 1
            elif t > now:
                future += 1

    def key(r: dict) -> tuple[str, str]:
        return survey_version(r), str(r.get("닉네임") or "").strip()

    people = {key(r) for r in rows if key(r)[1]}
    kept = [r for r in rows if key(r)[1]]          # 모두 센다 (11/26)
    good = people & ok
    return kept, {"전체": len(people), "검증": len(good), "제외": 0,
                  "폼 응답 미래 시각": future, "폼 응답 시각 없음": no_time,
                  "폼에 없음": len({p for p in people - good if p not in {(v, str(r.get("닉네임") or "").strip())
                                                                          for v, rs in forms.items() for r in rs}})}


def survey_version(row: dict) -> str:
    """'정리' 탭 한 줄의 버전. 1차 폼 응답만 '1차', 나머지(버전 칸이 없던 예전 줄 포함)는 '2차'."""
    return "1차" if str(row.get("버전") or "").strip() == "1차" else "2차"


def survey_compare(rows: list[dict]) -> dict:
    """1차(로그인 · 물어보기 없던 첫 버전) → 2차(지금) 비교 (관리자 '사용자 테스트' 탭).
    - 버전별 survey_summary
    - 지표 표: (이름, 1차, 2차, 단위, 클수록 좋은지, 목표)
    - 같은 사람: 닉네임이 1차 · 2차 모두에 있는 사람의 질문 1 시간 · 해낸 과제 수 · 만족도 변화"""
    by = {"1차": [r for r in rows if survey_version(r) == "1차"], "2차": [r for r in rows if survey_version(r) == "2차"]}
    s = {v: survey_summary(rs) for v, rs in by.items()}
    a, b = s["1차"], s["2차"]
    metrics = [
        ("과제 성공률", a["성공률"], b["성공률"], "%", True, SURVEY_TARGET["success"]),
        ("질문 1 평균 시간 (이번 주말 서울 팝업 찾기)", a["질문1초"], b["질문1초"], "초", False, SURVEY_TARGET["q1"]),
        *[(f"{t} 성공률 ({n})", a["과제별"][t]["성공률"], b["과제별"][t]["성공률"], "%", True, None)
          for t, n in SURVEY_TASKS.items()],
        *[(f"{t} 평균 시간 ({n})", a["과제별"][t]["평균초"], b["과제별"][t]["평균초"], "초", False, None)
          for t, n in SURVEY_TASKS.items() if t != "질문 1"],     # 질문 1 시간은 맨 위 줄
        ("평소 방법보다 편함 (5점)", a["비교"], b["비교"], "점", True, None),
        ("만족도 (5점)", a["만족도"], b["만족도"], "점", True, None),
        ("다시 쓸 의향", a["다시쓸의향"], b["다시쓸의향"], "%", True, None),
    ]

    def person(rs: list[dict]) -> dict:
        out: dict = {}
        for r in rs:
            nick = str(r.get("닉네임") or "").strip()
            if not nick:
                continue
            p = out.setdefault(nick, {"해낸 과제": 0, "질문1초": None, "만족도": None})
            if str(r.get("결과")) in SURVEY_OK:
                p["해낸 과제"] += 1
            if r.get("과제") == "질문 1":
                p["질문1초"] = (_nums([r.get("걸린시간초")]) or [None])[0]
                p["만족도"] = (_nums([r.get("만족도")]) or [None])[0]
        return out

    p1, p2 = person(by["1차"]), person(by["2차"])
    pairs = [{"닉네임": n, "질문 1 (1차)": p1[n]["질문1초"], "질문 1 (2차)": p2[n]["질문1초"],
              "해낸 과제 (1차)": p1[n]["해낸 과제"], "해낸 과제 (2차)": p2[n]["해낸 과제"],
              "만족도 (1차)": p1[n]["만족도"], "만족도 (2차)": p2[n]["만족도"]} for n in sorted(set(p1) & set(p2))]
    timed = [p for p in pairs if p["질문 1 (1차)"] and p["질문 1 (2차)"]]
    same = {
        "명": len(pairs),
        "빨라진 사람": sum(p["질문 1 (2차)"] < p["질문 1 (1차)"] for p in timed),
        "시간 잰 사람": len(timed),
        "평균 줄어든 초": round(sum(p["질문 1 (1차)"] - p["질문 1 (2차)"] for p in timed) / len(timed), 1) if timed else None,
        "더 해낸 사람": sum(p["해낸 과제 (2차)"] > p["해낸 과제 (1차)"] for p in pairs),
        "만족도 오른 사람": sum((p["만족도 (2차)"] or 0) > (p["만족도 (1차)"] or 0) for p in pairs
                           if p["만족도 (1차)"] and p["만족도 (2차)"]),
    }
    return {"1차": a, "2차": b, "지표": metrics, "같은 사람": same, "짝": pairs}
