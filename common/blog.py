"""팝업별 블로그 후기 (네이버 블로그 검색, 11/18).

네이버 검색 API 는 2026-07-31 부터 개발자센터 신규 신청이 막히고 네이버클라우드 **NAVER API HUB** 로 옮겨졌다.
API HUB 콘솔의 호출 예시에 맞춰 주소·헤더를 .env / Streamlit Secrets 로 바꿀 수 있게 둔다.

  NAVER_BLOG_CLIENT_ID      API HUB 의 Client ID
  NAVER_BLOG_CLIENT_SECRET  API HUB 의 Client Secret
  NAVER_BLOG_URL            블로그 검색 호출 주소. 비우면 https://naverapihub.apigw.ntruss.com/search/v1/blog
  NAVER_BLOG_HEADERS        'ncp' (X-NCP-APIGW-API-KEY-ID / -KEY, 기본) 또는 'naver' (X-Naver-Client-Id / -Secret)

키가 없으면 아무것도 하지 않는다 (화면에 칸이 안 생김). 실패해도 앱은 멈추지 않는다.
보내는 것은 팝업 작품명·매장명뿐이고 회원 정보는 보내지 않는다. 결과는 제목·요약·링크만 보여 준다.
"""
from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import requests

from .guard import mask

HUB_URL = "https://naverapihub.apigw.ntruss.com/search/v1/blog"     # NAVER API HUB 블로그 검색 (11/18 확인)
TIMEOUT = 6


@dataclass
class Post:
    title: str
    link: str
    desc: str
    blogger: str
    day: date | None


def enabled() -> bool:
    return bool(os.getenv("NAVER_BLOG_CLIENT_ID") and os.getenv("NAVER_BLOG_CLIENT_SECRET"))


def _headers() -> dict:
    cid, sec = os.getenv("NAVER_BLOG_CLIENT_ID", ""), os.getenv("NAVER_BLOG_CLIENT_SECRET", "")
    if os.getenv("NAVER_BLOG_HEADERS", "ncp").lower() == "naver":
        return {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}
    return {"X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": sec}


_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return mask(html.unescape(_TAG.sub("", str(text or ""))).strip())


def query_for(row: dict) -> str:
    """검색어: '작품 매장 팝업' (매장 이름의 괄호·지점 꾸밈은 뺀다)."""
    work = str(row.get("work") or "").strip()
    cafe = re.sub(r"\(.*?\)", "", str(row.get("cafe_name") or "")).strip()
    return " ".join(x for x in (work, cafe, "팝업") if x)


_GENERIC = {"카페", "팝업", "스토어", "팝업스토어", "콜라보", "매장", "지점", "본점", "space", "cafe", "store", "the",
            "애니", "서울", "부산", "대구", "인천", "광주", "대전", "울산", "경기", "더현"}


def _place_words(row: dict) -> list[str]:
    """매장 이름·동네에서 알아볼 낱말 ('애니메이트 카페 잠실롯데점' → 애니메이트, 잠실롯데, 잠실 …)."""
    from . import geo
    words = []
    for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", re.sub(r"\(.*?\)", " ", str(row.get("cafe_name") or ""))):
        w = re.sub(r"점$", "", w).lower()
        if len(w) >= 2 and w not in _GENERIC:
            words.append(w)
            if len(w) >= 4 and re.match(r"[가-힣]", w) and w[:2] not in _GENERIC:
                words.append(w[:2])          # '잠실롯데' → '잠실'
    addr = str(row.get("address") or "")
    for a in (geo.area_name(addr),):           # 동네 이름만 (시 이름 '서울' 은 너무 넓다)
        if a and len(a) >= 2 and a not in _GENERIC:
            words.append(a.lower())
    return list(dict.fromkeys(words))


