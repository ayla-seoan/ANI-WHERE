"""팝업 카페별 리뷰 게시판: 다녀온 후기·기대평과 그 아래 답글(대댓글).

저장은 카페와 같은 append-only 저장소를 쓰되 칸이 달라서 HEADERS 를 따로 둔다.
답글은 parent_id 로 원글에 매달고, 한 단계까지만 둔다 (답글에 단 답글도 같은 원글 아래로 모은다).
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from . import catalog
from .guard import Validation, scan

HEADERS = [
    "row_id", "entry_id", "revision", "status", "updated_at",
    "cafe_id", "parent_id", "kind", "nickname", "body",
    "rating",    # 다녀온 후기의 별점 1~5 (없으면 빈칸). 예전 칸 순서가 밀리지 않게 맨 끝에 둔다
    "images",    # 리뷰에 붙인 사진 파일 이름들 (쉼표로 이음, static/uploads/). 역시 맨 끝에 덧붙인다
]

MAX_IMAGES = 4       # 리뷰 한 건에 붙일 수 있는 사진 수
IMAGE_MB = 10        # 사진 한 장 최대 크기

KINDS = ["다녀온 후기", "기대평", "기타"]
RATED_KIND = "다녀온 후기"   # 별점을 고르는 종류


def stars(rating) -> str:
    """별점 숫자 → '★★★★☆'. 별점이 없거나 이상하면 빈 문자열."""
    try:
        n = int(rating)
    except (TypeError, ValueError):
        return ""
    return "★" * n + "☆" * (5 - n) if 1 <= n <= 5 else ""
MAX_BODY = 1000
MAX_NICK = 40      # 캐릭터 이름이 길 수 있다 ('반짝이는 소류 아스카 랑그레이#a3f9')

# ------------------------------------------------------------ 자동 닉네임
# 접속 IP 마다 늘 같은 닉네임이 나오게 한다. IP 자체는 저장하지 않고 소금 친 해시만 쓴다.
# '꾸벅꾸벅 조는 고죠 사토루#a3f9' 처럼 앞은 여러 꾸밈말 중 하나, 뒤는 작품 목록의 캐릭터 중 하나.
# 뒤의 #네 글자는 IP 로만 정해져서, 꾸밈말·캐릭터 목록이 바뀌어도 '내 글' 확인(can_delete)은 그대로 된다.
_ADJ = ["졸린", "배고픈", "신난", "수줍은", "용감한", "느긋한", "반짝이는", "꼼꼼한",
        "엉뚱한", "다정한", "씩씩한", "조용한", "행복한", "부지런한", "말랑한", "새침한",
        "꾸벅꾸벅 조는", "덕질하는", "굿즈 줍는", "줄 서는", "특전 노리는", "오픈런하는", "설레는", "두근두근",
        "방방 뛰는", "몰래 웃는", "커피 마시는", "산책하는", "노래하는", "춤추는", "길 잃은", "모험하는",
        "꿈꾸는", "반쯤 깬", "포근한", "까칠한", "쿨한", "수상한", "비밀스러운", "명랑한",
        "빛나는", "통통 튀는", "느릿느릿", "재빠른", "엉금엉금", "콧노래 부르는", "볼 빵빵한", "눈 반짝",
        "든든한", "귀여운", "멋쟁이", "낭만적인", "호기심 많은", "똑똑한", "덤벙대는", "늦잠 잔",
        "야식 먹는", "사진 찍는", "포카 모으는", "아크릴 든", "티켓 쥔", "응원하는", "기다리는", "웃음 많은"]
_NOUN_FALLBACK = ["고양이", "토끼", "펭귄", "여우", "수달", "다람쥐", "판다", "햄스터"]


def _characters() -> list[str]:
    """닉네임 뒤에 붙일 캐릭터 이름들 (작품 목록에서, 중복 없이 같은 순서로)."""
    names = sorted({n.strip() for v in catalog.characters_by_work().values() for n in v if n.strip()})
    return names or _NOUN_FALLBACK


def nickname_for(ip: str | None) -> str:
    """'꾸벅꾸벅 조는 고죠 사토루#a3f9' 처럼 IP 로 정해지는 닉네임. 로컬 접속(IP 없음)은 모두 같은 이름이 된다."""
    if not isinstance(ip, str):
        ip = None
    salt = os.getenv("REVIEW_NICK_SALT", "popup-cafe-map")
    h = hashlib.sha256(f"{salt}:{ip or 'local'}".encode()).hexdigest()
    names = _characters()
    return f"{_ADJ[int(h[12:20], 16) % len(_ADJ)]} {names[int(h[20:28], 16) % len(names)]}#{h[8:12]}"


def _tag(nickname: str) -> str:
    """닉네임 끝의 '#a3f9' (IP 로만 정해지는 부분). 없으면 닉네임 전체."""
    return nickname.rsplit("#", 1)[-1] if "#" in nickname else nickname


def validate(body: str, nickname: str = "", allow_empty: bool = False) -> Validation:
    """allow_empty: 다녀온 후기에 별점을 골랐으면 내용 없이도 등록할 수 있다."""
    v = Validation(ok=True)
    if not body.strip() and not allow_empty:
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
           parent_id: str = "", rating: int | None = None, images: list[str] | None = None) -> dict:
    kind = "" if parent_id else (kind if kind in KINDS else KINDS[0])
    # 별점은 다녀온 후기(원글)에만, 1~5 일 때만 남긴다
    ok = kind == RATED_KIND and isinstance(rating, int) and 1 <= rating <= 5
    return {
        "cafe_id": str(cafe_id),
        "parent_id": str(parent_id),
        "kind": kind,
        "nickname": nickname.strip() or "익명",
        "body": body.strip(),
        "rating": rating if ok else "",
        "images": ",".join(images or []),
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
    """카페별 리뷰 수 (답글 포함). 카드 목록에 붙인다.
    화면에 보이는 것만 센다 — 원글이 지워져 함께 숨겨진 답글은 빼고."""
    return {cafe: sum(1 + len(t.replies) for t in threads(rows, cafe))
            for cafe in {str(r.get("cafe_id")) for r in rows}}


def can_delete(row: dict, nickname: str) -> bool:
    """내가 쓴 글인지: 접속 IP 로 정해지는 '#네 글자' 가 같을 때만 고치고 지울 수 있다.
    (닉네임 앞부분 규칙이 바뀌기 전에 쓴 글도 그대로 내 글로 알아본다)"""
    return bool(nickname) and _tag(str(row.get("nickname") or "")) == _tag(nickname)
