"""공개 웹(Vercel)의 팝업 목록 캐시를 바로 비운다 (11/25).

웹은 Supabase 를 읽어 10분 동안 기억한다. 앱이나 GitHub Actions 가 Notion 에서 새 팝업을 넣어도
웹은 그 사실을 몰라, 10분이 지나고도 한 번 더 열어야 보였다. 가져오기가 끝나면 여기서 웹에 알린다.

- WEB_REVALIDATE_SECRET 이 없으면 아무것도 하지 않는다 (키 없이도 앱은 그대로 돈다).
- 저장소가 supabase 가 아니면 부르지 않는다 (로컬 시험이 운영 웹을 건드리지 않게).
- 실패해도 앱은 멈추지 않는다. 웹은 원래대로 10분 뒤에 스스로 새로 읽는다.
"""
from __future__ import annotations

import os

import requests

DEFAULT_URL = "https://ani-where.vercel.app/api/revalidate"
TIMEOUT = 5


def ping(store=None) -> bool:
    """웹 캐시를 비웠으면 True. 설정이 없거나 실패하면 False (예외를 올리지 않는다)."""
    secret = (os.getenv("WEB_REVALIDATE_SECRET") or "").strip()
    if not secret:
        return False
    if store is not None and getattr(store, "mode", "") != "supabase":
        return False
    url = (os.getenv("WEB_REVALIDATE_URL") or DEFAULT_URL).strip()
    try:
        res = requests.post(url, headers={"Authorization": f"Bearer {secret}"}, timeout=TIMEOUT)
        return res.status_code == 200
    except requests.RequestException:
        return False