def search(row: dict, limit: int = 5, usage=None, sort: str = "sim") -> tuple[list[Post], str]:
    """(글 목록, 오류 이유). 팝업 시작 30일 전부터 쓴 글만, 최신순. 키가 없으면 ([], 'off').
    usage(호출 수 저장소)를 주면 이번 달 MONTHLY_LIMIT 번을 넘으면 부르지 않는다 ([], 'limit').
    sort: 'sim'(정확도순, 처음 찾을 때) · 'date'(최신순, 저장해 둔 뒤 새 글만 더할 때)."""
    if not enabled():
        return [], "off"
    if blocked(usage):
        return [], "daily"
    if usage is not None:
        if not allowed(usage):
            return [], "limit"
        record(usage)
    url = os.getenv("NAVER_BLOG_URL") or HUB_URL
    try:
        res = requests.get(url, headers=_headers(), timeout=TIMEOUT,
                           params={"query": query_for(row), "display": 30, "sort": "date" if sort == "date" else "sim",
                                   "format": "json"})
    except requests.RequestException:
        return [], "연결 실패"
    if res.status_code == 429:
        _mark_blocked(usage)
        return [], "daily"
    if res.status_code != 200:
        return [], f"HTTP {res.status_code}"
    try:
        items = res.json().get("items") or []
    except ValueError:
        return [], "응답 형식 오류"
    start = str(row.get("start_date") or "")[:10]
    try:
        since = date.fromisoformat(start) - timedelta(days=30)
    except ValueError:
        since = None
    work = re.sub(r"\s+", "", str(row.get("work") or "")).lower()
    places = _place_words(row)
    posts = []
    for it in items:
        try:
            day = datetime.strptime(str(it.get("postdate") or ""), "%Y%m%d").date()
        except ValueError:
            day = None
        if since and day and day < since:
            continue                      # 팝업과 상관없는 예전 글
        title, desc = _clean(it.get("title")), _clean(it.get("description"))
        text = re.sub(r"\s+", "", title + desc).lower()
        if work and work[:4] not in text:
            continue                      # 작품 이름이 없는 글은 뺀다
        if places and not any(p in text for p in places):
            continue                      # 매장·동네 이름이 없는 글(전국 팝업 총정리 등)은 뺀다
        link = str(it.get("link") or "")
        if not link.startswith("https://") and not link.startswith("http://"):
            continue
        posts.append(Post(title=title[:80], link=link, desc=desc[:120], blogger=_clean(it.get("bloggername"))[:30], day=day))
    posts.sort(key=lambda p: p.day or date.min, reverse=True)
    return posts[:limit], ""


