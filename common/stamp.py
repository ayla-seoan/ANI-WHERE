"""후기 도장 랭크 (11/25 새 기능, docs/design/handoff/README.md 4절 · A-Rank 시안). 웹 web/lib/stamp.ts 와 같은 표 · 같은 규칙.

도장 수 = 내가 쓴 '다녀온 후기'가 있는 팝업 수.
  - 별점만 남긴 다녀온 후기도 1개, 같은 팝업은 여러 번 써도 1개
  - 기대평 · 답글, 지운 후기는 세지 않는다. 탈퇴한 회원은 도장이 없다
새 표를 만들지 않고 리뷰 기록(현재 행)에서 그때그때 센다. 이름 · 기준은 시안의 제안값이다.
"""
from __future__ import annotations

from dataclasses import dataclass

RATED_KIND = "다녀온 후기"


@dataclass(frozen=True)
class Tier:
    lv: int
    name: str
    en: str        # 96px 도장 둘레 글자
    need: int      # 이 랭크가 되는 도장 수
    ring: str      # 테두리
    fill: str      # 바탕
    fg: str        # 글자
    perk: str


TIERS = [
    Tier(1, "새싹 팬", "SPROUT", 1, "#5fbf9f", "#f0faf6", "#0f6b5c", "첫 후기 기념 도장 · 리뷰 닉네임 옆에 도장 표시"),
    Tier(2, "단골 팬", "REGULAR", 3, "#21b287", "#e9f7f2", "#0f6b5c", "도장이 진한 초록으로"),
    Tier(3, "성지순례러", "PILGRIM", 10, "#2c5bc5", "#eaf0fc", "#2c5bc5", "파란 도장"),
    Tier(4, "덕질 마스터", "MASTER", 25, "#7656c4", "#f1ecff", "#5b3fae", "보라 도장"),
    Tier(5, "전설의 덕후", "LEGEND", 50, "#c99a00", "#fff6d6", "#7a5a00", "금색 도장"),
]

RULES = [
    "별점만 남긴 다녀온 후기도 1개로 세요",
    "같은 팝업에는 도장 1개만 (여러 번 써도 1개)",
    "기대평 · 답글은 세지 않아요",
    "지운 후기, 관리자가 지운 후기는 빼고 세요",
    "탈퇴하면 도장도 함께 지워져요",
]


def tier_of(stamps: int) -> Tier | None:
    """도장 수 → 랭크. 0개면 None (아직 도장 없음)."""
    cur = None
    for t in TIERS:
        if stamps >= t.need:
            cur = t
    return cur


def next_tier(stamps: int) -> tuple[Tier, int] | None:
    """(다음 랭크, 남은 도장 수). 가장 높은 랭크면 None."""
    for t in TIERS:
        if stamps < t.need:
            return t, t.need - stamps
    return None


def _tag(nick: str) -> str:
    return nick.rsplit("#", 1)[1] if "#" in nick else ""


def counts(review_rows: list[dict]) -> dict[str, int]:
    """리뷰 현재 행들 → {글쓴이 꼬리표('m1a2b'): 도장 수}. 회원 글만 센다 (꼬리표가 'm' 으로 시작)."""
    seen: set[tuple[str, str]] = set()
    out: dict[str, int] = {}
    for r in review_rows:
        if str(r.get("parent_id") or "") or str(r.get("kind") or "") != RATED_KIND:
            continue
        if str(r.get("status") or "active") != "active":
            continue
        nick = str(r.get("nickname") or "")
        tag = _tag(nick)
        if not tag.startswith("m") or nick.startswith("탈퇴한 회원"):
            continue
        key = (tag, str(r.get("cafe_id") or ""))
        if key in seen:
            continue
        seen.add(key)
        out[tag] = out.get(tag, 0) + 1
    return out


def stamps_of(nick: str, table: dict[str, int]) -> int:
    """저장된 닉네임('닉네임#m1a2b') 의 도장 수."""
    return table.get(_tag(str(nick or "")), 0)


def lv_of(nick: str, table: dict[str, int]) -> int:
    """저장된 닉네임의 랭크 단계 (0 = 도장 없음)."""
    t = tier_of(stamps_of(nick, table))
    return t.lv if t else 0
