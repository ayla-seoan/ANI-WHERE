"""Notion '🎀 애니 팝업·콜라보 트래커' DB 에 매주 쌓이는 행사를 앱으로 자동으로 가져온다.

- NOTION_TOKEN(Notion 내부 통합 키)이 있을 때만 동작한다. DB 를 그 통합에 '연결' 해 두어야 읽을 수 있다.
- 메인 화면을 열 때 최대 SYNC_EVERY 마다 한 번 확인한다 (마지막 확인 시각은 data/notion_sync.json).
- 검수상태가 '검토 완료' 이고 기간(시작·종료)이 있는 행만 가져온다.
- 이미 가져온 Notion 페이지이거나, 같은 작품 + 같은 카페가 이미 있으면 새로 만들지 않는다.
  다만 앱 쪽에 이미지가 없고 Notion 에 이미지가 있으면 이미지만 채운다.
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
SOURCE = "노션 자동 수집"
UNKNOWN = ("확인 필요", "미확인", "")



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
    m = re.search(r"([0-9a-f]{32})", str(url or "").replace("-", ""))
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
    extra = {"tags": tags, "links": cafe.parse_links(" ".join(found))[0][:cafe.MAX_LINKS],
             "images": image_urls(row), "notion_id": _page_id(row.get("url")),
             "latlng": (float(lat), float(lng)) if lat and lng else None}
    return entry, extra, ""


LINK_FIELDS = ("출처", "주최링크", "참고링크")


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


def _match(store_rows: list[dict], entry: CafeEntry, notion_id: str,
           latlng: tuple[float, float] | None = None) -> dict | None:
    """이미 있는 같은 카페(같은 Notion 페이지, 같은 작품 + 같은 카페, 또는 같은 작품 + 같은 기간 + 같은 장소)의 최신 행.

    작품명이 '타네무라 아리나' / '타네무라 아리나 30주년' 처럼 조금 달라도 한쪽이 다른 쪽을 품고
    시작·종료일이 똑같고 위치가 500m 안이면 같은 행사로 본다 (직접 등록한 걸 Notion 에서 또 가져오지 않게).
    위치까지 보는 건, 같은 행사를 지점별(홍대점·부산점)로 나눠 적은 행을 중복으로 버리지 않기 위해서다.
    """
    for r in store_rows:
        if notion_id and f"notion:{notion_id}" in str(r.get("note") or ""):
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
        found = _match(store.current_rows(), entry, extra["notion_id"], latlng)
        if found:
            # 앱 쪽에 이미지가 없고 Notion 에 이미지가 있으면 이미지만 채운다 (다른 칸은 그대로)
            if fill_images and not images.split(found.get("images")) and extra["images"]:
                saved = _download(extra["images"])
                if saved:
                    payload = {k: found.get(k, "") for k in store.headers
                               if k not in ("row_id", "entry_id", "revision", "status", "updated_at")}
                    payload["images"] = ", ".join(saved)
                    store.append(payload, entry_id=str(found["entry_id"]))
                    report.setdefault("images", []).append((name, len(saved)))
                    continue
            report["skipped"].append((name, "이미 있음"))
            continue
        if any(f"notion:{extra['notion_id']}" in str(r.get("note") or "") for r in store.all_rows()):
            report["skipped"].append((name, "예전에 가져왔다가 내린 항목"))
            continue
        v = guard.validate_cafe(entry, today=today, existing=store.current_rows())
        if not v.ok or not g.ok:
            report["skipped"].append((name, "; ".join(v.errors) or g.note))
            continue
        saved = _download(extra["images"])
        store.append(cafe.entry_to_row(
            entry, g.lat, g.lng, source=SOURCE,
            note=f"{g.badge} ({g.matched}) | notion:{extra['notion_id']}",
            images=saved, tags=extra["tags"], links=extra["links"]))
        report["added"].append(name)
    return report


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
