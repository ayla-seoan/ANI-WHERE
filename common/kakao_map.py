"""메인 지도를 Streamlit 에 붙이는 얇은 래퍼.

React 빌드 없이, components/kakao_map/index.html 을 그대로 띄운다.
KAKAO_JS_KEY 가 있으면 카카오맵, 없으면 Leaflet 밝은 지도로 그린다. 둘 다 아시아 밖으로는 못 나간다.
카카오맵은 카카오 개발자 콘솔 > 앱 > 플랫폼 > Web 에 http://localhost:8501 을 등록해야 뜬다.
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit.components.v1 as components

_DIR = Path(__file__).resolve().parent.parent / "components" / "kakao_map"
_component = components.declare_component("kakao_map", path=str(_DIR))


def js_key() -> str | None:
    return os.getenv("KAKAO_JS_KEY") or None


def kakao_map(points: list[dict], selected: str | None, height: int,
              key: str = "kakao_map") -> dict | None:
    """카페 점을 지도에 찍고, 점을 누르면 {"id": entry_id, "at": 시각} 을 돌려준다.

    points: [{"id", "lat", "lng", "name", "tooltip"}]
    """
    return _component(app_key=js_key(), points=points, selected=selected, height=height,
                      key=key, default=None)
