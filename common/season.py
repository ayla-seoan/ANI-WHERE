"""계절 배경 그림 (11/18 요청): 3~5월 꽃잎 · 6~8월 잎사귀 · 9~11월 단풍 · 12~2월 눈.

직접 그린 작은 SVG (애니메이션은 app_cafemap._season_fx). 다른 사이트 그림은 쓰지 않는다.
"""
from __future__ import annotations

import base64

_NS = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"'

# 11/18: 입체(3D) 그림을 그려 봤다가 사용자 요청으로 처음의 단순한 그림으로 되돌렸다
SVGS = {
    "spring": [f'<svg {_NS}><path d="M10 1C14 5 15 11 10 19C5 11 6 5 10 1Z" fill="#F7B6C8"/><path d="M10 4V16" stroke="#EE93AE" stroke-width=".8"/></svg>',
               f'<svg {_NS}><path d="M10 2C15 4 16 10 10 18C4 10 5 4 10 2Z" fill="#FBD3DE"/><path d="M8 2L10 5L12 2" fill="#fff"/></svg>'],
    "summer": [f'<svg {_NS}><path d="M3 17C3 8 9 3 18 2C17 11 12 17 3 17Z" fill="#7CCB8C"/><path d="M3 17L14 6" stroke="#4FA766" stroke-width="1"/></svg>',
               f'<svg {_NS}><path d="M3 17C3 8 9 3 18 2C17 11 12 17 3 17Z" fill="#A6DDA0"/><path d="M3 17L14 6" stroke="#6CBF6F" stroke-width="1"/></svg>'],
    "autumn": [f'<svg {_NS}><path d="M10 1L12 6L16 4L15 9L19 10L15 12L16 16L11 14L10 19L9 14L4 16L5 12L1 10L5 9L4 4L8 6Z" fill="#E0674A"/></svg>',
               f'<svg {_NS}><path d="M10 1L12 6L16 4L15 9L19 10L15 12L16 16L11 14L10 19L9 14L4 16L5 12L1 10L5 9L4 4L8 6Z" fill="#F2A541"/></svg>',
               f'<svg {_NS}><path d="M3 17C3 8 9 3 18 2C17 11 12 17 3 17Z" fill="#E9C46A"/><path d="M3 17L14 6" stroke="#C99A3A" stroke-width="1"/></svg>'],
    "winter": [f'<svg {_NS}><circle cx="10" cy="10" r="7" fill="#CFE3F2"/></svg>',
               f'<svg {_NS}><g stroke="#B9D6EC" stroke-width="1.6" stroke-linecap="round"><path d="M10 2V18M3 6L17 14M3 14L17 6"/></g></svg>'],
}


def season_of(month: int) -> str:
    """3~5월 봄 · 6~8월 여름 · 9~11월 가을 · 12~2월 겨울."""
    return {3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer", 8: "summer",
            9: "autumn", 10: "autumn", 11: "autumn"}.get(month, "winter")


def urls(season: str) -> list[str]:
    return ["data:image/svg+xml;base64," + base64.b64encode(s.encode()).decode() for s in SVGS[season]]
