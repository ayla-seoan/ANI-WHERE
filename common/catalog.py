"""작품 · 캐릭터 목록 (data/anime_catalog.json).

등록·수정 화면에서 작품을 고르면 그 작품의 캐릭터만 고를 수 있게 하는 데 쓴다.
목록에 없는 작품·캐릭터도 화면에서 새로 입력할 수 있으므로, 이 목록은 '추천'이지 제한이 아니다.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "anime_catalog.json"


@lru_cache(maxsize=1)
def characters_by_work() -> dict[str, list[str]]:
    if not PATH.exists():
        return {}
    data = json.loads(PATH.read_text(encoding="utf-8"))
    return {w["work"]: list(w.get("characters", [])) for w in data.get("works", [])}


def _key(name: str) -> str:
    return re.sub(r"[\s!?·:]+", "", name).lower()


def canonical_work(name: str) -> str:
    """'귀멸의칼날' 처럼 띄어쓰기만 다른 이름을 목록의 이름으로 맞춘다. 없으면 그대로."""
    k = _key(name)
    return next((w for w in characters_by_work() if _key(w) == k), name.strip())
