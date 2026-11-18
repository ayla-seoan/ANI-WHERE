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
    intent: str = ""

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
    distances: dict = field(default_factory=dict)    # near 의도: cafe_id → km
    summary: str = ""                                 # by_region 의도: '서울 41곳 · 부산 7곳 …'
    total: int = 0                                    # 조건에 모두 맞는 팝업 수 (카드는 일부만 보여 줌)
    links: list = field(default_factory=list)         # 답 아래 바로가기 [(글자, 주소)] — 사용법 안내 등 (11/18)
    all_ids: list = field(default_factory=list)       # 조건에 모두 맞는 팝업 번호 전부 (카드는 5건까지, 나머지는 '더보기' → 리스트, 11/19)


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
    if "오늘" in q or "지금" in q or "현재" in q or re.search(r"진행\s*중|진행하는|하고\s*있는|열려\s*있는", q):
        return (today, today), "오늘(진행 중)"
    if "내일" in q:
        d = today + timedelta(days=1)
        return (d, d), "내일"
    if "모레" in q:
        d = today + timedelta(days=2)
        return (d, d), "모레"
    if re.search(r"다음\s*주\s*말", q):
        sat = today + timedelta(days=(5 - wd) % 7 + 7) if wd <= 5 else today + timedelta(days=6)
        return (sat, sat + timedelta(days=1)), "다음 주말"
    if "크리스마스" in q:
        y = today.year if (today.month, today.day) <= (12, 25) else today.year + 1
        return (date(y, 12, 24), date(y, 12, 25)), "크리스마스"
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
    if re.search(r"다음\s*달", q):
        start = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return (start, nxt - timedelta(days=1)), "다음 달"
    if "연말" in q:
        return (max(today, date(today.year, 12, 1)), date(today.year, 12, 31)), "연말"
    d = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", q) or re.search(r"(?<![\d.])(\d{1,2})\s*[/.]\s*(\d{1,2})(?![\d.])", q)
    if d and 1 <= int(d.group(1)) <= 12 and 1 <= int(d.group(2)) <= 31:
        mon, day = int(d.group(1)), int(d.group(2))
        year = today.year if mon >= today.month - 6 else today.year + 1
        try:
            one = date(year, mon, day)
            return (one, one), f"{mon}월 {day}일"
        except ValueError:
            pass
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
            if not hit:
                # 작품명의 첫 낱말만 말해도 ('산리오' ← '산리오 캐릭터즈', '원피스' ← '원피스 대해적시대') 3글자 이상이면 작품으로
                first = re.split(r"[\s·:×x\-]+", w.strip())[0]
                hit = len(_norm(first)) >= 3 and _norm(first) not in _STOP and _word_at_start(first, q)
                if hit:
                    w, nw = first, _norm(first)      # '원피스' 로 찾아서 '원피스 …' 작품을 모두 잡는다
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
    query.include_ended = False      # 끝난 팝업은 답하지 않는다 (11/18 요청: 종료된 팝업은 어디에도 안 보이게)
    known = [_norm(x) for x in query.works + query.characters + query.places]
    words = []
    for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", q):
        base = _PARTICLE.sub("", w)          # '주에' → '주', '성수에서' → '성수'
        if len(base) < 2 or w in _STOP or base in _STOP or _DATE_WORD.fullmatch(w) or _DATE_WORD.fullmatch(base):
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
         "보여줘", "보여", "보여줘요", "알려줄래", "나와", "나오는", "갈만한", "가고", "싶어", "아직", "열리는", "여는", "있을까",
         "모레", "다음달", "연말", "크리스마스", "있어요", "있나", "있음", "하나요", "해요", "하니", "할까", "하는거",
         "있는지", "궁금해", "궁금", "찾아줘", "찾아", "검색", "좀", "혹시", "정보", "언제까지", "언제부터", "몇", "개", "건"}
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


def retrieve(question: str, rows: list[dict], today: date, k: int | None = TOP_K) -> tuple[Query, list[Hit]]:
    query = parse(question, rows, today)
    hits = search(query, rows, today)
    return query, (hits[:k] if k else hits)


def search(query: Query, rows: list[dict], today: date) -> list[Hit]:
    """읽어 낸 조건(작품·캐릭터·장소·기간)에 **모두** 맞는 팝업. 점수 높은 순."""
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
            if any(_norm(c) in chars or _norm(c) in _norm(r.get("intro")) or _norm(c) in work
                   for c in query.characters):
                score += 4; why.append("캐릭터")
            else:
                continue          # 캐릭터를 말했으면 그 캐릭터가 나오는 팝업만 (작품과 함께 말해도 둘 다 맞아야)
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
    return hits


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


