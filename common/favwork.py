"""내 최애 작품 (11/18 요청: 리스트 보기의 '요즘 일정 많은 작품' 스토리 줄 + '최애 추가').

회원마다 따로. 저장소는 append-only 라 고르기/빼기도 새 행으로 쌓는다.
entry_id 는 '사람:작품해시' 라서 같은 사람·같은 작품의 최신 행이 active 면 최애, deleted 면 뺀 상태다.
"""
from __future__ import annotations

import hashlib

HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at", "work", "user"]
MAX = 10          # 최애는 10개까지


def _eid(user: str, work: str) -> str:
    return f"{user}:{hashlib.sha1(work.encode()).hexdigest()[:12]}"


def mine(rows: list[dict], user: str) -> list[str]:
    """이 사람의 최애 작품 (먼저 고른 순). rows 는 current_rows() (뺀 건 이미 빠져 있다)."""
    got = [r for r in rows if str(r.get("user")) == user and str(r.get("work") or "").strip()]
    got.sort(key=lambda r: str(r.get("updated_at") or ""))
    return [str(r["work"]) for r in got]


def save(store, user: str, before: list[str], after: list[str]) -> None:
    """고른 목록을 저장한다. 새로 고른 건 active, 뺀 건 deleted 로 새 행을 쌓는다 (지난 기록은 남김)."""
    for w in [w for w in after if w not in before]:
        store.append({"work": w, "user": user}, entry_id=_eid(user, w), status="active")
    for w in [w for w in before if w not in after]:
        store.append({"work": w, "user": user}, entry_id=_eid(user, w), status="deleted")


def story_works(rows: list[dict], favs: list[str], limit: int = 12) -> list[tuple[str, int, bool]]:
    """스토리 줄에 놓을 작품 [(작품, 진행 중·예정 팝업 수, 내 최애인지)].
    내 최애가 맨 앞(고른 순), 그다음 팝업이 많은 작품 순. rows 는 진행 중·예정 팝업만 넘긴다."""
    count: dict[str, int] = {}
    for r in rows:
        w = str(r.get("work") or "").strip()
        if w:
            count[w] = count.get(w, 0) + 1
    out = [(w, count.get(w, 0), True) for w in favs]
    rest = sorted((w for w in count if w not in favs), key=lambda w: (-count[w], w))
    out += [(w, count[w], False) for w in rest]
    return out[:max(limit, len(favs))]
