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
def _works() -> list[dict]:
    if not PATH.exists():
        return []
    return json.loads(PATH.read_text(encoding="utf-8")).get("works", [])


def characters_by_work() -> dict[str, list[str]]:
    return {w["work"]: list(w.get("characters", [])) for w in _works()}


def work_aliases() -> dict[str, list[str]]:
    """작품 → 공지에서 찾을 이름들 (목록 이름, 괄호 안 다른 이름, 별칭). 간편등록이 쓴다."""
    out = {}
    for w in _works():
        name = w["work"]
        base = re.sub(r"\s*\(.*?\)\s*$", "", name)
        # '하이큐!!' 는 '하이큐' 로도 찾는다
        names = [name, base, re.sub(r"[!?！？]+$", "", base)]
        names += [p.strip() for p in re.findall(r"\((.*?)\)", name)]
        out[name] = list(dict.fromkeys(n for n in names + list(w.get("aliases", [])) if n))
    return out


def character_aliases(work: str) -> dict[str, str]:
    """그 작품의 캐릭터 이름(별칭 포함) → 목록의 이름. 간편등록이 공지에서 캐릭터를 찾을 때 쓴다."""
    w = next((x for x in _works() if x["work"] == work), None)
    if not w:
        return {}
    out = {c: c for c in w.get("characters", [])}
    for full, short in (w.get("character_aliases") or {}).items():
        out.update({s: full for s in short})
    return out


def _key(name: str) -> str:
    return re.sub(r"[\s!?·:]+", "", name).lower()


def canonical_work(name: str) -> str:
    """'귀멸의칼날' 처럼 띄어쓰기만 다른 이름을 목록의 이름으로 맞춘다. 없으면 그대로."""
    k = _key(name)
    return next((w for w in characters_by_work() if _key(w) == k), name.strip())
