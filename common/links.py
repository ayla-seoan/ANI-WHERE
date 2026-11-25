"""참고 웹사이트 링크 확인 (11/18 안정성).

공식 링크가 깨졌으면 상세 화면에서 '링크 확인 필요' 로 알린다. 확실히 깨진 경우만 표시한다:
  - 404 · 410 · 5xx, 주소를 못 찾음(DNS)·연결 거부 (HEAD 로 안 열리면 GET 으로 한 번 더 보고 정한다)
  - 401 · 403 · 405 · 429 (막아 둔 사이트), 시간 초과는 '모름' 으로 두고 표시하지 않는다 (멀쩡한 링크를 깨졌다고 하지 않게)
ANIWHERE_LINKCHECK=0 이면 확인하지 않는다 (테스트·오프라인).
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; ANI-WHERE link check)"}
TIMEOUT = 4


def check(url: str) -> bool | None:
    """True = 열림, False = 깨짐(확실), None = 모름."""
    if os.getenv("ANIWHERE_LINKCHECK", "1") == "0":
        return None
    try:
        res = requests.head(url, allow_redirects=True, timeout=TIMEOUT, headers=UA)
        # HEAD 를 막거나 HEAD 에만 404 를 주는 사이트가 많다 (11/25 khgames.co.kr: HEAD 404 · GET 200) → 안 열리면 GET 으로 한 번 더
        if res.status_code >= 400:
            res = requests.get(url, allow_redirects=True, timeout=TIMEOUT, headers=UA, stream=True)
            res.close()
        code = res.status_code
    except requests.exceptions.Timeout:
        return None
    except (requests.exceptions.ConnectionError, requests.exceptions.InvalidURL,
            requests.exceptions.MissingSchema, requests.exceptions.TooManyRedirects):
        return False
    except requests.RequestException:
        return None
    if code in (404, 410) or code >= 500:
        return False
    if code in (401, 403, 429):
        return None
    return code < 400


def check_many(urls: list[str]) -> dict[str, bool | None]:
    if not urls:
        return {}
    with ThreadPoolExecutor(max_workers=min(4, len(urls))) as ex:
        return dict(zip(urls, ex.map(check, urls)))
