"""간편등록: 형식 없는 팝업·콜라보 공지문 → 등록 칸 값. AI 없이 정규식 + 사전 + 문장 패턴만 쓴다.

원칙 (규칙서 0장)
- 추측 금지: 확인이 안 되면 None. '미정' 같은 자리 채움 값을 만들지 않는다.
- 순서 무관: 공식 공지·커뮤니티 반말·트위터체 모두 같은 칸으로 모은다.
- 보수적: 애매하면 '검토대기'. 많이 뽑기보다 틀린 걸 안 뽑는다 (재현율보다 정밀도).

사전은 기존 것과 합쳐 쓴다.
- 작품·캐릭터 이름과 별칭: data/anime_catalog.json (catalog.work_aliases / character_aliases)
- 동네 → 지역('홍대' → '서울 마포구'): geo.DISTRICT_OF
- 이벤트 낱말: 이 파일의 EVENT_WORDS (Notion 가져오기도 같이 쓴다)
- 특전·굿즈 상품명: 이 파일의 ITEM_NOUNS (cafe 의 특전·굿즈 낱말 목록을 합친 것)
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from . import catalog, geo
from .cafe import _GOODS_WORDS, _PERK_WORDS, EVENT_TAGS, parse_links
from .guard import mask

# ================================================================ 2. 전처리
_ZERO_WIDTH = re.compile("[​-‍⁠﻿]")
_LAUGH = re.compile(r"[ㅋㅎㅠㅜ]{2,}")
# 이모지는 공백으로. ☆★(U+2605·2606)은 '마도카☆마기카' 같은 작품명에 쓰여서 남긴다
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-☄☇-➿⭐⭕️]")
_BULLET = re.compile(r"^[*\-•·▶▷►◆◇■□○●]\s*")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+|\n+")


def preprocess(raw: str) -> str:
    t = str(raw or "").replace("\r\n", "\n")
    t = _ZERO_WIDTH.sub("", t)
    t = _LAUGH.sub(" ", t)
    t = _EMOJI.sub(" ", t)
    return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in t.split("\n")).strip()


def _sentences(text: str) -> list[str]:
    """종결부호와 줄바꿈을 모두 문장 경계로. 불릿 한 줄 = 한 문장."""
    return [_BULLET.sub("", s).strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


# ================================================================ 10. 부정·불확실
_NEGATION = re.compile(r"안\s*(?:한대요|해요|합니다|함)|없(?:대요|어요|습니다|음)|미정|추후\s*공지|예정\s*없")
_UNCERTAIN = re.compile(
    r"같아요|같은데|인\s*것\s*같|라고\s*들었|듣긴\s*했|아시는\s*분|못\s*찾|"
    r"정확(?:한|히)\s*(?:위치|날짜|정보)?\s*(?:는|은)?\s*(?:아직|모름|몰라)"
)
UNCERTAIN_FACTOR = 0.3


# ================================================================ 6.1 운영시간 (날짜보다 먼저)
_TIME_RANGE = re.compile(r"\d{1,2}\s*:\s*\d{2}\s*[~\-–]\s*\d{1,2}\s*:\s*\d{2}")
_HOURS_LINE = re.compile(r"^[^\n]*(?:운영|영업|오픈)\s*시간\s*[:：]?[^\n]*$", re.M)


def _mask_hours(text: str) -> tuple[str, str | None]:
    """'10:30 ~ 20:30' 이 날짜 범위로 잡히지 않게 가린다. 운영시간 줄은 통째로 가린다."""
    hours = None
    for m in _HOURS_LINE.finditer(text):
        t = _TIME_RANGE.search(m.group())
        hours = hours or (re.sub(r"\s", "", t.group()) if t else
                          re.sub(r"^.*?시간\s*[:：]?\s*", "", m.group()).strip() or None)
    text = _HOURS_LINE.sub("§TIME§", text)

    def keep(m):
        nonlocal hours
        hours = hours or re.sub(r"\s", "", m.group())
        return "§TIME§"

    return _TIME_RANGE.sub(keep, text), hours


# ================================================================ 3. 작품명
_EVENT_WORD = r"(?:팝업\s*카페|콜라보\s*카페|콜라보레이션|콜라보|팝업\s*스토어|팝업|전시|페어)"
_TITLE_CANDIDATE = re.compile(rf"([가-힣A-Za-z0-9·:!?☆★×\s]{{2,25}}?)\s*{_EVENT_WORD}")
_TITLE_NOISE = re.compile(r"^(?:(?:헐|와|야|이번에|이번|드디어|기다리던|혹시|너|요즘|진짜|대박|곧)\s+)+")
_SHORT_CONTEXT = re.compile(r"^.{0,20}?(?:카페|콜라보|팝업|전시|굿즈)", re.S)


def _is_short(alias: str) -> bool:
    k = alias.replace(" ", "")
    return (k.isascii() and len(k) <= 3) or (not k.isascii() and len(k) <= 2)


def _alias_re(alias: str) -> re.Pattern:
    """띄어쓰기·대소문자를 가리지 않는 이름 패턴. 영문은 낱말 경계를 둔다 ('eva' 가 'evaluation' 에 걸리지 않게).

    짧은 한글 이름은 앞뒤가 다른 한글이면 안 된다 (작품 '카' 가 '카페' 안에서 잡히지 않게).
    뒤에 조사(이랑·의·가 …)는 붙어도 된다.
    """
    body = r"\s*".join(re.escape(c) for c in alias.replace(" ", ""))
    if alias.isascii():
        return re.compile(rf"(?<![A-Za-z]){body}(?![A-Za-z])", re.I)
    if _is_short(alias):
        return re.compile(rf"(?<![가-힣]){body}(?={_PARTICLE}(?![가-힣]))")
    return re.compile(body, re.I)


def _find_work(text: str) -> tuple[str | None, float, str]:
    """(작품명, 신뢰도, 찾은 근거 글). 사전 > 라벨 > 『』 > 'OO 콜라보' > 해시태그 순."""
    best = None
    for work, names in catalog.work_aliases().items():
        for a in names:
            for m in _alias_re(a).finditer(text):
                # '코난' 처럼 짧은 별칭은 20자 안에 카페·콜라보·팝업·전시·굿즈가 있을 때만
                if _is_short(a) and not _SHORT_CONTEXT.match(text[m.end():]):
                    continue
                if best is None or len(m.group()) > len(best[1]):
                    best = (work, m.group())
                break
    if best:
        return best[0], 1.0, best[1]
    m = re.search(r"^\s*(?:작품명?|IP)\s*[:：]\s*(.+)$", text, re.M)
    if m:
        return catalog.canonical_work(m.group(1).strip()[:40]), 0.9, m.group()
    m = re.search(r"[『「《〈]([^』」》〉\n]{2,40})[』」》〉]", text)
    if m:
        return catalog.canonical_work(m.group(1).strip()), 0.8, m.group()
    for s in _sentences(text):
        m = _TITLE_CANDIDATE.search(s)
        if not m:
            continue
        cand = re.split(r"[\]】』」)|]", m.group(1))[-1]
        cand = _TITLE_NOISE.sub("", cand.strip().lstrip("#[【").strip())
        cand = _strip_store(cand)
        if len(cand) >= 2 and not re.fullmatch(r"[\d\s]+", cand):
            return catalog.canonical_work(cand), 0.6, s
    tags = re.findall(r"#([^\s#]+)", text)
    for tag in tags:
        name = re.sub(rf"{_EVENT_WORD}$", "", tag.replace("_", " ")).strip()
        if len(name) >= 2:
            return catalog.canonical_work(name), 0.5, f"#{tag}"
    return None, 0.0, ""


# ================================================================ 4. 카페명
STORES = {
    "애니메이트 카페": ["애니메이트 카페", "애니메이트카페", "animate cafe"],
    "애니메이트": ["애니메이트", "animate"],
    "애니플러스": ["애니플러스", "aniplus"],
    "일러스타 카페": ["일러스타 카페", "일러스타카페"],
    "브이스퀘어": ["브이스퀘어", "v square"],
    "Gratte": ["gratte", "그라떼"],
    "JS스토어": ["js스토어", "제이에스스토어", "jsstore"],
}
_BRANCH = re.compile(r"(홍대|합정|서면|잠실\s*롯데|잠실|성수|신촌|건대입구|용산|강남|부산|대구|일산|수원)\s*(점|지점)?")
_VENUE = re.compile(
    r"((?:롯데월드몰|아이파크몰|현대백화점|신세계백화점|롯데백화점|AK\s*(?:&|플라자|PLAZA)\s*홍대|"
    r"더현대\s*서울|킨텍스|코엑스|에스팩토리|무신사\s*스토어|스타필드)"
    r"(?:\s*[가-힣]{1,6}점)?(?:\s*(?:유플렉스|[가-힣]{1,4}관))?)", re.I)
_FLOOR = re.compile(r"(지하\s*\d+\s*층|B\d+층?|\d{1,2}\s*층|\d{1,2}\s*F)(?![A-Za-z0-9])", re.I)
_GENERIC_VENUE = re.compile(r"(?:에\s*있는|쪽에?\s*있는)\s*(?:카페|매장|곳)")
# 매장 사전에 없는 '카페 모모', '브라운커피', '커피앤북 홍대점' 같은 고유 이름
_NAMED_CAFE = re.compile(
    r"(?<![가-힣A-Za-z])((?:카페|cafe)\s+[가-힣A-Za-z]{2,10}|[가-힣A-Za-z]{2,10}(?:카페|커피|cafe|coffee))"
    r"(?:\s+([가-힣A-Za-z0-9]{1,8}점))?", re.I)
_NOT_NAME = re.compile(r"^(?:콜라보|팝업|테마|이색|그|이|한|어떤|무슨|그런|이번|있는|근처)\s*(?:카페|cafe)|"
                       r"(?:콜라보|팝업|테마)(?:카페|cafe)$", re.I)


def _strip_store(text: str) -> str:
    for names in STORES.values():
        for a in names:
            text = _alias_re(a).sub("", text)
    return _BRANCH.sub("", text).strip(" ·-|")


def _label(text: str, labels: str) -> tuple[str, str] | None:
    """(라벨, 값) — '카페명: ...' 같은 줄."""
    m = re.search(rf"^\s*(?:[*\-•·]\s*)?({labels})\s*[:：]\s*(.+)$", text, re.M)
    return (m.group(1), m.group(2).strip()) if m else None


def _find_cafe(text: str, address: str | None) -> tuple[str | None, float, str]:
    lab = _label(text, r"카페명|카페|매장명?|장소|위치")
    if lab:
        kind, value = lab
        if value and not re.search(r"입력해주세요|확인 필요|미정", value):
            # '장소: 아이파크몰 6층 (서울 용산구 한강대로 23길 55)' → 주소·층·괄호를 빼고 남은 이름
            name = re.sub(r"\(.*?\)", "", value)
            name = _ROAD.sub("", name) if _ROAD.search(name) else name
            name = _FLOOR.sub("", name)
            name = re.sub(rf"^(?:{_PROV})\S*\s*", "", name).strip(" ,·-")
            name = re.sub(r"^[가-힣]{1,10}(?:시|군|구)\s+", "", name).strip(" ,·-")
            if name and not _GENERIC_VENUE.search(value):
                return mask(name[:40]), 1.0, value
    if _GENERIC_VENUE.search(text) and not any(_alias_re(a).search(text) for n in STORES.values() for a in n):
        # '연무장길 33에 있는 카페' — 고유한 이름이 없다
        return None, 0.0, ""
    for store, names in STORES.items():
        for a in names:
            m = _alias_re(a).search(text)
            if not m:
                continue
            near = text[max(0, m.start() - 12):m.start()] + " " + text[m.end():m.end() + 15]
            b = _BRANCH.search(text[m.end():m.end() + 15]) or _BRANCH.search(text[max(0, m.start() - 12):m.start()])
            name = store
            if b:
                branch = re.sub(r"\s+", "", b.group(1))
                name = f"{store} {branch}{b.group(2) or '점'}"
            return name, 0.9, near.strip()
    for s in _sentences(text):
        m = _VENUE.search(s)
        if m and not _GENERIC_VENUE.search(s[m.end():m.end() + 15]):
            return re.sub(r"\s+", " ", m.group(1)).strip(), 0.6, s
    for s in _sentences(text):
        if s.startswith("#"):
            continue
        for m in _NAMED_CAFE.finditer(s):
            name = m.group(1).strip()
            if _NOT_NAME.search(name) or _GENERIC_VENUE.search(s[m.end():m.end() + 10]):
                continue
            # '카페 홍대 쪽' 처럼 이름 자리에 동네 이름만 있으면 가게 이름이 아니다
            rest = re.sub(r"^(?:카페|cafe)\s+|(?:카페|커피|cafe|coffee)$", "", name, flags=re.I)
            if rest in geo.DISTRICT_OF or rest in geo.GAZETTEER or re.match(r"\s*쪽", s[m.end():]):
                continue
            if m.group(2):
                name = f"{name} {m.group(2)}"
            return mask(name[:40]), 0.6, s
    return None, 0.0, ""


# ================================================================ 5. 주소 / 지역
_PROV = "서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주"
_ROAD = re.compile(
    rf"((?:(?:{_PROV})[가-힣]*\s+)?(?:[가-힣]{{1,10}}(?:시|군|구)\s+){{0,2}})?"
    r"([가-힣]{1,8}동\s+)?"
    r"((?<!으)[가-힣A-Za-z0-9]{1,15}(?:대로|로|길)(?:\s*\d+(?:번)?길)?\s*\d+(?:-\d+)?)"
    r"(?!\s*(?:종|개|명|원|장|회|일|월|시|번째|%|가지|인|분|세))"
)
_LOT = re.compile(r"((?:(?:" + _PROV + r")[가-힣]*\s+)?[가-힣]{1,10}(?:시|군|구))\s*([가-힣]{1,10}동)\s*(\d+(?:-\d+)?)(?:번지)?")
_REGION_IN_ADDR = re.compile(rf"({_PROV})[가-힣]*\s+([가-힣]{{1,10}}(?:시|군|구))")


def _district_of_gu(gu: str) -> str | None:
    """'송파구' → '서울 송파구' (DISTRICT_OF 에 있는 구만)."""
    return next((v for v in geo.DISTRICT_OF.values() if v.endswith(" " + gu)), None)


def _find_area(text: str) -> str | None:
    """지역은 동네 이름에서 유추해도 된다 ('서울 홍대 쪽' → '서울 마포구')."""
    m = _REGION_IN_ADDR.search(text)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    hits = [(text.find(k), k) for k in geo.DISTRICT_OF if k in text]
    if hits:
        return geo.DISTRICT_OF[min(hits, key=lambda h: (h[0], -len(h[1])))[1]]
    m = re.search(r"([가-힣]{1,10}구)(?![가-힣])", text)
    if m and _district_of_gu(m.group(1)):
        return _district_of_gu(m.group(1))
    m = re.search(rf"(?<![가-힣])({_PROV})(?![가-힣])", text)
    return m.group(1) if m else None


def _find_address(text: str) -> tuple[str | None, float, str]:
    """도로명·지번 주소만 주소로 본다. 지역 이름만 있으면 주소는 None (유추하지 않는다)."""
    lab = _label(text, r"주소|위치|장소")
    sources = ([lab[1]] if lab else []) + _sentences(text)
    for i, s in enumerate(sources):
        conf = 1.0 if (lab and i == 0) else 0.9
        m = _ROAD.search(s)
        if m:
            prefix, dong, road = (m.group(1) or "").strip(), (m.group(2) or "").strip(), m.group(3)
            # 구·시가 없으면 동네로 구를 찾아 붙인다 ('서울 성수동 연무장길 33' → '서울 성동구 연무장길 33')
            if not re.search(r"(?:시|군|구)$", prefix):
                district = next((geo.DISTRICT_OF[k] for k in geo.DISTRICT_OF if k in f"{dong} {prefix}"), None)
                prefix = district or prefix
            elif not re.match(_PROV, prefix):
                prefix = _district_of_gu(prefix.split()[-1]) or prefix
            road = re.sub(r"\s+", " ", road)
            addr = f"{prefix} {road}".strip()
            # 건물명 + 층수를 뒤에 붙인다 ('… 한강대로 23길 55 아이파크몰 6층')
            venue, floor = _VENUE.search(s), _FLOOR.search(s)
            if venue and venue.group(1) not in addr:
                addr += " " + re.sub(r"\s+", " ", venue.group(1))
            if floor:
                addr += " " + re.sub(r"\s+", "", floor.group(1))
            return mask(addr[:80]), conf, s
        m = _LOT.search(s)
        if m:
            return mask(" ".join(m.groups())[:80]), conf, s
    return None, 0.0, ""


# ================================================================ 6. 기간
_WD = "월화수목금토일"
_WEEKDAY = re.compile(rf"(\d{{1,2}})\s*(?:월\s*|[/.]\s*)(\d{{1,2}})\s*일?\s*\(\s*([{_WD}])(?:요일)?\s*\)")
_SEP = r"(?:부터|~|-|–|〜)"
DATE_PATTERNS = [
    # P1: 2026년 11월 12일 ~ (2026년) 12월 6일
    ("ymd_kr", re.compile(rf"(\d{{4}})\s*년\s*(\d{{1,2}})\s*월\s*(\d{{1,2}})\s*일\s*{_SEP}+\s*"
                          rf"(?:(\d{{4}})\s*년\s*)?(?:(\d{{1,2}})\s*월\s*)?(\d{{1,2}})\s*일")),
    # P4: 2026.11.12 ~ 2026.12.06 / 2026-11-12 ~ 12-06
    ("ymd_dot", re.compile(rf"(\d{{4}})\s*[.\-/]\s*(\d{{1,2}})\s*[.\-/]\s*(\d{{1,2}})\.?\s*(?:{_SEP}|부터)\s*"
                           rf"(?:(\d{{4}})\s*[.\-/]\s*)?(\d{{1,2}})\s*[.\-/]\s*(\d{{1,2}})")),
    # P2: 11월 8일(부터|~) (11월) 30일(까지)
    ("md_kr", re.compile(rf"(\d{{1,2}})\s*월\s*(\d{{1,2}})\s*일?\s*{_SEP}\s*(?:(\d{{1,2}})\s*월\s*)?(\d{{1,2}})\s*일")),
    # P3: 11/3(부터|~) 11/23 · 11.1-7 · 11/1~15
    ("md_slash", re.compile(rf"(?<![\d.])(\d{{1,2}})\s*[/.]\s*(\d{{1,2}})\s*{_SEP}\s*(?:(\d{{1,2}})\s*[/.]\s*)?(\d{{1,2}})(?![\d:])")),
]
# P5: 날짜 하나 + 시작/끝 표현
_SINGLE = re.compile(r"(?:(\d{4})\s*년\s*)?(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*(부터|까지|시작|종료|오픈|마감)")
_SINGLE_LABELED = re.compile(r"^\s*(?:기간|일정|날짜|일시)\s*[:：]\s*(?:(\d{4})\s*[년.\-/]\s*)?(\d{1,2})\s*[월.\-/]\s*(\d{1,2})", re.M)
_TWO_ISO = re.compile(r"(20\d{2})[-.](\d{1,2})[-.](\d{1,2})")
_VAGUE = re.compile(r"\d{1,2}\s*월\s*(?:초순|중순|하순|중순경|말경|초|말|중)(?![가-힣])|\d{1,2}\s*월\s*경")


def _mkdate(y, m, d) -> date | None:
    try:
        return date(int(y), int(m), int(d))
    except (TypeError, ValueError):
        return None


def _fix_year(start: date, end: date | None, today: date) -> tuple[date, date | None]:
    """연도 없는 날짜 보정 (6.4)."""
    if end and end < start:
        end = _mkdate(end.year + 1, end.month, end.day)
    if start < today - timedelta(days=183):
        start, end = _mkdate(start.year + 1, start.month, start.day), end and _mkdate(end.year + 1, end.month, end.day)
    elif start > today + timedelta(days=365):
        start, end = _mkdate(start.year - 1, start.month, start.day), end and _mkdate(end.year - 1, end.month, end.day)
    return start, end


def _check_weekday(d: date | None, weekdays: dict, explicit_year: bool) -> tuple[date | None, bool]:
    """원문 요일과 대조 (6.5). 연도 없으면 올해·작년·내년 중 요일이 맞는 해로. 맞는 해가 없으면 (None, False)."""
    if d is None or (d.month, d.day) not in weekdays:
        return d, True
    want = _WD.index(weekdays[(d.month, d.day)])
    years = [d.year] if explicit_year else [d.year, d.year - 1, d.year + 1]
    for y in years:
        c = _mkdate(y, d.month, d.day)
        if c and c.weekday() == want:
            return c, True
    return None, False


def _find_dates(text: str, today: date) -> tuple[date | None, date | None, float, list[str]]:
    notes = []
    weekdays = {(int(m), int(d)): wd for m, d, wd in _WEEKDAY.findall(text)}
    plain = re.sub(rf"\s*\(\s*[{_WD}](?:요일)?\s*\)", "", text)
    start = end = None
    explicit = False
    for kind, pat in DATE_PATTERNS:
        m = pat.search(plain)
        if not m:
            continue
        g = m.groups()
        if kind in ("ymd_kr", "ymd_dot"):
            y1, m1, d1, y2, m2, d2 = g
            start, end, explicit = _mkdate(y1, m1, d1), _mkdate(y2 or y1, m2 or m1, d2), True
            if start and end and end < start and not y2:
                end = _mkdate(int(y1) + 1, m2 or m1, d2)
        else:
            m1, d1, m2, d2 = g
            start, end = _mkdate(today.year, m1, d1), _mkdate(today.year, m2 or m1, d2)
        break
    if start is None:
        isos = _TWO_ISO.findall(plain)
        if len(isos) >= 2:
            start, end, explicit = _mkdate(*isos[0]), _mkdate(*isos[1]), True
    if start is None:
        m = _SINGLE_LABELED.search(plain)
        if m:
            start = end = _mkdate(m.group(1) or today.year, m.group(2), m.group(3))
            explicit = bool(m.group(1))
    if start is None:
        # 날짜 하나만: '부터·시작·오픈' 이면 시작일, '까지·종료·마감' 이면 종료일
        for m in _SINGLE.finditer(plain):
            d = _mkdate(m.group(1) or today.year, m.group(2), m.group(3))
            explicit = explicit or bool(m.group(1))
            if m.group(4) in ("부터", "시작", "오픈"):
                start = start or d
            else:
                end = end or d
        if start or end:
            notes.append("기간의 시작이나 끝 중 하나만 있어요")
    if start is None and end is None:
        if _VAGUE.search(plain):
            notes.append("'11월 중순' 같은 흐릿한 기간은 날짜로 바꾸지 않았어요")
        else:
            notes.append("기간을 찾지 못했어요")
        return None, None, 0.0, notes
    if not explicit and start:
        start, end = _fix_year(start, end, today)
    start, ok1 = _check_weekday(start, weekdays, explicit)
    end, ok2 = _check_weekday(end, weekdays, explicit)
    if not (ok1 and ok2):
        notes.append("원문의 요일과 맞는 날짜가 없어요 (지난 행사일 수 있어요)")
        return None, None, 0.0, notes
    if start and end and end < start:
        notes.append("종료일이 시작일보다 빨라요")
        return None, None, 0.0, notes
    return start, end, (1.0 if start and end else 0.5), notes


# ================================================================ 7. 캐릭터
_CHAR_CONTEXT = re.compile(r"캐릭터|굿즈|메뉴|특전|등장|\d+\s*명|의\s*(?:특별|한정)|라떼|케이크|음료|드링크|디저트")
_PARTICLE = r"(?:랑|이랑|와|과|하고|의|가|이|는|은|도|를|을|짱|님|쨩)?"


def _find_characters(text: str, sentences: list[str], work: str | None, work_text: str) -> list[str]:
    lab = _label(text, r"캐릭터|등장\s*캐릭터|참여\s*캐릭터")
    names = catalog.character_aliases(work) if work else {}
    if lab:
        found = [c.strip() for c in re.split(r"[,/·、]|\s+(?:랑|와|과|하고)\s+", lab[1]) if c.strip()]
        found = [c for c in found if not re.search(r"확인 필요|입력해주세요|해당 없음", c)]
        return list(dict.fromkeys(names.get(c, c) for c in found))[:10]
    if not names:
        return []      # 작품 사전이 없으면 캐릭터를 추측하지 않는다 ('4명', '팬들' 같은 오탐 방지)
    out = []
    for s in sentences:
        if not _CHAR_CONTEXT.search(s):
            continue
        if work_text:
            s = s.replace(work_text, " ")          # '카드캡터 사쿠라' 의 '사쿠라' 는 캐릭터가 아니다
        hits = []
        for alias in sorted(names, key=len, reverse=True):
            for m in re.finditer(rf"(?<![가-힣A-Za-z]){re.escape(alias)}(?={_PARTICLE}(?:[^가-힣A-Za-z]|$))", s):
                if not any(a <= m.start() < b for a, b, _ in hits):
                    hits.append((m.start(), m.end(), names[alias]))
        out += [full for _, _, full in sorted(hits)]
    return list(dict.fromkeys(out))[:10]


# ================================================================ 8. 특전 vs 굿즈
_GIVE = re.compile(r"증정|제공|지급|드립니다|드려요|드림|준다|줍니다|준대|주는|받을\s*수\s*있|사은품|방문\s*혜택|선착순|특전")
_SELL = re.compile(r"판매|출시|발매|구매\s*가능|판대|나온다|나와요|나옵니다|라인업|팔아|판다|팝니다")
_CONDITION = re.compile(
    r"((?:음료|드링크|메뉴|디저트|한정\s*메뉴|콜라보\s*메뉴)\s*(?:1\s*잔\s*|1\s*개\s*)?(?:당\s*)?"
    r"(?:주문|구매|시키면|시키시면|주문하면|주문하시면|사면)\s*(?:시|하시면|하면)?|"
    r"(?:굿즈\s*)?\d+[만천]?\s*원\s*이상\s*(?:구매|결제)\s*(?:시|하면|하시면)?|방문\s*시|"
    r"(?:음료|드링크|메뉴|디저트|입장|방문)\s*특전)")
# 상품명: 규칙서 8.5 + 기존 특전·굿즈 낱말 목록을 합친 것 (긴 이름부터 맞춘다)
ITEM_NOUNS = sorted(set([
    "코스터", "포토카드", "엽서", "엽서 세트", "스티커", "포스터", "태피스트리", "미니 태피스트리",
    "아크릴 스탠드", "아크릴스탠드", "아크릴 키링", "키링", "캔뱃지", "뱃지", "badge", "인형", "쿠션",
    "마스킹테이프", "클리어파일", "머그컵", "틴케이스", "봉투", "카드",
] + _PERK_WORDS + _GOODS_WORDS), key=len, reverse=True)
_MODIFIER = r"(?:(?:랜덤|한정|특별|오리지널|캐릭터|일러스트|미니|콜라보|스페셜)\s*)*"
_CLAUSE_SPLIT = re.compile(r",\s*|，\s*|\s/\s|\s그리고\s|\s및\s|(?<=[가-힣])(?:하고|하며|이고|고|며)\s+")


def _items(clause: str) -> list[str]:
    taken, out = [], []
    for noun in ITEM_NOUNS:
        for m in re.finditer(_MODIFIER + re.escape(noun), clause, re.I):
            if any(a < m.end() and m.start() < b for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            out.append((m.start(), re.sub(r"\s+", " ", m.group()).strip()))
    return [t for _, t in sorted(out)]


def _condition(clause: str) -> str:
    m = _CONDITION.search(clause)
    if not m:
        return ""
    c = re.sub(r"\s+", " ", m.group()).strip()
    c = re.sub(r"(시키면|시키시면|주문하면|주문하시면|사면)$", "주문 시", c)
    c = re.sub(r"(주문|구매|결제)\s*(하면|하시면)$", r"\1 시", c)
    c = re.sub(r"(주문|구매|결제)$", r"\1 시", c)
    c = re.sub(r"1\s*잔\s*당?\s*|1\s*개\s*당?\s*|당\s+", "", c)
    return c


def _perks_goods(sentences: list[str]) -> tuple[list[str], list[str]]:
    perks, goods, given = [], [], set()
    sells = []
    for s in sentences:
        give, sell = bool(_GIVE.search(s)), bool(_SELL.search(s))
        clauses = [s] if give != sell else (_CLAUSE_SPLIT.split(s) if give and sell else [])
        for c in clauses:
            cg, cs = bool(_GIVE.search(c)), bool(_SELL.search(c))
            if give and sell and cg == cs:
                cg, cs = give and not sell, sell and not give      # 절로 못 나누면 문장 판단을 따른다
            if cg and not cs:
                # 한 문장에 조건이 여럿이면 쉼표로 나눠 조건마다 따로 ('메뉴 구매 시 …, 5만원 이상 구매 시 …')
                for part in _CLAUSE_SPLIT.split(c) if len(_CONDITION.findall(c)) > 1 else [c]:
                    its = _items(part)
                    if not its:
                        continue
                    given.update(i.split()[-1] for i in its)
                    cond = _condition(part) or _condition(s)
                    perks.append(f"{cond + ' ' if cond else ''}{', '.join(its)} 증정")
            elif cs and not cg:
                sells.append((c, give and sell))
    for c, mixed in sells:
        its = _items(c)
        # 증정으로 나온 상품은 굿즈에 다시 넣지 않는다 (같은 문장에 '판매' 가 따로 적힌 상품은 넣는다)
        its = [i for i in its if not (mixed and i.split()[-1] in given)]
        if not its:
            m = re.search(r"((?:캐릭터|한정|콜라보|오피셜|공식)\s*굿즈)", c)
            its = [re.sub(r"\s+", " ", m.group(1))] if m else []
        goods += its
    return list(dict.fromkeys(perks))[:10], list(dict.fromkeys(goods))[:10]


# ================================================================ 9. 이벤트
# 앱의 '이벤트 추가 정보' 항목(EVENT_TAGS) → 공지에서 찾을 낱말. Notion 가져오기도 같이 쓴다
EVENT_WORDS = {
    "사전 예약": ["사전 예약", "사전예약", "예약제", "예약 후 입장", "선예약", "예약 판매"],
    "럭키 드로우": ["럭키드로우", "럭키 드로우", "럭드"],
    "가챠": ["가챠", "캡슐"],
    "미성년자 입장불가": ["미성년자", "19세", "성인만"],
    "포토부스": ["포토부스", "포토 부스", "네컷", "인생네컷"],
    "스탬프 투어": ["스탬프"],
    "랜덤 특전": ["랜덤 특전"],
}
# 앱 항목에는 없는 체험·참여형 이벤트 (화면에 보여 주기만 한다)
OTHER_EVENTS = ["래플", "추첨", "이벤트 존", "포토존", "전시", "상영", "토크쇼"]


def event_tags(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", text)
    return [t for t in EVENT_TAGS if any(re.sub(r"\s+", "", w) in compact for w in EVENT_WORDS.get(t, [t]))]


# ================================================================ 11. 중복 판정
def _norm(s) -> str:
    s = re.sub(r"[\s·:!?~\-–()]", "", str(s or "").lower())
    return re.sub(r"(점|지점|카페|cafe)$", "", s)


def possible_duplicates(result: dict, rows: list[dict]) -> list[dict]:
    """작품 + 장소(카페명, 없으면 지역) + 기간이 모두 같은 앱의 행. 기간이 없으면 비교하지 않는다."""
    if not (result.get("work") and result.get("start_date") and result.get("end_date")):
        return []
    place = _norm(result.get("cafe_name") or result.get("area"))
    out = []
    for r in rows:
        same_place = place and (place == _norm(r.get("cafe_name")) or place in _norm(r.get("address")))
        if (_norm(r.get("work")) == _norm(result["work"]) and same_place
                and str(r.get("start_date"))[:10] == result["start_date"].isoformat()
                and str(r.get("end_date"))[:10] == result["end_date"].isoformat()):
            out.append(r)
    return out


# ================================================================ 14. 전체 순서
def parse_notice(raw_text: str, today: date | None = None) -> dict:
    """공지 한 건 → 등록 칸 값 + 신뢰도 + 상태('자동등록' | '검토대기') + 이유.

    여러 행사를 '---' 줄로 나눠 붙여넣으면 첫 번째만 읽는다 (빈 줄은 문단일 수 있어 나누지 않는다).
    """
    today = today or date.today()
    raw = re.split(r"\n\s*(?:-{3,}|={3,})\s*\n", str(raw_text or ""))[0]
    text = preprocess(raw)                                  # 1
    masked, hours = _mask_hours(text)                       # 2
    sentences = _sentences(masked)                          # 3
    usable = [s for s in sentences if not _NEGATION.search(s)]   # 4 부정 문장은 특전·굿즈·캐릭터·이벤트에서 뺀다
    uncertain = [s for s in sentences if _UNCERTAIN.search(s)]

    def conf(value: float, source: str) -> float:
        return round(value * UNCERTAIN_FACTOR, 2) if source and any(source in u or u in source for u in uncertain) else value

    work, c_work, work_src = _find_work(masked)                         # 5
    start, end, c_date, notes = _find_dates(masked, today)              # 6
    address, c_addr, addr_src = _find_address(masked)                   # 7
    area = _find_area(address or masked)
    cafe_name, c_cafe, cafe_src = _find_cafe(masked, address)           # 8
    characters = _find_characters(masked, usable, work, work_src)      # 9
    perk_lab, goods_lab = _label(masked, r"특전"), _label(masked, r"굿즈")
    rest = [s for s in usable if not re.match(r"^\s*(?:특전|굿즈)\s*[:：]", s)]
    perks, goods = _perks_goods(rest)                                   # 10, 11
    split = lambda v: [p.strip() for p in re.split(r"\s*[,/·、]\s*", v) if p.strip()
                       and not re.search(r"입력해주세요|확인 필요", p)]
    if perk_lab:
        perks = split(perk_lab[1]) or perks
    if goods_lab:
        goods = split(goods_lab[1]) or goods
    events_text = " ".join(usable)
    tags = event_tags(events_text)                                      # 12
    others = [e for e in OTHER_EVENTS if re.sub(r"\s+", "", e) in re.sub(r"\s+", "", events_text)]

    # 작품명은 사전과 맞으면 문장이 '~같아요' 여도 확실하다. 감점은 카페명·주소·기간에만 (규칙서 예시 5)
    confidence = {"작품명": c_work, "카페명": conf(c_cafe, cafe_src),
                  "주소": conf(c_addr, addr_src), "기간": c_date}
    if any(re.search(r"\d{1,2}\s*(?:월|/)", u) for u in uncertain):     # 날짜가 불확실한 문장에 있으면 감점
        confidence["기간"] = round(confidence["기간"] * UNCERTAIN_FACTOR, 2)
    reasons = list(notes)                                               # 14 판정
    if not work:
        reasons.append("작품명을 찾지 못했어요")
    elif confidence["작품명"] < 0.8:
        reasons.append("작품명이 목록에 없어 확인이 필요해요")
    if not (address or area):
        reasons.append("주소나 지역을 찾지 못했어요")
    if uncertain:
        reasons.append("'~같아요', '아시는 분' 같은 불확실한 표현이 있어요")
    ended = bool(end and end < today)
    if ended:
        reasons.append(f"이미 끝난 행사예요 ({start} ~ {end}). 요일로 연도를 맞췄다면 지난 공지일 수 있어요")
    auto = bool(work and confidence["작품명"] >= 0.8 and start and end and (address or area)
                and not uncertain and not ended)
    return {
        "work": work, "cafe_name": cafe_name, "address": address, "area": area,
        "start_date": start, "end_date": end,
        "characters": characters, "perks": perks, "goods": goods,
        "tags": tags, "events": others, "hours": hours,
        "links": parse_links(" ".join(re.findall(r"https?://\S+", raw)))[0],
        "confidence": confidence, "status": "자동등록" if auto else "검토대기",
        "reasons": list(dict.fromkeys(reasons)),
    }