GUIDE_HEAD = "말씀을 못 알아들었어요. 작품 이름 · 장소 · 날짜를 넣어서 물어봐 주세요."
GUIDE_EXAMPLES = ["치이카와 이번 달 서울 팝업 있어?", "이번 주말 홍대 팝업", "12월 5일 부산에서 하는 팝업",
                  "주술회전 팝업 언제까지야?", "곧 끝나는 팝업"]
GUIDE = GUIDE_HEAD + "\n예) " + " · ".join(f"'{x}'" for x in GUIDE_EXAMPLES)


def phrase(query: Query) -> str:
    """조건을 말로: '이번 달 서울에서 하는 치이카와'."""
    when = {"오늘(진행 중)": "지금 진행 중인"}.get(query.window_label, query.window_label)
    where = f"{'·'.join(query.places)}에서 하는" if query.places else ""
    what = " ".join(query.works + [c for c in query.characters if not any(_norm(c) in _norm(w) for w in query.works)])
    return " ".join(x for x in (when, where, what) if x).strip()


def understood(query: Query, rows: list[dict]) -> tuple[bool, list[str]]:
    """질문에서 팝업 조건(작품·캐릭터·장소·기간)이나 데이터에 있는 낱말을 하나라도 읽었는가. (읽었나, 모르는 낱말)"""
    text = _norm(" ".join(" ".join(str(r.get(c) or "") for c in ("work", "characters", "cafe_name", "perks", "goods", "tags"))
                          for r in rows))
    unknown = [w for w in query.words if _norm(w) not in text]
    known = [w for w in query.words if _norm(w) in text]
    if query.works or query.characters or query.places:
        return True, unknown
    if query.window:
        # 날짜만 읽었는데 팝업과 상관없는 말이 섞였으면 ('오늘 날씨 어때?') 못 알아들은 것으로
        return not unknown or bool(known), unknown
    return bool(known), unknown


def relax_hint(query: Query, rows: list[dict], today: date) -> str:
    """0건일 때: 조건 하나를 빼면 몇 건인지 ('서울을 빼면 3건 있어요')."""
    tips = []
    for field_, label in (("places", lambda q: "·".join(q.places)), ("window", lambda q: q.window_label),
                          ("characters", lambda q: ", ".join(q.characters)), ("works", lambda q: ", ".join(q.works))):
        if not getattr(query, field_):
            continue
        q2 = Query(**{**query.__dict__})
        if field_ == "window":
            q2.window, q2.window_label = None, ""
        else:
            setattr(q2, field_, [])
        if not (q2.works or q2.characters or q2.places or q2.window):
            continue
        n = len(search(q2, rows, today))
        if n:
            name = {"오늘(진행 중)": "지금"}.get(label(query), label(query))
            tips.append(f"'{name}' 조건을 빼면 {n}건 있어요")
    return (" " + " · ".join(tips[:2]) + ".") if tips else ""


def count_answer(query: Query, n: int, rows: list[dict], today: date) -> str:
    cond = phrase(query) or ("'" + "', '".join(query.words) + "' 이(가) 들어간")
    if n:
        return f"네, {cond} 팝업이 {n}건 있어요." + (" 아래에 5건까지 보여 드려요." if n > 5 else "")
    return f"현재 진행하는 팝업이 없어요. ({cond} 조건으로 찾았어요.)" + relax_hint(query, rows, today)