_OG = re.compile(r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']""", re.I)


def thumbnail(link: str) -> str:
    """블로그 글의 대표 사진(og:image) 주소. 못 찾으면 ''. 네이버 블로그는 모바일 주소가 가볍다."""
    url = link.replace("://blog.naver.com/", "://m.blog.naver.com/")
    try:
        res = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0 (compatible; ANI-WHERE)"})
        m = _OG.search(res.text[:200_000])
    except requests.RequestException:
        return ""
    img = html.unescape(m.group(1)) if m else ""
    return img if img.startswith("https://") and '"' not in img and "'" not in img else ""


def with_thumbs(posts: list[Post]) -> list[tuple[Post, str]]:
    """글마다 대표 사진을 함께 (11/20: 5개씩 → 10개씩 한꺼번에. 글은 많아야 SHOW_MAX 개, 하나에 3초까지)."""
    from concurrent.futures import ThreadPoolExecutor
    if not posts:
        return []
    with ThreadPoolExecutor(max_workers=min(10, len(posts))) as ex:
        return list(zip(posts, ex.map(lambda p: thumbnail(p.link), posts)))


# ------------------------------------------------------------------ 호출 한도 (11/18 요청: 한 달 30,000번에서 완전히 멈춤)
import threading
import time as _time

MONTHLY_LIMIT = 30_000
# 달마다 다른 한도 (11/19 사용자 결정): 2026년 11월은 네이버 API HUB 한시적 무료라 크게 열어 둔다.
# 12월부터는 다시 MONTHLY_LIMIT(30,000번)에서 멈춘다 — 이 표에 없는 달은 모두 30,000번.
MONTH_LIMITS = {"2026-11": 1_000_000}


def monthly_limit(month: str | None = None) -> int:
    """이번 달(한국 시간) 블로그 검색 호출 한도."""
    return MONTH_LIMITS.get(month or _month(), MONTHLY_LIMIT)
USAGE_HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at", "api", "month", "calls"]
_FLUSH_EVERY = 25                 # 25번마다 한 줄씩 쌓는다 (저장소가 한 달에 최대 1,200줄 정도)
_lock = threading.Lock()
_pending = 0
_cache: tuple[float, str, int] | None = None     # (읽은 시각, 달, 그달 합계)


def _month() -> str:
    from datetime import timezone
    return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m")


def month_calls(store) -> int:
    """이번 달(한국 시간) 블로그 검색 호출 수 = 저장된 합계 + 아직 안 적은 수. 못 읽으면 예외."""
    global _cache
    m = _month()
    now = _time.time()
    if not (_cache and _cache[1] == m and now - _cache[0] < 60):
        total = sum(int(r.get("calls") or 0) for r in store.all_rows()
                    if r.get("api") == "blog" and r.get("month") == m)
        _cache = (now, m, total)
    return _cache[2] + _pending


# 네이버가 '일별 사용량 한도 초과'(HTTP 429)라고 하면 그날(한국 시간)은 더 부르지 않는다 (11/19).
# 서버가 다시 켜져도 · 공개 웹(Vercel)도 알 수 있게 api_usage 에 그날 표시 한 줄을 쌓는다 (api='blog_429', month=날짜).
# (예전에는 막힌 뒤에도 팝업 116곳을 계속 불러 한도만 더 써 버렸다)
_blocked_day = ""


def _day() -> str:
    from datetime import timezone
    return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")


def blocked(store=None) -> bool:
    """오늘 네이버 하루 한도에 걸렸으면 True (부르지 않는다)."""
    global _blocked_day
    today = _day()
    if _blocked_day == today:
        return True
    if store is not None:
        try:
            if any(r.get("api") == "blog_429" and r.get("month") == today for r in store.all_rows()):
                _blocked_day = today
                return True
        except Exception:
            pass
    return False


def _mark_blocked(store=None) -> None:
    global _blocked_day
    if _blocked_day == _day():
        return
    _blocked_day = _day()
    if store is not None:
        try:
            store.append({"api": "blog_429", "month": _day(), "calls": 0}, entry_id=f"blog_429:{_day()}")
        except Exception:
            pass


def warm_claim(store) -> bool:
    """블로그 글 수 미리 세기는 하루에 한 번만 (서버가 다시 켜질 때마다 116곳을 다시 세던 문제, 11/19).
    오늘 이미 센 표시(api='blog_warm')가 있으면 False, 없으면 표시를 남기고 True."""
    today = _day()
    try:
        if any(r.get("api") == "blog_warm" and r.get("month") == today for r in store.all_rows()):
            return False
        store.append({"api": "blog_warm", "month": today, "calls": 0}, entry_id=f"blog_warm:{today}")
        return True
    except Exception:
        return False


def allowed(store) -> bool:
    """한도 안이면 True. 호출 수를 읽지 못하면(표가 없거나 연결 실패) 안전하게 False — 부르지 않는다."""
    try:
        return month_calls(store) < monthly_limit()
    except Exception:
        return False


def record(store) -> None:
    """한 번 불렀다고 센다. 25번마다 저장소에 한 줄."""
    global _pending, _cache
    with _lock:
        _pending += 1
        if _pending < _FLUSH_EVERY:
            return
        n, _pending = _pending, 0
    try:
        store.append({"api": "blog", "month": _month(), "calls": n})
        if _cache and _cache[1] == _month():
            _cache = (_cache[0], _cache[1], _cache[2] + n)
    except Exception:
        with _lock:
            _pending += n                  # 못 적었으면 다음에 다시


def total(row: dict, usage=None) -> int | None:
    """이 팝업의 네이버 블로그 글 수 (검색 결과 총수). 못 세면 None. 한도 안에서만 부른다."""
    if not enabled() or blocked(usage):
        return None
    if usage is not None:
        if not allowed(usage):
            return None
        record(usage)
    try:
        res = requests.get(os.getenv("NAVER_BLOG_URL") or HUB_URL, headers=_headers(), timeout=TIMEOUT,
                           params={"query": query_for(row), "display": 1, "format": "json"})
        if res.status_code == 429:
            _mark_blocked(usage)
            return None
        return int(res.json().get("total") or 0) if res.status_code == 200 else None
    except (requests.RequestException, ValueError, TypeError):
        return None


# ------------------------------------------------------------------ 찾은 글 저장 (11/19 요청, supabase 013)
# "불러온 거 저장해 놓고 보이게 하고 추가된 것만 새로 불러오면 되잖아" — 찾은 글은 blog_posts 에 쌓고 화면은 거기서 읽는다.
# 네이버는 팝업마다 하루 한 번만 묻는다 (blog_checks 에 그날 표시). 처음엔 정확도순, 그다음부터는 최신순으로 새 글만 더한다.
import hashlib
from collections import Counter

POST_HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at",
                "cafe_id", "link", "title", "descr", "blogger", "day", "thumb"]
