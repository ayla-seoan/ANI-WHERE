"""카카오 우편번호 서비스를 Streamlit 에 붙이는 얇은 래퍼.

React 빌드 없이, components/kakao_postcode/index.html 을 그대로 띄운다. 키가 필요 없다.
우편번호 서비스는 좌표를 주지 않으므로, 고른 주소의 좌표는 geo.geocode() 로 따로 찾는다.
"""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_DIR = Path(__file__).resolve().parent.parent / "components" / "kakao_postcode"
_component = components.declare_component("kakao_postcode", path=str(_DIR))


def postcode(key: str) -> dict | None:
    """'우편번호로 주소 찾기' 버튼. 주소를 고르면
    {"address", "jibun", "building", "zonecode", "at"} 를 돌려준다."""
    return _component(key=key, default=None)
