"""Notion '🎀 애니 팝업·콜라보 트래커' DB 에 매주 쌓이는 행사를 앱으로 자동으로 가져온다.

- NOTION_TOKEN(Notion 내부 통합 키)이 있을 때만 동작한다. DB 를 그 통합에 '연결' 해 두어야 읽을 수 있다.
- 메인 화면을 열 때 최대 SYNC_EVERY 마다 한 번 확인한다 (마지막 확인 시각은 data/notion_sync.json).
- 검수상태가 '검토 완료' 이고 기간(시작·종료)이 있는 행만 가져온다.
- 이미 가져온 Notion 페이지이거나, 같은 작품 + 같은 카페가 이미 있으면 새로 만들지 않는다.
  다만 앱 쪽에 이미지·팝업 소개가 없고 Notion 에 있으면 그 칸만 채운다.
- '팝업소개' 칸은 앱의 팝업 소개(intro)로, '공식공지' 링크는 참고 웹사이트 맨 앞에 넣는다.
- '지점' 칸(한 줄에 '지점명|위도|경도|주소')에 여러 곳이 적혀 있으면 지점마다 따로 가져온다.
- 이미지: Notion 의 '이미지' 칸(주소 여러 개 가능)과 '파일과 미디어' 칸을 모두 읽는다.
  첫 장은 포스터, 나머지는 추가 이미지로 넣는다.
- 저장소는 append-only 라 새 행만 쌓는다. 실패해도 앱은 멈추지 않는다.
"""
from __future__ import annotations

import json
import math
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import cafe, geo, guard, images, notice
from .schema import CafeEntry

DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "3da1fd80371141c697fabf7b742e0edc")
STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "notion_sync.json"
SYNC_EVERY = timedelta(hours=1)
SOURCE = "AI 자동 수집"
UNKNOWN = ("확인 필요", "미확인", "")



def _has_id(r: dict, notion_id: str) -> bool:
    """앱 행의 note 에 이 Notion 페이지(지점) 번호가 있는지. 'abc' 가 'abc-2' 에 걸리지 않게 끝까지 본다."""
    return bool(notion_id) and re.search(rf"notion:{re.escape(notion_id)}(?![\w-])", str(r.get("note") or "")) is not None


def _known(text) -> str:
    t = str(text or "").strip()
    return "" if any(t == u or t.startswith(u) for u in UNKNOWN if u) or not t else t


def _split(text, seps=r"\s*/\s*|,") -> list[str]:
    return [p.strip() for p in re.split(seps, _known(text)) if _known(p)]


def _work(name: str) -> str:
    """'프로젝트 세카이 (프로세카)' → '프로젝트 세카이' (괄호 속 별칭은 뺀다)."""
    return re.sub(r"\s*\(.*?\)\s*$", "", str(name or "")).strip()


def _place(name) -> str:
    """여러 지점이 함께 적힌 장소명에서 첫 지점만 남긴다.
    '애니메이트 Gratte (잠실롯데 / 홍대)' → '애니메이트 Gratte 잠실롯데',
    '애니플러스 서울 합정점 / 부산 서면점' → '애니플러스 서울 합정점'."""
    t = _known(name)
    m = re.match(r"^(.*?)\s*\(([^()]*/[^()]*)\)\s*$", t)
    if m:
        return f"{m.group(1)} {m.group(2).split('/')[0].strip()}".strip()
    return t.split(" / ")[0].strip()


def _page_id(url: str) -> str:
    """Notion 페이지 번호 (지점으로 나눈 행은 '번호-2' 처럼 뒤에 지점 순서가 붙는다)."""
    raw = str(url or "")
    m = re.search(r"notion-([0-9a-f]{32}-\d+)$", raw)
    if m:
        return m.group(1)
    m = re.search(r"([0-9a-f]{32})", raw.replace("-", ""))
    return m.group(1) if m else ""


