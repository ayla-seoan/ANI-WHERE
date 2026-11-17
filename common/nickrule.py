"""닉네임 규칙: 욕설·음란한 말·운영자 사칭은 닉네임으로 쓸 수 없다 (11/18).

띄어쓰기·특수문자·숫자를 끼워 넣어 피하는 경우(예: '시1발', 'ㅅ.ㅂ')도 잡도록, 비교하기 전에
한글·영문만 남기고 소문자로 바꾼다. 막을 말을 찾으면 여기 목록에 추가한다 (화면 문구는 auth.validate_nick).
"""
from __future__ import annotations

import re

# 욕설 · 비하
_ABUSE = [
    "시발", "씨발", "씨빨", "씨팔", "시팔", "쓰발", "ㅅㅂ", "ㅆㅂ", "ㅅㅃ", "ㅆㅃ",
    "병신", "븅신", "빙신", "ㅂㅅ", "ㅄ", "지랄", "ㅈㄹ", "좆", "존나", "졸라", "ㅈㄴ",
    "개새끼", "개새기", "개색기", "개색끼", "개세끼", "개쉐", "개같", "개년", "개놈", "ㄱㅅㄲ",
    "미친놈", "미친년", "미친새", "ㅁㅊ", "또라이", "똘아이", "닥쳐", "꺼져", "엿먹", "염병", "육시랄",
    "썅", "쌍년", "쌍놈", "썅년", "니미", "느금", "니애미", "니애비", "애미", "애비", "에미", "앰창", "엠창",
    "등신", "찐따", "틀딱", "한남충", "김치녀", "맘충", "급식충", "일베", "메갈",
    "fuck", "fuk", "shit", "bitch", "asshole", "bastard", "nigger", "nigga", "retard",
]
# 음란한 말
_SEXUAL = [
    "섹스", "쎅스", "섹드립", "보지", "자지", "꼬추", "고추먹", "딸딸이", "자위", "야동", "포르노",
    "강간", "성폭행", "윤간", "창녀", "창년", "걸레년", "매춘", "원조교제", "조건만남", "빨통", "젖꼭지",
    "가슴만지", "엉덩이만지", "발정", "음란", "변태", "몸캠", "노출증", "섹시녀",
    "sex", "porn", "pussy", "dick", "cock", "penis", "vagina", "boob", "nude", "hentai", "milf",
]
# 운영자 사칭
_RESERVED = ["관리자", "운영자", "운영진", "애니웨어", "aniwhere", "admin", "administrator", "운영팀", "고객센터"]

_ONLY = re.compile(r"[^0-9a-z가-힣ㄱ-ㅎㅏ-ㅣ]")


def normalize(text: str) -> str:
    """한글(자모 포함)·영문만 남기고 소문자로. 숫자·띄어쓰기·특수문자는 뺀다 ('시 1 발' → '시발')."""
    t = _ONLY.sub("", str(text or "").lower())
    return re.sub(r"[0-9]", "", t)


def problem(nick: str) -> str:
    """닉네임에 쓸 수 없는 말이 있으면 그 종류('욕설'·'음란'·'사칭'), 없으면 ''."""
    n = normalize(nick)
    if not n:
        return ""
    for kind, words in (("사칭", _RESERVED), ("음란", _SEXUAL), ("욕설", _ABUSE)):
        if any(w in n for w in words):
            return kind
    return ""


def same(a: str, b: str) -> bool:
    """중복 확인용 비교: 띄어쓰기·대소문자 차이는 같은 닉네임으로 본다."""
    key = lambda s: re.sub(r"\s+", "", str(s or "")).lower()
    return bool(key(a)) and key(a) == key(b)
