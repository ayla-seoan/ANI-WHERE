"""팝업 카페별 리뷰 게시판: 다녀온 후기·기대평과 그 아래 답글(대댓글).

저장은 카페와 같은 append-only 저장소를 쓰되 칸이 달라서 HEADERS 를 따로 둔다.
답글은 parent_id 로 원글에 매달고, 한 단계까지만 둔다 (답글에 단 답글도 같은 원글 아래로 모은다).
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from .guard import Validation, scan

HEADERS = [
    "row_id", "entry_id", "revision", "status", "updated_at",
    "cafe_id", "parent_id", "kind", "nickname", "body",
]

KINDS = ["다녀온 후기", "기대평", "기타"]
MAX_BODY = 1000
MAX_NICK = 20

# ------------------------------------------------------------ 자동 닉네임
# 접속 IP 마다 늘 같은 닉네임이 나오게 한다. IP 자체는 저장하지 않고 소금 친 해시만 쓴다.
_ADJ = ["졸린", "배고픈", "신난", "수줍은", "용감한", "느긋한", "반짝이는", "꼼꼼한",
        "엉뚱한", "다정한", "씩씩한", "조용한", "행복한", "부지런한", "말랑한", "새침한"]
_NOUN = ["고양이", "토끼", "펭귄", "여우", "수달", "다람쥐", "판다", "햄스터",
         "너구리", "부엉이", "강아지", "오리", "고슴도치", "알파카", "코알라", "돌고래"]


def nickname_for(ip: str | None) -> str:
    """'졸린 수달#a3f9' 처럼 IP 로 정해지는 닉네임. 로컬 접속(IP 없음)은 모두 같은 이름이 된다."""
    if not isinstance(ip, str):
        ip = None
    salt = os.getenv("REVIEW_NICK_SALT", "popup-cafe-map")
    h = hashlib.sha256(f"{salt}:{ip or 'local'}".encode()).hexdigest()
    return f"{_ADJ[int(h[0:4], 16) % len(_ADJ)]} {_NOUN[int(h[4:8], 16) % len(_NOUN)]}#{h[8:12]}"


def validate(body: str, nickname: str = "") -> Validation:
    v = Validation(ok=True)
    if not body.strip():
        v.fail("내용을 입력해 주세요.")
    if len(body) > MAX_BODY:
        v.fail(f"내용은 {MAX_BODY}자까지 쓸 수 있습니다.")
    if len(nickname) > MAX_NICK:
        v.fail(f"닉네임은 {MAX_NICK}자까지 쓸 수 있습니다.")
    kinds = sorted({f.kind for f in scan(f"{nickname} {body}")})
    if kinds:
        v.fail(f"민감한 개인정보({', '.join(kinds)})는 입력할 수 없습니다.")
    return v


def to_row(cafe_id: str, body: str, nickname: str = "", kind: str = "",
           parent_id: str = "") -> dict:
    return {
        "cafe_id": str(cafe_id),
        "parent_id": str(parent_id),
        "kind": "" if parent_id else (kind if kind in KINDS else KINDS[0]),
        "nickname": nickname.strip() or "익명",
        "body": body.strip(),
    }


@dataclass
class Thread:
    post: dict
    replies: list[dict] = field(default_factory=list)


def threads(rows: list[dict], cafe_id: str) -> list[Thread]:
    """한 카페의 리뷰를 원글 최신순, 답글은 오래된 순으로 묶는다."""
    mine = [r for r in rows if str(r.get("cafe_id")) == str(cafe_id)]
    by_id = {str(r["entry_id"]): r for r in mine}

    def root(r: dict) -> str:
        # 답글의 답글도 맨 위 원글로 올려 붙인다. 원글이 지워졌으면 답글도 숨긴다
        seen = set()
        while str(r.get("parent_id") or "") and str(r["entry_id"]) not in seen:
            seen.add(str(r["entry_id"]))
            r = by_id.get(str(r["parent_id"]), {})
            if not r:
                return ""
        return str(r.get("entry_id", ""))

    posts = {str(r["entry_id"]): Thread(r) for r in mine if not str(r.get("parent_id") or "")}
    for r in mine:
        if str(r.get("parent_id") or ""):
            top = posts.get(root(r))
            if top:
                top.replies.append(r)
    out = sorted(posts.values(), key=lambda t: str(t.post.get("updated_at")), reverse=True)
    for t in out:
        t.replies.sort(key=lambda r: str(r.get("updated_at")))
    return out


def counts(rows: list[dict]) -> dict[str, int]:
    """카페별 리뷰 수 (답글 포함). 카드 목록에 붙인다."""
    out: dict[str, int] = {}
    for r in rows:
        out[str(r.get("cafe_id"))] = out.get(str(r.get("cafe_id")), 0) + 1
    return out
