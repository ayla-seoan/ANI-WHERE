"""팝업 Q&A (RAG): 질문 → 앱 데이터에서 후보 찾기(검색) → 후보만 근거로 답 만들기(생성).

  1. retrieve()  — 질문에서 작품·캐릭터·지역·날짜 조건을 읽고, 팝업마다 점수를 매겨 상위 k 개를 고른다.
                   임베딩 대신 규칙 기반 검색을 쓴다: 데이터가 수백 건이고 질문이 '작품·지역·날짜' 조합이라
                   정확히 일치하는 쪽이 더 잘 맞고, 키 없이도 돈다.
  2. answer()    — 후보 목록만 프롬프트에 넣어 AI 가 답한다 (common/prompts/ask.v*.txt).
                   AI 가 후보에 없는 id 를 근거로 들면 지운다 (지어내기 방어).
                   AI 가 실패하면 규칙 기반 답(후보 목록 요약)으로 대체한다.

화면에 의존하지 않는다. scripts/eval_ask.py 가 같은 함수로 검색 정확도를 잰다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import ai, catalog, geo, guard, mycal
from .schema import AskAnswer

MAX_QUESTION = 200
TOP_K = 6

_WEEKDAYS = "월화수목금토일"


@dataclass
class Query:
    """질문에서 읽어 낸 조건."""

    works: list[str] = field(default_factory=list)
    characters: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)
    window: tuple[date, date] | None = None
    window_label: str = ""
    include_ended: bool = False
    words: list[str] = field(default_factory=list)

    def describe(self) -> str:
        parts = []
        if self.works:
            parts.append("작품 " + ", ".join(self.works))
        if self.characters:
            parts.append("캐릭터 " + ", ".join(self.characters))
        if self.places:
            parts.append("지역 " + ", ".join(self.places))
        if self.window_label:
            parts.append(self.window_label)
        return " · ".join(parts) or "조건 없음 (낱말로만 찾음)"


@dataclass
class Hit:
    row: dict
    score: float
    why: list[str]


@dataclass
class Answer:
    text: str
    hits: list[Hit]
    used_ids: list[str]
    source: str              # "ai" | "fallback" | "rule"
    badge: str
    query: Query
    dropped_ids: list[str] = field(default_factory=list)   # AI 가 지어낸 근거 id (지워짐)
    confidence: str = "high"
    error: str | None = None


# ------------------------------------------------------------- 입력 검사
def validate(question: str) -> list[str]:
    q = (question or "").strip()
    errors = []
    if not q:
        errors.append("질문을 입력해 주세요. 예: 이번 주말 성수에서 하는 팝업 있어?")
    elif len(q) < 2:
        errors.append("질문이 너무 짧아요. 작품 이름이나 지역을 함께 적어 주세요.")
    if len(q) > MAX_QUESTION:
        errors.append(f"질문은 {MAX_QUESTION}자까지 쓸 수 있어요. 지금 {len(q)}자예요.")
    if guard.scan(q):
        errors.append("전화번호·이메일 같은 개인정보는 질문에 넣지 말아 주세요. 가린 뒤에 찾아요.")
    return errors


# ------------------------------------------------------------- 조건 읽기
def _norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "")).lower()


def _window(q: str, today: date) -> tuple[tuple[date, date] | None, str]:
    wd = today.weekday()
    if "오늘" in q or "지금" in q:
        return (today, today), "오늘"
    if "내일" in q:
        d = today + timedelta(days=1)
        return (d, d), "내일"
    if "이번 주말" in q or "이번주말" in q or ("주말" in q and "다음" not in q):
        sat = today + timedelta(days=(5 - wd) % 7) if wd <= 5 else today
        sun = sat + timedelta(days=1) if sat.weekday() == 5 else sat
        return (sat, sun), "이번 주말"
    if "다음 주" in q or "다음주" in q:
        mon = today + timedelta(days=7 - wd)
        return (mon, mon + timedelta(days=6)), "다음 주"
    if "이번 주" in q or "이번주" in q:
        return (today, today + timedelta(days=6 - wd)), "이번 주"
    if "이번 달" in q or "이번달" in q:
        nxt = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        return (today, nxt - timedelta(days=1)), "이번 달"
    m = re.search(r"(\d{1,2})\s*월", q)
    if m and 1 <= int(m.group(1)) <= 12:
        mon = int(m.group(1))
        year = today.year if mon >= today.month - 6 else today.year + 1
        start = date(year, mon, 1)
        nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return (start, nxt - timedelta(days=1)), f"{mon}월"
    return None, ""


def parse(question: str, rows: list[dict], today: date) -> Query:
    q = question.strip()
    nq = _norm(q)
    query = Query()

    works = {str(r.get("work") or "").strip() for r in rows} | set(catalog.characters_by_work().keys())
    for w in sorted((w for w in works if w), key=len, reverse=True):
        nw = _norm(w)
        if len(nw) < 2 or nw in _STOP:
            continue          # '업'·'카' 같은 한 글자 이름은 질문 어디에나 걸린다
        if len(nw) == 2:
            hit = _word_at_start(w, q)       # '은혼'·'라바' 는 낱말 첫머리에 올 때만 ('은혼 팝업' O, '바라바' X)
        else:
            # 작품명 전체, 또는 4글자 이상 앞부분('주술회전' ← '주술회전 0')이 질문에 있으면 작품으로 본다
            hit = nw in nq or (len(nw) >= 4 and nw[:4] in nq)
        if hit and not any(_norm(x) in nw or nw in _norm(x) for x in query.works):
            query.works.append(w)

    chars = {c.strip() for r in rows for c in str(r.get("characters") or "").split(",") if c.strip()}
    for v in catalog.characters_by_work().values():
        chars |= {c.strip() for c in v if c.strip()}
    for c in sorted(chars, key=len, reverse=True):
        nc = _norm(c)
        if len(nc) < 2 or nc in _STOP or any(nc in _norm(x) for x in query.characters + query.works):
            continue
        if (nc in nq) if len(nc) > 2 else _word_at_start(c, q):
            query.characters.append(c)

    # 지역: 동네 사전(홍대·성수…) + 데이터에 나오는 시 이름
    places = set(geo.GAZETTEER) | {geo.city_name(str(r.get("address") or "")) for r in rows}
    for p in sorted((p for p in places if p and len(p) >= 2), key=len, reverse=True):
        if p in q and not any(p in x for x in query.places):
            query.places.append(p)

    query.window, query.window_label = _window(q, today)
    query.include_ended = any(w in q for w in ("지난", "끝난", "종료"))
    known = [_norm(x) for x in query.works + query.characters + query.places]
    words = []
    for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", q):
        base = _PARTICLE.sub("", w)          # '주에' → '주', '성수에서' → '성수'
        if len(base) < 2 or w in _STOP or base in _STOP or _DATE_WORD.fullmatch(w):
            continue
        if any(k and (k in _norm(w) or _norm(base) in k) for k in known):
            continue
        words.append(base)
    query.words = words
    return query


_STOP = {"팝업", "카페", "콜라보", "있어", "있나요", "있니", "어디", "어디서", "알려줘", "알려", "주세요", "근처",
         "에서", "하는", "해요", "해", "뭐", "뭐야", "언제", "이번", "다음", "주말", "오늘", "내일", "지금", "이번주",
         "다음주", "이번달", "지난", "끝난", "종료", "추천", "추천해줘", "가볼", "만한", "곳", "있는", "열리는",
         # 서술어: 조건이 아니라 말투라서 검색어로 쓰지 않는다 (eval v1 에서 '오늘 열려 있는 팝업' 0건으로 틀림)
         "열려", "열린", "열려있는", "시작", "시작하는", "시작해", "끝나는", "진행", "진행중", "진행중인", "중인",
         "보여줘", "보여", "보여줘요", "알려줄래", "나와", "나오는", "갈만한", "가고", "싶어"}
_PARTICLE = re.compile(r"(?:에서|에는|에|의|은|는|이|가|을|를|도|로|으로)$")
_DATE_WORD = re.compile(r"\d{1,2}월|\d{1,2}일|주말에?|이번주에?|이번달에?|다음주에?")


def _word_at_start(name: str, q: str) -> bool:
    """name 이 질문 속 낱말의 첫머리에 있는가 (뒤에 조사는 붙어도 된다)."""
    return bool(re.search(rf"(?<![가-힣A-Za-z0-9]){re.escape(name.strip())}", q))


def _place_match(place: str, row: dict) -> bool:
    addr = str(row.get("address") or "")
    if place in addr or place in str(row.get("cafe_name") or ""):
        return True
    if place in (geo.area_name(addr), geo.city_name(addr)):
        return True
    district = geo.DISTRICT_OF.get(place, "")       # '홍대' → '서울 마포구'
    return bool(district) and _norm(district) in _norm(addr)


# ------------------------------------------------------------- 검색
def _overlaps(row: dict, window: tuple[date, date]) -> bool:
    s, e = mycal._day(row.get("start_date")), mycal._day(row.get("end_date"))
    return bool(s and e and s <= window[1] and e >= window[0])


def retrieve(question: str, rows: list[dict], today: date, k: int = TOP_K) -> tuple[Query, list[Hit]]:
    query = parse(question, rows, today)
    hits: list[Hit] = []
    for r in rows:
        end = mycal._day(r.get("end_date"))
        if end and end < today and not query.include_ended:
            continue
        if query.window and not _overlaps(r, query.window):
            continue
        score, why = 0.0, []
        work = _norm(r.get("work"))
        if query.works:
            if any(_norm(w) in work or (work and work in _norm(w)) for w in query.works):
                score += 5; why.append("작품")
            else:
                continue          # 작품을 콕 집어 물었으면 다른 작품은 뺀다
        chars = _norm(r.get("characters"))
        if query.characters:
            if any(_norm(c) in chars or _norm(c) in _norm(r.get("intro")) for c in query.characters):
                score += 4; why.append("캐릭터")
            elif not query.works:
                continue          # 캐릭터만 콕 집어 물었으면 그 캐릭터가 없는 팝업은 뺀다
        if query.places:
            if any(_place_match(p, r) for p in query.places):
                score += 3; why.append("지역")
            else:
                continue
        if query.window:
            score += 2; why.append(query.window_label)
        text = _norm(" ".join(str(r.get(c) or "") for c in
                              ("work", "characters", "cafe_name", "intro", "perks", "goods", "tags")))
        extra = sum(1 for w in query.words if _norm(w) in text)
        if extra:
            score += min(extra, 3) * 0.5; why.append("낱말")
        elif query.words and not (query.works or query.characters):
            # 작품·캐릭터로 읽히지 않은 낱말('치이카와')이 있는데 어디에도 없으면, 날짜·지역만 맞는 팝업을 내밀지 않는다
            continue
        if score == 0:
            continue
        # 같은 점수면 오늘 열려 있는 것 → 곧 시작하는 것 순
        s = mycal._day(r.get("start_date")) or today
        live = 0.3 if s <= today <= (end or today) else 0.0
        hits.append(Hit(r, score + live, why))
    hits.sort(key=lambda h: (-h.score, str(h.row.get("start_date") or "")))
    return query, hits[:k]


# ------------------------------------------------------------- 답 만들기
def _card(r: dict, today: date) -> str:
    s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
    state = "종료" if e and e < today else "예정" if s and s > today else "진행 중"
    intro = guard.mask(str(r.get("intro") or ""))[:160].replace("\n", " ")
    return (f'- id: {r.get("entry_id")} | {r.get("work")} · {r.get("cafe_name")} | '
            f'{r.get("start_date")} ~ {r.get("end_date")} ({state}) | {geo.area_name(str(r.get("address") or ""))} '
            f'{guard.mask(str(r.get("address") or ""))} | 특전: {r.get("perks") or "-"} | 소개: {intro or "-"}')


def _rule_answer(query: Query, hits: list[Hit], today: date) -> AskAnswer:
    if not hits:
        return AskAnswer(answer="조건에 맞는 팝업을 찾지 못했어요.", used_ids=[], confidence="low")
    lines = []
    for h in hits[:3]:
        r = h.row
        lines.append(f'{r.get("work")} · {r.get("cafe_name")} ({r.get("start_date")} ~ {r.get("end_date")}, '
                     f'{geo.area_name(str(r.get("address") or "")) or "지역 미상"})')
    head = f"{query.describe()} 조건으로 {len(hits)}곳을 찾았어요."
    return AskAnswer(answer=head + " " + " / ".join(lines), used_ids=[str(h.row.get("entry_id")) for h in hits[:3]],
                     confidence="high")


def answer(question: str, rows: list[dict], today: date, version: str | None = None) -> Answer:
    question = guard.mask(question.strip())[:MAX_QUESTION]
    query, hits = retrieve(question, rows, today)
    if not hits:
        return Answer(text="", hits=[], used_ids=[], source="rule", badge="규칙 기반 대체", query=query,
                      confidence="low")
    week = _WEEKDAYS[today.weekday()]
    content = (f"질문: {question}\n오늘: {today.isoformat()} ({week})\n"
               f"질문에서 읽은 조건: {query.describe()}\n\n[후보 팝업]\n" +
               "\n".join(_card(h.row, today) for h in hits))
    res = ai.call_structured("ask", content, AskAnswer, fallback=lambda: _rule_answer(query, hits, today),
                             version=version)
    data: AskAnswer = res.data if res.ok else _rule_answer(query, hits, today)
    allowed = {str(h.row.get("entry_id")) for h in hits}
    used = [i for i in data.used_ids if i in allowed]
    dropped = [i for i in data.used_ids if i not in allowed]
    return Answer(text=guard.mask(data.answer), hits=hits, used_ids=used,
                  source=res.source if res.ok else "fallback", badge=res.badge if res.ok else "규칙 기반 대체",
                  query=query, dropped_ids=dropped, confidence=data.confidence, error=res.error)
