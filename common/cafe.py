"""주제 2 전용 로직: 공지 원문 → 팝업 카페 정보, 그리고 규칙 기반 대체 경로."""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

from .catalog import canonical_work
from .geo import GAZETTEER
from .guard import mask
from .schema import CafeEntry, CafeExtraction

# ------------------------------------------------------------------ 날짜
# 공지에 실제로 쓰이는 표기: 11/1~12/15, 11.1-7, 11월 1일 ~ 11월 7일, 2026-11-01
_RANGE_SLASH = re.compile(r"(\d{1,2})\s*[/.]\s*(\d{1,2})\s*[~\-–]\s*(?:(\d{1,2})\s*[/.]\s*)?(\d{1,2})")
_RANGE_KR = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일?\s*[~\-–]\s*(?:(\d{1,2})\s*월\s*)?(\d{1,2})\s*일")
_SINGLE_KR = re.compile(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일")
# "11월 8일부터 11월 14일까지" 처럼 ~ 없이 쓰는 표기
_RANGE_BUTEO = re.compile(
    r"(\d{1,2})\s*월\s*(\d{1,2})\s*일?\s*부터\s*(?:(\d{1,2})\s*월\s*)?(\d{1,2})\s*일?\s*까지"
)
_ISO = re.compile(r"(20\d{2})[-.](\d{1,2})[-.](\d{1,2})")


def parse_dates(text: str, today: date | None = None) -> tuple[date | None, date | None]:
    """본문에서 시작일과 종료일을 뽑는다. 못 찾으면 (None, None)."""
    today = today or date.today()
    year = today.year

    iso = _ISO.findall(text)
    if len(iso) >= 2:
        return _safe(int(iso[0][0]), int(iso[0][1]), int(iso[0][2])), \
               _safe(int(iso[1][0]), int(iso[1][1]), int(iso[1][2]))
    if len(iso) == 1:
        d = _safe(int(iso[0][0]), int(iso[0][1]), int(iso[0][2]))
        return d, d

    for pattern in (_RANGE_BUTEO, _RANGE_KR, _RANGE_SLASH):
        m = pattern.search(text)
        if m:
            m1, d1, m2, d2 = m.groups()
            start = _safe(year, int(m1), int(d1))
            end = _safe(year, int(m2 or m1), int(d2))
            return start, end

    m = _SINGLE_KR.search(text)
    if m:
        d = _safe(year, int(m.group(1)), int(m.group(2)))
        return d, d
    return None, None


def _safe(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


# ------------------------------------------------------------------ 주소
_LABEL = re.compile(r"^\s*(주소|위치|장소)\s*[:：]\s*")
# 지역 이름 뒤에 붙는 꼬리를 주소로 본다 ("마포구 연남동 227-15", "서면 카페 모모")
_TAIL = re.compile(r"[^\n]{0,40}")


def parse_address(text: str) -> str:
    """지역 사전에 있는 이름이 들어간 줄을 찾아 그 지점부터 주소로 본다.

    정규식만으로 한국 주소를 잡으면 "슬로건 판매합니다" 같은 문장도 주소로
    걸린다. 지도에 올릴 수 있는 지역 이름이 실제로 있는지를 먼저 본다.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # 1) "주소:" 라벨이 붙은 줄이 가장 확실하다
    for line in lines:
        if _LABEL.match(line):
            return _LABEL.sub("", line).strip()[:60]

    # 2) 지역 이름이 들어간 줄. 긴 이름부터 맞춘다
    names = sorted(GAZETTEER, key=len, reverse=True)
    for line in lines:
        if line.startswith("#") or _looks_like_date(line):
            continue
        for name in names:
            idx = line.find(name)
            if idx >= 0:
                return line[idx:][:60].strip()

    # 3) "OO역", "OO동" 으로 끝나는 두 글자 이상 토큰
    m = re.search(r"[가-힣]{2,}(?:동|로|길|역|가)\b[^\n,·]{0,24}", text)
    return m.group().strip()[:60] if m else ""


def _looks_like_date(line: str) -> bool:
    return bool(re.fullmatch(r"[\d\s/.~\-–월일부터까지년]+", line.strip()))


# ------------------------------------------------------- 카페명 · 특전 · 굿즈
_PERK_WORDS = ["포토카드", "포카", "코스터", "컵홀더", "엽서", "스티커", "클리어파일",
               "랜덤 카드", "일러스트 카드", "포스터", "브로마이드", "티켓"]
_GOODS_WORDS = ["아크릴 스탠드", "아크릴 키링", "캔뱃지", "캔배지", "키링", "인형", "피규어",
                "머그", "에코백", "쿠션", "담요", "파우치", "블라인드"]


_CAFE_WORDS = ("카페", "커피", "coffee", "cafe")


def parse_cafe_name(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # 1) 라벨이 붙은 줄
    for line in lines:
        m = re.match(r"\s*(?:카페명|카페|장소)\s*[:：]\s*(.+)", line)
        if m:
            return m.group(1).strip()[:40]

    # 2) '카페'/'커피' 가 들어간 줄에서 그 단어부터 끝까지
    for line in lines:
        if _looks_like_date(line):
            continue
        low = line.lower()
        for word in _CAFE_WORDS:
            idx = low.find(word)
            if idx < 0:
                continue
            # '콜라보 카페', '팝업 카페' 는 가게 이름이 아니다
            if re.search(r"(콜라보|팝업|테마)\s*$", line[:idx]):
                continue
            return line[idx:].strip()[:40]

    # 3) 해시태그·날짜가 아닌 첫 줄
    for line in lines:
        if not line.startswith("#") and not _looks_like_date(line):
            return re.sub(r"[\[\]【】]", "", line)[:40]
    return ""


def _find_words(text: str, words: list[str]) -> list[str]:
    hits = [w for w in words if w in text]
    # '아크릴 키링' 을 찾았으면 '키링' 은 따로 세지 않는다
    return [w for w in hits if not any(w != o and w in o for o in hits)]


_EVENT_WORDS = r"(?:콜라보\s*카페|콜라보|팝업\s*카페|팝업\s*스토어|팝업|테마\s*카페)"


def parse_work(text: str) -> str:
    """작품명. 라벨 → 『』 괄호 → 'OO 콜라보/팝업' → 첫 해시태그 순으로 본다."""
    m = re.search(r"^\s*작품\s*[:：]\s*(.+)$", text, re.M)
    if m:
        return m.group(1).strip()[:40]
    m = re.search(r"[『「《〈]([^』」》〉\n]+)[』」》〉]", text)
    if m:
        return m.group(1).strip()[:40]
    m = re.search(rf"#?([가-힣A-Za-z0-9 :!?]+?)\s*{_EVENT_WORDS}", text)
    if m and m.group(1).strip():
        return m.group(1).strip().lstrip("[【").strip()[:40]
    tags = re.findall(r"#([가-힣A-Za-z0-9_]+)", text)
    return tags[0].replace("_", " ") if tags else ""


def parse_characters(text: str) -> list[str]:
    """캐릭터는 라벨이 붙은 줄에서만 뽑는다. 이름 사전 없이 추측하면 틀린 값이 들어간다."""
    m = re.search(r"^\s*(?:캐릭터|등장\s*캐릭터|참여\s*캐릭터)\s*[:：]\s*(.+)$", text, re.M)
    if not m:
        return []
    return [c.strip() for c in re.split(r"[,/·、]", m.group(1)) if c.strip()][:10]


def rule_based(raw_text: str, today: date | None = None) -> CafeExtraction:
    """AI 가 실패했을 때 쓰는 대체 경로.

    정규식으로 날짜와 주소만 뽑고 나머지는 비워 둔다.
    사람이 확인 단계에서 채우게 하는 것이 틀린 값을 저장하는 것보다 낫다.
    """
    today = today or date.today()
    entries: list[CafeEntry] = []

    for block in _split_blocks(raw_text):
        start, end = parse_dates(block, today)
        if start is None:
            start = end = today
        if end is None:
            end = start
        entries.append(CafeEntry(
            cafe_name=mask(parse_cafe_name(block)) or "(이름 확인 필요)",
            work=canonical_work(parse_work(block)) or "(확인 필요)",
            characters=parse_characters(block),
            address=mask(parse_address(block)),
            start_date=start,
            end_date=end,
            perks=_find_words(block, _PERK_WORDS),
            goods=_find_words(block, _GOODS_WORDS),
            confidence="low",     # 규칙 기반은 항상 사람 확인이 필요하다
        ))
    return CafeExtraction(entries=entries)


def _split_blocks(raw_text: str) -> list[str]:
    """빈 줄 두 개 또는 --- 로 구분된 트윗 여러 건을 나눈다."""
    blocks = [b.strip() for b in re.split(r"\n\s*(?:---+|===+)\s*\n|\n{2,}", raw_text) if b.strip()]
    return blocks or ([raw_text.strip()] if raw_text.strip() else [])


def build_user_content(raw_text: str, today: date | None = None) -> str:
    today = today or date.today()
    return (
        f"오늘 날짜는 {today.isoformat()} 이다. 연도가 없는 날짜는 올해로 본다.\n"
        f"아래는 애니메이션 캐릭터 팝업 카페 공지 글이다. 여러 건이 섞여 있을 수 있다.\n\n"
        f"{mask(raw_text)}"
    )


# ------------------------------------------------------------------ 변환
# 등록 화면의 '이벤트 추가 정보' 체크 항목
EVENT_TAGS = ["사전 예약", "럭키 드로우", "가챠", "미성년자 입장불가", "포토부스", "스탬프 투어", "랜덤 특전"]


MAX_LINKS = 5


def parse_links(text: str) -> tuple[list[str], list[str]]:
    """참고 웹사이트 입력 → (쓸 수 있는 주소들, 잘못된 값들). 줄바꿈·공백·쉼표로 나눈다."""
    good, bad = [], []
    for part in re.split(r"[\s,]+", str(text or "").strip()):
        if not part:
            continue
        if re.fullmatch(r"https?://[^\s/$.?#][^\s]*", part, flags=re.I):
            if part not in good:
                good.append(part)
        else:
            bad.append(part)
    return good, bad


def entry_to_row(entry: CafeEntry, lat: float | None, lng: float | None,
                 source: str = "", note: str = "",
                 images: list[str] | None = None, tags: list[str] | None = None,
                 links: list[str] | None = None) -> dict:
    return {
        "links": " ".join((links or [])[:MAX_LINKS]),
        "images": ", ".join(images or []),
        "tags": ", ".join(t for t in (tags or []) if t in EVENT_TAGS),
        "cafe_name": entry.cafe_name,
        "work": entry.work,
        "characters": ", ".join(entry.characters),
        "address": entry.address,
        "lat": "" if lat is None else round(lat, 6),
        "lng": "" if lng is None else round(lng, 6),
        "start_date": entry.start_date.isoformat(),
        "end_date": entry.end_date.isoformat(),
        "perks": ", ".join(entry.perks),
        "goods": ", ".join(entry.goods),
        "source": source[:200],
        "note": note[:200],
    }


def rows_to_frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # 나중에 생긴 칸(images·tags 등)은 옛 행에 없어서 NaN 이 된다. 화면에 'nan' 이 뜨지 않게 빈 글자로 둔다
    for col in ("characters", "address", "perks", "goods", "images", "tags", "links", "note", "source"):
        df[col] = df[col].fillna("").astype(str) if col in df else ""
    for col in ("lat", "lng"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    for col in ("start_date", "end_date"):
        df[col] = pd.to_datetime(df.get(col), errors="coerce").dt.date
    return df


def expire_ended(store, today: date) -> list[str]:
    """종료일이 지난 카페를 지도에서 내린다 (append-only: 지우지 않고 '내림' 기록을 쌓는다).

    내린 카페 이름들을 돌려준다. 이미 내린 카페는 current_rows 에 없으니 다시 건드리지 않는다.
    """
    done = []
    for r in store.current_rows():
        try:
            end = date.fromisoformat(str(r.get("end_date") or "")[:10])
        except ValueError:
            continue
        if end < today:
            store.soft_delete(str(r["entry_id"]))
            done.append(str(r.get("cafe_name") or ""))
    return done
