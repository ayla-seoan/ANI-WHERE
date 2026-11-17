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


def search(row: dict, limit: int = 5, usage=None) -> tuple[list[Post], str]:
    """(글 목록, 오류 이유). 팝업 시작 30일 전부터 쓴 글만, 최신순. 키가 없으면 ([], 'off').
    usage(호출 수 저장소)를 주면 이번 달 MONTHLY_LIMIT 번을 넘으면 부르지 않는다 ([], 'limit')."""
    if not enabled():
        return [], "off"
    if usage is not None:
        if not allowed(usage):
            return [], "limit"
        record(usage)
    url = os.getenv("NAVER_BLOG_URL") or HUB_URL
    try:
        res = requests.get(url, headers=_headers(), timeout=TIMEOUT,
                           params={"query": query_for(row), "display": 30, "sort": "sim", "format": "json"})
    except requests.RequestException:
        return [], "연결 실패"
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
    """글마다 대표 사진을 함께 (동시에 최대 5개씩 가져온다)."""
    from concurrent.futures import ThreadPoolExecutor
    if not posts:
        return []
    with ThreadPoolExecutor(max_workers=min(5, len(posts))) as ex:
        return list(zip(posts, ex.map(lambda p: thumbnail(p.link), posts)))


# ------------------------------------------------------------------ 호출 한도 (11/18 요청: 한 달 30,000번에서 완전히 멈춤)
import threading
import time as _time

MONTHLY_LIMIT = 30_000
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


def allowed(store) -> bool:
    """한도 안이면 True. 호출 수를 읽지 못하면(표가 없거나 연결 실패) 안전하게 False — 부르지 않는다."""
    try:
        return month_calls(store) < MONTHLY_LIMIT
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
    if not enabled():
        return None
    if usage is not None:
        if not allowed(usage):
            return None
        record(usage)
    try:
        res = requests.get(os.getenv("NAVER_BLOG_URL") or HUB_URL, headers=_headers(), timeout=TIMEOUT,
                           params={"query": query_for(row), "display": 1, "format": "json"})
        return int(res.json().get("total") or 0) if res.status_code == 200 else None
    except (requests.RequestException, ValueError, TypeError):
        return None
