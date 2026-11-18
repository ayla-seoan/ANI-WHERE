"""브라우저의 로그인 쿠키를 Streamlit 서버로 넘겨주는 얇은 래퍼 (components/cookie_bridge/index.html).

배포(Streamlit Community Cloud)에서는 앱 서버가 st.context.cookies 로 우리 쿠키를 받지 못해
새로고침 · 간편 로그인 뒤 원래 창에서 로그인이 풀렸다 (11/18). 화면에 아무것도 그리지 않는다.
"""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_DIR = Path(__file__).resolve().parent.parent / "components" / "cookie_bridge"
_component = components.declare_component("cookie_bridge", path=str(_DIR))

KEY = "_cookie_bridge"


def mount(name: str) -> None:
    """한 번 그릴 때마다 한 번만 부른다. 읽은 값은 st.session_state[KEY] 에 남는다."""
    _component(name=name, key=KEY, default=None)