def entry_from_row(row: dict) -> tuple[CafeEntry | None, dict, str]:
    """평평한 행 → (CafeEntry, 덧붙일 정보, 건너뛴 이유). 행 키는 Notion 속성 이름 그대로
    ('작품명', '장소명', ..., 'date:기간:start', 'date:기간:end', 'url')."""
    if row.get("검수상태") != "검토 완료":
        return None, {}, "검토 필요"
    start, end = row.get("date:기간:start"), row.get("date:기간:end")
    if not start or not end:
        return None, {}, "기간 없음"
    place = _place(row.get("장소명"))
    work = _work(row.get("작품명"))
    if not place or not work:
        return None, {}, "작품명·장소명 없음"
    # 주소가 비어 있으면 장소명으로 위치를 찾는다 ('애니플러스 서울 합정점' → 합정)
    address = _known(row.get("주소")) or place
    event_text = str(row.get("이벤트") or "") + " " + str(row.get("특전") or "")
    # 이벤트 문구 → 앱의 '이벤트 추가 정보' 항목 (간편등록과 같은 낱말 표를 쓴다)
    tags = notice.event_tags(event_text)
    entry = CafeEntry(
        cafe_name=place, work=work, characters=_split(row.get("캐릭터"), r",|·"),
        address=address,
        start_date=date.fromisoformat(str(start)[:10]), end_date=date.fromisoformat(str(end)[:10]),
        perks=_split(row.get("특전")), goods=_split(row.get("굿즈"), r","),
        confidence="high",
    )
    # 출처·주최링크·참고링크(줄바꿈으로 여러 개)를 모두 '참고 웹사이트' 로. 겹치는 주소는 한 번만
    found = re.findall(r"https?://\S+", " ".join(str(row.get(k) or "") for k in LINK_FIELDS))
    lat, lng = row.get("위도"), row.get("경도")
    # recal.kr 은 공식 공지·주최 링크 뒤로 (다른 사이트가 없으면 그대로 첫 번째)
    extra = {"tags": tags, "links": cafe.order_links(cafe.parse_links(" ".join(found))[0])[:cafe.MAX_LINKS],
             "intro": clean_intro(row.get("팝업소개")), "intro_src": intro_source(row),
             "images": image_urls(row), "notion_id": _page_id(row.get("url")),
             "latlng": (float(lat), float(lng)) if lat and lng else None}
    return entry, extra, ""


LINK_FIELDS = ("공식공지", "출처", "주최링크", "참고링크")


def clean_intro(text) -> str:
    """Notion 의 팝업소개(마크다운 섞인 글) → 앱에 보여 줄 평문.

    줄바꿈(<br />)은 살리고, 마크다운 이스케이프(역슬래시 + [ ~ 등)와 링크 표기는 글자만 남긴다.
    전화번호·이메일은 저장하지 않으므로, 가려지는 줄(문의처 등)은 통째로 뺀다.
    """
    t = _known(text)
    if not t:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</?(?:b|i|u|em|strong|span|p|div)(?:\s[^>]*)?>", "", t, flags=re.I)
    t = re.sub(r"\[([^\]]*)\]\((?:<[^>]*>|[^)]*)\)", r"\1", t)   # [글자](주소) · [글자](<주소>) → 글자
    t = re.sub(r"\\([\[\]~*_#>`|\\-])", r"\1", t)                 # \[ → [
    lines = []
    for line in t.splitlines():
        if "●" in guard.mask(line):
            continue                     # 전화번호·이메일이 든 줄은 싣지 않는다
        lines.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()[:cafe.MAX_INTRO]


def intro_source(row: dict) -> str:
    """'소개출처' 칸의 첫 주소. 소개가 없으면 출처도 두지 않는다."""
    if not clean_intro(row.get("팝업소개")):
        return ""
    m = re.search(r"https?://[^\s<>()\]]+", str(row.get("소개출처") or ""))
    return m.group(0) if m else ""


