"""Storage.append_many (11/20): 한 번에 쌓아도 append 를 여러 번 한 것과 같은 번호 · 모양이어야 한다."""
import importlib

import pytest


@pytest.fixture()
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("ANIWHERE_DATA_DIR", str(tmp_path))
    from common import storage as mod
    mod = importlib.reload(mod)
    yield mod
    monkeypatch.undo()
    importlib.reload(mod)


def test_append_many_numbers_like_append(storage):
    st = storage.Storage(worksheet="blog_posts", headers=["row_id", "entry_id", "revision", "status", "updated_at",
                                                          "cafe_id", "link", "title"])
    st.append({"cafe_id": "c1", "link": "https://a", "title": "old"}, entry_id="c1:a")
    st.append({"cafe_id": "c1", "link": "https://a"}, entry_id="c1:a", status="deleted")
    out = st.append_many([({"cafe_id": "c1", "link": "https://a", "title": "again"}, "c1:a"),
                          ({"cafe_id": "c1", "link": "https://b", "title": "new"}, "c1:b")])
    assert [(r["entry_id"], r["revision"], r["status"]) for r in out] == [("c1:a", 3, "active"), ("c1:b", 1, "active")]
    rows = st.all_rows()
    assert len(rows) == 4 and len({r["row_id"] for r in rows}) == 4
    assert {r["entry_id"]: r["title"] for r in st.current_rows()} == {"c1:a": "again", "c1:b": "new"}
    assert st.append_many([]) == []


def test_append_many_cached_numbers(storage):
    st = storage.Storage(worksheet="blog_checks", headers=["row_id", "entry_id", "revision", "status", "updated_at",
                                                           "cafe_id", "day"])
    st.append({"cafe_id": "c1", "day": "2026-11-19"}, entry_id="c1:2026-11-19")
    out = st.append_many([({"cafe_id": "c1", "day": "2026-11-20"}, "c1:2026-11-20"),
                          ({"cafe_id": "c1", "day": "2026-11-19"}, "c1:2026-11-19")], fresh=False)
    assert [(r["entry_id"], r["revision"]) for r in out] == [("c1:2026-11-20", 1), ("c1:2026-11-19", 2)]
    assert len(st.all_rows()) == 3
