"""브라우저에서 내 위치(위도·경도)를 한 번 받아 오는 얇은 래퍼 + 가까운 지역 고르기.

React 빌드 없이 components/locate/index.html 을 높이 0 으로 띄운다.
위치는 화면에서 지역을 고르는 데만 쓰고 저장하지 않는다 (소수 셋째 자리까지만, 동네를 고를 만큼).
"""
from __future__ import annotations

import math
from pathlib import Path

import streamlit.components.v1 as components

_DIR = Path(__file__).resolve().parent.parent / "components" / "locate"
_component = components.declare_component("locate", path=str(_DIR))


def my_location(key: str = "my_loc") -> dict | None:
    """{'lat', 'lng'} / {'error': 'denied' 등} / 아직 답이 없으면 None."""
    return _component(key=key, default=None)


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """두 좌표 사이 거리(km). 지역 순서를 정하는 데만 쓰니 구면 근사로 충분하다."""
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 6371 * 2 * math.asin(math.sqrt(h))


def home_box(me: tuple[float, float], points: list[tuple[float, float]], k: int = 3) -> dict:
    """지도 처음 화면: 나를 가운데 두고 가장 가까운 팝업 k 곳이 들어오는 정사각 범위.
    너무 확대되거나(최소 약 3km) 너무 넓어지지(최대 약 40km) 않게 반경을 묶는다."""
    near = sorted(_km(me, p) for p in points)[:k]
    r_km = min(max((near[-1] if near else 5) * 1.15, 3.0), 40.0)
    dlat = r_km / 111.0
    dlng = r_km / (111.0 * max(math.cos(math.radians(me[0])), 0.2))
    return {"south": me[0] - dlat, "north": me[0] + dlat, "west": me[1] - dlng, "east": me[1] + dlng}


def areas_by_distance(me: tuple[float, float], points: list[tuple[str, float, float]]) -> list[str]:
    """지역 이름들을 내 위치에서 가까운 순으로. points 는 (지역, 위도, 경도) — 지역마다 카페들의 가운데를 잰다."""
    sums: dict[str, list[float]] = {}
    for area, lat, lng in points:
        s = sums.setdefault(area, [0.0, 0.0, 0])
        s[0] += lat
        s[1] += lng
        s[2] += 1
    centers = {a: (s[0] / s[2], s[1] / s[2]) for a, s in sums.items()}
    return sorted(centers, key=lambda a: _km(me, centers[a]))