def _intro_by_person(store, entry_id: str) -> bool:
    """이 카페의 지금 팝업 소개를 사람이 (앱에서) 직접 쓴 것인지. 그렇다면 Notion 으로 덮어쓰지 않는다."""
    hist = sorted((r for r in store.all_rows() if str(r.get("entry_id")) == str(entry_id)),
                  key=lambda r: int(r.get("revision", 0)))
    prev = ""
    who = None
    for r in hist:
        cur = str(r.get("intro") or "").strip()
        if cur != prev:
            who = (str(r.get("editor") or ""), str(r.get("source") or ""))
        prev = cur
    return bool(who) and who[0] != "AI" and who[1] not in (SOURCE, "노션 자동 수집")


def expand_branches(row: dict) -> list[dict]:
    """'지점' 칸에 여러 곳이 적힌 행을 지점마다 한 행으로 나눈다. 한 곳뿐이거나 비었으면 그대로.

    주간 수집은 '행사 × 지점 = 1행' 으로 저장하고 '지점' 칸에는 형제 지점 전체를 적는다.
    그래서 이 행의 장소명이 목록 안에 있으면 형제 목록일 뿐이라 나누지 않는다 (형제는 각자 행으로 들어온다).
    장소명이 목록에 없을 때(예전 방식으로 한 행에 여러 지점을 적은 경우)만 나눈다.

    첫 지점은 원래 페이지 번호를 그대로 써서 예전에 가져온 행과 맞춰 보고,
    둘째부터는 '페이지번호-2' 처럼 따로 번호를 붙여 지점끼리 서로 '이미 있음' 으로 걸리지 않게 한다.
    """
    lines = [x.strip() for x in str(row.get("지점") or "").splitlines() if x.strip() and "|" in x]
    if len(lines) < 2:
        return [row]
    norm = lambda t: re.sub(r"\s+", "", str(t or ""))
    if norm(row.get("장소명")) in {norm(x.split("|")[0]) for x in lines}:
        return [row]
    base = _page_id(row.get("url"))
    out = []
    for i, line in enumerate(lines):
        parts = [x.strip() for x in line.split("|")]
        nums = [x for x in parts[1:] if re.fullmatch(r"-?\d+(?:\.\d+)?", x)]
        rest = [x for x in parts[1:] if x not in nums and not x.startswith("(")]
        b = dict(row)
        b["장소명"] = parts[0]
        b["주소"] = rest[-1] if rest else parts[0]
        b["위도"], b["경도"] = (nums[0], nums[1]) if len(nums) >= 2 else (None, None)
        b["url"] = row.get("url") if i == 0 else f"notion-{base}-{i + 1}"
        b["__branch_of__"] = base
        out.append(b)
    return out


def image_urls(row: dict) -> list[str]:
    """'이미지' 칸(공백·쉼표·줄바꿈으로 여러 개)과 파일 칸('__files__')의 주소들. 순서대로, 중복 없이."""
    urls = re.findall(r"https?://[^\s,]+", str(row.get("이미지") or "")) + list(row.get("__files__") or [])
    return list(dict.fromkeys(urls))


def _near(r: dict, latlng: tuple[float, float] | None, km: float = 0.5) -> bool:
    """앱 행의 좌표가 latlng 에서 km 안에 있는지. 어느 쪽이든 좌표가 없으면 False."""
    try:
        lat, lng = float(r.get("lat")), float(r.get("lng"))
    except (TypeError, ValueError):
        return False
    if not latlng:
        return False
    # 짧은 거리라 평면 근사로 충분하다 (위도 1도 ≈ 111km, 경도 1도 ≈ 111km × cos(위도))
    dy = (lat - latlng[0]) * 111.0
    dx = (lng - latlng[1]) * 111.0 * math.cos(math.radians(lat))
    return math.hypot(dx, dy) <= km


def _district(address) -> str:
    """주소의 시·구 ('서울 서대문구 연세로 13' → '서울 서대문구'). 못 찾으면 빈 문자열."""
    words = str(address or "").split()
    for a, b in zip(words, words[1:]):
        if re.fullmatch(r"[가-힣]+(?:구|군)", b):
            return f"{a[:2]} {b}"
    return ""