def answer(question: str, rows: list[dict], today: date, version: str | None = None,
           ctx: dict | None = None) -> Answer:
    """ctx: {'loc': {'lat','lng'} | None, 'ratings': {cafe_id: (평균, 개수)}, 'favs': {cafe_id: 북마크 수}}"""
    question = guard.mask(question.strip())[:MAX_QUESTION]
    special = intent_answer(question, rows, today, ctx or {})
    if special is not None:
        return special
    query, all_hits = retrieve(question, rows, today, k=None)
    ok, unknown = understood(query, rows)
    if not ok:                               # 팝업 조건을 하나도 못 읽음 → 묻는 법 안내
        query.intent = "unknown"
        return Answer(text=GUIDE, hits=[], used_ids=[], source="rule", badge="규칙 기반 대체", query=query,
                      confidence="low")
    head = count_answer(query, len(all_hits), rows, today)
    hits = all_hits[:TOP_K]
    if not hits:
        return Answer(text=head, hits=[], used_ids=[], source="rule", badge="규칙 기반 대체", query=query,
                      confidence="low")
    week = _WEEKDAYS[today.weekday()]
    content = (f"질문: {question}\n오늘: {today.isoformat()} ({week})\n"
               f"질문에서 읽은 조건: {query.describe()}\n조건에 모두 맞는 팝업 수: {len(all_hits)}건\n\n[후보 팝업]\n" +
               "\n".join(_card(h.row, today) for h in hits))
    res = ai.call_structured("ask", content, AskAnswer, fallback=lambda: _rule_answer(query, hits, today),
                             version=version)
    data: AskAnswer = res.data if res.ok else _rule_answer(query, hits, today)
    allowed = {str(h.row.get("entry_id")) for h in hits}
    used = [i for i in data.used_ids if i in allowed]
    dropped = [i for i in data.used_ids if i not in allowed]
    # 첫 문장은 늘 규칙으로 센 건수 (AI 가 다른 숫자를 말해도 흔들리지 않게), 그 뒤에 AI 설명
    extra = guard.mask(data.answer) if res.ok and res.source == "ai" else ""
    out = Answer(text=head + (("\n" + extra) if extra else ""), hits=hits, used_ids=used,
                 source=res.source if res.ok else "fallback", badge=res.badge if res.ok else "규칙 기반 대체",
                 query=query, dropped_ids=dropped, confidence=data.confidence, error=res.error)
    out.summary = head
    out.total = len(all_hits)
    out.all_ids = [str(h.row.get("entry_id")) for h in all_hits]
    return out


# ================================================================== 자주 묻는 질문 규칙 (의도)
# 검색어 해석(retrieve)보다 먼저 본다. 모두 규칙이라 AI 없이도 늘 같은 답을 낸다.
# 지역·작품·날짜 조건은 parse() 로 같이 읽어서 거른다 (예: '부산 팝업 추천', '주말에 가까운 팝업').
# 사용법 안내 페이지(/guide)의 칸 이름. 앱이 링크를 만들 때 쓴다 (예: ./guide#add)
GUIDE_SECTIONS = {"map": "지도로 보기", "list": "리스트로 보기", "cal": "내 캘린더 · 알림", "add": "팝업 등록하기",
                  "edit": "정보 수정하기", "delete": "삭제 요청하기", "bookmark": "북마크", "login": "로그인 · 회원가입",
                  "ask": "물어보기"}

