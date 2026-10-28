"""찜하기. 로그인이 없어서 리뷰 닉네임처럼 접속 IP 로 사람을 구분한다.

저장소는 append-only 라 찜/찜 해제도 새 행으로 쌓는다. entry_id 는 '사람:카페' 라서
같은 사람·같은 카페의 최신 행 status 가 active 면 찜한 상태, deleted 면 해제한 상태다.
"""
from __future__ import annotations

import hashlib
import os

HEADERS = ["row_id", "entry_id", "revision", "status", "updated_at", "cafe_id", "user"]


def user_key(ip: str | None) -> str:
    """IP 를 그대로 저장하지 않고 짧은 해시로 바꾼다. 로컬 접속(IP 없음)은 모두 같은 사람이 된다."""
    if not isinstance(ip, str):
        ip = None
    salt = os.getenv("REVIEW_NICK_SALT", "popup-cafe-map")
    return hashlib.sha256(f"{salt}:fav:{ip or 'local'}".encode()).hexdigest()[:16]


def mine(rows: list[dict], user: str) -> set[str]:
    """이 사람이 찜한 카페 id 들. rows 는 저장소의 current_rows() (해제된 건 이미 빠져 있다)."""
    return {str(r["cafe_id"]) for r in rows if str(r.get("user")) == user}


def counts(rows: list[dict]) -> dict[str, int]:
    """카페별 찜한 사람 수."""
    out: dict[str, int] = {}
    for r in rows:
        out[str(r["cafe_id"])] = out.get(str(r["cafe_id"]), 0) + 1
    return out


def toggle(store, cafe_id: str, user: str, on: bool) -> None:
    """찜하기(on=True) / 찜 해제(on=False). 지난 기록은 남기고 새 행을 쌓는다."""
    store.append({"cafe_id": str(cafe_id), "user": user}, entry_id=f"{user}:{cafe_id}",
                 status="active" if on else "deleted")