def _match(store_rows: list[dict], entry: CafeEntry, notion_id: str,
           latlng: tuple[float, float] | None = None, all_rows: list[dict] | None = None) -> dict | None:
    """이미 있는 같은 카페(같은 Notion 페이지, 같은 작품 + 같은 카페, 또는 같은 작품 + 같은 기간 + 같은 장소)의 최신 행.

    작품명이 '타네무라 아리나' / '타네무라 아리나 30주년' 처럼 조금 달라도 한쪽이 다른 쪽을 품고
    시작·종료일이 똑같고 위치가 500m 안이면 같은 행사로 본다 (직접 등록한 걸 Notion 에서 또 가져오지 않게).
    위치까지 보는 건, 같은 행사를 지점별(홍대점·부산점)로 나눠 적은 행을 중복으로 버리지 않기 위해서다.
    """
    # 같은 Notion 페이지: 앱에서 고친 뒤의 최신 행에는 표시가 없을 수 있어 예전 기록까지 본다
    ids = {str(r.get("entry_id")) for r in (all_rows or store_rows) if _has_id(r, notion_id)}
    for r in store_rows:
        if str(r.get("entry_id")) in ids:
            return r
    norm = lambda s: re.sub(r"\s+", "", str(s or ""))
    for r in store_rows:
        # 카페명은 띄어쓰기만 다른 경우('서울합정점' / '서울 합정점')도 같다고 본다
        if _work(r.get("work")) == entry.work and norm(r.get("cafe_name")) == norm(entry.cafe_name):
            return r
    for r in store_rows:
        a, b = norm(_work(r.get("work"))), norm(entry.work)
        same_work = a and b and (a in b or b in a)
        # 같은 작품을 같은 곳에서 기간이 겹치게 두 번 하지는 않으니, Notion 이 날짜를 고쳤어도 같은 행사다
        overlap = str(r.get("start_date"))[:10] <= entry.end_date.isoformat() \
            and entry.start_date.isoformat() <= str(r.get("end_date"))[:10]
        # 같은 곳: 좌표가 500m 안이거나, 도로명 주소('양화로 188')가 같으면 (앱 쪽 좌표가 대략 위치일 수 있다)
        road = _road(r.get("address"))
        if same_work and overlap and (_near(r, latlng) or (road and road == _road(entry.address))):
            return r
    for r in store_rows:
        # 같은 작품을 같은 시·구에서 시작·종료일까지 똑같이 하면 같은 행사다
        # (매장 이름·주소 표기가 'SMG CAFE 신촌점 / 연세로 13' 과 '현대백화점 신촌점 유플렉스 / 신촌로 83' 처럼 달라도)
        same_days = str(r.get("start_date"))[:10] == entry.start_date.isoformat()             and str(r.get("end_date"))[:10] == entry.end_date.isoformat()
        d = _district(r.get("address"))
        if _work(r.get("work")) == entry.work and same_days and d and d == _district(entry.address):
            return r
    return None


def _road(address) -> str:
    """주소의 도로명 + 번지 ('서울 마포구 양화로 188 5층' → '양화로188'). 없으면 빈 문자열."""
    m = re.search(r"([가-힣A-Za-z0-9]+(?:로|길))\s*(\d+(?:-\d+)?)", str(address or ""))
    return f"{m.group(1)}{m.group(2)}" if m else ""


def _download(urls: list[str]) -> list[str]:
    """이미지들을 내려받아 저장한다. 첫 장이 포스터. 실패한 장은 건너뛴다."""
    import requests

    saved = []
    for i, url in enumerate(urls[: 1 + images.MAX_EXTRAS]):
        try:
            res = requests.get(url, timeout=15)
            res.raise_for_status()
            if images.too_big(res.content, images.POSTER_MB if i == 0 else images.EXTRA_MB):
                continue
            ext = (re.search(r"\.(png|jpe?g|webp|gif)(?:$|\?)", url.lower()) or [None, "jpg"])[1]
            saved.append(images.save(f"image.{ext}", res.content))
        except Exception:
            continue        # 이미지는 없어도 등록한다 (기본 그림이 보인다)
    return saved


