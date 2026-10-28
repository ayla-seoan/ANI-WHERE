"""상세 화면의 공유 버튼(카카오톡·인스타그램·링크 복사)을 Streamlit 에 붙이는 얇은 래퍼.

React 빌드 없이, components/share/index.html 을 그대로 띄운다.
공유 주소는 '?cafe=<카페 id>' 라서 받은 사람이 누르면 그 카페 상세가 바로 열린다.
카카오톡 카드 공유는 KAKAO_JS_KEY 가 있을 때만 되고, 없으면 기본 공유 창이나 링크 복사로 대신한다.
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit.components.v1 as components

_DIR = Path(__file__).resolve().parent.parent / "components" / "share"
_component = components.declare_component("share", path=str(_DIR))


def share_buttons(cafe_id: str, title: str, text: str, image: str, key: str = "share") -> None:
    _component(cafe_id=cafe_id, title=title, text=text, image=image,
               kakao_key=os.getenv("KAKAO_JS_KEY") or None, key=key, default=None)
