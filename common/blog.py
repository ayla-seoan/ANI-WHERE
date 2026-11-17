"""팝업별 블로그 후기 (네이버 블로그 검색, 11/18).

네이버 검색 API 는 2026-07-31 부터 개발자센터 신규 신청이 막히고 네이버클라우드 **NAVER API HUB** 로 옮겨졌다.
API HUB 콘솔의 호출 예시에 맞춰 주소·헤더를 .env / Streamlit Secrets 로 바꿀 수 있게 둔다.

  NAVER_BLOG_CLIENT_ID      API HUB 의 Client ID
  NAVER_BLOG_CLIENT_SECRET  API HUB 의 Client Secret
  NAVER_BLOG_URL            블로그 검색 호출 주소 (콘솔의 예시 그대로). 비우면 예전 개발자센터 주소
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

OLD_URL = "https://openapi.naver.com/v1/search/blog.json"
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


def search(row: dict, limit: int = 5) -> tuple[list[Post], str]:
    """(글 목록, 오류 이유). 팝업 시작 30일 전부터 쓴 글만, 최신순. 키가 없으면 ([], 'off')."""
    if not enabled():
        return [], "off"
    url = os.getenv("NAVER_BLOG_URL") or OLD_URL
    try:
        res = requests.get(url, headers=_headers(), timeout=TIMEOUT,
                           params={"query": query_for(row), "display": 20, "sort": "sim"})
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
    posts = []
    for it in items:
        try:
            day = datetime.strptime(str(it.get("postdate") or ""), "%Y%m%d").date()
        except ValueError:
            day = None
        if since and day and day < since:
            continue                      # 팝업과 상관없는 예전 글
        title, desc = _clean(it.get("title")), _clean(it.get("description"))
        if work and work[:4] not in re.sub(r"\s+", "", title + desc).lower():
            continue                      # 작품 이름이 없는 글은 뺀다
        link = str(it.get("link") or "")
        if not link.startswith("https://") and not link.startswith("http://"):
            continue
        posts.append(Post(title=title[:80], link=link, desc=desc[:120], blogger=_clean(it.get("bloggername"))[:30], day=day))
    posts.sort(key=lambda p: p.day or date.min, reverse=True)
    return posts[:limit], ""