def import_rows(store, rows: list[dict], today: date, fill_images: bool = True) -> dict:
    """행들을 앱 저장소에 넣는다. {'added': [...], 'skipped': [(이름, 이유)]} 를 돌려준다.

    fill_images 가 False 면 이미 있는 행은 이미지도 건드리지 않고 새 행만 넣는다.
    """
    report = {"added": [], "skipped": []}
    rows = [b for row in rows for b in expand_branches(row)]
    for row in rows:
        name = f"{row.get('작품명')} · {row.get('장소명')}"
        entry, extra, why = entry_from_row(row)
        if entry is None:
            report["skipped"].append((name, why))
            continue
        # 위치: Notion 에 위도·경도가 있으면 그대로 쓰고, 없으면 주소로 찾는다
        if extra["latlng"]:
            g = geo.GeoResult(ok=True, lat=extra["latlng"][0], lng=extra["latlng"][1],
                              precision="exact", matched="Notion 좌표")
        else:
            g = geo.geocode(entry.address)
        latlng = (g.lat, g.lng) if g.ok else None
        found = _match(store.current_rows(), entry, extra["notion_id"], latlng, all_rows=store.all_rows())
        if found:
            # 앱 쪽에 이미지·팝업 소개가 비어 있고 Notion 에 있으면 그 칸만 채운다 (다른 칸은 그대로)
            saved = (_download(extra["images"]) if fill_images and not images.split(found.get("images"))
                     and extra["images"] else [])
            # 팝업 소개는 Notion 기준 (바뀌면 바꾸고, Notion 에서 지웠으면 비운다). 사람이 앱에서 쓴 소개는 그대로
            intro = None if _intro_by_person(store, found["entry_id"]) else extra["intro"]
            before = str(found.get("intro") or "").strip()
            if fill_found(store, found, intro=intro, images_=saved,
                          intro_src=None if intro is None else extra["intro_src"]):
                if saved:
                    report.setdefault("images", []).append((name, len(saved)))
                if intro is not None and intro != before:
                    report.setdefault("intros", []).append(name)
                continue
            report["skipped"].append((name, "이미 있음"))
            continue
        if any(_has_id(r, extra['notion_id']) for r in store.all_rows()):
            report["skipped"].append((name, "예전에 가져왔다가 내린 항목"))
            continue
        v = guard.validate_cafe(entry, today=today, existing=store.current_rows())
        if not v.ok or not g.ok:
            report["skipped"].append((name, "; ".join(v.errors) or g.note))
            continue
        saved = _download(extra["images"])
        store.append(cafe.entry_to_row(
            entry, g.lat, g.lng, source=SOURCE, editor="AI",
            note=f"{g.badge} ({g.matched}) | notion:{extra['notion_id']}",
            images=saved, tags=extra["tags"], links=extra["links"], intro=extra["intro"],
            intro_src=extra["intro_src"]))
        report["added"].append(name)
    return report


def fill_found(store, found: dict, intro: str | None = None, images_: list[str] | None = None,
               intro_src: str | None = None) -> bool:
    """이미 있는 카페의 빈 이미지를 채우고, 팝업 소개를 intro 로 맞춰 새 행으로 쌓는다 (intro=None 이면 소개는 그대로).
    바뀐 게 있으면 True."""
    payload = {k: found.get(k, "") for k in store.headers
               if k not in ("row_id", "entry_id", "revision", "status", "updated_at")}
    changed = False
    if images_ and not images.split(found.get("images")):
        payload["images"], changed = ", ".join(images_), True
    if intro is not None and guard.mask(intro)[:cafe.MAX_INTRO] != str(found.get("intro") or "").strip():
        payload["intro"], changed = guard.mask(intro)[:cafe.MAX_INTRO], True
    if intro_src is not None and intro_src != str(found.get("intro_src") or ""):
        payload["intro_src"], changed = intro_src, True
    if not changed:
        return False
    payload.update(source=SOURCE, editor="AI")      # 수정 이력에 'AI 자동 수집 · AI' 로 남는다
    store.append(payload, entry_id=str(found["entry_id"]))
    return True


