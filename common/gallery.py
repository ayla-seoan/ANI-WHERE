"""상세 화면의 이미지 슬라이드를 Streamlit 에 붙이는 얇은 래퍼.

React 빌드 없이, components/gallery/index.html 을 그대로 띄운다.
몇 초마다 다음 이미지로 넘어가고, 좌우 버튼·점으로 넘겨 볼 수 있다. 이미지를 누르면 화면 전체로 크게 본다.
"""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_DIR = Path(__file__).resolve().parent.parent / "components" / "gallery"
_component = components.declare_component("gallery", path=str(_DIR))


def gallery(urls: list[str], height: int = 420, key: str = "gallery") -> None:
    """urls: 페이지 기준 이미지 주소들 (첫 번째가 포스터)."""
    _component(urls=urls, height=height, key=key, default=None)
