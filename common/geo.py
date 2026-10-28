"""주소를 지도 좌표로 바꾼다.

세 가지 경로를 차례로 쓴다.
  1) KAKAO_REST_API_KEY 가 있으면 카카오 로컬 API 로 정확히 변환
  2) NAVER_MAPS_CLIENT_ID/SECRET 가 있으면 네이버 클라우드 지오코딩으로 정확히 변환
  3) 키가 없으면 아래 표에서 지역명을 찾아 그 동네 중심 좌표를 쓴다

등록 화면의 '주소 검색' 은 search() 를 쓴다. 카카오 주소 검색(도로명·지번 주소)과
키워드 장소 검색(가게·건물 이름)을 함께 돌려 후보를 보여 준다. 카카오 키가 없으면 네이버를 쓴다.

2) 는 "OO역 3번 출구 도보 5분" 같은 약식 주소를 위해서도 필요하다.
   좌표가 근사값이므로 화면에 '대략 위치'로 표시한다.
   README 만 보고 바로 돌려볼 수 있어야 해서 키 없이도 동작하게 만들었다.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from common import guard

# 지역 중심 좌표(근사값). 정확한 번지 좌표가 아니라 '그 동네' 를 가리킨다.
GAZETTEER: dict[str, tuple[float, float]] = {
    # 서울
    "강남": (37.5172, 127.0473), "서초": (37.4837, 127.0324), "송파": (37.5145, 127.1059),
    "잠실": (37.5133, 127.1000), "마포": (37.5663, 126.9019), "홍대": (37.5563, 126.9236),
    "합정": (37.5497, 126.9136), "연남": (37.5637, 126.9256), "성동": (37.5634, 127.0369),
    "성수": (37.5447, 127.0557), "광진": (37.5385, 127.0823), "건대": (37.5403, 127.0695),
    "종로": (37.5730, 126.9794), "명동": (37.5636, 126.9850), "을지로": (37.5660, 126.9910),
    "용산": (37.5324, 126.9900), "이태원": (37.5345, 126.9946), "영등포": (37.5264, 126.8963),
    "여의도": (37.5219, 126.9245), "강서": (37.5509, 126.8495), "관악": (37.4784, 126.9516),
    "신촌": (37.5551, 126.9368), "이대": (37.5569, 126.9459), "동대문": (37.5744, 127.0396),
    "노원": (37.6542, 127.0568), "은평": (37.6027, 126.9291), "구로": (37.4954, 126.8874),
    "금천": (37.4569, 126.8956), "강동": (37.5301, 127.1238), "중랑": (37.6066, 127.0927),
    "서대문": (37.5791, 126.9368), "양천": (37.5170, 126.8665), "도봉": (37.6688, 127.0471),
    "강북": (37.6396, 127.0257), "성북": (37.5894, 127.0167), "동작": (37.5124, 126.9393),
    # 경기 · 인천
    "수원": (37.2636, 127.0286), "성남": (37.4200, 127.1267), "분당": (37.3595, 127.1052),
    "판교": (37.3948, 127.1112), "용인": (37.2411, 127.1776), "고양": (37.6584, 126.8320),
    "일산": (37.6584, 126.7700), "부천": (37.5035, 126.7660), "안양": (37.3943, 126.9568),
    "송도": (37.3826, 126.6569), "의정부": (37.7381, 127.0337),
    # 그 밖의 도시
    "서면": (35.1578, 129.0595), "해운대": (35.1631, 129.1635),
    "동성로": (35.8690, 128.5950), "둔산": (36.3520, 127.3780),
    "창원": (35.2280, 128.6811), "전주": (35.8242, 127.1480),
    "천안": (36.8151, 127.1139), "청주": (36.6424, 127.4890),
    # 서울 나머지 동네
    "광화문": (37.5759, 126.9768), "압구정": (37.5271, 127.0286),
    "신사": (37.5163, 127.0203), "가로수길": (37.5207, 127.0230), "삼성": (37.5089, 127.0631),
    "코엑스": (37.5116, 127.0595), "왕십리": (37.5612, 127.0371), "신림": (37.4842, 126.9297),
    "목동": (37.5268, 126.8751), "상암": (37.5794, 126.8895), "망원": (37.5560, 126.9101),
    # 경기 · 인천 나머지
    "하남": (37.5393, 127.2149), "스타필드": (37.5452, 127.2240), "김포": (37.6153, 126.7156),
    "파주": (37.7600, 126.7802), "광명": (37.4786, 126.8646), "시흥": (37.3800, 126.8029),
    "안산": (37.3219, 126.8309), "화성": (37.1995, 126.8312), "동탄": (37.2006, 127.0745),
    "평택": (36.9921, 127.1129), "오산": (37.1498, 127.0773), "군포": (37.3616, 126.9352),
    "의왕": (37.3448, 126.9683), "과천": (37.4292, 126.9876), "구리": (37.5943, 127.1296),
    "남양주": (37.6360, 127.2165), "광주시": (37.4295, 127.2550), "이천": (37.2720, 127.4350),
    "여주": (37.2984, 127.6374), "양주": (37.7853, 127.0458), "포천": (37.8949, 127.2003),
    "동두천": (37.9036, 127.0606), "가평": (37.8315, 127.5105), "양평": (37.4917, 127.4875),
    "안성": (37.0080, 127.2797), "광교": (37.2850, 127.0446), "부평": (37.5070, 126.7219),
    "청라": (37.5326, 126.6450), "영종": (37.4925, 126.4930),
    # 강원 · 충청 · 전라 · 경상
    "춘천": (37.8813, 127.7298), "원주": (37.3422, 127.9202), "강릉": (37.7519, 128.8761),
    "속초": (38.2070, 128.5918), "세종": (36.4800, 127.2890), "아산": (36.7898, 127.0018),
    "공주": (36.4465, 127.1190), "충주": (36.9910, 127.9259), "군산": (35.9677, 126.7366),
    "익산": (35.9483, 126.9577), "목포": (34.8118, 126.3922), "여수": (34.7604, 127.6622),
    "순천": (34.9506, 127.4872), "포항": (36.0190, 129.3435), "경주": (35.8562, 129.2247),
    "구미": (36.1195, 128.3446), "안동": (36.5684, 128.7294), "김해": (35.2285, 128.8894),
    "진주": (35.1800, 128.1076), "양산": (35.3350, 129.0371), "거제": (34.8806, 128.6211),
    "서귀포": (33.2541, 126.5600), "세종대로": (37.5704, 126.9769),
}

# 시·도·광역시. GAZETTEER 에서 못 찾았을 때만 쓴다.
# "경기도 김포시" 처럼 시·도 이름이 더 길어도 구체적인 동네가 먼저 걸리게 하려고 따로 둔다.
PROVINCES: dict[str, tuple[float, float]] = {
    "서울": (37.5665, 126.9780), "인천": (37.4563, 126.7052), "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014), "대전": (36.3504, 127.3845), "광주": (35.1595, 126.8526),
    "울산": (35.5384, 129.3114), "제주": (33.4996, 126.5312),
    "서울특별시": (37.5665, 126.9780), "경기도": (37.2752, 127.0095), "경기": (37.2752, 127.0095),
    "인천광역시": (37.4563, 126.7052), "강원": (37.8854, 127.7298), "충청북도": (36.6357, 127.4917),
    "충북": (36.6357, 127.4917), "충청남도": (36.6588, 126.6728), "충남": (36.6588, 126.6728),
    "전라북도": (35.8203, 127.1088), "전북": (35.8203, 127.1088), "전라남도": (34.8161, 126.4630),
    "전남": (34.8161, 126.4630), "경상북도": (36.5760, 128.5056), "경북": (36.5760, 128.5056),
    "경상남도": (35.2383, 128.6925), "경남": (35.2383, 128.6925),
}


@dataclass
class GeoResult:
    ok: bool
    lat: float | None = None
    lng: float | None = None
    precision: str = "none"     # "exact" | "approx" | "none"
    matched: str = ""
    note: str = ""

    @property
    def badge(self) -> str:
        return {"exact": "정확한 주소", "approx": "대략 위치", "none": "좌표 없음"}[self.precision]


def geocode(address: str) -> GeoResult:
    """주소 문자열 → 좌표. 실패해도 예외를 던지지 않는다."""
    address = (address or "").strip()
    if not address:
        return GeoResult(ok=False, note="주소가 비어 있습니다.")

    key = _kakao_key()
    if key:
        result = _kakao(address, key)
        if result.ok:
            return result
        # 카카오가 못 찾으면 네이버, 그다음 아래 표로 한 번 더 시도한다.

    if _naver_maps_keys():
        found = _naver_geocode(address)
        if found.ok and found.candidates:
            c = found.candidates[0]
            return GeoResult(ok=True, lat=c.lat, lng=c.lng, precision="exact", matched=c.address)

    return _from_gazetteer(address)


def _kakao_key() -> str | None:
    return os.getenv("KAKAO_REST_API_KEY") or None


def _kakao(address: str, key: str) -> GeoResult:
    address = guard.mask(address)
    try:
        import requests

        res = requests.get(
            "https://dapi.kakao.com/v2/local/search/address.json",
            headers={"Authorization": f"KakaoAK {key}"},
            params={"query": address},
            timeout=5,
        )
        res.raise_for_status()
        docs = res.json().get("documents", [])
        if not docs:
            # 주소로 못 찾으면 장소 이름으로 다시 찾는다 ("OO역", 가게 이름)
            res = requests.get(
                "https://dapi.kakao.com/v2/local/search/keyword.json",
                headers={"Authorization": f"KakaoAK {key}"},
                params={"query": address, "size": 1},
                timeout=5,
            )
            res.raise_for_status()
            docs = res.json().get("documents", [])
        if docs:
            return GeoResult(
                ok=True, lat=float(docs[0]["y"]), lng=float(docs[0]["x"]),
                precision="exact", matched=docs[0].get("address_name", address),
            )
    except Exception as exc:
        return GeoResult(ok=False, note=f"카카오 API 호출 실패: {exc}")
    return GeoResult(ok=False, note="카카오에서 주소를 찾지 못했습니다.")


# -------------------------------------------------------------- 네이버 주소 검색
@dataclass
class Candidate:
    """주소 검색 후보 하나. 고르면 주소와 좌표를 그대로 쓴다."""
    name: str           # 가게·건물 이름 (주소 검색 결과면 비어 있음)
    address: str        # 도로명 주소, 없으면 지번 주소
    lat: float
    lng: float
    source: str         # "카카오맵" | "카카오 우편번호" | "네이버 지도" | "네이버 지역 검색"
    precision: str = "exact"    # 우편번호로 고른 주소는 좌표를 따로 찾으므로 "approx"·"none" 일 수 있다

    @property
    def label(self) -> str:
        return f"{self.name} · {self.address}" if self.name else self.address


@dataclass
class SearchResult:
    ok: bool
    candidates: list[Candidate] = field(default_factory=list)
    note: str = ""


def _naver_maps_keys() -> tuple[str, str] | None:
    cid, secret = os.getenv("NAVER_MAPS_CLIENT_ID"), os.getenv("NAVER_MAPS_CLIENT_SECRET")
    return (cid, secret) if cid and secret else None


def _naver_search_keys() -> tuple[str, str] | None:
    cid, secret = os.getenv("NAVER_SEARCH_CLIENT_ID"), os.getenv("NAVER_SEARCH_CLIENT_SECRET")
    return (cid, secret) if cid and secret else None


def search_available() -> bool:
    return bool(_kakao_key() or _naver_maps_keys() or _naver_search_keys())


def search(query: str) -> SearchResult:
    """주소나 가게 이름으로 후보를 찾는다. 키가 없거나 호출이 실패해도 예외를 던지지 않는다."""
    query = (query or "").strip()
    if not query:
        return SearchResult(ok=False, note="검색어를 입력해 주세요.")
    if not search_available():
        return SearchResult(ok=False, note="카카오 API 키가 없어 주소 검색을 쓸 수 없습니다. "
                                           ".env 에 KAKAO_REST_API_KEY 를 넣어 주세요.")
    query = guard.mask(query)

    # 카카오가 있으면 카카오만 쓴다. 없을 때만 네이버로 찾는다
    callers = ([(True, _kakao_search)] if _kakao_key()
               else [(_naver_maps_keys(), _naver_geocode), (_naver_search_keys(), _naver_local)])
    found: list[Candidate] = []
    errors: list[str] = []
    for enabled, call in callers:
        if not enabled:
            continue
        r = call(query)
        found += [c for c in r.candidates if c.address not in {f.address for f in found}]
        if not r.ok and r.note:
            errors.append(r.note)
    if found:
        return SearchResult(ok=True, candidates=found)
    return SearchResult(ok=False, note=" / ".join(errors) or "검색 결과가 없습니다. 다른 이름이나 주소로 찾아 보세요.")


def _kakao_search(query: str) -> SearchResult:
    """카카오 로컬 API. 주소 검색(도로명·지번)과 키워드 장소 검색(가게·건물 이름)을 함께 돌린다."""
    headers = {"Authorization": f"KakaoAK {_kakao_key()}"}
    out: list[Candidate] = []
    try:
        import requests

        res = requests.get("https://dapi.kakao.com/v2/local/search/address.json",
                           headers=headers, params={"query": query, "size": 5}, timeout=5)
        res.raise_for_status()
        for d in res.json().get("documents", []):
            road = d.get("road_address") or {}
            out.append(Candidate(name=road.get("building_name", ""),
                                 address=road.get("address_name") or d.get("address_name", ""),
                                 lat=float(d["y"]), lng=float(d["x"]), source="카카오맵"))

        res = requests.get("https://dapi.kakao.com/v2/local/search/keyword.json",
                           headers=headers, params={"query": query, "size": 5}, timeout=5)
        res.raise_for_status()
        for d in res.json().get("documents", []):
            out.append(Candidate(name=d.get("place_name", ""),
                                 address=d.get("road_address_name") or d.get("address_name", ""),
                                 lat=float(d["y"]), lng=float(d["x"]), source="카카오맵"))
    except Exception as exc:
        return SearchResult(ok=bool(out), candidates=out, note=f"카카오 검색 호출 실패: {exc}")
    return SearchResult(ok=True, candidates=out)


def _naver_geocode(query: str) -> SearchResult:
    """네이버 클라우드 Maps 지오코딩. 도로명·지번 주소에 강하다."""
    cid, secret = _naver_maps_keys()
    host = os.getenv("NAVER_MAPS_API_HOST", "https://naveropenapi.apigw.gov-ntruss.com")
    try:
        import requests

        res = requests.get(
            f"{host}/map-geocode/v2/geocode",
            headers={"x-ncp-apigw-api-key-id": cid, "x-ncp-apigw-api-key": secret,
                     "Accept": "application/json"},
            params={"query": query, "count": 5},
            timeout=5,
        )
        res.raise_for_status()
        items = res.json().get("addresses", [])
    except Exception as exc:
        return SearchResult(ok=False, note=f"네이버 지오코딩 호출 실패: {exc}")
    return SearchResult(ok=True, candidates=[
        Candidate(name="", address=a.get("roadAddress") or a.get("jibunAddress", ""),
                  lat=float(a["y"]), lng=float(a["x"]), source="네이버 지도")
        for a in items if a.get("x") and a.get("y")
    ])


def _naver_local(query: str) -> SearchResult:
    """네이버 검색 API 지역 검색. '홍대 카페 솔' 처럼 가게 이름으로 찾을 때 쓴다."""
    cid, secret = _naver_search_keys()
    try:
        import requests

        res = requests.get(
            "https://openapi.naver.com/v1/search/local.json",
            headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret},
            params={"query": query, "display": 5},
            timeout=5,
        )
        res.raise_for_status()
        items = res.json().get("items", [])
    except Exception as exc:
        return SearchResult(ok=False, note=f"네이버 지역 검색 호출 실패: {exc}")
    out = []
    for it in items:
        try:
            # mapx·mapy 는 경위도에 10^7 을 곱한 정수다
            lng, lat = int(it["mapx"]) / 1e7, int(it["mapy"]) / 1e7
        except (KeyError, ValueError):
            continue
        out.append(Candidate(
            name=re.sub(r"<[^>]+>", "", it.get("title", "")),
            address=it.get("roadAddress") or it.get("address", ""),
            lat=lat, lng=lng, source="네이버 지역 검색",
        ))
    return SearchResult(ok=True, candidates=out)


def _from_gazetteer(address: str) -> GeoResult:
    # 동네 표를 먼저, 그다음 시·도 표를 본다. 각 표 안에서는 긴 이름부터 맞춰본다
    for table in (GAZETTEER, PROVINCES):
        name = next((n for n in sorted(table, key=len, reverse=True) if n in address), None)
        if name:
            lat, lng = table[name]
            return GeoResult(
                ok=True, lat=lat, lng=lng, precision="approx", matched=name,
                note=f"'{name}' 지역 중심 좌표로 표시합니다. 정확한 위치가 아닙니다.",
            )
    return GeoResult(
        ok=False, precision="none",
        note="아는 지역 이름이 없어 지도에 올릴 수 없습니다. 시/구 이름을 넣어 주세요.",
    )


# 서울·경기 밖 광역시. 이 도시 주소는 동네(서면·동성로) 대신 도시 이름으로 보여 준다
_METRO_CITIES = ("부산", "대구", "대전", "울산", "인천", "세종")
# 광역시 안의 동네 → 도시 ('부산 서면' 이 아니라 '서면 카페 모모' 처럼 도시 이름 없이 적은 주소용)
_CITY_OF = {"서면": "부산", "해운대": "부산", "동성로": "대구", "둔산": "대전",
            "송도": "인천", "부평": "인천", "청라": "인천", "영종": "인천"}
_CAPITAL = ("서울", "경기")


def area_name(address: str) -> str:
    """카드 왼쪽 위 지역 배지용 짧은 이름. 모르면 빈 문자열.

    서울·경기는 동네 이름('홍대', '판교'), 그 밖의 지역은 시 이름('부산', '창원')으로 보여 준다.
    """
    address = (address or "").strip()
    # 1) 광역시로 시작하는 주소는 동네와 상관없이 도시 이름 ('부산 강서구' 가 서울 '강서' 로 잡히지 않게)
    if address.startswith("광주광역시") or re.match(r"광주\s+(?:광산|북|남|동|서)구", address):
        return "광주"
    for city in _METRO_CITIES:
        if address.startswith(city):
            return city
    # 2) 동네·도시 사전. 광역시 안의 동네면 도시로 바꾼다
    name = next((n for n in sorted(GAZETTEER, key=len, reverse=True) if n in address), None)
    if name:
        return _CITY_OF.get(name, name)
    # 3) 서울·경기 밖에서 사전에 없는 시는 'OO시' 를 그대로 쓴다 ('경남 통영시' → '통영')
    if not address.startswith(_CAPITAL):
        m = re.search(r"([가-힣]{2,})시(?:\s|$)", address)
        if m and not m.group(1).endswith(("특별", "광역", "자치")):
            return m.group(1)
    name = next((n for n in sorted(PROVINCES, key=len, reverse=True) if n in address), None)
    return name.replace("특별시", "").replace("광역시", "") if name else ""