def sync_intros(store, rows: list[dict]) -> dict:
    """Notion 행들의 팝업소개로, 예전에 가져온 카페의 팝업 소개를 Notion 기준으로 맞춘다.
    {'updated': [...], 'cleared': [...], 'kept': [...]} (kept: 사람이 앱에서 쓴 소개라 그대로 둔 곳)."""
    out = {"updated": [], "cleared": [], "kept": []}
    for row in rows:
        nid, intro, src = _page_id(row.get("url")), clean_intro(row.get("팝업소개")), intro_source(row)
        ids = {str(r.get("entry_id")) for r in store.all_rows() if _has_id(r, nid)}
        found = next((r for r in store.current_rows() if str(r.get("entry_id")) in ids), None)
        if not found:
            continue
        name = f"{found.get('work')} · {found.get('cafe_name')}"
        before = str(found.get("intro") or "").strip()
        if before == intro and str(found.get("intro_src") or "") == src:
            continue
        if _intro_by_person(store, found["entry_id"]):
            out["kept"].append(name)
            continue
        if fill_found(store, found, intro=intro, intro_src=src):
            out["cleared" if not intro else "updated"].append(name)
    return out


# ------------------------------------------------------------ Notion API
def _flatten(page: dict) -> dict:
    """Notion API 의 페이지 → entry_from_row 가 받는 평평한 행."""
    out = {"url": page.get("url", "")}
    for name, prop in (page.get("properties") or {}).items():
        t = prop.get("type")
        if t in ("title", "rich_text"):
            out[name] = "".join(x.get("plain_text", "") for x in prop.get(t) or [])
        elif t == "select":
            out[name] = (prop.get("select") or {}).get("name", "")
        elif t == "url":
            out[name] = prop.get("url") or ""
        elif t == "number":
            out[name] = prop.get("number")
        elif t == "files":
            # '파일과 미디어' 칸: 올린 파일(file)과 링크(external) 주소를 모두 모은다
            out.setdefault("__files__", [])
            for fobj in prop.get("files") or []:
                u = (fobj.get("file") or fobj.get("external") or {}).get("url")
                if u:
                    out["__files__"].append(u)
        elif t == "date":
            d = prop.get("date") or {}
            out[f"date:{name}:start"], out[f"date:{name}:end"] = d.get("start"), d.get("end")
    return out


def fetch_rows(token: str) -> list[dict]:
    import requests

    rows, cursor = [], None
    while True:
        body = {"page_size": 100, **({"start_cursor": cursor} if cursor else {})}
        res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
                            headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28",
                                     "Content-Type": "application/json"},
                            json=body, timeout=15)
        res.raise_for_status()
        data = res.json()
        rows += [_flatten(p) for p in data.get("results", [])]
        if not data.get("has_more"):
            return rows
        cursor = data.get("next_cursor")


def maybe_sync(store, today: date) -> dict | None:
    """키가 있고 마지막 확인에서 SYNC_EVERY 가 지났으면 가져온다. 안 했으면 None."""
    token = os.getenv("NOTION_TOKEN")
    if not token:
        return None
    now = datetime.now(timezone.utc)
    try:
        last = datetime.fromisoformat(json.loads(STATE_FILE.read_text(encoding="utf-8"))["last"])
        if now - last < SYNC_EVERY:
            return None
    except Exception:
        pass
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"last": now.isoformat()}), encoding="utf-8")
    try:
        return import_rows(store, fetch_rows(token), today)
    except Exception as exc:
        return {"added": [], "skipped": [], "error": str(exc)}