CHECK_HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at", "cafe_id", "day", "found"]
SHOW_MAX = 30          # 한 팝업에 보여 주는 글 수 (최신순)


def _post_id(cafe_id: str, link: str) -> str:
    return f"{cafe_id}:{hashlib.sha1(link.encode('utf-8')).hexdigest()[:12]}"


def stored(posts_store, cafe_id: str) -> list[dict]:
    """저장해 둔 이 팝업의 글 (같은 글은 마지막 기록 하나, 최신순). {'title','link','desc','blogger','day','thumb'}"""
    latest: dict[str, dict] = {}
    for r in posts_store.all_rows():
        if str(r.get("cafe_id")) != str(cafe_id):
            continue
        k = str(r.get("entry_id"))
        if k not in latest or int(r.get("revision") or 0) >= int(latest[k].get("revision") or 0):
            latest[k] = r
    out = []
    for r in latest.values():
        if r.get("status") == "deleted":
            continue
        try:
            day = date.fromisoformat(str(r.get("day") or "")[:10])
        except ValueError:
            day = None
        out.append({"title": str(r.get("title") or ""), "link": str(r.get("link") or ""), "desc": str(r.get("descr") or ""),
                    "blogger": str(r.get("blogger") or ""), "day": day, "thumb": str(r.get("thumb") or "")})
    out.sort(key=lambda p: p["day"] or date.min, reverse=True)
    return out[:SHOW_MAX]


def counts(posts_store) -> Counter:
    """팝업별 저장해 둔 글 수 ('블로그 후기 (N)' 탭 이름). 네이버를 부르지 않는다."""
    seen = {(str(r.get("cafe_id")), str(r.get("entry_id"))) for r in posts_store.all_rows() if r.get("status") != "deleted"}
    return Counter(c for c, _ in seen)


def checked_today(checks_store, cafe_id: str) -> bool:
    today = _day()
    return any(str(r.get("cafe_id")) == str(cafe_id) and str(r.get("day")) == today for r in checks_store.all_rows())


def refresh(row: dict, cafe_id: str, posts_store, checks_store, usage=None, thumbs: bool = True) -> tuple[list[dict], str]:
    """저장해 둔 글 + (오늘 아직 안 물어봤으면) 네이버에서 새 글만 더해 돌려준다. (글 목록, 오류 이유)
    오류(한도 · 연결 실패)여도 저장해 둔 글은 그대로 돌려준다 — 화면은 '찾지 못했어요' 대신 저장된 글을 보여 준다."""
    have = stored(posts_store, cafe_id)
    if not enabled() or checked_today(checks_store, cafe_id):
        return have, ""
    found, err = search(row, limit=SHOW_MAX, usage=usage, sort="date" if have else "sim")
    if err:
        return have, err
    known = {p["link"] for p in have}
    new = [p for p in found if p.link not in known]
    pics = dict((p.link, th) for p, th in with_thumbs(new)) if (thumbs and new) else {}
    # 한 번에 쌓는다 (11/20 속도: 글마다 append 하면 글마다 표 전체를 새로 읽어 글 10개면 몇 초씩 걸렸다)
    try:
        posts_store.append_many([({"cafe_id": str(cafe_id), "link": p.link[:500], "title": p.title[:200], "descr": p.desc[:300],
                                   "blogger": p.blogger[:60], "day": p.day.isoformat() if p.day else "",
                                   "thumb": (pics.get(p.link) or "")[:600]}, _post_id(str(cafe_id), p.link)) for p in new])
    except Exception:
        pass
    try:
        checks_store.append({"cafe_id": str(cafe_id), "day": _day(), "found": str(len(new))},
                            entry_id=f"{cafe_id}:{_day()}")
    except Exception:
        pass
    return stored(posts_store, cafe_id) if new else have, ""
