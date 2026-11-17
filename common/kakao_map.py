"""메인 지도를 Streamlit 에 붙이는 얇은 래퍼.

React 빌드 없이, components/kakao_map/index.html 을 그대로 띄운다.
네이버 지도 키가 있으면 네이버 지도, 아니면 KAKAO_JS_KEY 로 카카오맵, 둘 다 없거나 실패하면 Leaflet(OpenStreetMap) 으로 그린다. 둘 다 아시아 밖으로는 못 나간다.
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


def naver_key() -> str | None:
    """네이버 클라우드 Maps Client ID (Dynamic Map 사용). 있으면 네이버 지도를 먼저 쓴다.
    따로 NAVER_MAP_CLIENT_ID 를 두면 그것을, 없으면 주소 검색용 NAVER_MAPS_CLIENT_ID 를 같이 쓴다."""
    return os.getenv("NAVER_MAP_CLIENT_ID") or os.getenv("NAVER_MAPS_CLIENT_ID") or None


def kakao_map(points: list[dict], selected: str | None, height: int,
              key: str = "kakao_map", home: dict | None = None) -> dict | None:
    """카페 점을 지도에 찍고, 점을 누르면 {"id": entry_id, "at": 시각} 을 돌려준다.

    points: [{"id", "lat", "lng", "name", "tooltip"}]
    home: 처음 보여 줄 범위 {"south", "west", "north", "east"}. 없으면 포천~제주 전체.
    """
    return _component(app_key=js_key(), naver_key=naver_key(), points=points, selected=selected, height=height,
                      home=home, key=key, default=None)