INTENTS = [
    # 나에 대한 질문 · 사용법 · 잡담 (11/18 추가) — 팝업 검색보다 먼저 본다
    ("me_nick", re.compile(r"(내|제|나의)\s*(닉네임|닉|별명|이름)|나\s*(는\s*)?(누구|이름)")),
    ("me_loc", re.compile(r"(내|제|나의|지금|현재)\s*(위치|있는\s*곳|동네)\s*(가|는|이|은)?\s*(어디|뭐|알려|확인)"
                          r"|나\s*(지금\s*)?어디|여기\s*(가\s*)?어디|현재\s*위치")),
    ("guide_add", re.compile(r"등록\s*(은|는|하는|하려면|하고\s*싶|방법|어떻게|할\s*수)|어떻게\s*등록"
                             r"|(팝업|카페)\s*(올리|추가)\s*(하|는|방법)")),
    ("guide_edit", re.compile(r"수정\s*(은|는|하는|하려면|방법|어떻게|할\s*수)|어떻게\s*(수정|고쳐|고치)"
                              r"|(정보|날짜|주소)\s*(가|이)?\s*(틀|잘못|달라)")),
    ("guide_delete", re.compile(r"삭제\s*(는|은|하는|하려면|방법|어떻게|요청|할\s*수)|어떻게\s*(삭제|지워|지우)"
                                r"|지우는\s*(법|방법)|내\s*(글|리뷰)\s*지우")),
    ("guide_bookmark", re.compile(r"북마크\s*(는|은|하는|하려면|방법|어떻게|가\s*뭐)|찜\s*(하는|어떻게|은|는)|어떻게\s*(북마크|찜)")),
    ("guide_login", re.compile(r"(로그인|로그아웃|회원\s*가입|가입|탈퇴)\s*(은|는|하는|하려면|방법|어떻게|안\s*(돼|되)|할\s*수)"
                               r"|어떻게\s*(로그인|가입|탈퇴)")),
    ("guide_cal", re.compile(r"캘린더\s*(는|은|가|뭐|어떻게|사용|보는)|알림\s*(은|는|이|언제|어떻게|왜|안\s*(와|오))")),
    ("guide_map", re.compile(r"지도\s*(보기)?\s*(는|은|어떻게|사용|보는\s*법)")),
    ("guide_list", re.compile(r"리스트\s*(보기)?\s*(는|은|어떻게|사용|보는\s*법)")),
    ("usage", re.compile(r"사용법|사용\s*방법|이용\s*방법|쓰는\s*(법|방법)|어떻게\s*(써|쓰|사용|이용)|가이드|도움말|매뉴얼"
                         r"|기능\s*(이|은|뭐|알려|소개)|뭐\s*할\s*수|뭘\s*할\s*수|뭘\s*물어|뭐\s*물어")),
    ("my_favs", re.compile(r"(내|제|나의)\s*(북마크|찜)")),
    ("today", re.compile(r"오늘\s*(이\s*)?(몇\s*월|며칠|몇\s*일|날짜|무슨\s*요일|요일)")),
    ("contact", re.compile(r"문의|연락처|고객\s*센터|신고|관리자\s*(에게|한테|연락|누구)|운영자")),
    ("who", re.compile(r"(너|넌|당신)\s*(는|은)?\s*(누구|뭐|무엇|뭘)|(너|넌)\s*(이름|정체)|자기\s*소개")),
    ("thanks", re.compile(r"^(고마워|고맙|감사|땡큐|thanks?|thx|잘\s*했)", re.I)),
    ("count_all", re.compile(r"(팝업|카페)\s*(이|가|은|는)?\s*(몇\s*(개|곳|군데)|총|전체\s*몇)|몇\s*(개|곳)\s*(있|등록|열려)"
                             r"|등록된\s*팝업\s*(수|몇)")),
    ("help", re.compile(r"^(안녕|하이|hi|hello|반가|도움|도와)", re.I)),
    # 순위 질문 (11/18): 블로그 후기 수 · 리뷰 수 · 별점 — 가장/제일 많은·적은·높은·낮은
    ("blog_rank", re.compile(r"블로그.*(많|적|높|낮|순위|랭킹)|(많|적).*블로그")),
    ("rating_rank", re.compile(r"(별점|평점)\s*(이|가)?\s*(가장|제일|젤|높|낮|좋|나쁜|순|랭킹)|(높|낮|좋|나쁜)\S*\s*(별점|평점)")),
    ("review_rank", re.compile(r"(리뷰|후기|댓글)\s*(가|이)?\s*(가장|제일|젤)?\s*(많|적|없|순|랭킹)|(많|적)\S*\s*(리뷰|후기)")),
    ("near", re.compile(r"가까운|근처|주변|내\s*위치|여기서|가까이")),
    ("by_region", re.compile(r"지역\s*별|지역마다|동네\s*별|어느\s*지역|지역\s*순")),
    ("recommend", re.compile(r"추천|어디\s*갈까|갈\s*만한|가볼\s*만한|볼\s*만한|베스트|좋은\s*팝업", re.I)),
    ("ending", re.compile(r"곧\s*끝|마감|끝나기\s*전|종료\s*임박|얼마\s*안\s*남|막바지|끝나는")),
    ("upcoming", re.compile(r"오픈\s*예정|곧\s*(열|시작|오픈)|새로\s*(열|생|오픈)|신규|예정\s*(된|중|인)|예정이|다가오는|"
                            r"오픈하는|시작하는|아직\s*(안\s*(열|시작)|시작\s*전|오픈\s*전|예정)|시작\s*전|오픈\s*전")),
    ("popular", re.compile(r"인기|북마크\s*많|핫한|사람\s*많|유명한")),
    ("reviewed", re.compile(r"리뷰\s*많|후기\s*많|후기\s*좋|별점\s*(높|좋)|평점")),
]


_KOR_NUM = {"한": 1, "하나": 1, "두": 2, "둘": 2, "세": 3, "셋": 3, "네": 4, "넷": 4, "다섯": 5, "여섯": 6, "일곱": 7,
            "여덟": 8, "아홉": 9, "열": 10}
RANK_MAX = 10


def wanted_count(question: str, default: int = 5) -> int:
    """'3개', '다섯 개', '5곳' → 몇 개 보여 줄지 (1~RANK_MAX)."""
    m = re.search(r"(\d{1,2})\s*(개|곳|군데|위)", question)
    if m:
        return max(1, min(RANK_MAX, int(m.group(1))))
    m = re.search(r"(하나|한|두|둘|세|셋|네|넷|다섯|여섯|일곱|여덟|아홉|열)\s*(개|곳|군데)", question)
    if m:
        return _KOR_NUM[m.group(1)]
    return default


def lowest_first(question: str) -> bool:
    """'적은·낮은·나쁜·없는' 을 물었으면 작은 것부터."""
    return bool(re.search(r"적|낮|나쁜|없는|최하|꼴찌", question))


