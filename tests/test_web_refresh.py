"""공개 웹 캐시 비우기(common/web_refresh.py)와 링크 확인(common/links.py) — 실제 인터넷은 쓰지 않는다."""
import requests

from common import links, web_refresh


class _Res:
    def __init__(self, code):
        self.status_code = code

    def close(self):
        pass


class _Store:
    def __init__(self, mode):
        self.mode = mode


def test_ping_without_secret_does_nothing(monkeypatch):
    monkeypatch.delenv("WEB_REVALIDATE_SECRET", raising=False)
    monkeypatch.setattr(requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("부르면 안 됨")))
    assert web_refresh.ping(_Store("supabase")) is False


def test_ping_skips_local_storage(monkeypatch):
    monkeypatch.setenv("WEB_REVALIDATE_SECRET", "x" * 32)
    monkeypatch.setattr(requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("부르면 안 됨")))
    assert web_refresh.ping(_Store("local")) is False


def test_ping_sends_secret_and_survives_failure(monkeypatch):
    monkeypatch.setenv("WEB_REVALIDATE_SECRET", "x" * 32)
    monkeypatch.delenv("WEB_REVALIDATE_URL", raising=False)
    seen = {}

    def ok(url, headers=None, timeout=None):
        seen.update(url=url, auth=headers["Authorization"])
        return _Res(200)

    monkeypatch.setattr(requests, "post", ok)
    assert web_refresh.ping(_Store("supabase")) is True
    assert seen == {"url": web_refresh.DEFAULT_URL, "auth": "Bearer " + "x" * 32}

    def down(*a, **k):
        raise requests.ConnectionError("끊김")

    monkeypatch.setattr(requests, "post", down)
    assert web_refresh.ping(_Store("supabase")) is False


def test_link_head_404_but_get_200_is_alive(monkeypatch):
    # 11/25 khgames.co.kr: HEAD 에만 404 를 주는 사이트를 '링크 확인 필요' 로 잘못 표시했다
    monkeypatch.setenv("ANIWHERE_LINKCHECK", "1")
    monkeypatch.setattr(requests, "head", lambda *a, **k: _Res(404))
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Res(200))
    assert links.check("https://example.com/a") is True


def test_link_really_gone_is_broken(monkeypatch):
    monkeypatch.setenv("ANIWHERE_LINKCHECK", "1")
    monkeypatch.setattr(requests, "head", lambda *a, **k: _Res(404))
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Res(404))
    assert links.check("https://example.com/a") is False
