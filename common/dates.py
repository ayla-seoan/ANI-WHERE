"""팝업 기간 표기 정리 (11/18, 평가표 '안정성').

들어오는 기간 표기가 섞여 있다: '11.20~12.5', '11/20 - 12/05', '2026.11.20(금) ~ 12.2', '12월 중', '상시'.
  - 시작~끝을 읽으면 그대로 쓴다 (kind='exact')
  - 끝이 없거나 '상시·상설·무기한' 이면 '상시' (kind='always') — 종료일 칸에는 ALWAYS_END 를 넣는다
  - '12월 중' 처럼 달만 있으면 그달 1일~말일로 두고 '기간 확인 필요' 표시 (kind='approx')
  - 아무것도 못 읽으면 버리지 않는다: 오늘~ALWAYS_END 로 두고 '기간 확인 필요' + 원문을 남긴다 (kind='unknown')

날짜 숫자 읽기는 간편등록과 같은 규칙(common/notice.py 의 _find_dates)을 쓴다.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

from . import notice

ALWAYS_END = date(2099, 12, 31)          # '상시' 팝업의 종료일 칸 값 (화면에는 '상시' 로 보인다)
TAG_ALWAYS = "상시"
TAG_CHECK = "기간 확인 필요"
RAW_MARK = "기간원문:"                    # note 칸 끝에 '| 기간원문:<원문>' 으로 남긴다

_ALWAYS_WORDS = re.compile(r"상시|상설|무기한|기한\s*없|종료\s*시\s*까지|별도\s*(?:공지|안내)\s*시\s*까지|소진\s*시\s*까지|오픈\s*런\s*상시")
_START_ONLY = re.compile(r"(?:(20\d{2})\s*[.\-/년]\s*)?(\d{1,2})\s*[./월]\s*(\d{1,2})\s*일?\s*(?:\([^)]*\))?\s*(?:~|부터|-)\s*$")
_MONTH_ONLY = re.compile(r"(?:(20\d{2})\s*[년.]\s*)?(\d{1,2})\s*월\s*(?:중|중순|초|초순|말|하순|경|내)?(?![\d일])")


@dataclass
class Period:
    start: date
    end: date
    kind: str          # exact | always | approx | unknown
    raw: str

    @property
    def tags(self) -> list[str]:
        if self.kind == "always":
            return [TAG_ALWAYS]
        if self.kind in ("approx", "unknown"):
            return [TAG_CHECK]
        return []


def parse_period(text: str, today: date) -> Period:
    """기간 원문 → Period. 어떤 경우에도 None 을 돌려주지 않는다 (읽지 못해도 버리지 않음)."""
    raw = " ".join(str(text or "").split())[:80]
    if not raw:
        return Period(today, ALWAYS_END, "unknown", "")
    start, end, _, _ = notice._find_dates(raw, today)
    if _ALWAYS_WORDS.search(raw):
        return Period(start or today, ALWAYS_END, "always", raw)
    if start and end:
        return Period(start, end, "exact", raw)
    if not start and not end:
        m = _START_ONLY.search(raw)                 # '11.20~' 처럼 끝이 비어 있음
        if m:
            d = notice._mkdate(m.group(1) or today.year, m.group(2), m.group(3))
            if d and not m.group(1):
                d, _ = notice._fix_year(d, None, today)
            if d:
                return Period(d, ALWAYS_END, "always", raw)
    if start and not end:                       # 시작만 있고 끝이 없음 → 상시
        return Period(start, ALWAYS_END, "always", raw)
    if end and not start:                       # 끝만 있음 → 오늘부터 그날까지, 확인 필요
        return Period(min(today, end), end, "approx", raw)
    m = _MONTH_ONLY.search(raw)
    if m:
        y = int(m.group(1)) if m.group(1) else today.year
        mon = int(m.group(2))
        if 1 <= mon <= 12:
            if not m.group(1) and date(y, mon, calendar.monthrange(y, mon)[1]) < today:
                y += 1                          # 연도 없이 지난 달이면 내년
            last = calendar.monthrange(y, mon)[1]
            return Period(date(y, mon, 1), date(y, mon, last), "approx", raw)
    return Period(today, ALWAYS_END, "unknown", raw)


def is_always(end) -> bool:
    try:
        return str(end)[:10] == ALWAYS_END.isoformat()
    except Exception:
        return False


def raw_from_note(note) -> str:
    """note 칸의 '| 기간원문:<원문>' 에서 원문만."""
    text = str(note or "")
    i = text.find(RAW_MARK)
    if i < 0:
        return ""
    return text[i + len(RAW_MARK):].split("|", 1)[0].strip()


def needs_check(tags) -> bool:
    return TAG_CHECK in [t.strip() for t in str(tags or "").split(",")] if not isinstance(tags, list) \
        else TAG_CHECK in tags