def detect_intent(question: str) -> str | None:
    q = question.strip()
    for name, pat in INTENTS:
        if pat.search(q):
            return name
    return None


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    from math import asin, cos, radians, sin, sqrt
    lat1, lng1, lat2, lng2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(h))


def _ongoing(r: dict, today: date) -> bool:
    s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
    return bool(s and e and s <= today <= e)


def _filtered(query: Query, rows: list[dict], today: date, ongoing_only: bool = True) -> list[dict]:
    """질문 속 작품·지역·날짜 조건 + (기본) 진행 중만."""
    out = []
    for r in rows:
        e = mycal._day(r.get("end_date"))
        if e and e < today:
            continue                     # 끝난 팝업은 어떤 질문에도 내밀지 않는다
        if ongoing_only and not query.window and not _ongoing(r, today):
            continue
        if query.window and not _overlaps(r, query.window):
            continue
        work = _norm(r.get("work"))
        if query.works and not (work and any(_norm(w) in work or work in _norm(w) for w in query.works)):
            continue
        if query.places and not any(_place_match(p, r) for p in query.places):
            continue
        out.append(r)
    return out


def _done(query: Query, rows: list[dict], text: str, intent: str, limit: int = 5) -> "Answer":
    hits = [Hit(r, 0.0, [intent]) for r in rows[:limit]]
    query.intent = intent
    return Answer(text=text, hits=hits, used_ids=[str(h.row.get("entry_id")) for h in hits], source="rule",
                  badge="규칙 기반 대체", query=query, confidence="high" if hits else "low")


