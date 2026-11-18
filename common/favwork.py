"""스토리 줄 '내가 관심있는 작품' (11/18 요청, 리스트·지도 보기 맨 위).

처음엔 '최애 작품' 을 따로 저장했다가, 같은 날 요청으로 '팝업 북마크' 에서 작품을 뽑도록 바꿨고,
이어서 '내가 북마크한 팝업만' 보이도록 바꿨다 (따로 저장하는 표 없음 — 북마크 표 favorites 하나만 쓴다).
"""
from __future__ import annotations


def story_works(marked_rows: list[dict]) -> list[tuple[str, int]]:
    """[(작품, 내가 북마크한 그 작품의 팝업 수)]. 북마크한 팝업만 넘긴다 (진행 중·예정만). 먼저 나온 작품 순."""
    out: dict[str, int] = {}
    for r in marked_rows:
        w = str(r.get("work") or "").strip()
        if w:
            out[w] = out.get(w, 0) + 1
    return list(out.items())