def intent_answer(question: str, rows: list[dict], today: date, ctx: dict) -> "Answer | None":
    intent = detect_intent(question)
    if intent is None:
        return None
    query = parse(question, rows, today)
    cond = query.describe()
    cond_txt = "" if cond.startswith("조건 없음") else f"{cond} 조건으로 "
    ratings: dict = ctx.get("ratings") or {}
    favs: dict = ctx.get("favs") or {}

    def eid(r: dict) -> str:
        return str(r.get("entry_id"))

    def rating(r: dict) -> tuple[float, int]:
        return ratings.get(eid(r), (0.0, 0))

    if intent in ("blog_rank", "review_rank", "rating_rank"):
        return _rank_answer(intent, question, query, rows, today, ctx, cond_txt)

    if intent == "help":
        return _done(query, [], "작품·지역·날짜로 물어보세요. 예: '내 주변 가까운 팝업', '팝업 추천해줘', '지금 진행 중인 부산 팝업', "
                                "'곧 끝나는 팝업', '이번 주말 성수 팝업'.", intent)

    if intent in _ME_INTENTS:
        # 나·사용법·잡담. 작품·장소가 붙은 '몇 개'·'내 북마크' 질문은 None → 아래 팝업 검색으로
        return _me_answer(intent, query, rows, today, ctx)

    if intent == "near":
        if query.places:
            # '홍대 근처 팝업' 처럼 지역을 말했으면 '그 지역 주변' 이라는 뜻 → 내 위치가 아니라 지역 검색으로
            return None
        loc = ctx.get("loc")
        if not (isinstance(loc, dict) and "lat" in loc):
            return _done(query, [], "내 위치를 아직 몰라요. 브라우저 주소창의 위치 권한을 허용하거나 지도 보기를 한 번 열어 주세요. "
                                    "'홍대 팝업'처럼 동네 이름으로 물어봐도 돼요.", intent)
        me = (float(loc["lat"]), float(loc["lng"]))
        cand = []
        for r in _filtered(query, rows, today):
            try:
                cand.append((_km(me, (float(r.get("lat")), float(r.get("lng")))), r))
            except (TypeError, ValueError):
                continue
        cand.sort(key=lambda t: t[0])
        if not cand:
            return _done(query, [], f"{cond_txt}지금 열려 있는 팝업 중 위치를 아는 곳이 없어요.", intent)
        res = _done(query, [r for _, r in cand], f"{cond_txt}내 위치에서 가까운 진행 중인 팝업이에요.", intent)
        res.distances = {eid(r): km for km, r in cand[:5]}
        return res

    if intent == "by_region":
        groups: dict[str, list[dict]] = {}
        for r in _filtered(query, rows, today):
            g = geo.city_name(str(r.get("address") or "")) or "지역 미상"
            groups.setdefault(g, []).append(r)
        if not groups:
            return _done(query, [], "지금 진행 중인 팝업이 없어요.", intent)
        order = sorted(groups.items(), key=lambda kv: -len(kv[1]))
        summary = " · ".join(f"{g} {len(v)}곳" for g, v in order)
        reps = [sorted(v, key=lambda r: (-rating(r)[0], -favs.get(eid(r), 0)))[0] for _, v in order]
        res = _done(query, reps, f"지역별 진행 중 팝업: {summary}", intent, limit=8)
        res.summary = summary
        return res

    if intent == "recommend":
        live = _filtered(query, rows, today)
        if not live:
            return _done(query, [], f"{cond_txt}지금 진행 중인 팝업이 없어요. 조건을 하나 빼 보세요.", intent)
        # 별점 높은 순 → 리뷰 많은 순 → 북마크 많은 순 → 곧 끝나는 순 (진행 중만)
        live.sort(key=lambda r: (-rating(r)[0], -rating(r)[1], -favs.get(eid(r), 0), str(r.get("end_date") or "")))
        rated = any(rating(r)[1] for r in live)
        why = "별점 높은 순 → 리뷰 많은 순" if rated else "아직 별점이 없어 북마크 많은 순"
        return _done(query, live, f"{cond_txt}지금 갈 수 있는 팝업을 {why}으로 골랐어요.", intent)

    if intent == "ending":
        live = [r for r in _filtered(query, rows, today)
                if mycal._day(r.get("end_date")) and (mycal._day(r.get("end_date")) - today).days <= 7]
        live.sort(key=lambda r: str(r.get("end_date") or ""))
        if not live:
            return _done(query, [], f"{cond_txt}7일 안에 끝나는 팝업이 없어요.", intent)
        return _done(query, live, f"{cond_txt}7일 안에 끝나는 팝업이에요 (끝나는 날이 가까운 순).", intent)

    if intent == "upcoming":
        soon = [r for r in rows if mycal._day(r.get("start_date")) and mycal._day(r.get("start_date")) > today]
        q2 = Query(works=query.works, characters=query.characters, places=query.places)
        soon = _filtered(q2, soon, today, ongoing_only=False)
        soon.sort(key=lambda r: str(r.get("start_date") or ""))
        if not soon:
            return _done(query, [], f"{cond_txt}오픈 예정인 팝업이 없어요.", intent)
        return _done(query, soon, f"{cond_txt}곧 열리는 팝업이에요 (시작일이 가까운 순).", intent)

    if intent == "popular":
        live = _filtered(query, rows, today)
        live.sort(key=lambda r: (-favs.get(eid(r), 0), -rating(r)[1]))
        if not live:
            return _done(query, [], f"{cond_txt}지금 진행 중인 팝업이 없어요.", intent)
        return _done(query, live, f"{cond_txt}북마크가 많은 진행 중 팝업이에요.", intent)

    if intent == "reviewed":
        live = [r for r in _filtered(query, rows, today) if rating(r)[1]]
        live.sort(key=lambda r: (-rating(r)[1], -rating(r)[0]))
        if not live:
            return _done(query, [], f"{cond_txt}아직 다녀온 후기가 달린 진행 중 팝업이 없어요.", intent)
        return _done(query, live, f"{cond_txt}다녀온 후기가 많은 진행 중 팝업이에요.", intent)
    return None


_ME_INTENTS = {"me_nick", "me_loc", "usage", "my_favs", "today", "contact", "who", "thanks", "count_all"} | \
    {f"guide_{k}" for k in ("add", "edit", "delete", "bookmark", "login", "cal", "map", "list")}
_WEEK_KO = "월화수목금토일"

# 기능별 짧은 안내 (자세한 건 /guide 의 같은 칸)
_GUIDE_TEXT = {
    "add": "팝업 등록은 회원만 할 수 있어요. 화면 오른쪽 아래 코랄색 + 버튼 → 작품·카페·기간·주소를 넣고 저장하면 바로 지도와 리스트에 올라가요.",
    "edit": "팝업 상세 화면 오른쪽의 '수정하기' 탭에서 고칠 수 있어요 (회원만). 고친 기록은 모두 남아서 예전 내용으로 되돌릴 수도 있어요.",
    "delete": "글은 바로 지워지지 않고 '삭제 요청'으로 받아요. 상세 화면에서 삭제 요청(사유 적기)을 보내면 관리자가 확인하고, 결과는 종 알림으로 알려 드려요.",
    "bookmark": "카드나 상세 화면의 북마크 버튼을 누르면 돼요 (회원만). 북마크한 팝업은 내 캘린더에 날짜 막대로 보이고, 오픈·종료 3일 전부터 알림이 와요.",
    "login": "메뉴바 오른쪽 '로그인'에서 카카오·네이버 간편 로그인이나 아이디로 가입할 수 있어요. 로그아웃·탈퇴는 내 닉네임을 누르면 나오는 마이페이지에 있어요.",
    "cal": "내 캘린더(회원)는 북마크한 팝업을 날짜 막대로 보여 주고, 오른쪽에 최근 3일 알림과 내 주변 추천이 있어요. 알림은 북마크한 팝업의 오픈·종료 3일 전부터 와요.",
    "map": "지도로 보기는 왼쪽 데일리 팝업 노트(날짜·지역별 목록)와 가운데 지도를 함께 봐요. 핀에 마우스를 올리면 카드, 누르면 그 팝업 목록이 열려요.",
    "list": "리스트로 보기는 포스터 카드로 모아 봐요. 위에서 북마크만 보기·지역·정렬을 고르고, 아래 'N건 더보기'로 더 불러와요. 오른쪽에서 저에게 물어볼 수도 있어요.",
}


def _guide_link(key: str) -> list:
    return [(f"사용자 튜토리얼 · {GUIDE_SECTIONS[key]} 보기", f"./guide#{key}")]


def _me_answer(intent: str, query: Query, rows: list[dict], today: date, ctx: dict) -> "Answer | None":
    """나·사용법·잡담 질문의 답 (모두 규칙). 조건이 붙은 '몇 개'·'내 북마크' 질문은 None (검색으로 넘김)."""
    def say(text: str, links: list | None = None, hit_rows: list[dict] | None = None) -> Answer:
        res = _done(query, hit_rows or [], text, intent)
        res.links = links or []
        return res

    if intent == "me_nick":
        nick = str(ctx.get("nick") or "").strip()
        if not nick:
            return say("아직 로그인하지 않았어요. 로그인하면 닉네임을 알려 드릴게요.", _guide_link("login"))
        return say(f"{nick}님이에요! 닉네임은 마이페이지(메뉴바의 내 닉네임)에서 언제든 바꿀 수 있어요.")
    if intent == "me_loc":
        loc = ctx.get("loc")
        if not (isinstance(loc, dict) and "lat" in loc):
            return say("내 위치를 아직 몰라요. 브라우저 주소창의 위치 권한을 허용하거나 지도 보기를 한 번 열어 주세요.")
        lat, lng = float(loc["lat"]), float(loc["lng"])
        region = ""
        finder = ctx.get("region_of")
        if callable(finder):
            try:
                region = str(finder(lat, lng) or "")
            except Exception:
                region = ""
        if not region:                       # 지역 이름을 못 받으면 가장 가까운 팝업의 지역으로 어림
            best = None
            for r in rows:
                try:
                    km = _km((lat, lng), (float(r.get("lat")), float(r.get("lng"))))
                except (TypeError, ValueError):
                    continue
                if best is None or km < best[0]:
                    best = (km, r)
            if best:
                addr = str(best[1].get("address") or "")
                region = geo.area_name(addr) or geo.city_name(addr)
        if not region:
            return say("위치는 받았는데 지역 이름을 찾지 못했어요. 지도 보기에서 내 위치를 확인해 주세요.")
        return say(f"현재 위치는 {region} 근처예요. '내 주변 가까운 팝업'이라고 물어보면 가까운 순으로 찾아 드려요.")
    if intent == "usage":
        return say("지도로 보기 · 리스트로 보기 · 내 캘린더 · 등록하기 · 수정하기 · 삭제 요청 방법을 한 페이지에 정리해 뒀어요. "
                   "아래 링크를 눌러 보세요.", [("사용자 튜토리얼 열기", "./guide")])
    if intent.startswith("guide_"):
        key = intent.removeprefix("guide_")
        return say(_GUIDE_TEXT[key], _guide_link(key))
    if intent == "today":
        return say(f"오늘은 {today.year}년 {today.month}월 {today.day}일 {_WEEK_KO[today.weekday()]}요일이에요.")
    if intent == "who":
        return say("저는 ANI:WHERE 팝업 도우미예요. 등록된 애니 팝업·카페·굿즈 행사에서 작품·지역·날짜로 찾아 드려요.",
                   [("사용자 튜토리얼 열기", "./guide")])
    if intent == "thanks":
        return say("천만에요! 더 궁금한 팝업이 있으면 언제든 물어봐 주세요.")
    if intent == "contact":
        return say("문의·신고는 개인정보처리방침의 연락처(10번)로 보내 주세요. 잘못된 글은 상세 화면의 '삭제 요청'으로 관리자에게 바로 알릴 수 있어요.",
                   [("개인정보처리방침 · 연락처 보기", "./privacy")])
    if query.works or query.places or query.window:
        return None                          # '주술회전 팝업 몇 개', '내 북마크 중 홍대' 등 → 검색으로
    if intent == "count_all":
        live = sum(1 for r in rows if _ongoing(r, today))
        soon = sum(1 for r in rows if (mycal._day(r.get("start_date")) or today) > today)
        return say(f"지금 진행 중인 팝업은 {live}곳, 오픈 예정은 {soon}곳이에요 (모두 {live + soon}곳).")
    if intent == "my_favs":
        mine = ctx.get("my_favs")
        if mine is None:
            return say("북마크는 회원만 쓸 수 있어요. 로그인하면 북마크한 팝업을 보여 드릴게요.", _guide_link("login"))
        ids = set(mine)
        keep = [r for r in rows if str(r.get("entry_id")) in ids
                and not ((mycal._day(r.get("end_date")) or today) < today)]
        if not keep:
            return say("아직 북마크한 팝업이 없어요. 카드의 북마크 버튼을 눌러 보세요.", _guide_link("bookmark"))
        return say(f"북마크한 팝업 {len(keep)}곳이에요.", hit_rows=keep)
    return None


def _rank_answer(intent: str, question: str, query: Query, rows: list[dict], today: date, ctx: dict,
                 cond_txt: str) -> "Answer":
    """순위 질문: 끝나지 않은 팝업(질문 속 작품·지역·날짜 조건 적용) 중 블로그 후기 수 / 리뷰 수 / 별점 순."""
    n = wanted_count(question)
    low = lowest_first(question)
    pool = _filtered(query, rows, today, ongoing_only=False)
    word = {"blog_rank": "블로그 후기", "review_rank": "리뷰", "rating_rank": "별점"}[intent]
    if intent == "blog_rank":
        counter = ctx.get("blog_totals")
        totals = counter(pool) if callable(counter) else {}
        if not totals:
            return _done(query, [], "블로그 후기 수를 지금은 셀 수 없어요 (네이버 검색 연결이 꺼져 있거나 이번 달 검색 한도를 다 썼어요).",
                         intent)
        value = lambda r: totals.get(str(r.get("entry_id")))           # noqa: E731
        pool = [r for r in pool if value(r) is not None]
        unit = lambda v: f"블로그 글 {v:,}개"                            # noqa: E731
    elif intent == "review_rank":
        counts = ctx.get("review_counts") or {}
        value = lambda r: counts.get(str(r.get("entry_id")), 0)         # noqa: E731
        unit = lambda v: f"리뷰 {v}개"                                   # noqa: E731
    else:
        ratings = ctx.get("ratings") or {}
        pool = [r for r in pool if ratings.get(str(r.get("entry_id")), (0, 0))[1]]
        if not pool:
            return _done(query, [], f"{cond_txt}아직 별점이 달린 팝업이 없어요. 다녀온 후기에 별점을 남기면 순위를 보여 드려요.", intent)
        value = lambda r: ratings[str(r.get("entry_id"))][0]            # noqa: E731
        unit = lambda v: f"별점 {v:.1f}"                                  # noqa: E731
    if not pool:
        return _done(query, [], f"{cond_txt}지금 볼 수 있는 팝업이 없어요.", intent)
    if intent == "review_rank" and not low and not any(value(r) for r in pool):
        return _done(query, [], f"{cond_txt}아직 리뷰가 달린 팝업이 없어요. 첫 리뷰를 남겨 보세요.", intent)
    # 같은 값이면 곧 끝나는 순
    pool.sort(key=lambda r: ((value(r) if low else -value(r)), str(r.get("end_date") or "")))
    top = pool[:n]
    head = f"{word} {'적은' if low and intent != 'rating_rank' else '낮은' if low else '많은' if intent != 'rating_rank' else '높은'} 순"
    lines = " · ".join(f"{i + 1}. {r.get('work')} ({unit(value(r))})" for i, r in enumerate(top[:3]))
    res = _done(query, top, f"{cond_txt}{head}으로 {len(top)}곳이에요. {lines}", intent, limit=n)
    res.summary = head
    return res


def find(question: str, rows: list[dict], today: date, ctx: dict | None = None) -> tuple[Query, list[Hit]]:
    """AI 없이 찾기만: 자주 묻는 질문 규칙(의도) → 없으면 검색어 해석. 평가(scripts/eval_ask.py)가 쓴다."""
    special = intent_answer(guard.mask(question.strip())[:MAX_QUESTION], rows, today, ctx or {})
    if special is not None:
        return special.query, special.hits
    return retrieve(question, rows, today)
