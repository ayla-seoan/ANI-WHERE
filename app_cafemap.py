"""주제 2 — 애니메이션 캐릭터 팝업 카페 위키 지도.

핵심 흐름 하나:
    공지 원문 붙여넣기 → AI 추출 → 사람이 확인·수정 → 검증 → 저장 → 지도에 즉시 노출

화면은 두 장이다.
    지도(메인)  — 왼쪽 카드 리스트 + 오른쪽 지도. 카드나 점을 고르면
                  왼쪽 패널이 상세로 바뀌고, 리뷰 게시판과 수정하기 탭이 열린다.
    등록하기    — 지도 위 버튼으로 들어가고, 저장하면 지도로 돌아온다.

위키형이라 누구나 등록·수정·삭제할 수 있다. 승인 대신 검증과 되돌리기로 막는다.
실행:  streamlit run app_cafemap.py
"""
from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import quote
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from common import (ai, cafe, catalog, favorite, gallery, geo, guard, images, kakao_map,
                    kakao_postcode, mycal, notice, notion_sync, review, share)
from common import locate as my_place   # 앱 안의 locate() (주소 → 좌표) 와 이름이 겹쳐서 따로 부른다
from common.schema import CafeEntry
from common.storage import Storage

load_dotenv()

ROOT = Path(__file__).resolve().parent
TODAY = date.today()
MAP_HEIGHT = 620
LOGOS = ["logo.png", "logo2.png"]   # static/ 의 제목 로고. 화면을 누를 때마다 다음 것으로 바뀐다
FIXED_LOGO = "logo2.png"           # 상세·등록 화면에서는 이 로고로 고정
TOPBAR_TOP = "0rem"      # 상단 고정 묶음이 붙는 위치 (Streamlit 상단 메뉴 줄은 숨겨서 맨 위)
TOPBAR_H = "282px"        # 상단 묶음 높이 (로고 + 문구 + 검색 필터. '팝업 카페 N곳' 줄은 묶음 밖)

# 바탕은 흰색, 포인트만 우유빛 민트. 기본 색은 .streamlit/config.toml, 여기는 글꼴·모양·카드처럼 설정으로 안 되는 것
MINT = "#56C2A7"
MINT_DEEP = "#2E9C82"
MINT_SOFT = "#E6F6F0"     # 포인트 배경 (배지·선택 상태 등 좁은 곳에만)
MINT_LINE = "#9EDDCC"     # 카드 테두리: 포인트(MINT)보다 살짝 밝은 민트
GRAY_SOFT = "#F4F6F5"     # 이미지 없는 칸, 업로드 칸 같은 기본 면
GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jua&display=swap');
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
/* @import 는 맨 앞에 와야 해서(앞에 다른 규칙이 있으면 폰트가 무시된다) 변수는 그 뒤에 둔다 */
/* 포인트 컬러 변수 (map-template.html 과 같은 값). 지도·등록하기 버튼 등이 쓴다 */
:root {{ --accent: #14b8a6; --accent-soft: #e6fbf7; --accent-deep: #0d9488; }}
html, body, [class*="st-"], .stMarkdown, button, input, textarea {{
  font-family: "Pretendard", -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; }}
/* 위의 글꼴 지정이 아이콘 글꼴까지 덮지 않게 (안 그러면 '_arrow_right' 같은 이름 글자가 보인다) */
[data-testid="stIconMaterial"], .material-symbols-rounded {{
  font-family: "Material Symbols Rounded" !important; }}
h1, h2, h3, h4, h5, .wiz-title {{ font-family: "Jua", "Pretendard", sans-serif !important;
  font-weight: 400 !important; letter-spacing: .01em; }}
/* 버튼: 동글동글한 알약 모양 */
.stButton button, .stLinkButton a, .stDownloadButton button {{ border-radius: 999px !important;
  font-weight: 600; transition: transform .12s, box-shadow .12s; }}
.stButton button:hover {{ transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,.08); }}
.stButton button[kind="primary"]:not(:disabled) {{ color: #fff; box-shadow: 0 3px 10px rgba(86,194,167,.35); }}
.stButton button:disabled {{ background: #edf5f2 !important; color: #9bb5ad !important;
  border-color: #dcebe6 !important; box-shadow: none; transform: none; }}
/* 내 리뷰의 '⋯' (누르면 수정·삭제): 글자만 있는 작은 버튼을 칸 오른쪽 끝에 붙이고, 펼침 화살표는 숨긴다 */
/* 칸(stColumn) 안의 세로 묶음까지 오른쪽으로 붙여야 실제로 오른쪽 끝에 선다 (리스트 전체보기 버튼과 같은 방법) */
[data-testid="stColumn"]:has([class*="st-key-rv_more_"]) [data-testid="stVerticalBlock"] {{ align-items: flex-end; }}
[class*="st-key-rv_more_"] {{ display: flex; justify-content: flex-end; width: auto !important; margin-left: auto; }}
[class*="st-key-rv_more_"] button {{ background: transparent !important; border: 0 !important;
  box-shadow: none !important; color: {MINT} !important; min-height: 0 !important;
  padding: 0 .2rem !important; }}
[class*="st-key-rv_more_"] button p {{ font-size: 1.6rem !important; font-weight: 400 !important;
  line-height: 1; letter-spacing: .04em; }}
[class*="st-key-rv_more_"] button:hover {{ color: {MINT_DEEP} !important; transform: none; }}
[class*="st-key-rv_more_"] button [data-testid="stIconMaterial"] {{ display: none; }}
/* 리스트 전체보기·지도보기: 글자에 맞는 너비로 오른쪽에 붙인다 */
[data-testid="stColumn"]:has(.st-key-list_only_btn, .st-key-show_map) [data-testid="stVerticalBlock"] {{
  align-items: flex-end; }}
.st-key-list_only_btn button, .st-key-show_map button {{ padding: 0 1.4rem !important; }}
/* 지도보기·리스트 전체보기: 흰 바탕에 민트 테두리·글자 */
.st-key-show_map button, .st-key-list_only_btn button {{ border: 1.5px solid {MINT} !important;
  color: {MINT_DEEP} !important; background: #fff !important; box-shadow: none !important; }}
.st-key-show_map button:hover, .st-key-list_only_btn button:hover {{ background: {MINT_SOFT} !important; }}
/* 상단 고정 묶음(제목·문구·버튼): 스크롤해도 늘 위에 붙어 있다.
   Streamlit 이 키 컨테이너를 같은 높이의 칸으로 한 번 더 감싸서, 바깥 칸에 sticky 를 건다 */
[data-testid="stLayoutWrapper"]:has(> .st-key-topbar) {{ position: sticky; top: {TOPBAR_TOP};
  z-index: 50; background: #fff; padding-bottom: .5rem; box-shadow: 0 8px 12px -12px rgba(0,0,0,.18); }}
/* 모바일(폭 640px 이하, 칸이 세로로 쌓이는 화면)에서는 위에 붙는 것 없이 그냥 함께 스크롤한다
   (메인·등록 화면의 상단 묶음, 메인의 지도 칸) */
@media (max-width: 640px) {{
  /* 세로로 쌓인 칸은 화면 폭을 다 쓴다. Streamlit 기본값(전체 폭 - 1.5rem)이면 오른쪽만 24px 비어
     지도·리스트가 왼쪽으로 쏠려 보였다. 한 줄로 둔 칸(카드 포스터·상세 제목 등)은 더 구체적인 규칙이 덮어쓴다 */
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width: 100% !important; min-width: 100% !important; flex: 1 1 100% !important; }}
  [data-testid="stLayoutWrapper"]:has(> .st-key-topbar) {{ position: static !important; box-shadow: none !important; }}
  [data-testid="stColumn"]:has(iframe[src*="kakao_map"]) {{ position: static !important; }}
}}
/* 메인 '등록하기'·상세 '리스트로 돌아가기'·등록 화면 '홈으로 돌아가기' 버튼:
   포인트 색으로 채운 둥근 사각형, 흰 굵은 글자 (공식 안내 보기 버튼 모양) */
.st-key-add_btn button, .st-key-back_to_list button, .st-key-wiz_home button {{ background: var(--accent) !important; border: 0 !important; border-radius: 10px !important;
  min-height: 0 !important; height: 32px !important; width: auto !important; padding: 0 .9rem !important;
  box-shadow: 0 3px 10px rgba(20,184,166,.3) !important; }}
.st-key-add_btn, .st-key-back_to_list, .st-key-wiz_home, .st-key-add_btn > div, .st-key-back_to_list > div, .st-key-wiz_home > div {{ display: flex !important; justify-content: flex-end !important; }}
.st-key-add_btn button, .st-key-back_to_list button, .st-key-wiz_home button {{ margin-left: auto !important; }}
.st-key-add_btn button p, .st-key-back_to_list button p, .st-key-wiz_home button p {{ color: #fff !important; font-weight: 800 !important; font-size: .92rem !important;
  letter-spacing: .01em; white-space: pre; }}
.st-key-add_btn button:hover, .st-key-back_to_list button:hover, .st-key-wiz_home button:hover {{ background: var(--accent-deep) !important; transform: translateY(-1px); }}
/* 메인 '등록하기': 위쪽이 아니라 화면 오른쪽 아래에 떠 있는 버튼. 포인트(민트)와 구분되게 코랄 색 */
.st-key-add_btn {{ position: fixed !important; right: 28px; bottom: 28px; z-index: 1001; width: auto !important; }}
.st-key-add_btn button {{ background: #FF6B6B !important; height: 50px !important; padding: 0 1.4rem !important;
  border-radius: 999px !important; box-shadow: 0 8px 22px rgba(255,107,107,.45) !important; }}
.st-key-add_btn button p {{ font-size: 1rem !important; }}
.st-key-add_btn button:hover {{ background: #F25454 !important; }}
@media (max-width: 640px) {{
  /* 모바일: 아래 가운데 '필터 / 지도보기' 버튼 위로 비켜 둔다 */
  .st-key-add_btn {{ right: 16px; bottom: 76px; }}
  .st-key-add_btn button {{ height: 44px !important; padding: 0 1.1rem !important; }}
  .st-key-add_btn button p {{ font-size: .92rem !important; }}
}}
/* '팔로우' 스위치 (팔로우한 곳만 보기). 키에 'fav_' 를 쓰지 않는다 — 카드 팔로우 버튼 규칙([class*="st-key-fav_"])에 걸리지 않게 */
[class*="st-key-folsw"] button {{ position: relative; min-height: 0 !important; height: 24px; min-width: 70px;
  border-radius: 999px !important; border: 0 !important; background: #E4E8E6 !important;
  padding: 0 9px 0 25px !important; transition: background .15s; }}
[class*="st-key-folsw"] button::before {{ content: ""; position: absolute; left: 3px; top: 3px; width: 18px; height: 18px;
  border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,.2); transition: left .15s; }}
[class*="st-key-folsw"] button p {{ font-size: .7rem !important; font-weight: 800 !important; color: #5B6663 !important; }}
[class*="st-key-folsw"][class*="_on"] button {{ background: var(--accent) !important; padding: 0 25px 0 9px !important; }}
[class*="st-key-folsw"][class*="_on"] button::before {{ left: calc(100% - 21px); }}
[class*="st-key-folsw"][class*="_on"] button p {{ color: #fff !important; }}
/* 목록 위 '팔로우' 스위치는 칸 오른쪽 끝, 바로 옆 '지역 고르기' 에 붙인다 */
.st-key-listtools [data-testid="stColumn"]:has([class*="st-key-folsw_"]) [data-testid="stVerticalBlock"] {{ align-items: flex-end; }}
/* 등록 화면의 홈으로 돌아가기: 둘째 줄 오른쪽 끝 */
[data-testid="stColumn"]:has(.st-key-wiz_home) [data-testid="stVerticalBlock"] {{ align-items: flex-end; }}
/* 화면에 안 보이는 칸(스타일만 담은 칸, 스크립트용 iframe)은 줄 간격을 차지하지 않게 흐름에서 뺀다 */
[data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style),
[data-testid="stElementContainer"]:has(> iframe[data-testid="stIFrame"]),
[data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]) {{ position: absolute !important;
  width: 0 !important; height: 0 !important; overflow: hidden; margin: 0 !important; }}
/* 개발용 상단 메뉴 줄(Deploy ⋮)은 숨기고, 맨 위 여백을 줄인다 */
[data-testid="stHeader"] {{ display: none !important; }}
.stMainBlockContainer {{ padding-top: 2.5rem !important; }}
/* 제목 옆 링크 아이콘은 숨긴다 */
[data-testid="stHeaderActionElements"] {{ display: none; }}
/* 테두리 있는 상자: 하얀 카드 + 민트 그림자 */
[data-testid="stVerticalBlockBorderWrapper"] {{ background: #fff; border-radius: 20px !important;
  box-shadow: 0 2px 12px rgba(0,0,0,.05); }}
/* 입력칸 */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {{
  border-radius: 14px !important; }}
/* 머리글 */
.brand-tag {{ margin-top: .4rem; font-family: "Jua", sans-serif; font-size: 1.25rem; color: #26302D; }}
.brand-tag span {{ font-family: "Pretendard", sans-serif; font-size: .78rem; font-weight: 700;
  letter-spacing: .14em; color: {MINT}; }}
/* 누르면 메인으로 가는 제목: 버튼이지만 글자처럼 보이게 */
.st-key-home_brand button, .st-key-home_add button {{ background: none !important; border: 0 !important;
  box-shadow: none !important; padding: 0 !important; min-height: 0; transform: none !important; }}
/* 제목 로고: 버튼 바탕에 로고 그림을 깔고 글자는 숨긴다 (누르면 처음 화면으로) */
.st-key-home_brand button {{ width: 270px !important; height: 76px !important;
  background: url("app/static/logo.png") no-repeat left center / contain !important; }}
.st-key-home_brand button p {{ font-size: 0 !important; color: transparent !important; }}
.st-key-home_brand button:hover {{ filter: brightness(1.06) saturate(1.1); }}
@media (max-width: 640px) {{
  .st-key-home_brand button {{ width: 200px !important; height: 56px !important; }}
}}
.st-key-home_add, .st-key-home_add .stButton {{ display: flex; justify-content: center; width: 100%; }}
.st-key-home_add button p {{ font-family: "Jua", sans-serif !important; font-size: 1.8rem !important;
  color: #26302D; }}
.st-key-home_brand button:hover p, .st-key-home_add button:hover p {{ color: {MINT}; }}
</style>
"""

st.set_page_config(page_title="ANI:WHERE", page_icon="🗺️", layout="wide")

store = Storage(worksheet="cafes")
reviews = Storage(worksheet="reviews", headers=review.HEADERS)
favs = Storage(worksheet="favorites", headers=favorite.HEADERS)
# 실행 번호: 찜 정보를 한 번 그릴 때 한 번만 읽고, 다음 실행에서는 새로 읽게 한다
st.session_state["_run"] = st.session_state.get("_run", 0) + 1


def _fav_state() -> tuple[str, set[str], dict[str, int]]:
    """(나, 내가 찜한 카페들, 카페별 찜 수). 한 번 그릴 때 한 번만 읽도록 실행마다 새로 담아 둔다."""
    run = st.session_state.get("_run", 0)
    cached = st.session_state.get("_fav_cache")
    if cached and cached[0] == run:
        return cached[1]
    me = favorite.user_key(st.context.ip_address)
    rows = favs.current_rows()
    state = (me, favorite.mine(rows, me), favorite.counts(rows))
    st.session_state["_fav_cache"] = (run, state)
    return state


def _heart(cafe_id: str, where: str, label_count: bool = False) -> None:
    """팔로우 버튼. 팔로우하면 포인트 색으로 채운 '팔로잉', 아니면 테두리만 있는 '+ 팔로우'.
    where 는 위치(w: 전체보기 카드, s: 반반 카드, d: 상세)."""
    me, mine, counts = _fav_state()
    on = str(cafe_id) in mine
    n = counts.get(str(cafe_id), 0)
    label = ("팔로잉" if on else "팔로우") + (f" {n}" if label_count else "")
    if st.button(label, key=f"fav_{'on' if on else 'off'}_{where}_{cafe_id}",
                 help="팔로우 취소" if on else "팔로우"):
        favorite.toggle(favs, str(cafe_id), me, not on)
        st.session_state.pop("_fav_cache", None)
        st.rerun()
# 왼쪽 사이드바는 쓰지 않는다 (저장소 상태 안내도 화면에 띄우지 않는다)


def go(page: str) -> None:
    st.switch_page(PAGES[page])


def _split(text: str) -> list[str]:
    return [p.strip() for p in str(text).split(",") if p.strip()]


def _characters_by_work() -> dict[str, list[str]]:
    """작품별 캐릭터 목록. 작품·캐릭터 목록 파일에 이미 등록된 카페에서 쓰인 이름을 더한다."""
    found = {w: list(c) for w, c in catalog.characters_by_work().items()}
    for r in store.current_rows():
        work = catalog.canonical_work(str(r.get("work", "")))
        if work:
            chars = found.setdefault(work, [])
            # '아냐 포저' 가 이미 있으면 등록 때 줄여 쓴 '아냐' 는 따로 늘어놓지 않는다
            chars += [c for c in _split(r.get("characters") or "")
                      if not any(c == x or c in x for x in chars)]
    return found


def pick_work_and_characters(work: str, characters: list[str], key: str) -> tuple[str, list[str]]:
    """작품을 고르면 그 작품의 캐릭터만 고를 수 있게 한다. 둘 다 없으면 새로 입력.

    작품을 바꾸면 캐릭터 목록이 곧바로 바뀌어야 해서 st.form 밖에 둔다.
    """
    by_work = _characters_by_work()
    work = catalog.canonical_work(work) if work else ""
    works = sorted(by_work)
    if work and work not in works:
        works.append(work)
    pick = st.selectbox(
        "작품", works, index=works.index(work) if work in works else None,
        placeholder="작품명으로 찾기 · 없으면 새로 입력", accept_new_options=True,
        key=f"work_{key}",
    )
    pick = (pick or "").strip()

    options = list(by_work.get(pick, []))
    # 다른 작품의 캐릭터가 따라오지 않게, 처음 값은 같은 작품일 때만 채운다
    default = [c for c in characters if pick == work]
    options += [c for c in default if c not in options]
    chars = st.multiselect(
        "캐릭터", options, default=default, accept_new_options=True,
        placeholder="캐릭터 고르기 · 없으면 이름을 입력하고 Enter" if pick else "작품을 먼저 골라주세요",
        disabled=not pick, key=f"chars_{key}_{pick}",
    )
    return pick, chars


def show_report(report: dict) -> None:
    if report["saved"]:
        st.success(f"{len(report['saved'])}곳을 지도에 올렸습니다.")
        for name, badge in report["saved"]:
            st.write(f"- {name} — {badge}")
    if report["blocked"]:
        st.error(f"{len(report['blocked'])}곳은 저장하지 않았습니다.")
        for name, errs in report["blocked"]:
            st.write(f"- **{name}** — {'; '.join(errs)}")


# ================================================================ 주소 검색
def _picked(c: geo.Candidate) -> dict:
    return {"address": c.address, "lat": c.lat, "lng": c.lng, "source": c.source,
            "precision": c.precision}


def locate(address: str, picked: dict | None) -> geo.GeoResult:
    """주소 검색에서 고른 주소를 그대로 두었으면 그 좌표를, 손으로 고쳤으면 다시 찾은 좌표를 쓴다."""
    precision = (picked or {}).get("precision", "exact")
    if picked and picked["address"] == address.strip() and precision != "none":
        return geo.GeoResult(ok=True, lat=picked["lat"], lng=picked["lng"], precision=precision,
                             matched=f"{picked['source']}: {picked['address']}")
    return geo.geocode(address)


def _postcode_field(key: str, on_pick) -> None:
    """카카오 우편번호 서비스로 주소를 고르게 한다. 좌표는 고른 주소로 다시 찾는다."""
    got = kakao_postcode.postcode(key=f"{key}_postcode")
    # 컴포넌트는 재실행해도 마지막 값을 들고 있어서, 고른 시각이 바뀔 때만 반영한다
    if not got or st.session_state.get(f"_postcode_{key}") == got.get("at"):
        return
    st.session_state[f"_postcode_{key}"] = got.get("at")
    address = str(got.get("address") or "").strip()
    g = geo.geocode(address)
    if not g.ok and got.get("jibun"):
        g = geo.geocode(got["jibun"])
    # 건물 이름은 카페명과 다를 때가 많아 넘기지 않는다 (등록 화면이 카페명을 건물 이름으로 채우지 않게)
    on_pick(geo.Candidate(name="", address=address,
                          lat=g.lat or 0.0, lng=g.lng or 0.0, source="카카오 우편번호",
                          precision=g.precision if g.ok else "none"))
    st.rerun()


def address_field(value: str, key: str, on_pick, placeholder: str = "") -> str:
    """주소 입력칸 + 카카오 우편번호 찾기. 등록·간편등록·수정하기가 함께 쓴다.

    우편번호 버튼으로 주소를 고르면 on_pick(후보) 를 부르고 다시 그린다.
    입력칸을 새 값으로 채우는 일(키 바꾸기)과 좌표 보관은 부르는 쪽이 맡는다.
    """
    addr = st.text_input("주소", value=value, key=f"{key}_addr", placeholder=placeholder)
    _postcode_field(key, on_pick)
    return addr


# ================================================================ 카페 상세
_WEEKDAYS = "월화수목금토일"


def _day(d, with_year: bool) -> str:
    """'26.10.27(화)' / '11.11(수)'."""
    d = pd.to_datetime(d).date()
    return f"{d:%y.%m.%d}({_WEEKDAYS[d.weekday()]})" if with_year else f"{d:%m.%d}({_WEEKDAYS[d.weekday()]})"


def _map_link(current: dict) -> str:
    """'지도에서 확인하기': 카카오맵에서 이 카페 위치를 연다 (좌표가 있으면 그 자리, 없으면 주소 검색)."""
    name = re.sub(r"[,/]", " ", str(current.get("cafe_name") or "카페")).strip()
    lat, lng = str(current.get("lat") or "").strip(), str(current.get("lng") or "").strip()
    if lat and lng:
        return f"https://map.kakao.com/link/map/{quote(name)},{lat},{lng}"
    return f"https://map.kakao.com/link/search/{quote(str(current.get('address') or name))}"


def _detail_info_html(current: dict) -> str:
    """상세 정보 블록: 위치(주소 + 지도에서 확인하기) · 일정 → 혜택(특전·굿즈·이벤트) → 참고 웹사이트 카드."""
    # 위치 · 일정: 왼쪽에 항목 이름, 오른쪽에 내용 (오른쪽 정렬)
    addr = str(current.get("address") or "-")
    start, end = pd.to_datetime(current.get("start_date")), pd.to_datetime(current.get("end_date"))
    span = f"{_day(start, True)} - {_day(end, end.year != start.year)}"
    # 위치: 카페 이름을 크고 굵게 맨 위에, 그 아래 주소, 그 아래 '지도에서 확인하기'
    # '방문 전 확인' 회색 상자: 왼쪽 항목 이름(고정 폭), 오른쪽 내용(왼쪽 정렬)
    rows = (
        '<div class="dinfo-title">방문 전 확인</div>'
        # 위치 줄: 항목 이름 | 카페 이름·주소 | (같은 줄 오른쪽 끝) 지도에서 확인하기
        '<div class="drow"><div class="dlabel">위치</div><div class="dval">'
        f'<div class="dcafe">{escape(str(current.get("cafe_name") or "-"))}</div>'
        f'<div class="daddr">{escape(addr)}</div></div>'
        f'<a class="dbtn" href="{escape(_map_link(current))}" target="_blank" rel="noopener">📍 지도에서 확인하기</a>'
        '</div>'
        f'<div class="drow"><div class="dlabel">일정</div><div class="dval">{escape(span)}</div></div>'
    )
    # 혜택: 특전 · 굿즈 · 이벤트마다 검은 알약 라벨, 그 옆에 회색 상자 안 목록 (라벨 | 내용 한 줄)
    groups = [("특전", "🎁", _split(current.get("perks") or "")),
              ("굿즈", "🛍️", _split(current.get("goods") or "")),
              ("이벤트", "🎪", _split(current.get("tags") or ""))]
    perks = "".join(
        f'<div class="dgroup"><span class="dpill">{name}</span><ul class="dbox">'
        + "".join(f"<li>{icon} {escape(x)}</li>" for x in items) + "</ul></div>"
        for name, icon, items in groups if items)
    perks_html = (f'<div class="dsec"><div class="dsec-title">혜택</div>{perks}</div>' if perks else
                  '<div class="dsec"><div class="dsec-title">혜택</div><div class="dnone">등록된 특전·굿즈가 없어요</div></div>')
    # 참고 웹사이트: 연회색 카드 (사이트 이름 + 주소 + ↗), 카드 전체를 누르면 새 탭
    links = cafe.parse_links(current.get("links") or "")[0]
    link_html = ""
    if links:
        cards = "".join(
            f'<a class="dlink" href="{escape(u)}" target="_blank" rel="noopener">'
            f'<div class="dlink-text"><div class="dlink-title">{escape(_site_name(u))}</div>'
            f'<div class="dlink-url">{escape(u)}</div></div><span class="dlink-go">↗</span></a>'
            for u in links)
        link_html = f'<div class="dsec"><div class="dsec-title">참고 웹사이트</div>{cards}</div>'
    return f'<div class="dinfo">{rows}</div><div class="dband"></div>{perks_html}{link_html}'


def render_detail(current: dict) -> None:
    """상세 화면 왼쪽: 이미지 슬라이드 · 작품(+캐릭터) · 위치(카페명·주소)·일정 · 혜택 · 참고 웹사이트 · 공유.
    지도는 상세에 따로 그리지 않고, 위치의 '지도에서 확인하기' 로 카카오맵을 연다."""
    entry_id = str(current["entry_id"])
    # 포스터와 추가 이미지를 한 슬라이드로: 몇 초마다 넘어가고, 버튼으로 넘기고, 누르면 크게 본다.
    # 포스터가 없으면 기본 그림을 보여 준다 (저장소에는 넣지 않는다)
    pics = images.paths(current.get("images"))
    gallery.gallery([images.url(p) for p in pics] or [images.DEFAULT_POSTER_URL],
                    key=f"gallery_{entry_id}")
    # 머리글 (LIST_CSS 의 .dhead):
    #   1줄 📍 지역 ······························· 진행 상태 배지(작게)
    #   2줄 작품 이름(크게) ························ [공유][♡]
    #   3줄 캐릭터(포인트 색)
    top, title_html, chars_html = _detail_head_html(current)
    st.markdown(top, unsafe_allow_html=True)
    # 2줄: 작품 이름 칸이 남는 폭을 쓰고, 오른쪽에 공유·찜 버튼 칸 (공유를 누르면 공유 칸이 넓어지며 왼쪽으로 펼쳐진다)
    with st.container(key="detail_actions"):
        title_col, share_col, fav_col = st.columns([6, 1, 1], vertical_alignment="center")
    with title_col:
        st.markdown(title_html, unsafe_allow_html=True)
    with fav_col:
        _heart(entry_id, "d")      # 하트만 (글자·찜 수 없이)
    with share_col:
        # 받은 사람이 누르면 이 카페 상세가 바로 열린다 (?cafe=...)
        share.share_buttons(
            entry_id,
            title=f"{current.get('work', '')} · {current.get('cafe_name', '')}",
            text=f"{current.get('start_date')} ~ {current.get('end_date')} · {current.get('address') or ''}",
            image=images.url(pics[0]) if pics else images.DEFAULT_POSTER_URL,
            key=f"share_{entry_id}",
        )
    if chars_html:
        st.markdown(chars_html, unsafe_allow_html=True)
    # 위치(카페명·주소) · 일정 · 혜택 · 참고 웹사이트 (LIST_CSS 의 .dinfo / .dsec / .dlink)
    st.markdown(_detail_info_html(current), unsafe_allow_html=True)


def _detail_head_html(current: dict) -> tuple[str, str, str]:
    """상세 머리글 세 조각: (📍 지역 + 진행 상태 배지 줄, 작품 이름, 캐릭터 줄).
    일정 날짜는 아래 '일정' 줄에만 둔다. 캐릭터가 없으면 셋째는 빈 문자열."""
    area = geo.area_name(str(current.get("address") or ""))
    color, _ = _area_colors(current.get("address"))
    start = pd.to_datetime(current.get("start_date")).date()
    end = pd.to_datetime(current.get("end_date")).date()
    if end < TODAY:
        state = "종료"
    elif end == TODAY:
        state = "오늘 종료"
    elif start > TODAY:
        state = f"오픈 예정 D-{(start - TODAY).days}"
    else:
        state = "진행 중"
    chars = str(current.get("characters") or "").strip()
    top = ('<div class="dhead dtop">'
           + f'<span class="dregion" style="color:{color}">{"📍 " + escape(area) if area else ""}</span>'
           + f'<span class="dstate{" ended" if state == "종료" else ""}">{state}</span></div>')
    title = f'<div class="dtitle">{escape(str(current.get("work") or ""))}</div>'
    sub = f'<div class="dsub"><span class="dchars">{escape(chars)}</span></div>' if chars else ""
    return top, title, sub



def render_detail_tabs(current: dict) -> None:
    """상세 화면 오른쪽: 리뷰 / 수정하기 탭."""
    entry_id = str(current["entry_id"])
    n = review.counts(reviews.current_rows()).get(entry_id, 0)
    # 키를 주고 고른 탭을 서버가 기억하게 한다. 그렇지 않으면 수정하기에서 이미지를 지우거나 올려
    # 다시 그릴 때마다 첫 탭(리뷰)으로 돌아가 버린다
    tab_review, tab_edit = st.tabs([f"💬 리뷰 {n}", "✏️ 수정하기"], key=f"detail_tabs_{entry_id}",
                                   on_change="rerun")
    with tab_review:
        render_reviews(entry_id)
    with tab_edit:
        render_edit(current)


# ================================================================ 리뷰 게시판
def _plain(text: str) -> str:
    """사용자가 쓴 글을 마크다운으로 해석하지 않고 그대로 보여 준다."""
    escaped = re.sub(r"([\\`*_{}\[\]()#+\-.!|>~<$])", r"\\\1", str(text))
    return escaped.replace("\n", "  \n")


def _when(stamp: str) -> str:
    try:
        return datetime.fromisoformat(str(stamp)).astimezone().strftime("%m/%d %H:%M")
    except ValueError:
        return ""


def _write_box(cafe_id: str, parent_id: str = "") -> None:
    """글쓰기 칸. parent_id 가 있으면 답글 칸이다.

    입력이 끝나면 칸을 비워야 해서, 저장할 때마다 키 번호(n)를 올려 새 입력칸을 그린다.
    """
    slot = f"rv_{cafe_id}_{parent_id or 'top'}"
    n = st.session_state.get(f"{slot}_n", 0)
    kind = ""
    nick = review.nickname_for(st.context.ip_address)
    # 닉네임 → 종류 → 내용 순으로 한 줄씩, 같은 왼쪽 선에 맞춰 둔다
    st.caption(f"✍️ 닉네임 **{nick}**", help="접속한 IP 에 따라 자동으로 정해지는 닉네임입니다")
    rating = None
    if not parent_id:
        kind = st.pills("종류", review.KINDS, default=review.KINDS[0], key=f"{slot}_kind_{n}",
                        label_visibility="collapsed")
        # 다녀온 후기는 별점(1~5)을 고를 수 있다. st.feedback 은 0~4 를 돌려줘서 1 을 더한다
        if kind == review.RATED_KIND:
            with st.container(key=f"{slot}_rate_box_{n}"):
                st.markdown('<div class="rv-rate-q">이 팝업 방문하셨나요?</div>'
                            '<div class="rv-rate-sub">방문 예정인 분들에게 도움이 되는 후기를 작성해주세요</div>',
                            unsafe_allow_html=True)
                picked = st.feedback("stars", key=f"{slot}_rating_{n}")
            rating = picked + 1 if picked is not None else None
    body = st.text_area(
        "내용", key=f"{slot}_body_{n}", height=80 if parent_id else 100, label_visibility="collapsed",
        max_chars=review.MAX_BODY,
        placeholder="답글을 남겨 주세요" if parent_id else
        "다녀온 후기나 기대하는 점을 남겨 주세요 (대기 시간, 특전 소진 여부 등)",
    )
    bad = _block_sensitive(body)

    c1, c2 = st.columns(2) if parent_id else (st.container(), None)
    with c1:
        # 입력칸이 비었는지는 화면에서 바로 본다 (_live_send). 입력칸은 칸을 벗어나야 값이 넘어와서
        # 여기서 막으면 한 글자를 써도 버튼이 계속 꺼져 있다
        clicked = st.button("답글 등록" if parent_id else "리뷰 등록", type="primary",
                            width="stretch", disabled=bad, key=f"{slot}_send_{n}")
    if c2 is not None:
        with c2:
            # 답글 칸 비우기 (키 번호를 올려 빈 입력칸으로 다시 그린다)
            if st.button("취소", width="stretch", key=f"{slot}_cancel_{n}"):
                st.session_state[f"{slot}_n"] = n + 1
                st.rerun()

    if clicked:
        # 입력 직후 바로 누르면 위의 비활성화보다 먼저 들어올 수 있어서 한 번 더 검사한다
        v = review.validate(body, nick)
        if not v.ok:
            for err in v.errors:
                st.error(err)
            return
        reviews.append(review.to_row(cafe_id, body, nick, kind or "", parent_id, rating=rating))
        st.session_state[f"{slot}_n"] = n + 1
        st.session_state["flash"] = "답글을 남겼습니다." if parent_id else "리뷰를 남겼습니다."
        st.rerun()


# 리뷰 종류마다 배지 색을 달리한다 (기타는 회색)
KIND_COLORS = {"다녀온 후기": "green", "기대평": "blue", "기타": "gray"}


@st.dialog("리뷰 삭제")
def confirm_review_delete(entry_id: str, replies: int) -> None:
    st.write("이 글을 삭제할까요? 삭제하면 다시 볼 수 없어요."
             + (f" 달린 답글 {replies}개도 함께 안 보이게 돼요." if replies else ""))
    c1, c2 = st.columns(2)
    if c1.button("취소", width="stretch", key=f"rv_del_no_{entry_id}"):
        st.rerun()
    if c2.button("삭제", type="primary", width="stretch", key=f"rv_del_ok_{entry_id}"):
        # 버튼이 보였더라도 지우는 순간 한 번 더 확인한다 (내 닉네임과 같은 글만)
        row = next((r for r in reviews.current_rows() if str(r["entry_id"]) == entry_id), None)
        if row and review.can_delete(row, review.nickname_for(st.context.ip_address)):
            reviews.soft_delete(entry_id)       # 저장소는 지우지 않고 '삭제됨' 행을 쌓는다
            st.session_state["flash"] = "삭제했습니다."
        else:
            st.session_state["flash"] = "내가 쓴 글만 삭제할 수 있어요."
        st.rerun()


def _review_card(r: dict, reply: bool = False, replies: int = 0) -> None:
    head = f"**{_plain(r.get('nickname') or '익명')}**"
    if r.get("kind"):
        # 다녀온 후기는 종류 배지 옆에 별점 (★★★★☆)
        rated = review.stars(r.get("rating")) if r.get("kind") == review.RATED_KIND else ""
        head = (f":{KIND_COLORS.get(r['kind'], 'gray')}-badge[{r['kind']}] "
                + (f":orange[{rated}] " if rated else "") + head)
    if reply:
        head = ":gray-badge[답글] " + head
    eid = str(r["entry_id"])
    when = f" · :gray[{_when(r.get('updated_at'))}]"
    if int(r.get("revision") or 1) > 1:
        when += " :gray[(수정됨)]"
    # 내가 쓴 글(접속 IP 로 정해진 닉네임이 같은 글)에만 '⋯' 를 보여 주고, 누르면 수정·삭제를 고른다
    mine = review.can_delete(r, review.nickname_for(st.context.ip_address))
    if mine:
        t, b = st.columns([6, 1], vertical_alignment="center")
        t.markdown(head + when)
        with b.popover("⋯", key=f"rv_more_{eid}", type="tertiary", help="수정 · 삭제"):
            if st.button("수정", key=f"rv_edit_{eid}", width="stretch"):
                st.session_state["rv_editing"] = eid
                st.rerun()
            if st.button("삭제", key=f"rv_del_{eid}", width="stretch"):
                confirm_review_delete(eid, replies)
    else:
        st.markdown(head + when)
    if mine and st.session_state.get("rv_editing") == eid:
        _review_edit_box(r)
    else:
        st.markdown(_plain(r.get("body", "")))


def _review_edit_box(r: dict) -> None:
    """내 글 고치기: 원글은 종류·내용, 답글은 내용만. 저장하면 새 수정본이 쌓인다 (지난 내용은 남는다)."""
    eid = str(r["entry_id"])
    kind = r.get("kind") or ""
    rating = None
    if not str(r.get("parent_id") or ""):
        kind = st.pills("종류", review.KINDS, default=kind or review.KINDS[0], key=f"rv_edit_kind_{eid}",
                        label_visibility="collapsed")
        if kind == review.RATED_KIND:
            # 지금 별점을 미리 골라 둔 채로 보여 준다 (st.feedback 은 0~4)
            try:
                old = int(r.get("rating")) - 1
            except (TypeError, ValueError):
                old = None
            picked = st.feedback("stars", key=f"rv_edit_rating_{eid}",
                                 default=old if old is not None and 0 <= old <= 4 else None)
            rating = picked + 1 if picked is not None else None
    body = st.text_area("내용", value=str(r.get("body") or ""), key=f"rv_edit_body_{eid}", height=90,
                        max_chars=review.MAX_BODY, label_visibility="collapsed")
    bad = _block_sensitive(body)
    c1, c2 = st.columns(2)
    if c1.button("취소", width="stretch", key=f"rv_edit_no_{eid}"):
        st.session_state.pop("rv_editing", None)
        st.rerun()
    if c2.button("저장", type="primary", width="stretch", key=f"rv_edit_ok_{eid}", disabled=bad):
        nick = review.nickname_for(st.context.ip_address)
        current = next((x for x in reviews.current_rows() if str(x["entry_id"]) == eid), None)
        # 저장하는 순간에도 내 글인지 한 번 더 확인한다
        if not current or not review.can_delete(current, nick):
            st.error("내가 쓴 글만 수정할 수 있어요.")
            return
        v = review.validate(body, nick)
        if not v.ok:
            for err in v.errors:
                st.error(err)
            return
        payload = {k: current.get(k, "") for k in review.HEADERS
                   if k not in ("row_id", "entry_id", "revision", "status", "updated_at")}
        payload["body"] = body.strip()
        if not str(current.get("parent_id") or ""):
            payload["kind"] = kind if kind in review.KINDS else review.KINDS[0]
            # 별점은 다녀온 후기일 때만 남기고, 종류를 바꾸면 비운다
            payload["rating"] = rating if payload["kind"] == review.RATED_KIND and rating else ""
        reviews.append(payload, entry_id=eid)
        st.session_state.pop("rv_editing", None)
        st.session_state["flash"] = "수정했습니다."
        st.rerun()


def render_reviews(cafe_id: str) -> None:
    # 맨 위 리뷰 쓰기: 닉네임·종류·별점·입력칸·리뷰 등록 버튼을 처음부터 펼쳐 둔다. 그 아래에 리뷰를 보여 준다
    with st.container(border=True, key=f"rvbox_{cafe_id}"):
        _write_box(cafe_id)

    threads = review.threads(reviews.current_rows(), cafe_id)
    if not threads:
        st.caption("아직 리뷰가 없습니다. 다녀온 후기나 기대하는 점을 처음으로 남겨 보세요.")
        return

    # 다녀온 후기와 기대평을 따로 볼 수 있게 나눈다 (개수 함께 표시)
    count = {k: sum(1 for t in threads if t.post.get("kind") == k) for k in review.KINDS}
    labels = {"전체": f"전체 {len(threads)}", **{k: f"{k} {count[k]}" for k in review.KINDS}}
    pick = st.segmented_control("리뷰 보기", list(labels), default="전체", key=f"rv_filter_{cafe_id}",
                                format_func=lambda k: labels[k], label_visibility="collapsed")
    shown = [t for t in threads if pick in (None, "전체") or t.post.get("kind") == pick]
    if not shown:
        st.caption(f"아직 {pick}이 없어요. 위에서 처음으로 남겨 보세요." if pick == "기대평"
                   else f"아직 {pick}가 없어요. 위에서 처음으로 남겨 보세요.")

    for t in shown:
        pid = str(t.post["entry_id"])
        with st.container(border=True):
            _review_card(t.post, replies=len(t.replies))
            for r in t.replies:
                _review_card(r, reply=True)
            # 답글은 입력칸만 보여 주고, 칸을 누르면(또는 글이 있으면) 닉네임과 등록·취소 버튼이 나온다
            # (LIST_CSS 의 .st-key-rpbox_ — 칸을 눌렀는지는 브라우저만 알아서 CSS 로 처리한다)
            with st.container(key=f"rpbox_{pid}"):
                _write_box(cafe_id, parent_id=pid)


# ================================================================ 수정하기
@st.dialog("지도에서 내리기")
def confirm_delete(entry_id: str) -> None:
    st.write("정말로 지도에서 삭제하시겠습니까? 완전히 삭제 됩니다.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("취소", width="stretch", key=f"delete_cancel_{entry_id}"):
            st.rerun()
    with c2:
        if st.button("삭제", type="primary", width="stretch", key=f"delete_ok_{entry_id}"):
            store.soft_delete(entry_id)
            st.session_state["selected"] = None
            st.session_state["flash"] = "지도에서 내렸습니다. 이력은 남아 있습니다."
            st.session_state["scroll_top"] = True
            st.rerun()


@st.dialog("포스터 변경", dismissible=False)
def _confirm_poster(slot: str, sig: str, data: bytes) -> None:
    """포스터는 한 장만. 이미 있는데 새로 올리면 바꿀지 묻는다."""
    st.write("포스터는 한 장만 올릴 수 있어요. 새 포스터로 **변경하시겠습니까?**")
    st.image(data, width=220)
    c1, c2 = st.columns(2)
    if c1.button("취소", width="stretch", key=f"{slot}_no"):
        # 올린 파일을 업로드 칸에서 지운다 (칸의 키를 바꿔 새로 그린다)
        st.session_state[f"{slot}_ver"] = st.session_state.get(f"{slot}_ver", 0) + 1
        st.rerun()
    if c2.button("변경", type="primary", width="stretch", key=f"{slot}_yes"):
        st.session_state[f"{slot}_ok"] = sig
        st.rerun()


def _poster_upload(slot: str, label: str, has_poster: bool, **kw):
    """포스터 업로드 칸. 이미 포스터가 있는데 새로 올리면 변경할지 확인한 뒤에만 돌려준다.

    돌려주는 값: (이름, 바이트) 또는 None (안 올렸거나 아직 확인 전·취소).
    """
    up = st.file_uploader(label, type=images.TYPES, key=f"{slot}_{st.session_state.get(f'{slot}_ver', 0)}",
                          help="포스터는 한 장만 올릴 수 있어요", **kw)
    if not up:
        return None
    data = up.getvalue()
    sig = hashlib.md5(data).hexdigest()
    if has_poster and st.session_state.get(f"{slot}_ok") != sig:
        _confirm_poster(slot, sig, data)
        return None
    return up.name, data


def _edit_images(current: dict, k: str) -> tuple[list[tuple[str, bytes | None]], list[str]]:
    """수정하기의 이미지 칸. 지금 이미지를 보여 주고 포스터 바꾸기·추가·지우기를 받는다.

    돌려주는 목록은 (이름, 바이트) 이고 첫 번째가 포스터다. 바이트가 None 이면 이미 저장된 파일 이름이다.
    """
    current_files = images.split(current.get("images"))
    st.markdown("**이미지**")
    # '삭제' 를 누른 이미지는 화면에서 바로 빠지고, '수정 저장' 을 눌러야 실제로 반영된다
    removed: set[str] = st.session_state.setdefault(f"img_removed_{k}", set())
    keep = [(name, None) for name in current_files if name not in removed]
    if keep:
        st.caption("첫 번째가 포스터예요.")
        cols = st.columns(4)
        for i, (name, _) in enumerate(keep):
            with cols[i % 4]:
                path = images.IMAGE_DIR / Path(name).name
                if path.is_file():
                    st.image(str(path), width="stretch")
                else:
                    st.caption("(파일 없음)")
                if st.button("삭제", key=f"img_del_{k}_{name}", width="stretch"):
                    removed.add(name)
                    st.rerun()
    else:
        st.caption("아직 이미지가 없어요.")
    if removed:
        note, undo = st.columns([3, 1], vertical_alignment="center")
        note.caption(f"🗑️ {len(removed)}장 삭제 예정 · **수정 저장**을 눌러야 반영돼요.")
        if undo.button("삭제 취소", key=f"img_undo_{k}", width="stretch"):
            removed.clear()
            st.rerun()

    poster = _poster_upload(f"img_poster_{k}", f"포스터 바꾸기 (1장, ~ {images.POSTER_MB} MB)",
                            has_poster=bool(keep))
    extras = st.file_uploader("이미지 추가", type=images.TYPES, accept_multiple_files=True,
                              key=f"img_extras_{k}")

    errors = []
    if poster and images.too_big(poster[1], images.POSTER_MB):
        errors.append(f"포스터는 {images.POSTER_MB} MB 까지 올릴 수 있습니다.")
    if any(images.too_big(f.getvalue(), images.EXTRA_MB) for f in extras or []):
        errors.append(f"추가 이미지는 한 장에 {images.EXTRA_MB} MB 까지 올릴 수 있습니다.")

    # 포스터는 한 장: 새 포스터로 변경하면 원래 포스터(맨 앞)를 빼고 그 자리에 둔다
    if poster:
        st.caption("✅ 새 포스터로 변경돼요. **수정 저장**을 눌러야 반영돼요.")
        st.image(poster[1], width=160)
    result = (([poster] + keep[1:]) if poster else keep) + [(f.name, f.getvalue()) for f in extras or []]
    if len(result) - 1 > images.MAX_EXTRAS:
        errors.append(f"추가 이미지는 {images.MAX_EXTRAS}장까지 둘 수 있습니다. 몇 장 지워 주세요.")
    for e in errors:
        st.error(e)
    return result, errors


def render_edit(current: dict) -> None:
    entry_id = str(current["entry_id"])
    st.caption("누구나 수정할 수 있습니다. 기존 기록은 남기고 새 줄로 쌓여서 언제든 되돌릴 수 있습니다.")

    # revision 을 키에 넣어야 되돌리기 후 입력칸이 새 값으로 다시 채워진다
    k = f"{entry_id}_{current.get('revision')}"
    new_work, new_chars = pick_work_and_characters(
        str(current.get("work", "")), _split(current.get("characters") or ""), key=f"edit_{k}")
    # 주소 검색·지도가 들어가서 st.form 을 쓰지 않는다 (폼 안에서는 검색 버튼·지도를 쓸 수 없다)
    new_name = st.text_input("카페명", value=str(current.get("cafe_name", "")), key=f"name_{k}")

    # 검색·우편번호로 고른 주소: 입력칸을 새 값으로 다시 그리려고 번호(ver)를 올리고 좌표를 보관한다
    slot = f"edit_pick_{k}"
    pick_state = st.session_state.setdefault(slot, {"ver": 0, "picked": None})

    def pick(c: geo.Candidate) -> None:
        pick_state["picked"] = _picked(c)
        pick_state["ver"] += 1

    picked = pick_state["picked"]
    new_addr = address_field(
        picked["address"] if picked else str(current.get("address", "")),
        key=f"edit_{k}_{pick_state['ver']}", on_pick=pick,
    )
    d1, d2 = st.columns(2)
    with d1:
        new_start = st.date_input("시작", value=pd.to_datetime(current["start_date"]).date(),
                                  key=f"start_{k}")
    with d2:
        new_end = st.date_input("종료", value=pd.to_datetime(current["end_date"]).date(),
                                key=f"end_{k}")
    new_perks = st.text_input("특전", value=str(current.get("perks", "")), key=f"perks_{k}",
                              help="쉼표로 구분")
    new_goods = st.text_input("굿즈", value=str(current.get("goods", "")), key=f"goods_{k}",
                              help="쉼표로 구분")
    new_tags = st.pills("이벤트 추가 정보", cafe.EVENT_TAGS, selection_mode="multi",
                        default=[t for t in _split(current.get("tags") or "") if t in cafe.EVENT_TAGS],
                        key=f"tags_{k}")
    new_links, bad_links = _links_field("\n".join(cafe.parse_links(current.get("links") or "")[0]),
                                        key=f"links_{k}")
    new_images, img_errors = _edit_images(current, k)
    bad = _block_sensitive(new_name, new_addr, new_perks, new_goods)
    submitted = st.button("수정 저장", type="primary", width="stretch", key=f"save_{k}",
                          disabled=bad or bool(img_errors) or bad_links)

    if submitted:
        entry = CafeEntry(
            cafe_name=new_name, work=new_work, characters=new_chars, address=new_addr,
            start_date=new_start, end_date=new_end,
            perks=_split(new_perks), goods=_split(new_goods),
            confidence="high",
        )
        v = guard.validate_cafe(entry, today=TODAY)
        g = locate(entry.address, picked)
        if not g.ok:
            v.fail(g.note)
        if v.ok:
            # 새로 올린 파일만 저장한다. 지운 이미지 파일은 남겨 둔다 (되돌리기가 옛 행을 쓸 수 있다)
            saved = [name if data is None else images.save(name, data) for name, data in new_images]
            store.append(cafe.entry_to_row(entry, g.lat, g.lng, source="직접 수정", note=g.badge,
                                           images=saved, tags=new_tags, links=new_links),
                         entry_id=entry_id)
            # 저장해도 상세에 그대로 머물고, 맨 위로 올려 바뀐 내용을 처음부터 보여 준다
            st.session_state["flash"] = "수정했습니다."
            st.session_state["scroll_top"] = True
            st.rerun()
        for err in v.errors:
            st.error(err)

    b1, b2 = st.columns(2)
    with b1:
        if st.button("되돌리기", width="stretch", key=f"revert_{k}",
                     help="직전 내용으로 복구합니다"):
            if store.revert(entry_id):
                st.session_state["flash"] = "직전 내용으로 되돌렸습니다."
                st.rerun()
            st.warning("되돌릴 이전 기록이 없습니다.")
    with b2:
        if st.button("지도에서 내리기", width="stretch", key=f"delete_{k}"):
            confirm_delete(entry_id)

    with st.expander("수정 이력"):
        history = [r for r in store.all_rows() if str(r["entry_id"]) == entry_id]
        h = pd.DataFrame(history).sort_values("revision", key=lambda s: s.astype(int),
                                              ascending=False)
        # 저장은 UTC 로 하므로 한국 시간으로 바꿔 보여 준다
        when = pd.to_datetime(h["updated_at"], utc=True).dt.tz_convert("Asia/Seoul")
        st.dataframe(
            pd.DataFrame({
                "번호": h["revision"].astype(int).map(lambda n: f"{n}번째"),
                "상태": h["status"].map({"active": "지도에 표시", "deleted": "지도에서 내림"})
                                   .fillna(h["status"]),
                "수정 시각": when.dt.strftime("%Y-%m-%d %H:%M"),
                "카페명": h["cafe_name"],
                "작품": h["work"],
                "주소": h["address"],
                "기간": pd.to_datetime(h["start_date"]).dt.strftime("%m/%d") + " ~ "
                        + pd.to_datetime(h["end_date"]).dt.strftime("%m/%d"),
                "방법": h["source"],
            }),
            width="stretch", hide_index=True,
        )
        st.caption("맨 위가 가장 최근 기록입니다. 되돌리기를 누르면 바로 아래 기록으로 돌아갑니다.")


# ================================================================ 카드 리스트
def _status(row) -> tuple[str, str, int]:
    """(라벨, 배지 색, 정렬 순위). 진행 중이 맨 위로 온다."""
    start = pd.to_datetime(row["start_date"]).date()
    end = pd.to_datetime(row["end_date"]).date()
    if end < TODAY:
        return "종료", "gray", 2
    if start > TODAY:
        return f"D-{(start - TODAY).days}", "blue", 1
    return "진행 중", "green", 0


def _poster_url(value) -> str:
    """카드에 쓸 포스터 주소. 포스터가 없으면 기본 그림 (포스터를 올린 카드와 똑같이 보인다)."""
    poster = images.poster(value)
    return images.url(poster) if poster else images.DEFAULT_POSTER_URL


def _chips(r, full: bool = False) -> str:
    """이벤트 정보는 민트로 채운 칩, 굿즈는 민트 테두리 칩. full 이 아니면 몇 개만 보이고 나머지는 +N 으로 줄인다."""
    all_tags, goods = _split(r.get("tags") or ""), _split(r.get("goods") or "")
    tags = [f'<span class="chip tag">{escape(t)}</span>' for t in (all_tags if full else all_tags[:2])]
    shown = [f'<span class="chip">{escape(g)}</span>' for g in (goods if full else goods[:3])]
    more = [f'<span class="chip">+{len(goods) - 3}</span>'] if not full and len(goods) > 3 else []
    return "".join(tags + shown + more)


def _card_more(r) -> str:
    """리스트 전체보기 카드에 커서를 올리면 펼쳐지는 정보: 캐릭터·주소·특전 전부·칩 전부."""
    def line(icon: str, label: str, value) -> str:
        v = str(value or "").strip()
        return f'<div class="m"><b>{icon} {label}</b><span>{escape(v)}</span></div>' if v else ""
    perks = "".join(f"<li>{escape(x)}</li>" for x in _split(r.get("perks") or ""))
    return (
        line("🎭", "캐릭터", r.get("characters"))
        + line("📍", "주소", r.get("address"))
        + (f'<div class="m"><b>🎁 특전</b><ul>{perks}</ul></div>' if perks else "")
        + (f'<div class="m"><b>🏷️ 이벤트 · 굿즈</b><div class="chips">{_chips(r, full=True)}</div></div>'
           if _chips(r, full=True) else "")
    )


# 위치 배지 색: 시마다 다르게 (바탕, 글자). 서울의 동네는 모두 서울 색, 경기는 시마다.
# 자주 나오는 시는 색을 정해 두고, 그 밖의 시는 이름으로 아래 색 묶음 중 하나를 늘 같게 고른다
CITY_COLORS = {
    "서울": ("#56C2A7", "#fff"), "부산": ("#3B82C4", "#fff"), "인천": ("#8B6CD1", "#fff"),
    "대구": ("#E0884A", "#fff"), "대전": ("#D9A400", "#fff"), "광주": ("#4CA36A", "#fff"),
    "울산": ("#2BA3B5", "#fff"), "제주": ("#F2789B", "#fff"), "세종": ("#7F8C3A", "#fff"),
    "수원": ("#E06C6C", "#fff"), "고양": ("#5A7BD8", "#fff"), "성남": ("#B0639E", "#fff"),
}
_MORE_COLORS = [("#6C9A8B", "#fff"), ("#C77D4E", "#fff"), ("#7A6FB3", "#fff"), ("#4F95A8", "#fff"),
                ("#B5654A", "#fff"), ("#5E8F4A", "#fff"), ("#A0628B", "#fff"), ("#8A7D3E", "#fff")]


def _area_colors(address) -> tuple[str, str]:
    city = geo.city_name(str(address or ""))
    if city in CITY_COLORS:
        return CITY_COLORS[city]
    return _MORE_COLORS[sum(map(ord, city)) % len(_MORE_COLORS)] if city else ("#9AA5A1", "#fff")


def _area_badge(address, cls: str = "abadge") -> str:
    """📍 지역 배지 HTML (시마다 다른 색). 지역을 모르면 빈 문자열.

    테두리는 시 색 그대로(100%), 바탕은 같은 색을 90% 투명하게(불투명도 10%).
    흰 카드 위(지도보기)에서는 글자도 시 색, 포스터 위(리스트 전체보기)에서는 사진 위에서 읽히게 흰 글자.
    """
    area = geo.area_name(str(address or ""))
    if not area:
        return ""
    color, _ = _area_colors(address)
    text = "#fff;text-shadow:0 1px 2px rgba(0,0,0,.45)" if cls == "area" else color
    return (f'<span class="{cls}" style="background:{color}1A;border:1.5px solid {color};color:{text}">'
            f'{escape(area)}</span>')


def _busiest_area(mapped: pd.DataFrame) -> dict | None:
    """지도 처음 화면 범위: 지금 보이는 카페를 시(서울·부산·수원…) 단위로 묶어 가장 많은 시의 점들을 감싸는 범위.
    점이 한 곳에 몰려 있으면 너무 확대되지 않게 최소 폭을 둔다. 카페가 없으면 None (지도 쪽 기본 범위)."""
    if mapped.empty:
        return None
    city = mapped["address"].map(lambda a: geo.city_name(str(a or "")) or "?")
    top = city.value_counts().index[0]
    pts = mapped[city == top]
    south, north = float(pts["lat"].min()), float(pts["lat"].max())
    west, east = float(pts["lng"].min()), float(pts["lng"].max())
    pad_lat = max((north - south) * 0.15, 0.02)       # 위아래·좌우로 조금 여유 (최소 약 2km)
    pad_lng = max((east - west) * 0.15, 0.025)
    return {"south": south - pad_lat, "north": north + pad_lat, "west": west - pad_lng, "east": east + pad_lng}


def _home_area(mapped: pd.DataFrame) -> dict | None:
    """지도 처음 화면 범위: 내 위치를 알면 내 주변(가까운 팝업 몇 곳이 들어오게), 모르면 팝업이 가장 많은 시."""
    loc = st.session_state.get("_my_loc")
    if isinstance(loc, dict) and "lat" in loc and not mapped.empty:
        pts = list(zip(mapped["lat"].astype(float), mapped["lng"].astype(float)))
        return my_place.home_box((float(loc["lat"]), float(loc["lng"])), pts)
    return _busiest_area(mapped)


def _poster_card(r, label: str) -> str:
    return f"""
<div class="pcard" style="background-image:url('{_poster_url(r.get("images"))}')">
  {_area_badge(r.get("address"), cls="area")}
  <span class="state">{escape(label)}</span>
  <div class="info">
    <div class="t">{escape(str(r['work']))}</div>
    <div class="s">☕ {escape(str(r['cafe_name']))}</div>
    <div class="d">{r['start_date']:%m월 %d일} - {r['end_date']:%m월 %d일}</div>
    <div class="chips short">{_chips(r)}</div>
    <div class="more">{_card_more(r)}</div>
  </div>
</div>"""


SORTS = ["최신순", "등록순", "오픈 임박순", "종료 임박순", "인기순", "리뷰 많은 순"]


def _sort_view(view: pd.DataFrame, how: str) -> pd.DataFrame:
    """목록 정렬. 등록 시각은 각 카페의 첫 기록(revision 1)의 시각이다."""
    if view.empty:
        return view
    created: dict[str, str] = {}
    for r in store.all_rows():
        eid, at = str(r.get("entry_id")), str(r.get("updated_at") or "")
        if eid not in created or at < created[eid]:
            created[eid] = at
    all_reviews = reviews.current_rows()
    activity = review.counts(all_reviews)                       # 리뷰 + 답글
    posts = review.counts([r for r in all_reviews if not str(r.get("parent_id") or "")])
    v = view.assign(
        _created=view["entry_id"].map(lambda e: created.get(str(e), "")),
        _activity=view["entry_id"].map(lambda e: activity.get(str(e), 0)),
        _posts=view["entry_id"].map(lambda e: posts.get(str(e), 0)),
        _upcoming=view["start_date"].map(lambda d: 0 if d > TODAY else 1),   # 시작 전이 먼저
        _ended=view["end_date"].map(lambda d: 1 if d < TODAY else 0),        # 종료된 건 뒤로
    )
    by = {
        "최신순": (["_created"], [False]),
        "등록순": (["_created"], [True]),
        "오픈 임박순": (["_upcoming", "start_date", "_created"], [True, True, False]),
        "종료 임박순": (["_ended", "end_date", "_created"], [True, True, False]),
        "인기순": (["_activity", "_created"], [False, False]),
        "리뷰 많은 순": (["_posts", "_activity", "_created"], [False, False, False]),
    }[how if how in SORTS else SORTS[0]]
    return (v.sort_values(by[0], ascending=by[1], kind="stable")
             .drop(columns=["_created", "_activity", "_posts", "_upcoming", "_ended"])
             .reset_index(drop=True))


def _list_bar(count: int, wide: bool, note: str = "") -> None:
    """'팝업 카페 N곳' + 리스트 전체보기/지도보기 전환. 상단 고정 묶음 안에 그린다.
    note 는 제목 옆 도움말(?)에 커서를 올리면 보인다."""
    head, toggle = st.columns([5, 1.3], vertical_alignment="center")
    with head:
        # 지도보기에서는 개수 제목을 두지 않는다 (리스트 전체보기에서만)
        if wide:
            st.markdown(f"#### 팝업 카페 :green[**{count}**]곳", help=note or None)   # 숫자만 굵게
    with toggle:
        if wide:
            if st.button("지도보기", key="show_map", width="content"):
                st.session_state["list_only"] = False
                st.session_state["scroll_top"] = True    # 화면 길이가 바뀌어도 맨 위부터 보이게
                st.rerun()
        elif st.button("리스트 전체보기", key="list_only_btn", width="content",
                       help="지도 없이 리스트만 크게 봅니다"):
            st.session_state["list_only"] = True
            st.session_state["selected"] = None    # 상세를 보던 중이면 닫고 리스트로
            st.session_state["scroll_top"] = True
            st.rerun()


def render_list(view: pd.DataFrame, wide: bool = False) -> None:
    """카페 카드 목록. wide 면 지도 없이 화면 전체에 4열로 깐다."""
    if view.empty:
        st.info("조건에 맞는 카페가 없습니다. 검색어나 필터를 넓혀 보세요.")
        return
    n_reviews = review.counts(reviews.current_rows())

    def open_button(r) -> None:
        """카드 전체를 덮는 투명 버튼. 카드 어디를 눌러도 상세로 넘어간다 (LIST_CSS 의 .st-key-card_)."""
        if st.button("자세히 보기", key=f"open_{r['entry_id']}", width="stretch"):
            # 상세는 지도와 함께 보여 준다. 아래쪽 카드를 눌러도 상세 맨 위부터 보이게 올린다
            # 보던 모드(리스트 전체보기 / 지도보기)는 그대로 둔다. 상세는 모드와 상관없이 지도와 함께 보이고,
            # 리스트로 돌아가면 원래 보던 모드로 돌아간다
            st.session_state["selected"] = r["entry_id"]
            st.session_state["scroll_top"] = True
            st.rerun()

    if wide:
        # 전체보기: dukplace 처럼 포스터가 꽉 찬 카드를 4열로. 카드 비율이 같아 높이가 늘 맞는다
        # 모바일에서는 4개 칸을 하나의 격자로 풀어 2~3열로 작게 보인다 (LIST_CSS 의 .st-key-wide_grid).
        # 칸마다 i%4 번째 카드가 들어가 있어서, 원래 순서대로 놓이게 카드마다 순번(order)을 준다
        order_css = "".join(f'[data-testid="stLayoutWrapper"]:has(> .st-key-card_w_{r["entry_id"]}),'
                            f'.st-key-card_w_{r["entry_id"]}{{order:{i}}}'
                            for i, (_, r) in enumerate(view.iterrows()))
        st.markdown(f"<style>@media (max-width: 640px) {{ {order_css} }}</style>", unsafe_allow_html=True)
        with st.container(key="wide_grid"):
            grid = st.columns(4, gap="small")
            for i, (_, r) in enumerate(view.iterrows()):
                with grid[i % 4], st.container(key=f"card_w_{r['entry_id']}"):
                    st.markdown(_poster_card(r, _status(r)[0]), unsafe_allow_html=True)
                    open_button(r)
                    _heart(r["entry_id"], "w")
        return

    # 반반 보기: 페이지를 스크롤하면 리스트만 내려가고 지도는 화면에 붙어 있다 (LIST_CSS 의 sticky)
    with st.container(border=False):
        for _, r in view.iterrows():
            label, color, _ = _status(r)
            with st.container(border=True, key=f"card_s_{r['entry_id']}"):
                _heart(r["entry_id"], "s")
                thumb, top = st.columns([1.1, 3], vertical_alignment="center")
                with thumb:
                    st.markdown(f'<div class="thumb" style="background-image:url(\'{_poster_url(r.get("images"))}\')"></div>',
                                unsafe_allow_html=True)
                with top:
                    # 📍 지역은 시마다 다른 색 (CITY_COLORS). 진행 상태는 아래 작품 이름 오른쪽에
                    badge = _area_badge(r.get("address"))
                    if badge:
                        st.markdown(badge.replace('">', '">📍 ', 1), unsafe_allow_html=True)
                    chars = str(r.get("characters") or "").strip()
                    # 포스터 옆: 작품(굵게) · 캐릭터(민트) → 카페 이름(회색) → 날짜 · 위치.
                    # 한 덩어리로 그려 카페 이름과 날짜 사이에 칸 간격(빈 줄)이 생기지 않게 한다
                    meta = [f"🗓️ {r['start_date']} ~ {r['end_date']}",
                            f"📍 {escape(str(r['address'] or '-'))}"
                            + ("" if pd.notna(r["lat"]) else " · 지도 표시 안 됨")]
                    if n_reviews.get(r["entry_id"]):
                        meta.append(f"💬 리뷰 {n_reviews[r['entry_id']]}")
                    st.markdown(
                        f'<p class="ctitle"><strong>{escape(str(r["work"]))}</strong>'
                        + f' <span class="cstate {color}">{escape(label)}</span>'
                        + (f'<br/><span class="cchars">{escape(chars)}</span>' if chars else "")
                        + f'<br/><span class="ccafe">☕ {escape(str(r["cafe_name"]))}</span></p>'
                        + f'<p class="cmeta">{"<br/>".join(meta)}</p>',
                        unsafe_allow_html=True)
                # 포스터 아래(카드 전체 폭): 이벤트 정보·굿즈 칩, 그 아래 특전 칩.
                # 두 줄을 한 묶음(.cbottom)으로 그려, 어느 줄만 있든 카드 아래 테두리와 같은 여백을 둔다
                chips = _chips(r)
                gifts = "".join(f'<span class="chip perk">🎁 {escape(x)}</span>'
                                for x in _split(r.get("perks") or ""))
                rows = ((f'<div class="chips below">{chips}</div>' if chips else "")
                        + (f'<div class="chips gifts">{gifts}</div>' if gifts else ""))
                # 굿즈·특전이 없어도 빈 묶음을 두어, 다른 카드처럼 아래 테두리와 여백이 생기게 한다
                st.markdown(f'<div class="cbottom{"" if rows else " none"}">{rows}</div>', unsafe_allow_html=True)
                open_button(r)


# ===================================================================== 지도
LIST_CSS = f"""
<style>
/* 카드 클릭: 카드를 덮는 투명 버튼을 깔고, 커서를 올리면 민트로 물들며 살짝 눌려 들어간다 */
[class*="st-key-card_"] {{ position:relative; cursor:pointer; }}
[class*="st-key-card_"] [class*="st-key-open_"] {{
  position:absolute; inset:0; z-index:5; margin:0; }}
[class*="st-key-open_"] .stButton, [class*="st-key-open_"] .stButton button {{
  width:100%; height:100%; opacity:0; cursor:pointer; }}
/* 팔로우 버튼: 카드 오른쪽 위. 팔로우하면 포인트 색으로 채운다 */
[class*="st-key-card_"] [class*="st-key-fav_"] {{ position:absolute; z-index:7; width:auto; }}
/* 리스트 전체보기: 팔로우는 카드 맨 아래 오른쪽 모서리. 글자 칸 오른쪽을 비워 긴 제목이 버튼 밑으로 들어가지 않게 */
[class*="st-key-card_w_"] [class*="st-key-fav_"] {{ top:auto; bottom:16px; right:20px; }}
[class*="st-key-card_w_"] .pcard .info {{ padding-right:100px; }}
[class*="st-key-card_s_"] [class*="st-key-fav_"] {{ top:12px; right:12px; }}
/* 카드 작품 이름 오른쪽의 진행 상태 배지 */
.cstate {{ display:inline-block; vertical-align:middle; margin-left:6px; font-size:.78rem; font-weight:700;
          line-height:1.4; padding:.1rem .45rem; border-radius:.5rem; white-space:nowrap; }}
.cstate.green {{ background:#E3F6EA; color:#1F7A44; }}
.cstate.blue {{ background:#E5EEFC; color:#2C5BC5; }}
.cstate.gray {{ background:#EEF0EF; color:#6B7672; }}
/* 카드·상세의 팔로우 버튼도 '팔로우한 곳만' 과 같은 스위치: 꺼지면 회색 바탕 + 왼쪽 흰 동그라미 '팔로우',
   켜지면 포인트 색 바탕 + 오른쪽 동그라미 '팔로잉' */
[class*="st-key-fav_"] button {{ position:relative; min-height:0 !important; height:22px; min-width:64px;
  border-radius:999px !important; border:0 !important; background:#E4E8E6 !important;
  padding:0 8px 0 23px !important; box-shadow:0 1px 4px rgba(0,0,0,.12); white-space:nowrap; transition:background .15s; }}
[class*="st-key-fav_"] button::before {{ content:""; position:absolute; left:3px; top:3px; width:16px; height:16px;
  border-radius:50%; background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.2); transition:left .15s; }}
[class*="st-key-fav_"] button p {{ font-size:.66rem !important; font-weight:800 !important; color:#5B6663 !important; }}
[class*="st-key-fav_on_"] button {{ background:var(--accent) !important; padding:0 23px 0 8px !important; }}
[class*="st-key-fav_on_"] button::before {{ left:calc(100% - 19px); }}
[class*="st-key-fav_on_"] button p {{ color:#fff !important; }}
[class*="st-key-fav_off_"] button:hover {{ background:#D5DBD9 !important; }}
[class*="st-key-fav_on_"] button:hover {{ background:var(--accent-deep) !important; }}
/* 카드 테두리: 회색 대신 포인트(민트)보다 살짝 밝은 민트. 커서를 올리면 아래 :hover 처럼 연한 민트 바탕 + 진한 테두리 */
[class*="st-key-card_s_"] {{ border: 2.5px solid {MINT_LINE} !important; transition:transform .18s ease,
  background-color .18s ease, border-color .18s ease, box-shadow .18s ease; }}
[class*="st-key-card_w_"] .pcard {{ border: 2.5px solid {MINT_LINE}; box-sizing: border-box; }}
[class*="st-key-card_s_"] strong {{ font-size:1.2rem; }}
[class*="st-key-card_s_"] [data-testid="stMarkdownContainer"] p {{ font-size:1rem; }}
[class*="st-key-card_s_"] [data-testid="stCaptionContainer"],
[class*="st-key-card_s_"] [data-testid="stCaptionContainer"] p {{ font-size:15px !important;
  color:#3f4a47 !important; line-height:1.7; }}
[class*="st-key-card_s_"]:hover {{ transform:scale(.975); background:{MINT_SOFT} !important;
  border-color:{MINT} !important; box-shadow:0 0 0 2px {MINT} inset; }}
[class*="st-key-card_s_"]:active {{ transform:scale(.96); }}
[class*="st-key-card_w_"] .pcard {{ transition:transform .18s ease, box-shadow .18s ease; }}
[class*="st-key-card_w_"]:hover .pcard {{ transform:scale(.965);
  box-shadow:0 0 0 3px {MINT}, 0 4px 14px rgba(0,0,0,.08); }}
[class*="st-key-card_w_"]:hover .pcard {{ filter:saturate(1.1) brightness(.95); }}
[class*="st-key-card_w_"]:active .pcard {{ transform:scale(.95); }}
/* 커서를 올리면 글자 칸이 카드 전체로 펼쳐지며 숨어 있던 정보를 모두 보여 준다 */
.pcard .more {{ display:none; }}
.pcard .area, .pcard .state {{ z-index:2; }}   /* 펼친 막 위에서도 지역·상태 배지가 보이게 */
.pcard .info {{ transition:height .25s ease, background-color .25s ease; }}
/* 펼친 막: 위는 검정에 가까운 아주 어두운 초록, 아래로 갈수록 밝은 민트가 되는 그라데이션.
   색 90%(포스터는 10% 만 비친다)로 덮어 흰 글자가 잘 읽히게 한다 */
[class*="st-key-card_w_"]:hover .pcard .info {{ height:100%; padding-top:44px; overflow-y:auto;
  background:linear-gradient(180deg, rgba(4,28,22,.9) 0%, rgba(12,62,50,.9) 40%,
                             rgba(30,120,98,.9) 75%, rgba(60,170,142,.9) 100%); }}
/* 어두운 막 위에서 읽히게: 항목 이름은 밝은 민트, 민트로 채운 칩은 포인트 색 그대로 */
[class*="st-key-card_w_"]:hover .pcard .more .m b {{ color:#B8EBDD; }}
[class*="st-key-card_w_"]:hover .pcard .chip.tag {{ background:{MINT}; border-color:{MINT}; color:#fff; }}
[class*="st-key-card_w_"]:hover .pcard .chips.short {{ display:none; }}
[class*="st-key-card_w_"]:hover .pcard .more {{ display:block; margin-top:8px; }}
[class*="st-key-card_w_"]:hover .pcard .t {{ white-space:normal; }}
.pcard .more .m {{ font-size:13.5px; line-height:1.5; margin:0 0 8px; }}
.pcard .more .m b {{ display:block; color:#9fe3d1; font-size:12.5px; margin-bottom:2px; }}
.pcard .more ul {{ margin:0; padding-left:1.1em; }}
.pcard .more .chips {{ height:auto; flex-wrap:wrap; overflow:visible; }}
/* 상단 묶음(제목·등록하기·검색 필터): 스크롤해도 늘 위에 붙어 있다 */
/* 반반 보기: 지도 칸은 상단 묶음 바로 아래에 붙어 있고 리스트만 스크롤된다 */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] iframe[src*="kakao_map"]) {{
  align-items: flex-start; }}
[data-testid="stColumn"]:has(iframe[src*="kakao_map"]) {{
  position: sticky; top: calc({TOPBAR_TOP} + {TOPBAR_H} + .75rem); }}
/* 지도 높이는 남은 화면 높이에 맞춘다 (화면이 작아도 지도 아래가 잘리지 않게) */
iframe[src*="kakao_map"] {{
  height: max(360px, calc(100vh - {TOPBAR_TOP} - {TOPBAR_H} - 1.75rem)) !important; }}
/* 필터 판 안의 '팔로우한 곳만' · '지역 고르기' 는 모바일에서만. 모바일에서는 목록 위의 같은 칸을 숨긴다 */
.st-key-m_only {{ display: none !important; }}
@media (max-width: 640px) {{
  .st-key-m_only {{ display: flex !important; }}
  /* 필터 판 맨 위에 둔다 (그리는 순서는 아래지만 화면에서는 앞으로) */
  .st-key-filters > [data-testid="stLayoutWrapper"]:has(> .st-key-m_only),
  .st-key-filters > .st-key-m_only {{ order: -1; }}
  .st-key-listtools [class*="st-key-folsw_"], .st-key-listtools .st-key-regions {{ display: none !important; }}
  /* 비어 버린 칸(필터 판으로 옮긴 찜·지역)은 칸째 빼고, '팝업 카페 N곳' ~ 정렬 사이 줄 간격을 좁힌다 */
  .st-key-listtools [data-testid="stColumn"]:has([class*="st-key-folsw_"]),
  .st-key-listtools [data-testid="stColumn"]:has(.st-key-regions),
  .st-key-listtools [data-testid="stColumn"]:not(:has([data-testid="stElementContainer"])) {{ display: none !important; }}
  .st-key-listbar [data-testid="stHorizontalBlock"] {{ gap: .35rem !important; }}
  /* '팝업 카페 N곳' 과 정렬 칸 사이, 정렬 칸과 목록 사이를 붙지 않게 띄운다 */
  .st-key-listtools > [data-testid="stHorizontalBlock"],
  .st-key-listtools [data-testid="stHorizontalBlock"]:has(.st-key-sort) {{ gap: .8rem !important; }}
  .st-key-listtools {{ margin-bottom: .6rem; }}
  /* 지도보기·리스트 전체보기 칸: 버튼은 화면 아래에 떠 있으니 칸 자체는 높이 0 (숨기면 버튼까지 사라져서 크기만 없앤다) */
  .st-key-listbar [data-testid="stColumn"]:has(.st-key-show_map),
  .st-key-listbar [data-testid="stColumn"]:has(.st-key-list_only_btn) {{
    height: 0 !important; min-height: 0 !important; margin: 0 !important; padding: 0 !important; }}
  .st-key-listbar h4 {{ padding-bottom: 0 !important; margin-bottom: 0 !important; }}
}}
/* 지도보기 · 리스트 전체보기 전환 버튼: PC·모바일 모두 화면 아래 가운데에 떠 있는 버튼 */
.st-key-show_map, .st-key-list_only_btn {{ position: fixed !important; left: 50%; bottom: 24px;
  transform: translateX(-50%); z-index: 1000; width: auto !important; }}
/* 평소: 흰 바탕 + 포인트(민트) 테두리·글자 / 커서를 올리거나 누르면: 포인트 바탕 + 흰 글자 */
.st-key-show_map button, .st-key-list_only_btn button, .st-key-m_filter_btn button {{ background: #fff !important;
  color: {MINT_DEEP} !important; border: 2px solid {MINT} !important; padding: .55rem 1.5rem !important;
  min-height: 0 !important; box-shadow: 0 6px 18px rgba(0,0,0,.16) !important; white-space: nowrap; }}
.st-key-show_map button p, .st-key-list_only_btn button p, .st-key-m_filter_btn button p {{ font-weight: 700; }}
.st-key-show_map button:hover, .st-key-list_only_btn button:hover, .st-key-m_filter_btn button:hover,
.st-key-show_map button:active, .st-key-list_only_btn button:active, .st-key-m_filter_btn button:active {{
  background: {MINT} !important; color: #fff !important; border-color: {MINT} !important; }}
/* 떠 있는 버튼이 맨 아래 카드를 가리지 않게 페이지 아래에 여백 */
.stMainBlockContainer {{ padding-bottom: 6rem !important; }}
@media (max-width: 640px) {{
  /* 모바일: '필터' 와 '지도보기 / 리스트 전체보기' 를 화면 아래 가운데에 나란히 (가운데에서 6px 씩 떨어져) */
  .st-key-show_map, .st-key-list_only_btn {{ bottom: 20px; transform: translateX(6px); }}
  .st-key-m_filter_btn {{ position: fixed !important; left: 50%; bottom: 20px;
    transform: translateX(calc(-100% - 6px)); z-index: 1000; width: auto !important; }}
  /* 두 버튼 폭을 똑같이 해서, 가운데에서 6px 씩 떨어진 두 버튼 묶음이 정확히 가운데에 오게 한다 */
  .st-key-show_map button, .st-key-list_only_btn button, .st-key-m_filter_btn button {{
    padding: .55rem .6rem !important; width: 140px !important; justify-content: center; }}
  /* 상세의 '리스트로 돌아가기' 는 화면 아래 가운데에 띄운다 (모양은 등록하기 버튼과 같다) */
  .st-key-back_to_list {{ position: fixed !important; left: 50%; bottom: 20px;
    transform: translateX(-50%); z-index: 1000; width: auto !important; }}
  .st-key-back_to_list button {{ height: 40px !important; padding: 0 1.4rem !important;
    box-shadow: 0 6px 18px rgba(0,0,0,.16) !important; white-space: nowrap; }}
  /* 떠 있는 버튼이 맨 아래 카드를 가리지 않게 페이지 아래에 여백 */
  .stMainBlockContainer {{ padding-bottom: 6rem !important; }}
}}
/* 모바일 리스트 전체보기: 4개 칸을 풀어 하나의 격자로 (폭 480px 이하 2열, 그 위 3열), 카드 글자도 작게 */
@media (max-width: 640px) {{
  .st-key-wide_grid [data-testid="stHorizontalBlock"] {{ display: grid !important;
    grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: .6rem !important; row-gap: 2rem !important;
    height: auto !important; align-items: start; }}
  /* 카드(격자 칸)는 내용 높이만큼만 차지하고, 목록 전체 아래에 여유를 둬 다음 영역과 겹치지 않게 */
  .st-key-wide_grid [data-testid="stLayoutWrapper"]:has(> [class*="st-key-card_w_"]),
  .st-key-wide_grid [class*="st-key-card_w_"] {{ height: auto !important; min-height: 0 !important;
    position: relative; }}
  .st-key-wide_grid {{ padding-bottom: 3.5rem; margin-bottom: 1.5rem; }}
  .st-key-wide_grid [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
  .st-key-wide_grid [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{
    display: contents !important; }}
  .st-key-wide_grid .pcard {{ border-radius: 12px; margin-bottom: 0; }}
  .st-key-wide_grid .pcard .info {{ height: 84px; padding: 8px 9px; }}
  .st-key-wide_grid .pcard .t {{ font-size: 14.5px; }}
  .st-key-wide_grid .pcard .s {{ font-size: 11.5px; }}
  .st-key-wide_grid .pcard .d {{ font-size: 12px; margin: 2px 0 0; }}
  .st-key-wide_grid .pcard .chips {{ display: none; }}
  .st-key-wide_grid .pcard .area {{ top: 6px; left: 6px; font-size: 10.5px; padding: 2px 6px; }}
  .st-key-wide_grid .pcard .state {{ top: 6px; right: 6px; font-size: 10.5px; padding: 2px 7px; }}
  .st-key-wide_grid [class*="st-key-fav_"] {{ top: auto !important; bottom: 8px !important; right: 12px !important; }}
  .st-key-wide_grid .pcard .info {{ padding-right: 76px; }}
  .st-key-wide_grid [class*="st-key-fav_"] button {{ height: 20px; min-width: 56px; padding: 0 6px 0 20px !important; }}
  .st-key-wide_grid [class*="st-key-fav_on_"] button {{ padding: 0 20px 0 6px !important; }}
  .st-key-wide_grid [class*="st-key-fav_"] button::before {{ width: 14px; height: 14px; }}
  .st-key-wide_grid [class*="st-key-fav_on_"] button::before {{ left: calc(100% - 17px); }}
  .st-key-wide_grid [class*="st-key-fav_"] button p {{ font-size: .6rem !important; }}
}}
@media (max-width: 480px) {{
  .st-key-wide_grid [data-testid="stHorizontalBlock"] {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
}}
/* 모바일 상세: 이미지 슬라이드와 작품 제목 사이 간격을 절반으로 (칸 사이 기본 간격 + 제목 위 여백을 줄인다) */
@media (max-width: 640px) {{
  .st-key-detail_left [data-testid="stElementContainer"]:has(iframe[src*="gallery"]) {{ margin-bottom: -.5rem; }}
  .st-key-detail_left h3 {{ padding-top: .2rem !important; }}
}}
/* 모바일 지도보기: 지도를 맨 위에, 그 아래 리스트는 왼쪽 작은 포스터 + 오른쪽 정보 (PC 는 그대로 반반) */
@media (max-width: 640px) {{
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] iframe[src*="kakao_map"]):not(:has(.st-key-detail_left)) {{
    flex-direction: column; }}
  [data-testid="stHorizontalBlock"]:not(:has(.st-key-detail_left)) > [data-testid="stColumn"]:has(iframe[src*="kakao_map"]) {{
    order: -1; }}
  /* 카드: 왼쪽에 작은 포스터(고정 폭), 오른쪽에 정보. 칸이 세로로 쌓이지 않고 가로로 나란히 */
  [class*="st-key-card_s_"] [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .thumb) {{
    flex-direction: row !important; flex-wrap: nowrap !important; gap: .8rem !important; align-items: center; }}
  [class*="st-key-card_s_"] [data-testid="stColumn"]:has(.thumb) {{
    flex: 0 0 84px !important; width: 84px !important; min-width: 84px !important; }}
  [class*="st-key-card_s_"] [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .thumb)
    > [data-testid="stColumn"]:not(:has(.thumb)) {{ flex: 1 1 auto !important; width: auto !important; min-width: 0 !important; }}
  [class*="st-key-card_s_"] .thumb {{ border-radius: 10px; }}
  iframe[src*="kakao_map"] {{ height: 58vh !important; min-height: 320px; }}
}}
/* 상세 화면: 왼쪽 칸(정보 + 지도)은 길어서 화면에 붙이지 않고, 지도는 고정 높이로 둔다 */
[data-testid="stColumn"]:has(.st-key-detail_left) {{ position: static !important; }}
[data-testid="stColumn"] .st-key-detail_left iframe[src*="kakao_map"] {{ height: 420px !important; }}
.st-key-detail_left [data-testid="stElementContainer"]:has(.stLinkButton) {{ align-self: center; width: auto !important; }}
.st-key-detail_left .stLinkButton a {{ border-radius: 999px !important; padding: 0 1.3rem !important;
  background: #fff !important; border: 1.5px solid {MINT} !important; color: {MINT_DEEP} !important; }}
.st-key-detail_left .stLinkButton a:hover {{ background: {MINT_SOFT} !important; }}
.thumb {{ aspect-ratio:3/4; border-radius:14px; background-size:cover; background-position:center; }}
/* 리뷰 답글: 평소엔 한 줄짜리 입력칸만. 칸을 누르거나 글이 들어 있으면 닉네임 줄과 등록·취소 버튼이 나오고 칸이 커진다 */
[class*="st-key-rpbox_"] [data-testid="stElementContainer"]:has([data-testid="stCaptionContainer"]),
[class*="st-key-rpbox_"] [data-testid="stHorizontalBlock"] {{ display: none; }}
[class*="st-key-rpbox_"]:focus-within [data-testid="stElementContainer"]:has([data-testid="stCaptionContainer"]),
[class*="st-key-rpbox_"]:has(textarea:not(:placeholder-shown)) [data-testid="stElementContainer"]:has([data-testid="stCaptionContainer"]) {{
  display: block; }}
[class*="st-key-rpbox_"]:focus-within [data-testid="stHorizontalBlock"],
[class*="st-key-rpbox_"]:has(textarea:not(:placeholder-shown)) [data-testid="stHorizontalBlock"] {{ display: flex; }}
[class*="st-key-rpbox_"] [data-baseweb="textarea"], [class*="st-key-rpbox_"] textarea {{
  min-height: 2.6rem !important; height: 2.6rem !important; transition: height .15s; }}
[class*="st-key-rpbox_"]:focus-within [data-baseweb="textarea"], [class*="st-key-rpbox_"]:focus-within textarea,
[class*="st-key-rpbox_"]:has(textarea:not(:placeholder-shown)) [data-baseweb="textarea"],
[class*="st-key-rpbox_"]:has(textarea:not(:placeholder-shown)) textarea {{ height: 5rem !important; }}
/* 다녀온 후기 별점: 가운데 정렬 질문 + 안내 + 큰 별 5개 (회색, 고른 별까지 노랑. 커서를 올리면 그 별까지 미리 노랑) */
[class*="_rate_box_"] {{ display: flex; flex-direction: column; align-items: center; text-align: center; gap: .2rem !important;
  padding: .4rem 0 .2rem; }}
[class*="_rate_box_"] [data-testid="stElementContainer"] {{ width: 100% !important; display: flex;
  justify-content: center; height: auto !important; }}
.rv-rate-q {{ font-weight: 800; font-size: 1.15rem; color: #26302D; text-align: center; width: 100%; }}
.rv-rate-sub {{ color: #8A9490; font-size: .95rem; margin-top: 4px; text-align: center; width: 100%; }}
[class*="_rate_box_"] [data-testid="stFeedback"] {{ margin-top: .5rem; }}
[class*="_rate_box_"] [data-testid="stFeedback"] [role="radiogroup"] {{ gap: .3rem; }}
/* 안 고른 별은 stFeedbackButton(아이콘 글자), 고른 별은 stFeedbackButtonActive(작은 노란 그림)라 둘 다 맞춘다.
   버튼 높이를 별 크기에 맞춰 위 안내 문구와 겹치지 않게 한다 */
[class*="_rate_box_"] [data-testid^="stFeedbackButton"] {{ padding: 0 !important; background: none !important;
  height: 2.9rem !important; min-height: 0 !important; width: 2.9rem !important; min-width: 2.9rem !important;
  line-height: 1; display: flex !important; align-items: center; justify-content: center; }}
[class*="_rate_box_"] [data-testid="stFeedback"] [role="radiogroup"] {{ gap: .45rem !important;
  justify-content: center; }}
[class*="_rate_box_"] [data-testid="stFeedbackButtonActive"] img {{ display: none !important; }}
[class*="_rate_box_"] [data-testid="stFeedbackButtonActive"] > span::before {{ content: "★";
  font-family: "Segoe UI Symbol", "Apple Color Emoji", sans-serif; font-size: 2.6rem; line-height: 1;
  color: #FFC94D; transition: color .12s; }}
/* 고른 상태에서 더 앞의 별에 커서를 올리면, 그 뒤의 고른 별은 회색으로 미리 보여 준다 */
[class*="_rate_box_"] [role="radiogroup"]:hover [data-testid^="stFeedbackButton"]:hover
  ~ [data-testid="stFeedbackButtonActive"] > span::before {{ color: #CDD3DE; }}
/* 아이콘 글꼴로는 '꽉 찬 별'을 만들 수 없어서, 아이콘 글자는 숨기고 그 자리에 큰 ★ 를 그린다 (색은 아래 규칙) */
[class*="_rate_box_"] [data-testid="stFeedbackButton"] [data-testid="stIconMaterial"] {{ font-size: 0 !important;
  width: auto !important; height: auto !important; color: #CDD3DE !important; transition: color .12s; }}
[class*="_rate_box_"] [data-testid="stFeedbackButton"] [data-testid="stIconMaterial"]::before {{ content: "★";
  font-family: "Segoe UI Symbol", "Apple Color Emoji", sans-serif; font-size: 2.6rem; line-height: 1; }}
[class*="_rate_box_"] [data-testid="stFeedbackButton"][aria-checked="true"] [data-testid="stIconMaterial"],
[class*="_rate_box_"] [data-testid="stFeedbackButton"]:has(~ [aria-checked="true"]) [data-testid="stIconMaterial"],
[class*="_rate_box_"] [role="radiogroup"]:hover [data-testid="stFeedbackButton"] [data-testid="stIconMaterial"] {{
  color: #FFC94D !important; }}
[class*="_rate_box_"] [role="radiogroup"]:hover [data-testid="stFeedbackButton"]:hover ~ [data-testid="stFeedbackButton"]
  [data-testid="stIconMaterial"] {{ color: #CDD3DE !important; }}
/* 지도보기 카드의 📍 지역 배지 (색은 시마다 다르게 글자에 직접 넣는다) — 옆의 상태 배지와 같은 크기 */
.abadge {{ display:inline-block; font-size:.8rem; font-weight:600; line-height:1.4; padding:.1rem .45rem;
          border-radius:.5rem; margin-right:.2rem; vertical-align:middle; }}
.chips {{ display:flex; flex-wrap:wrap; gap:4px; margin:2px 0 4px; }}
/* 칩: 이벤트 정보는 민트로 채우고, 굿즈는 민트 테두리 + 진한 민트 글자 */
.chip {{ font-size:12.5px; font-weight:600; padding:3px 10px; border-radius:999px; background:{MINT_SOFT};
        color:{MINT_DEEP}; border:1px solid {MINT}; white-space:nowrap; }}
.chip.tag {{ background:{MINT}; color:#fff; border-color:{MINT}; }}
/* 반반 보기 카드: 카페 이름은 회색, 캐릭터 이름은 민트 포인트 */
.ctitle .ccafe {{ color: #6b7672; }}
.ctitle .cchars {{ color: {MINT_DEEP}; font-weight: 600; }}
/* 반반 보기 카드: 카페 이름 바로 아래 날짜·위치 (예전 작은 회색 글씨와 같은 모양, 사이 간격 없이) */
.ctitle {{ margin-bottom: 4px !important; }}
[class*="st-key-card_s_"] .cmeta {{ font-size: 15px !important; color: #3f4a47; line-height: 1.7;
  margin: 0 !important; }}
/* 반반 보기 카드: 포스터 아래 칩 묶음(이벤트·굿즈 줄 + 특전 줄). 묶음 전체 아래에 카드 테두리와 한 칸 여백 */
.cbottom {{ margin: 4px 0 22px; }}
.cbottom .chips.below, .cbottom .chips.gifts {{ margin: 2px 0; }}
/* 칩이 하나도 없는 카드: 빈 묶음 칸(위 칸 간격) + 약간의 여백으로 다른 카드와 같은 아래 여백을 만든다 */
.cbottom.none {{ margin: 0 0 6px; height: 0; }}
.chip.perk {{ background:{MINT}; color:#fff; border-color:{MINT}; white-space:normal; line-height:1.4; }}
/* '방문 전 확인' 상자: 연회색 둥근 상자, 굵은 제목, 왼쪽 항목 이름(고정 폭·회색) + 오른쪽 내용(왼쪽 정렬) */
.dinfo {{ margin: 18px 0 0; background:{GRAY_SOFT}; border-radius:18px; padding:20px 24px 8px; }}
/* 공유·찜 줄과 '방문 전 확인' 상자 사이를 좁힌다 (칸 사이 기본 간격만 남기고 조금 더 당긴다) */
.st-key-detail_actions {{ margin-bottom: -.75rem; }}
.dinfo-title {{ font-weight:800; font-size:1.1rem; color:#1F2A27; margin-bottom:10px; }}
/* 폭이 모자라면(휴대폰) 오른쪽 끝의 '지도에서 확인하기' 만 다음 줄 오른쪽으로 내려간다 */
.drow {{ display:flex; flex-wrap:wrap; align-items:flex-start; column-gap:18px; row-gap:6px; padding:8px 0 14px; }}
.dlabel {{ flex:0 0 72px; color:#6B7672; font-weight:700; font-size:1rem; white-space:nowrap; line-height:1.7; }}
.dval {{ flex:1 1 180px; min-width:0; text-align:left; font-size:1.02rem; color:#26302D; line-height:1.7;
        word-break:keep-all; }}
/* 상세 머리글: 지역(작게, 시 색) → 작품 이름(아주 크게) → 캐릭터(회색) + 진행 상태 배지(포인트 색) */
.dhead {{ margin: 10px 0 6px; }}
.dregion {{ font-weight: 800; font-size: 1rem; margin-bottom: 4px; }}
/* 1줄: 📍 지역(왼쪽) + 진행 상태 배지(오른쪽 끝, 작게) */
.dtop {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 2px; }}
/* 2줄: 작품 이름 (공유·찜 버튼과 같은 줄, 이름이 길면 이름만 줄이 바뀐다) */
.dtitle {{ font-weight: 900; font-size: 2.2rem; line-height: 1.2; color: #111; word-break: keep-all; }}
.dsub {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 12px; }}
/* 캐릭터 이름: 포인트(민트) 색으로 강조 */
.dchars {{ color: {MINT_DEEP}; font-size: 1.05rem; font-weight: 700; }}
.dstate {{ display: inline-block; background: {MINT_DEEP}; color: #fff; font-weight: 800; font-size: .78rem;
          padding: .18rem .55rem; border-radius: 6px; white-space: nowrap; }}
.dstate.ended {{ background: #9AA5A1; }}
/* 상세 팔로우 스위치: 공유 버튼(40px) 옆에 세로 가운데로 */
.st-key-detail_actions [class*="st-key-fav_"] button {{ width: 70px !important; height: 24px !important;
  box-shadow: none !important; transform: none !important; }}
.st-key-detail_actions [class*="st-key-fav_"] button p {{ font-size: .7rem !important; }}
/* 2줄을 화면 폭과 상관없이 한 줄에: 작품 이름 칸이 남는 폭, 공유·찜 칸은 버튼 크기(40px)만큼 오른쪽 끝.
   공유를 누르면 공유 칸이 넓어진다(공유 컴포넌트가 바깥 칸 폭을 직접 바꾼다) */
.st-key-detail_actions [data-testid="stHorizontalBlock"] {{ flex-direction: row !important; flex-wrap: nowrap !important;
  gap: 8px !important; align-items: center !important; }}
.st-key-detail_actions [data-testid="stColumn"]:first-child {{ flex: 1 1 auto !important; width: auto !important;
  min-width: 0 !important; }}
.st-key-detail_actions [data-testid="stColumn"]:not(:first-child) {{ flex: 0 0 40px !important; width: 40px !important;
  min-width: 0 !important; transition: flex-basis .2s, width .2s; }}
.st-key-detail_actions [data-testid="stColumn"]:last-child {{ flex: 0 0 70px !important; width: 70px !important; }}
/* 공유 iframe 은 글자처럼 줄에 놓여 아래 8px 빈칸이 생기고, 그만큼 찜 버튼보다 위로 떠 보였다 → 블록으로 */
.st-key-detail_actions iframe {{ display: block; }}
/* 위치 안의 카페 이름: 굵게 (주소보다 돋보이게), 주소는 그 아래 */
.dcafe {{ font-weight:800; font-size:1.1rem; color:#1F2A27; line-height:1.6; }}
.daddr {{ color:#3F4A47; font-size:1rem; }}
/* 지도에서 확인하기: 위치 줄 오른쪽 끝에 붙는 작은 흰 알약 버튼 (줄 맨 위에 맞춘다) */
.dbtn {{ flex:0 0 auto; align-self:flex-start; margin-left:auto; padding:.3rem .85rem; border:1px solid #DDE2E0;
        border-radius:999px; background:#fff; color:#26302D !important; text-decoration:none !important;
        font-size:.92rem; font-weight:700; white-space:nowrap; }}
.dbtn:hover {{ border-color:{MINT}; color:{MINT_DEEP} !important; }}
/* '방문 전 확인' 상자와 혜택 사이 여백 (상자가 회색이라 따로 띠는 두지 않는다) */
.dband {{ height:0; margin:0 0 22px; }}
/* 혜택 · 참고 웹사이트 묶음: 굵은 제목, 검은 알약 라벨, 연회색 상자 목록 */
.dsec {{ margin-bottom:18px; }}
.dsec-title {{ font-family:"Jua", sans-serif; font-size:1.45rem; color:#26302D; margin:0 0 10px; }}
/* 라벨(왼쪽, 고정 폭) | 내용 상자(오른쪽, 남는 폭)를 한 줄에 */
.dgroup {{ display:flex; align-items:flex-start; gap:12px; margin-bottom:12px; }}
.dpill {{ display:inline-block; flex:0 0 auto; min-width:64px; text-align:center; background:#26302D; color:#fff;
         font-weight:700; font-size:.9rem; padding:.4rem .9rem; border-radius:999px; margin-top:10px; }}
.dbox {{ flex:1 1 auto; min-width:0; list-style:none; margin:0 !important; padding:14px 18px !important;
         background:{GRAY_SOFT}; border-radius:16px; }}
/* Streamlit 기본 목록 들여쓰기를 없애 상자 안쪽 여백에 바로 붙게 */
.dbox li {{ font-size:1rem; line-height:1.75; color:#26302D; margin:0 !important; padding:0 !important;
           list-style:none; }}
.dbox li::marker {{ content:""; }}
.dnone {{ color:#9AA5A1; }}
/* 참고 웹사이트 카드: 연회색 둥근 카드, 오른쪽 위 ↗. 카드 전체가 링크 */
.dlink {{ display:flex; justify-content:space-between; align-items:flex-start; gap:12px; background:{GRAY_SOFT};
         border-radius:16px; padding:16px 20px; margin-bottom:10px; text-decoration:none !important;
         color:#26302D !important; transition:background .15s; }}
.dlink:hover {{ background:{MINT_SOFT}; }}
.dlink-text {{ min-width:0; }}
.dlink-title {{ font-weight:700; font-size:1.05rem; }}
.dlink-url {{ color:#6B7672; font-size:.9rem; margin-top:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.dlink-go {{ color:{MINT_DEEP}; font-size:1.4rem; line-height:1; flex:0 0 auto; }}
/* 상세 화면의 특전·굿즈 칩: 크게, 긴 문구는 줄바꿈 */
.dchips {{ margin:4px 0 14px; }}
.dchips .lbl {{ font-weight:700; font-size:1rem; margin-bottom:6px; }}
.dchips .chips {{ gap:6px; }}
.dchips .chip {{ font-size:14px; padding:5px 13px; white-space:normal; line-height:1.4; }}
.dchips .chip.perk {{ background:{MINT}; color:#fff; border-color:{MINT}; }}
.dchips .none {{ color:#9aa5a1; }}
/* 포스터 카드 (리스트 전체보기) */
.pcard {{ position:relative; aspect-ratio:3/4.1; border-radius:18px; overflow:hidden;
          background-color:{GRAY_SOFT}; background-size:cover; background-position:center;
          box-shadow:0 4px 14px rgba(0,0,0,.08); margin-bottom:6px; transition:transform .15s; }}

.pcard .area {{ position:absolute; top:10px; left:10px; background:{MINT}; color:#fff;
                font-size:12px; font-weight:700; padding:3px 9px; border-radius:8px; }}
.pcard .state {{ position:absolute; top:10px; right:10px; background:#fff; box-shadow:0 1px 4px rgba(0,0,0,.1);
                 color:{MINT_DEEP}; font-size:13.5px; font-weight:800; padding:4px 12px; border-radius:999px; }}
/* 글자 칸은 높이를 고정한다. 특전·굿즈 칩이 없어도 카드마다 제목·날짜 줄이 같은 높이에 온다 */
.pcard .info {{ position:absolute; left:0; right:0; bottom:0; height:138px; padding:12px 14px;
                box-sizing:border-box; color:#fff; z-index:1; }}
/* 사진 카드는 글자가 잘 보이도록 아래쪽을 어둡게 (글자 칸 높이와 상관없이 같은 그라데이션) */
.pcard::after {{ content:""; position:absolute; left:0; right:0; bottom:0; height:55%;
                 background:linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,.72) 60%);
                 pointer-events:none; }}
.pcard .chips {{ height:26px; overflow:hidden; flex-wrap:nowrap; margin:0; }}

.pcard .t {{ font-family:"Jua", sans-serif; font-size:21px; line-height:1.25; margin-bottom:2px;
             overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.pcard .s {{ font-size:14.5px; opacity:.92; font-weight:600; overflow:hidden; text-overflow:ellipsis;
             white-space:nowrap; }}
.pcard .d {{ font-size:16.5px; font-weight:700; opacity:1; margin:3px 0 7px; }}
.pcard .chip {{ background:#fff; }}
.pcard .chip.tag {{ background:{MINT}; }}
</style>
"""


def _scroll_top() -> None:
    """페이지를 맨 위로 올린다. Streamlit 은 다시 그려도 스크롤 위치를 그대로 두어서,
    상세를 닫고 돌아오면 짧아진 페이지의 맨 아래에 머문다.

    지도·리스트가 다 그려지는 동안 페이지 길이가 바뀌며 위치가 다시 밀릴 수 있어서,
    1.2초 동안 몇 번 더 맨 위로 올린다 (그 사이 사용자가 스크롤하면 멈춘다).
    """
    # 내용이 지난번과 똑같으면 Streamlit 이 칸을 다시 쓰고 스크립트를 다시 돌리지 않는다.
    # (리스트 전체보기 → 지도보기처럼 연달아 올릴 때 두 번째가 안 먹었다) 그래서 매번 다른 번호를 붙인다
    n = st.session_state["_scroll_n"] = st.session_state.get("_scroll_n", 0) + 1
    components.html(
        f"<script>/* {n} */ const w = window.parent, d = w.document;"
        "if (w.__aniKeepStop) w.__aniKeepStop();"
        "const els = () => [d.querySelector('[data-testid=stMain]'),"
        " d.querySelector('[data-testid=stAppViewContainer]'), d.scrollingElement];"
        "let moved = false; const stop = () => { moved = true; };"
        "['wheel', 'touchmove', 'keydown'].forEach(t => d.addEventListener(t, stop, {once: true, capture: true}));"
        "const up = () => { if (!moved) els().forEach(e => e && e.scrollTo({top: 0})); };"
        "up(); [100, 300, 600, 1200].forEach(ms => setTimeout(up, ms));</script>",
        height=0,
    )


def _no_translate() -> None:
    """페이지를 한국어로 표시해 크롬 자동 번역이 'ANI:WHERE' 를 '아니:어디에' 로 바꾸지 않게 한다."""
    components.html(
        "<script>const d = window.parent.document;"
        "d.documentElement.lang = 'ko'; d.documentElement.setAttribute('translate', 'no');"
        "if (!d.querySelector('meta[name=google]')) { const m = d.createElement('meta');"
        "m.name = 'google'; m.content = 'notranslate'; d.head.appendChild(m); }</script>",
        height=0,
    )


def _history_guard(on_main: bool) -> None:
    """메인에서는 브라우저 뒤로가기로 다른 화면(등록 화면 등)에 가지 않게 한다.

    크롬은 스크립트로 쌓은 기록을 뒤로가기 때 건너뛰므로 기록을 쌓아 막을 수 없다.
    대신 화면마다 '지금 메인인지' 를 적어 두고, 메인에서 뒤로가기로 다른 화면에 가면 바로 앞으로 되돌린다.
    다른 화면(등록하기)에서의 뒤로가기는 그대로 둔다.
    """
    components.html(
        # 이 칸은 다시 그릴 때마다 새로 만들어지고, 사라진 칸의 코드는 브라우저가 실행하지 않는다.
        # 그래서 그릴 때마다 예전 감시 코드를 떼고 새로 붙인다
        "<script>const w = window.parent;"
        f"w.__aniOnMain = {'true' if on_main else 'false'};"
        "if (w.__aniBackGuard) w.removeEventListener('popstate', w.__aniBackGuard);"
        "w.__aniBackGuard = () => {"
        "  if (w.__aniOnMain && !/^\\/(map)?\\/?$/.test(w.location.pathname)) w.history.go(1); };"
        "w.addEventListener('popstate', w.__aniBackGuard);"
        "</script>",
        height=0,
    )


_KEEP_SCROLL_JS = """
(function () {
  if (window.__aniKeepScroll) return;
  window.__aniKeepScroll = true;
  let saved = null, until = 0, userMoved = false;
  const main = () => document.querySelector('[data-testid=stMain]');
  // 맨 위로 올릴 때(_scroll_top)는 지키던 위치를 놓아 준다
  window.__aniKeepStop = () => { until = 0; };
  // 선택 버튼(리뷰 종류·탭·체크·스위치)이나 상세 탭(리뷰·수정하기) 안을 누르는 순간의 스크롤 위치를 기억한다.
  // 수정하기에서 이미지 삭제·추가 같은 걸 누를 때마다 화면이 맨 아래로 튀지 않게 한다
  const PICKS = '[data-testid=stButtonGroup], [data-baseweb=tab], [data-testid=stCheckbox], [data-testid=stToggle],'
              + ' [role=tabpanel], [data-baseweb=tab-panel]';
  const remember = (e) => {
    if (!e.target.closest || !e.target.closest(PICKS)) return;
    const m = main(); if (!m) return;
    saved = m.scrollTop; until = Date.now() + 3000; userMoved = false;
    // 다시 그리는 동안 페이지가 잠깐 짧아졌다 길어지면 스크롤 이벤트 없이 위치가 바뀌므로 짧은 간격으로도 확인한다
    clearInterval(window.__aniKeepTimer);
    window.__aniKeepTimer = setInterval(() => {
      const mm = main();
      if (!mm || userMoved || Date.now() > until) { clearInterval(window.__aniKeepTimer); return; }
      if (Math.abs(mm.scrollTop - saved) > 30 && mm.scrollHeight - mm.clientHeight >= saved) mm.scrollTop = saved;
    }, 80);
  };
  document.addEventListener('pointerdown', remember, true);
  // 파일 창에서 이미지를 고르고 돌아오면 그때 다시 그려지므로, 고른 순간에도 위치를 기억한다
  document.addEventListener('change', remember, true);
  ['wheel', 'touchmove', 'keydown'].forEach((t) => document.addEventListener(t, () => { userMoved = true; }, true));
  // 그 뒤 2초 안에 사용자가 스크롤하지 않았는데 위치가 크게 바뀌면 되돌린다
  document.addEventListener('scroll', (e) => {
    const m = main();
    if (!m || e.target !== m || saved === null || userMoved || Date.now() > until) return;
    if (Math.abs(m.scrollTop - saved) > 30) m.scrollTop = saved;
  }, true);
})();
"""


def _keep_scroll() -> None:
    """리뷰 종류·탭 같은 선택 버튼을 눌렀을 때 화면이 맨 아래/맨 위로 튀지 않고 그 자리에 머물게 한다.

    다시 그릴 때 사라지는 칸이 아니라 바깥 페이지 안에서 직접 실행해(eval), 감시 코드가 계속 살아 있다.
    """
    components.html(f"<script>window.parent.eval({json.dumps(_KEEP_SCROLL_JS)});</script>", height=0)


_LIVE_SEND_JS = """
(function () {
  if (window.__aniLiveSend) return;
  window.__aniLiveSend = true;
  // 입력칸에 한 글자라도 있으면 버튼을 켜고, 비면 끈다 (칸을 벗어나지 않아도 바로)
  const toggle = (b, ta) => {
    if (!b || !ta) return;
    if (!ta.value.trim()) { if (!b.disabled) { b.disabled = true; b.dataset.aniEmpty = '1'; } }
    else if (b.dataset.aniEmpty) { b.disabled = false; delete b.dataset.aniEmpty; }
  };
  const sync = () => {
    // 리뷰·답글: rv_..._body_N 입력칸 ↔ rv_..._send_N 버튼
    document.querySelectorAll('[class*="st-key-rv_"][class*="_send_"] button').forEach((b) => {
      const box = b.closest('[class*="_send_"]');
      const cls = [...box.classList].find((c) => c.startsWith('st-key-rv_') && c.includes('_send_'));
      toggle(b, cls && document.querySelector('.' + CSS.escape(cls.replace('_send_', '_body_')) + ' textarea'));
    });
    // 공지로 간편등록: 공지 입력칸 ↔ 읽어오기 버튼
    toggle(document.querySelector('.st-key-quick_read button'),
           document.querySelector('.st-key-quick_raw textarea'));
  };
  document.addEventListener('input', sync, true);
  new MutationObserver(sync).observe(document.body, { childList: true, subtree: true });
  sync();
})();
"""


def _live_send() -> None:
    """리뷰 등록 버튼을 입력칸 내용에 맞춰 바로 켜고 끈다."""
    components.html(f"<script>window.parent.eval({json.dumps(_LIVE_SEND_JS)});</script>", height=0)


_DETAIL_BACK_JS = """
(function () {
  if (window.__aniDetailBack) return;
  window.__aniDetailBack = true;
  // 상세에서 브라우저 뒤로가기를 누르면 '리스트로 돌아가기' 를 누른 것과 똑같이 리스트로 돌아간다
  window.addEventListener('popstate', () => {
    if (window.__aniSkipPop) { window.__aniSkipPop = false; return; }
    if (window.__aniDetail && location.hash !== '#detail') {
      const b = document.querySelector('.st-key-back_to_list button');
      if (b) b.click();
    }
  });
})();
"""


def _detail_history(in_detail: bool) -> None:
    """상세를 열면 브라우저 기록을 하나 남겨(#detail) 뒤로가기로 리스트에 돌아올 수 있게 한다.

    상세는 같은 화면에서 내용만 바뀌어서 기록이 남지 않는다. 리스트로 돌아가기 버튼으로 나왔을 때는
    남겨 둔 기록을 걷어 내서, 리스트에서 뒤로가기를 두 번 눌러야 하는 일이 없게 한다.
    """
    components.html(
        "<script>const w = window.parent;"
        f"w.eval({json.dumps(_DETAIL_BACK_JS)});"
        f"w.__aniDetail = {'true' if in_detail else 'false'};"
        "if (w.__aniDetail && w.location.hash !== '#detail')"
        "  w.history.pushState(null, '', w.location.pathname + w.location.search + '#detail');"
        "if (!w.__aniDetail && w.location.hash === '#detail') { w.__aniSkipPop = true; w.history.back(); }"
        "</script>",
        height=0,
    )


_LOGO_SWAP_JS = """
(function () {
  const urls = __URLS__;
  if (window.__aniLogo || urls.length < 2) return;
  window.__aniLogo = true;
  // 처음엔 아무거나 하나, 그 뒤로는 누를 때마다 다음 로고로. 서버를 거치면 클릭 한 번에 화면이
  // 두 번 그려져 바뀌었다 되돌아가기도 해서, 바깥 페이지에서 직접 바꾼다
  const s = document.createElement('style');
  document.head.appendChild(s);
  let i = Math.floor(Math.random() * urls.length);
  const show = () => {
    s.textContent = `.st-key-home_brand button { background-image: url("${urls[i]}") !important; }`;
  };
  show();
  document.addEventListener('pointerdown', () => { i = (i + 1) % urls.length; show(); }, true);
})();
"""


def _logo_swap() -> None:
    """제목 로고를 LOGOS 중에서, 화면을 누를 때마다 바꾼다."""
    js = _LOGO_SWAP_JS.replace("__URLS__", json.dumps([f"app/static/{name}" for name in LOGOS]))
    components.html(f"<script>window.parent.eval({json.dumps(js)});</script>", height=0)


def _brand(home: bool = False, fixed: bool = False) -> bool:
    """ANI:WHERE 제목 + 문구. 제목(또는 home 일 때 '홈으로')을 눌렀으면 True.

    home 이면 'ANIME POP-UP · CAFE · GOODS' 줄 오른쪽 끝에 홈으로 돌아가기 버튼을 둔다 (등록 화면).
    """
    # 글자 대신 로고 그림을 보여 준다 (GLOBAL_CSS 의 .st-key-home_brand). 글자는 화면 읽기용으로 남긴다.
    # 로고 주소는 포스터처럼 'app/static/…' 상대 주소로 둔다 ('/' 로 시작하면 하위 경로에 배포했을 때 못 찾는다)
    # 화면 어디든 누를 때마다 로고가 다른 것으로 바뀐다 (_logo_swap — 브라우저에서 처리).
    # 상세·등록 화면은 바뀌지 않고 늘 같은 로고(FIXED_LOGO). 더 강한 선택자로 덮어써서, 목록으로 돌아가면 다시 바뀐다
    _logo_swap()
    if fixed:
        st.markdown(f'<style>html body .st-key-home_brand button {{ background-image: url("app/static/{FIXED_LOGO}")'
                    ' !important; }</style>', unsafe_allow_html=True)
    clicked = st.button("ANI:WHERE", key="home_brand", type="tertiary")
    if not home:
        st.markdown(
            '<div class="brand-tag">함께 만드는 애니 팝업 지도!! 찾고, 공유하고, 함께 기록해요!<br/>'
            '<span>ANIME POP-UP · CAFE · GOODS</span></div>',
            unsafe_allow_html=True,
        )
        return clicked
    st.markdown('<div class="brand-tag">함께 만드는 애니 팝업 지도!! 찾고, 공유하고, 함께 기록해요!</div>',
                unsafe_allow_html=True)
    sub, btn = st.columns([5, 1], vertical_alignment="center")
    sub.markdown('<div class="brand-tag"><span>ANIME POP-UP · CAFE · GOODS</span></div>',
                 unsafe_allow_html=True)
    with btn:
        clicked = st.button("홈으로 돌아가기", key="wiz_home", help="등록을 그만두고 메인으로") or clicked
    return clicked


def _follow_switch(key: str) -> None:
    """'팔로우한 곳만' 스위치. 글자가 스위치 안에 들어 있고 꺼지면 '팔로우', 켜지면 포인트 색 '팔로잉'.
    목록 위(PC)와 모바일 필터 판에 같은 스위치를 두고, 둘 다 같은 값(fav_only)을 바꾼다."""
    on = bool(st.session_state.get("fav_only"))
    if st.button("팔로잉" if on else "팔로우", key=f"{key}_{'on' if on else 'off'}",
                 help="팔로우한 곳만 보는 중 · 누르면 모두 보기" if on else "팔로우한 곳만 보기"):
        st.session_state["fav_only"] = not on
        st.rerun()


def _reset_filters() -> None:
    """메인의 검색 조건을 처음 값으로. 버튼 콜백이라 입력칸이 그려지기 전에 돌아서 값을 바로 바꿀 수 있다.

    키를 지우기만 하면 브라우저의 입력칸(특히 날짜)이 예전 값을 그대로 보여 줄 수 있어서,
    처음 값을 직접 넣어 화면까지 새로 그리게 한다.
    """
    st.session_state.update({"f_query": "", "f_work": "전체", "f_span": "진행중 + 예정"})
    st.session_state.pop(f"f_date_{st.session_state.get('date_ver', 0)}", None)
    st.session_state["date_ver"] = st.session_state.get("date_ver", 0) + 1
    for k in [k for k in st.session_state if str(k).startswith("filter_chars_")]:
        st.session_state[k] = []
    st.session_state["regions"] = []
    st.session_state["fav_only"] = False
    # 모바일 필터 판의 같은 칸도 함께 비운다
    st.session_state["regions_m"] = []


def page_map() -> None:
    st.markdown(GLOBAL_CSS + LIST_CSS, unsafe_allow_html=True)
    _no_translate()
    _history_guard(on_main=True)
    _keep_scroll()
    _live_send()
    # 처음 들어오면 기본은 리스트 전체보기 (지도보기는 버튼으로)
    st.session_state.setdefault("list_only", True)
    # 공유받은 링크(?cafe=<id>)로 들어오면 그 카페 상세를 연다. 한 번 쓰고 주소창에서 지운다
    shared = st.query_params.get("cafe")
    if shared:
        st.session_state["selected"] = str(shared)
        st.session_state["list_only"] = False
        del st.query_params["cafe"]
    # Notion 트래커 DB 에 새로 쌓인 행사를 가져온다 (NOTION_TOKEN 이 있을 때, 최대 1시간에 한 번)
    synced = notion_sync.maybe_sync(store, TODAY)
    if synced and synced.get("added"):
        st.toast(f"노션에서 {len(synced['added'])}곳을 새로 가져왔어요 🎀")
    # 기간이 지난 카페는 자동으로 지도에서 내린다 (기록은 남아서 수정 이력에서 되돌릴 수 있다)
    cafe.expire_ended(store, TODAY)    # 조용히 처리한다 (안내는 띄우지 않는다)
    rows = store.current_rows()
    selected = st.session_state.get("selected")
    current = next((r for r in rows if str(r["entry_id"]) == selected), None)
    _detail_history(in_detail=current is not None)
    if current:
        # 상세에서는 등록하기·검색 필터·카페 수·리스트 전체보기를 숨긴다.
        # 지우지 않고 숨기기만 해서, 돌아가면 골라 둔 필터·지역·정렬이 그대로 남는다
        st.markdown("<style>.st-key-filters, .st-key-listbar, .st-key-listtools, .st-key-m_filter_btn "
                    "{ display: none !important; }</style>", unsafe_allow_html=True)

    # 제목·등록하기(상세에서는 돌아가기)·검색 필터는 스크롤해도 늘 위에 붙어 있다 (LIST_CSS 의 .st-key-topbar)
    top = st.container(key="topbar")
    with top:
        head, btn = st.columns([4, 2], vertical_alignment="bottom")
    with head:
        # 제목을 누르면 상세를 닫고 보던 모드(리스트 전체보기 / 지도보기)의 첫 화면으로 돌아간다
        if _brand(fixed=current is not None):     # 상세에서는 로고 고정
            st.session_state["selected"] = None
            st.session_state["scroll_top"] = True
            st.rerun()
    with btn:
        # 상세에서는 등록하기 자리에 '리스트로 돌아가기' (상단에 늘 떠 있다)
        if current:
            if st.button("리스트로 돌아가기", key="back_to_list", type="primary", width="stretch"):
                st.session_state["selected"] = None
                st.session_state["scroll_top"] = True
                st.rerun()
        else:
            # 내 캘린더는 지도보기 오른쪽에 바로 보여서 따로 버튼을 두지 않는다
            with st.container(horizontal=True, horizontal_alignment="right", key="top_btns"):
                if st.button("등록하기  ↗", key="add_btn", type="primary"):
                    st.session_state.pop("wiz", None)     # 늘 1단계부터 시작
                    go("add")

    report = st.session_state.pop("save_report", None)
    if report:
        show_report(report)
    if st.session_state.pop("scroll_top", False):
        _scroll_top()
    flash = st.session_state.pop("flash", None)
    if flash:
        st.toast(flash)

    df = cafe.rows_to_frame(rows)

    if df.empty:
        st.markdown(
            "#### 아직 등록된 카페가 없습니다\n"
            "- 오른쪽 위 **등록하기** 버튼을 눌러 팝업 카페 공지를 붙여넣어 보세요.\n"
            "- `samples/tweets_sample.txt` 에 시험용 글 10건이 들어 있습니다."
        )
        return

    df["entry_id"] = df["entry_id"].astype(str)
    # '스파이패밀리' 와 '스파이 패밀리' 가 따로 걸리지 않게 목록의 작품명으로 맞춘다
    df["work"] = df["work"].fillna("").astype(str).map(catalog.canonical_work)

    # 모바일(폭 640px 이하)에서는 검색 필터를 접어 두고 '검색 필터' 버튼으로 연다. PC 에서는 버튼을 숨기고 늘 보인다.
    # 화면 폭은 서버가 모르니, 열림 상태는 서버가 기억하고 '좁은 화면일 때만 숨기기' 는 CSS 가 맡는다
    ss = st.session_state
    active = sum([
        bool(str(ss.get("f_query") or "").strip()), ss.get("f_work", "전체") != "전체",
        ss.get("f_span", "진행중 + 예정") != "진행중 + 예정",
        bool(ss.get(f"f_date_{ss.get('date_ver', 0)}")),
        any(ss.get(k) for k in list(ss) if str(k).startswith("filter_chars_")),
        bool(ss.get("regions")), bool(ss.get("fav_only")),
    ])
    m_open = ss.get("m_filters", False)
    with top:
        # 모바일에서는 화면 아래 '지도보기 / 리스트 전체보기' 옆에 떠 있는 버튼 (LIST_CSS 의 .st-key-m_filter_btn)
        label = "필터 닫기" if m_open else f"필터{f' · {active}' if active else ''}"
        if st.button(label, key="m_filter_btn"):
            ss["m_filters"] = not m_open
            st.rerun()
    # 열면 필터 묶음이 화면 아래에서 떠오르는 판(바텀 시트)으로 보인다. 닫으면 모바일에서는 숨긴다
    sheet = (".st-key-filters { position: fixed !important; left: 12px; right: 12px; bottom: 76px; z-index: 999;"
             " max-height: 62vh; overflow-y: auto; background: #fff; border-radius: 18px;"
             " padding: .9rem 1rem 1rem; box-shadow: 0 -4px 24px rgba(0,0,0,.18); }")
    st.markdown(
        "<style>.st-key-m_filter_btn { display: none; }"
        "@media (max-width: 640px) { .st-key-m_filter_btn { display: block; }"
        + (sheet if m_open else " .st-key-filters { display: none !important; }") + " }</style>",
        unsafe_allow_html=True,
    )

    with top:
        fbox = st.container(key="filters")      # 모바일 전용 칸(찜·지역)도 아래에서 이 묶음에 넣는다
    with fbox:
        c0, c1, c4, c2, c3, c5 = st.columns([2.4, 2, 2, 2, 2, 1.1], vertical_alignment="bottom")
    with c5:
        # 검색어·작품·캐릭터·기간·특전과 목록 위의 지역·찜 필터를 한 번에 처음 값으로 돌린다 (정렬은 그대로)
        st.button("↺ 초기화", key="filter_reset", width="stretch", on_click=_reset_filters,
                  help="검색 조건을 모두 지웁니다")
    with c0:
        query = st.text_input("검색", placeholder="작품·카페명·캐릭터·주소", key="f_query")
    with c1:
        works = ["전체"] + sorted(set(df["work"]) - {""})
        pick_work = st.selectbox("작품", works, key="f_work")
    with c4:
        # 작품을 고르면 그 작품의 캐릭터만 고를 수 있다
        chars = _characters_by_work().get(pick_work, []) if pick_work != "전체" else []
        pick_chars = st.multiselect(
            "캐릭터", chars, key=f"filter_chars_{pick_work}", disabled=pick_work == "전체",
            placeholder="캐릭터 고르기" if pick_work != "전체" else "작품을 먼저 골라주세요",
        )
    with c2:
        span = st.selectbox("진행여부", ["진행중 + 예정", "예정", "진행중"], key="f_span")
    with c3:
        # 날짜를 고르면 그날 열려 있는 곳만 보여 준다. 비워 두면 날짜로 거르지 않는다
        # 날짜 칸은 값을 비워도 브라우저 화면에 예전 날짜가 남아서, 초기화 때마다 키 번호를 올려 새 칸으로 그린다
        pick_day = st.date_input("날짜", value=None, key=f"f_date_{st.session_state.get('date_ver', 0)}",
                                 format="YYYY.MM.DD", help="이 날짜에 진행 중인 곳만 봅니다")

    # 지역 이름 (카드 배지와 같은 이름). 지역 고르기 칸 두 곳(필터 판·목록 위)이 함께 쓴다
    df["area"] = df["address"].map(lambda a: geo.area_name(str(a or "")))
    areas = sorted({a for a in df["area"] if a})
    # 모바일 필터 판에만 '팔로우' 스위치 · '지역 고르기' 를 한 번 더 둔다 (PC 는 목록 위에만, LIST_CSS 의 .st-key-m_only).
    # 같은 키를 두 번 쓸 수 없어 따로 키를 두고, 어느 쪽을 바꿔도 원래 값(fav_only·regions)에 맞춘다
    ss["regions_m"] = [r for r in ss.get("regions", []) if r in areas]
    with fbox, st.container(key="m_only"):
        _follow_switch("folswm")
        st.multiselect("지역", areas, key="regions_m", placeholder="📍 지역 고르기 (여러 곳 가능)",
                       on_change=lambda: ss.update(regions=ss["regions_m"]))

    view = df.copy()
    if query.strip():
        q = query.strip()
        hit = lambda col: view[col].astype(str).str.contains(q, case=False, regex=False)
        view = view[hit("cafe_name") | hit("work") | hit("characters") | hit("address")]
    if pick_work != "전체":
        view = view[view["work"] == pick_work]
    if pick_chars:
        # '아냐' 로 등록된 카페도 목록의 '아냐 포저' 로 찾히게, 한쪽이 다른 쪽을 품으면 같은 캐릭터로 본다
        same = lambda a, b: a == b or a in b or b in a
        view = view[view["characters"].fillna("").apply(
            lambda v: any(same(p, c) for p in pick_chars for c in _split(v)))]
    if span == "진행중 + 예정":
        view = view[view["end_date"] >= TODAY]
    elif span == "예정":
        view = view[view["start_date"] > TODAY]
    elif span == "진행중":
        view = view[(view["start_date"] <= TODAY) & (view["end_date"] >= TODAY)]
    if pick_day:
        view = view[(view["start_date"] <= pick_day) & (view["end_date"] >= pick_day)]
    # 팔로우한 곳만·지역·정렬은 리스트 전체보기에서만 보이고 걸린다 (지도보기에서는 숨기기만 해서 고른 값은 남는다)
    wide = bool(st.session_state.get("list_only")) and not current
    view = view.assign(area=df.loc[view.index, "area"])
    if wide:
        regions = st.session_state.get("regions", [])
        if regions:
            view = view[view["area"].isin(regions)]
        if st.session_state.get("fav_only"):
            view = view[view["entry_id"].astype(str).isin(_fav_state()[1])]
        view = _sort_view(view, st.session_state.get("sort", SORTS[0]))
    else:
        # 칸을 위젯으로 집어서 숨긴다 (':not(:first-child)' 로 잡으면 '팝업 카페 N곳' 칸 안의 리스트 전체보기 버튼 칸까지 숨는다)
        st.markdown("<style>.st-key-listtools [data-testid='stColumn']:has([class*='st-key-folsw_'], .st-key-regions, .st-key-sort),"
                    " .st-key-m_only { display: none !important; }</style>", unsafe_allow_html=True)

    mapped = view.dropna(subset=["lat", "lng"])
    # 조건에 맞는 수·지도 표시 수·안내는 '팝업 카페 N곳' 옆 도움말(?)에 커서를 올리면 보인다
    note = (f"조건에 맞는 카페 {len(view)}곳 · 지도에 표시 가능 {len(mapped)}곳"
            + (f" · 좌표 없음 {len(view) - len(mapped)}곳" if len(view) > len(mapped) else "")
            + " · 카드나 지도의 점을 누르면 상세를 보고 리뷰를 남기거나 수정할 수 있습니다.")
    # '팝업 카페 N곳' 과 찜·지역·정렬을 목록 바로 위 한 줄에 (상단 고정 묶음에는 넣지 않고 목록과 함께 스크롤한다)
    with st.container(key="listtools"):
        head, fav_only, region, sort = st.columns([3.5, 0.6, 2, 1.3], vertical_alignment="center")
    with head, st.container(key="listbar"):
        _list_bar(len(view), wide, note)
    with fav_only:
        _follow_switch("folsw")
    with region:
        # 지금 등록된 카페가 있는 지역만, 카드 배지와 같은 이름으로. 여러 곳을 함께 고를 수 있다
        st.multiselect("지역", areas, key="regions", label_visibility="collapsed",
                       placeholder="📍 지역 고르기 (여러 곳 가능)")
    with sort:
        st.selectbox("정렬", SORTS, key="sort", label_visibility="collapsed")

    # '리스트 전체보기' 를 누르면 지도 없이 리스트만 크게 본다. '지도보기' 를 누르면 다시 반반으로
    if wide:
        render_list(view, wide=True)
        return

    def draw_map() -> None:
        if mapped.empty:
            st.caption("지도에 표시할 카페가 없습니다.")
            return
        clicked = kakao_map.kakao_map(
            # 점에 커서를 올리면 포스터 · 작품 · 카페 · 위치 · 기간 카드가 뜬다
            points=[{"id": str(r["entry_id"]), "lat": float(r["lat"]), "lng": float(r["lng"]),
                     "work": str(r["work"]), "cafe": str(r["cafe_name"]),
                     "address": str(r["address"] or "-"),
                     "dates": f"{r['start_date']:%m.%d} ~ {r['end_date']:%m.%d}",
                     "poster": _poster_url(r.get("images"))}
                    for _, r in mapped.iterrows()],
            selected=selected, height=MAP_HEIGHT,
            home=_home_area(mapped),     # 처음 화면: 내 주변 (위치를 모르면 팝업이 가장 많은 지역)
        )
        # 같은 점을 다시 눌러도 반영되도록 누른 시각까지 비교한다
        if clicked and st.session_state.get("_last_kakao") != clicked.get("at"):
            st.session_state["_last_kakao"] = clicked.get("at")
            st.session_state["selected"] = clicked.get("id")
            st.session_state["scroll_top"] = True    # 상세는 맨 위부터 보이게

    if current:
        # 상세: 왼쪽은 이미지·정보·공유, 오른쪽은 리뷰·수정하기 (지도·길찾기는 두지 않는다)
        col_info, col_tabs = st.columns([1, 1], gap="medium")
        with col_info, st.container(key="detail_left"):
            render_detail(current)
        with col_tabs:
            render_detail_tabs(current)
    else:
        # 지도보기: 왼쪽 데일리 팝업 노트, 가운데 지도, 오른쪽 내 캘린더 (팝업 리스트는 두지 않는다)
        st.markdown(CAL_CSS, unsafe_allow_html=True)
        with st.container(key="map_row"):
            col_day, col_map, col_cal = st.columns([0.9, 3.4, 1.55], gap="medium")
        with col_day, st.container(key="map_daily"):
            render_daily(df)
        with col_map:
            draw_map()
        with col_cal, st.container(key="map_cal"):
            render_calendar(compact=True)

    # 지도에서 고른 게 이번 실행에서 바뀌었으면 왼쪽 패널·강조를 다시 그린다
    if st.session_state.get("selected") != selected:
        st.rerun()


# ================================================================ 데일리 팝업 노트
# 지도보기 왼쪽: 고른 날(처음엔 오늘)에 열려 있는 팝업을 지역별로. 날짜는 ‹ › 로 하루씩 옮긴다
DAILY_CSS = f"""
<style>
/* 머리 상자: 제목 / ‹ 날짜 › / ‹ 지역 › 세 줄을 촘촘하게 */
.st-key-daily_head {{ border:1px solid #DDE2E0; border-radius:12px; padding:8px 6px; background:#fff;
                     gap:4px !important; }}
.st-key-daily_head [data-testid="stMarkdownContainer"] {{ margin:0 !important; }}
.dn-title {{ text-align:center; color:#6B7672; font-size:.75rem; font-weight:600; line-height:1.2; }}
.st-key-daily_nav, .st-key-daily_areas {{ align-items:center !important; justify-content:center !important;
  gap:4px !important; flex-wrap:nowrap !important; }}
.st-key-daily_nav > div, .st-key-daily_areas > div {{ width:auto !important; flex:0 0 auto !important; }}
.st-key-daily_nav button, .st-key-daily_areas button {{ min-height:0 !important; height:22px; width:22px;
  padding:0 !important; line-height:1; }}
.st-key-daily_nav button p, .st-key-daily_areas button p {{ font-size:1rem !important; line-height:1 !important;
  color:var(--accent-deep) !important; font-weight:700; margin:0 !important; }}
.st-key-daily_nav [data-testid="stMarkdownContainer"], .st-key-daily_areas [data-testid="stMarkdownContainer"] {{
  display:flex; align-items:center; height:22px; margin:0 !important; }}
.st-key-daily_nav [data-testid="stMarkdownContainer"] p, .st-key-daily_areas [data-testid="stMarkdownContainer"] p {{
  margin:0; line-height:1; }}
.dn-date {{ font-weight:800; font-size:.88rem; color:#1F2A27; white-space:nowrap; }}
.dn-today {{ background:var(--accent-soft); color:var(--accent-deep); font-size:.66rem; font-weight:700;
            padding:.1rem .35rem; border-radius:5px; margin-right:4px; }}
.dn-area {{ display:inline-block; min-width:70px; text-align:center; font-size:.76rem; font-weight:700; color:#26302D;
           background:#F4F6F5; border-radius:999px; padding:.2rem .6rem; white-space:nowrap; }}
.dn-area span {{ color:#8A9490; font-weight:500; margin-left:3px; }}
/* 목록: 포스터 · 위치 · 작품명만. 포스터를 점선으로 잇는다 */
.dn-list {{ max-height:{MAP_HEIGHT - 120}px; overflow-y:auto; margin-top:12px; padding:0 2px; }}
.dn-item {{ display:flex; align-items:center; gap:10px; position:relative; padding:0 0 12px;
           text-decoration:none !important; color:inherit !important; }}
.dn-item:not(:last-child)::before {{ content:""; position:absolute; left:17px; top:38px; bottom:2px;
                                    border-left:1.5px dashed #C9D1CE; }}
.dn-thumb {{ flex:0 0 36px; height:36px; border-radius:50%; background:#F4F6F5 center/cover no-repeat;
            border:1px solid #E4E8E6; }}
.dn-body {{ flex:1; min-width:0; display:flex; flex-direction:column; align-items:flex-start; gap:3px; }}
.dn-body .abadge {{ font-size:.62rem; line-height:1.4; padding:0 .35rem; border-radius:5px; font-weight:700; }}
.dn-name {{ max-width:100%; font-weight:800; font-size:.8rem; line-height:1.25; color:#1F2A27;
           overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.dn-item:hover .dn-name {{ color:var(--accent-deep); }}
.dn-empty {{ color:#6B7672; text-align:center; padding:16px 4px; font-size:.76rem; margin-top:8px; }}
/* 내 위치를 묻는 칸은 보이지 않게 흐름에서 뺀다 (스크립트만 돈다) */
.st-key-daily_loc {{ position:absolute !important; width:0 !important; height:0 !important; overflow:hidden; }}
/* 제목 옆 ? : 커서를 올리거나(모바일은 누르면) 안내 말풍선 */
.dn-help {{ position:relative; display:inline-flex; align-items:center; justify-content:center; width:13px; height:13px;
           margin-left:4px; border:1px solid #B5BDBA; border-radius:50%; color:#8A9490; font-size:.6rem; font-weight:700;
           line-height:1; cursor:help; vertical-align:1px; }}
.dn-tip {{ display:none; position:absolute; top:calc(100% + 6px); left:50%; transform:translateX(-50%); z-index:50;
          width:170px; padding:7px 9px; border-radius:8px; background:#26302D; color:#fff; font-size:.7rem;
          font-weight:500; line-height:1.4; text-align:left; word-break:keep-all; box-shadow:0 4px 12px rgba(0,0,0,.18); }}
.dn-tip b {{ color:#7FE3D3; }}
.dn-help:hover .dn-tip, .dn-help:focus .dn-tip {{ display:block; }}
.st-key-daily_head {{ overflow:visible !important; }}
/* 지도보기: 지도는 화면에 붙어 따라 내려오지 않고 페이지와 함께 스크롤된다 */
.st-key-map_row [data-testid="stColumn"]:has(iframe[src*="kakao_map"]) {{ position: static !important; top: auto !important; }}
/* 모바일: 데일리 팝업 노트(왼쪽 좁게)와 지도를 한 줄에, 내 캘린더는 그 아래 전체 폭 */
@media (max-width: 640px) {{
  /* 예전 모바일 규칙(지도를 맨 위로 세로 쌓기: flex-direction column + order -1)을 이 줄에서는 덮어쓴다 */
  .st-key-map_row [data-testid="stHorizontalBlock"]:has(.st-key-map_daily) {{ flex-direction: row !important;
    flex-wrap: wrap !important; gap: 8px !important; }}
  .st-key-map_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ order: 0 !important; }}
  .st-key-map_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has(.st-key-map_daily) {{
    flex: 0 0 38% !important; width: 38% !important; min-width: 38% !important; }}
  .st-key-map_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has(iframe[src*="kakao_map"]) {{
    flex: 1 1 0 !important; width: auto !important; min-width: 0 !important; }}
  .st-key-map_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has(.st-key-map_cal) {{
    flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important; }}
  .st-key-daily_head {{ padding: 6px 2px; }}
  .dn-today {{ display: none; }}
  .dn-date {{ font-size: .76rem; }}
  .dn-area {{ min-width: 0; font-size: .7rem; padding: .15rem .45rem; }}
  .dn-name {{ font-size: .74rem; }}
  .dn-thumb {{ flex-basis: 30px; height: 30px; }}
  .dn-item {{ gap: 6px; }}
  .dn-item:not(:last-child)::before {{ left: 14px; top: 32px; }}
  /* 데일리 팝업 노트는 옆 지도(높이 58vh, 최소 320px)와 딱 같은 높이까지만, 목록은 그 안에서 스크롤 */
  .st-key-map_row [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has(.st-key-map_daily) {{
    height: max(320px, 58vh) !important; overflow: hidden !important; }}
  .dn-list {{ max-height: calc(max(320px, 58vh) - 136px); }}   /* 136px = 위 상자 + 목록 위 여백 */
}}
</style>
"""


def _daily_shift(delta: int) -> None:
    st.session_state["daily_day"] = st.session_state.get("daily_day", 0) + delta
    st.session_state["daily_area_i"] = 0      # 날이 바뀌면 지역은 다시 '전체'


def _daily_area_shift(delta: int, n: int) -> None:
    st.session_state["daily_area_i"] = (st.session_state.get("daily_area_i", 0) + delta) % n


def render_daily(df: pd.DataFrame) -> None:
    """데일리 팝업 노트: 고른 날 열려 있는 팝업을 포스터 · 위치 · 작품명으로.

    지역은 내 위치에서 가까운 곳부터 보여 주고 ‹ › 로 넘긴다 ('전체' 는 맨 끝).
    위치를 못 받으면 그날 팝업이 많은 지역부터. 팝업은 팔로우 많은 순.
    """
    st.markdown(DAILY_CSS, unsafe_allow_html=True)
    with st.container(key="daily_loc"):
        loc = my_place.my_location()
    st.session_state["_my_loc"] = loc     # 같은 실행에서 바로 뒤에 그리는 지도가 처음 화면을 내 주변으로 맞춘다
    off = st.session_state.get("daily_day", 0)
    day = TODAY + timedelta(days=off)
    # 날짜가 빈 행(NaT)은 비교하지 않고 뺀다
    open_ = df[[isinstance(a, date) and isinstance(b, date) and a <= day <= b
                for a, b in zip(df["start_date"], df["end_date"])]]
    # 지역은 ‹ › 로 하나씩 넘긴다: 내 위치에서 가까운 지역부터 (위치를 모르면 팝업이 많은 지역부터), '전체' 는 맨 끝
    by_area = open_["area"].replace("", "기타").value_counts() if not open_.empty else pd.Series(dtype=int)
    order = by_area.index.tolist()
    near = ""
    if isinstance(loc, dict) and "lat" in loc:
        placed = df.dropna(subset=["lat", "lng"])
        ranked = my_place.areas_by_distance(
            (float(loc["lat"]), float(loc["lng"])),
            [(a, float(la), float(ln)) for a, la, ln in zip(placed["area"], placed["lat"], placed["lng"]) if a])
        near = ranked[0] if ranked else ""
        rank = {a: i for i, a in enumerate(ranked)}
        order = sorted(order, key=lambda a: rank.get(a, len(rank)))
    choices = [*order, "전체"]
    area = choices[st.session_state.get("daily_area_i", 0) % len(choices)]
    count = len(open_) if area == "전체" else int(by_area[area])

    # 안내(내 위치 기준인지, 위치를 허용해야 하는지)는 제목 옆 ? 에 커서를 올리면 보인다
    if near:
        guide = f"내 위치(<b>{escape(near)}</b> 근처)에서 가까운 지역부터 보여 줘요"
    elif isinstance(loc, dict) and loc.get("error"):
        guide = "위치 권한을 허용하면 내 주변 지역 팝업부터 보여 줘요"
    else:
        guide = "내 위치를 확인하고 있어요"
    with st.container(key="daily_head"):
        st.markdown(f'<div class="dn-title">데일리 팝업 노트<span class="dn-help" tabindex="0">?'
                    f'<span class="dn-tip">{guide}</span></span></div>', unsafe_allow_html=True)
        with st.container(horizontal=True, key="daily_nav"):
            st.button("‹", key="daily_prev", type="tertiary", on_click=_daily_shift, args=(-1,), help="전날")
            st.markdown(('<span class="dn-today">오늘</span>' if off == 0 else "")
                        + f'<span class="dn-date">{day:%y. %m. %d.} {_WEEKDAYS[day.weekday()]}</span>',
                        unsafe_allow_html=True)
            st.button("›", key="daily_next", type="tertiary", on_click=_daily_shift, args=(1,), help="다음 날")
        with st.container(horizontal=True, key="daily_areas"):
            st.button("‹", key="daily_area_prev", type="tertiary", on_click=_daily_area_shift,
                      args=(-1, len(choices)), help="이전 지역", disabled=len(choices) < 2)
            st.markdown(f'<span class="dn-area">{escape(area)}<span>{count}</span></span>', unsafe_allow_html=True)
            st.button("›", key="daily_area_next", type="tertiary", on_click=_daily_area_shift,
                      args=(1, len(choices)), help="다음 지역", disabled=len(choices) < 2)

    if area != "전체":
        open_ = open_[open_["area"].replace("", "기타") == area]
    if open_.empty:
        st.markdown('<div class="dn-empty">이날 열려 있는 팝업이 없어요.</div>', unsafe_allow_html=True)
        return
    _, _, fcounts = _fav_state()
    rows = sorted(open_.to_dict("records"), key=lambda r: (-fcounts.get(str(r["entry_id"]), 0), r["start_date"]))
    items = "".join(
        f'<a class="dn-item" data-id="{escape(str(r["entry_id"]))}" href="./?cafe={quote(str(r["entry_id"]))}" target="_self"'
        f' title="{escape(str(r["work"]))} · {escape(str(r["cafe_name"]))}">'
        f'<span class="dn-thumb" style="background-image:url(\'{_poster_url(r.get("images"))}\')"></span>'
        f'<div class="dn-body">{_area_badge(r.get("address"))}'
        f'<div class="dn-name">{escape(str(r["work"]))}</div></div></a>'
        for r in rows)
    st.markdown(f'<div class="dn-list">{items}</div>', unsafe_allow_html=True)
    # 목록을 누르면 상세로 가지 않고, 지도에서 그 팝업 자리를 보여 주며 지도 안 목록 창에 띄운다
    components.html(f"<script>window.parent.eval({json.dumps(_DAILY_PEEK_JS)});</script>", height=0)


_DAILY_PEEK_JS = """
(function () {
  if (window.__aniDailyPeek) return;
  window.__aniDailyPeek = true;
  document.addEventListener('click', function (e) {
    const a = e.target.closest && e.target.closest('a.dn-item');
    if (!a) return;
    const f = document.querySelector('iframe[src*="kakao_map"]');
    let ok = false;
    try { ok = !!(f && f.contentWindow.peek && f.contentWindow.peek(a.dataset.id)); } catch (err) {}
    if (!ok) return;            // 지도에 없는 팝업이면 원래대로 상세로 간다
    e.preventDefault();
    // 모바일처럼 지도가 화면 밖에 있으면 지도가 보이게
    const r = f.getBoundingClientRect();
    if (r.top < 0 || r.bottom > window.innerHeight) f.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, true);
})();
"""

# =================================================================== 등록하기
# 한 화면에 한 단계씩 묻는다. 진행 막대 + 가운데 카드 하나.
# 마지막 '등록 확인' 단계에서 앞에서 넣은 정보를 한눈에 보여 주고 등록한다.
STEPS = [
    ("작품 · 캐릭터", "🎬"),
    ("카페 정보", "☕"),
    ("이미지", "🖼️"),
    ("기간", "📅"),
    ("특전 · 굿즈", "🎁"),
    ("등록 확인", "✅"),
]
ACCENT = MINT

WIZARD_CSS = f"""
<style>
.wiz-bar {{ height:6px; background:#eceff0; border-radius:2px; overflow:hidden; margin-bottom:.4rem; }}
.wiz-bar > div {{ height:100%; background:{ACCENT}; transition:width .3s; }}
.wiz-count {{ text-align:right; font-size:.8rem; color:#8a8d96; margin-bottom:.6rem; }}
.wiz-title {{ text-align:center; font-weight:700; font-size:1.15rem; margin:.6rem 0 1rem; }}
/* 이미지 올리는 칸: 회색 상자 + 민트 점선 */
[data-testid="stFileUploaderDropzone"] {{ background:{GRAY_SOFT}; border:1.5px dashed {ACCENT};
             border-radius:8px; min-height:140px; }}
/* 모바일: '홈으로 돌아가기' 를 화면 아래 가운데에 떠 있는 버튼으로 (메인의 떠 있는 버튼과 같은 모양, PC 는 원래 자리) */
@media (max-width: 640px) {{
  .st-key-wiz_home {{ position: fixed !important; left: 50%; bottom: 20px; transform: translateX(-50%);
    z-index: 1000; width: auto !important; }}
  .st-key-wiz_home button {{ height: 40px !important; padding: 0 1.4rem !important;
    box-shadow: 0 6px 18px rgba(0,0,0,.16) !important; white-space: nowrap; }}
  /* 떠 있는 버튼이 맨 아래 '이전 / 다음' 버튼을 가리지 않게 페이지 아래에 여백 */
  .stMainBlockContainer {{ padding-bottom: 6rem !important; }}
}}
.wiz-icon {{ width:140px; height:140px; margin:0 auto 1.2rem; border-radius:50%;
             background:{GRAY_SOFT};
             display:flex; align-items:center; justify-content:center; font-size:64px; }}
</style>
"""


def _wiz() -> dict:
    """등록 마법사의 상태. 단계를 오가도 값이 남도록 위젯이 아닌 여기에 담는다."""
    if "wiz" not in st.session_state:
        st.session_state.pop("poster_changing", None)   # 새 등록은 '변경 중' 상태 없이 시작
        st.session_state["wiz"] = {
            "step": 0, "v": 0,          # v: 값을 밖에서 채웠을 때 입력칸을 새로 그리기 위한 번호
            "work": "", "characters": "", "cafe_name": "", "address": "",
            "start_date": TODAY, "end_date": TODAY + timedelta(days=27),   # 팝업은 보통 몇 주 간다
            "perks": "", "goods": "",
            "poster": None, "extras": [],   # (파일 이름, 바이트). 등록할 때 data/images/ 에 저장한다
            "tags": [],
            "links": [],                # 참고 웹사이트 주소들
        }
    return st.session_state["wiz"]


def _move(delta: int) -> None:
    w = _wiz()
    w["step"] = max(0, min(len(STEPS) - 1, w["step"] + delta))
    st.rerun()


def _block_sensitive(*texts: str) -> bool:
    """입력값에 전화번호·계좌번호 같은 개인정보가 있으면 오류를 띄우고 True. 다음 단계를 막는 데 쓴다."""
    found = guard.scan(" ".join(str(t or "") for t in texts))
    if not found:
        return False
    kinds = ", ".join(sorted({f.kind for f in found}))
    st.error(f"민감한 개인정보({kinds})는 입력할 수 없습니다. 해당 내용을 지우고 다시 입력해 주세요.")
    return True


def _nav(next_label: str = "다음", next_ok: bool = True, on_next=None, primary: bool = True) -> None:
    """카드 아래 이전/다음 버튼. on_next 가 False 를 돌려주면 넘어가지 않는다."""
    w = _wiz()
    # 첫 단계는 '이전' 이 없으니 다음 버튼 하나를 카드 폭에 꽉 채운다 (반쪽에 치우치지 않게)
    if w["step"] > 0:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("이전", width="stretch", key=f"prev_{w['step']}"):
                _move(-1)
    else:
        b2 = st.container()
    with b2:
        if st.button(next_label, type="primary" if primary else "secondary", width="stretch",
                     disabled=not next_ok,
                     key=f"next_{w['step']}"):
            if on_next is None or on_next() is not False:
                _move(1)


def _step_work(w: dict) -> None:
    pick, chars = pick_work_and_characters(w["work"], _split(w["characters"]), key=f"wiz_{w['v']}")
    st.caption("캐릭터는 모르면 비워 두세요.")

    def save():
        w["work"], w["characters"] = pick, ", ".join(chars)

    bad = _block_sensitive(pick, *chars)
    _nav("다음", next_ok=bool(pick) and not bad, on_next=save)

    # 공지 글이 이미 있으면 단계를 밟지 않고 한 화면에서 바로 등록한다
    st.divider()
    st.caption("공지 글이 있나요? 붙여넣기만 하면 한 화면에서 바로 등록할 수 있어요.")
    if st.button("📝 공지로 간편등록", width="stretch", key="quick_start"):
        w["quick"] = True
        st.rerun()


def _quick_report(got: dict) -> None:
    """읽어온 결과 요약: 상태(자동등록/검토대기)와 이유, 칸별 신뢰도(초록·노랑·빨강), 지역·운영시간·기타 이벤트."""
    if not got:
        return
    st.caption("🔧 규칙 기반으로 읽었어요 (AI 아님). 비었거나 틀린 칸은 직접 고쳐 주세요.")
    # 무엇을 읽어 왔는지만 알려 준다: '작품명, 카페명, 기간을 읽어왔어요' (항목 이름은 포인트 색)
    fields = [("작품명", got.get("work")), ("카페명", got.get("cafe_name")), ("주소", got.get("address")),
              ("기간", got.get("start_date") and got.get("end_date")), ("캐릭터", got.get("characters")),
              ("특전", got.get("perks")), ("굿즈", got.get("goods")), ("이벤트", got.get("tags")),
              ("참고 웹사이트", got.get("links"))]
    found = [name for name, value in fields if value]
    if found:
        last = found[-1][-1]
        josa = "을" if "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 else "를"
        # :primary[] 는 테마의 포인트 색(민트)
        read = ", ".join(f":primary[{n}]" for n in found) + f"{josa} 읽어왔어요"
    else:
        read = "읽어 온 항목이 없어요. 칸을 직접 채워 주세요"
    if got.get("status") == "자동등록":
        # 규칙서는 카페명을 필수로 보지 않지만, 앱은 지도에 이름을 보여야 해서 직접 넣게 한다
        need = "" if got.get("cafe_name") else "\n\n- 공지에 가게 이름이 없어요. **카페명**만 직접 넣어 주세요"
        st.success(f"**{read}**{need}")
    else:
        st.warning(f"**{read}**\n\n" + "\n".join(f"- {r}" for r in got.get("reasons", [])))
    extra = [f"📍 지역 {got['area']}" if got.get("area") else "",
             f"🕒 운영시간 {got['hours']}" if got.get("hours") else "",
             f"🎪 그 밖의 이벤트 {', '.join(got['events'])}" if got.get("events") else ""]
    if any(extra):
        st.caption(" · ".join(e for e in extra if e) + " (저장 칸이 없어 참고로만 보여 줘요)")


# 간편등록 공지 입력칸에 미리 보이는 안내 (입력하면 사라진다)
QUICK_PLACEHOLDER = """공지 내용을 그대로 붙여넣어 주세요.

SNS, 블로그, 공식 홈페이지 등 어디서 가져온 공지든 괜찮아요. 읽어오기를 누르면 행사 정보를 자동으로 정리해 드려요.

입력 예시)

명일방주 콜라보 카페 오픈!
기간: 2026.10.16 ~ 11.17
장소: 애니메이트 카페 홍대점
주소: 서울 마포구 양화로 188 AK&홍대 5층
구매 금액별 한정 특전 증정!

※ 정리된 정보는 등록 전에 확인하고 수정할 수 있어요."""


def _quick(w: dict) -> None:
    """간편등록: 공지를 붙여넣고 '읽어오기' → 채워진 칸을 확인·수정 → 바로 등록."""
    raw = st.text_area("공지", key="quick_raw", height=300, label_visibility="collapsed",
                       placeholder=QUICK_PLACEHOLDER)
    # 비었는지는 화면에서 바로 본다 (_live_send). 입력칸은 칸을 벗어나야 값이 넘어와서
    # 여기서 막으면 글을 붙여넣어도 버튼이 계속 꺼져 있다
    if st.button("읽어오기", type="primary", width="stretch", key="quick_read"):
        if raw.strip() and not _block_sensitive(raw):
            got = notice.parse_notice(raw, today=TODAY)
            # 못 찾은 칸은 비워 둔다 (오늘 날짜 같은 값으로 채우지 않는다 — 추측 금지)
            w.update({
                "work": got["work"] or "", "characters": ", ".join(got["characters"]),
                "cafe_name": got["cafe_name"] or "", "address": got["address"] or "", "picked": None,
                "start_date": got["start_date"], "end_date": got["end_date"],
                "perks": ", ".join(got["perks"]), "goods": ", ".join(got["goods"]),
                "tags": got["tags"], "links": got["links"], "quick_read": True, "quick_got": got,
            })
            w["v"] += 1
            st.rerun()
    if not w.get("quick_read"):
        return

    # 결과 화면에는 늘 어떤 방식으로 읽었는지 적는다 (지금은 AI 없이 규칙으로만 읽는다)
    got = w.get("quick_got") or {}
    _quick_report(got)
    v_ = w["v"]
    work, chars = pick_work_and_characters(w["work"], _split(w["characters"]), key=f"quick_{v_}")
    name = st.text_input("카페명", value=w["cafe_name"], key=f"quick_cafe_{v_}", placeholder=_ask("카페명"))

    def pick(c: geo.Candidate) -> None:
        w["cafe_name"] = name.strip() or c.name
        w["address"] = c.address
        w["picked"] = _picked(c)
        w["v"] += 1

    # 주소는 유추하지 않는다. 지역만 찾았으면 칸은 비워 두고 지역을 힌트로 보여 준다
    area = got.get("area")
    addr = address_field(w["address"], key=f"quick_{v_}", on_pick=pick,
                         placeholder=(f"주소를 찾지 못했어요 · 지역: {area}" if area and not w["address"]
                                      else f"{_ask('주소')} (예: 서울 마포구 ...)"))
    d1, d2 = st.columns(2)
    start = d1.date_input("시작", value=w["start_date"], key=f"quick_start_{v_}", format="YYYY.MM.DD")
    end = d2.date_input("종료", value=w["end_date"], key=f"quick_end_{v_}", format="YYYY.MM.DD")
    perks = st.text_input("특전", value=w["perks"], key=f"quick_perks_{v_}", help="쉼표로 구분")
    goods = st.text_input("굿즈", value=w["goods"], key=f"quick_goods_{v_}", help="쉼표로 구분")
    tags = st.pills("이벤트 추가 정보", cafe.EVENT_TAGS, selection_mode="multi", default=w["tags"],
                    key=f"quick_tags_{v_}")
    links, bad_links = _links_field("\n".join(w["links"]), key=f"quick_links_{v_}")
    # 이미지: 단계별 등록과 같은 구성 (메인 이미지 1장 + 추가 이미지). 없어도 등록할 수 있다
    st.markdown("**🖼️ 메인 이미지 (포스터)** :gray[(1장만)]")
    poster = st.file_uploader(f"메인 이미지 (1장, ~ {images.POSTER_MB} MB)", type=images.TYPES,
                              key=f"quick_poster_{v_}", label_visibility="collapsed")
    if poster:
        st.image(poster.getvalue(), width=160)
    else:
        st.caption("포스터가 없어도 등록할 수 있어요. 있으면 목록에서 훨씬 눈에 띄어요!")
    st.markdown(f"**이미지 추가 등록** :gray[(최대 {images.MAX_EXTRAS}장)]")
    extras = st.file_uploader(f"추가 이미지 (~ {images.EXTRA_MB} MB)", type=images.TYPES,
                              accept_multiple_files=True, key=f"quick_extras_{v_}",
                              label_visibility="collapsed") or []
    if extras:
        st.caption(f"추가 이미지 미리보기 ({len(extras)}장)")
        _thumbs([f.getvalue() for f in extras[:images.MAX_EXTRAS]])
    img_errors = []
    if poster and images.too_big(poster.getvalue(), images.POSTER_MB):
        img_errors.append(f"메인 이미지는 {images.POSTER_MB} MB 까지 올릴 수 있습니다.")
    if len(extras) > images.MAX_EXTRAS:
        img_errors.append(f"추가 이미지는 {images.MAX_EXTRAS}장까지 올릴 수 있습니다.")
    if any(images.too_big(f.getvalue(), images.EXTRA_MB) for f in extras):
        img_errors.append(f"추가 이미지는 한 장에 {images.EXTRA_MB} MB 까지 올릴 수 있습니다.")
    for e in img_errors:
        st.error(e)
    big = bool(img_errors)

    entry = None
    ready = bool(work and name.strip() and addr.strip() and start and end)
    if ready:
        # 작품 + 장소 + 기간이 모두 같은 카페가 이미 있으면 알려 준다 (막지는 않는다)
        dupes = notice.possible_duplicates({"work": work, "cafe_name": name.strip(), "area": area,
                                            "start_date": start, "end_date": end}, store.current_rows())
        if dupes:
            st.warning("같은 작품·장소·기간의 카페가 이미 있어요: "
                       + ", ".join(f"{d['work']} · {d['cafe_name']}" for d in dupes[:3]))
        entry = CafeEntry(cafe_name=name.strip(), work=work, characters=chars, address=addr.strip(),
                          start_date=start, end_date=end, perks=_split(perks), goods=_split(goods),
                          confidence="high")
        v = guard.validate_cafe(entry, today=TODAY, existing=store.current_rows())
        for warn in v.warnings:
            st.warning(warn)
        for err in v.errors:
            st.error(err)
        ready = v.ok
    else:
        st.caption("작품 · 카페명 · 주소 · 기간을 채우면 등록할 수 있어요.")
    bad = _block_sensitive(name, addr, perks, goods)

    if st.button("등록하기", type="primary", width="stretch", key="quick_save",
                 disabled=not ready or bad or bad_links or big):
        g = locate(entry.address, w.get("picked") if addr.strip() == w["address"] else None)
        if not g.ok:
            st.error(g.note)
            return
        # 첫 장이 포스터. 포스터 없이 추가 이미지만 올리면 그 첫 장이 포스터가 된다 (단계별 등록과 같다)
        files = ([(poster.name, poster.getvalue())] if poster else []) + [(f.name, f.getvalue()) for f in extras]
        saved = [images.save(name, data) for name, data in files]
        store.append(cafe.entry_to_row(entry, g.lat, g.lng, source="간편 등록",
                                       note=f"{g.badge} ({g.matched})",
                                       images=saved, tags=tags, links=links))
        st.session_state["save_report"] = {"saved": [(entry.cafe_name, g.badge)], "blocked": []}
        for k in ("wiz", "quick_raw"):
            st.session_state.pop(k, None)
        go("map")


def _ask(label: str) -> str:
    """'(카페명)을 입력해주세요' — 받침에 따라 을/를을 붙인다."""
    last = label[-1]
    batchim = "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0
    return f"({label}){'을' if batchim else '를'} 입력해주세요"


def _links_field(value: str, key: str) -> tuple[list[str], bool]:
    """참고 웹사이트 입력칸 (한 줄에 하나). (주소들, 잘못된 값이 있는지) 를 돌려준다."""
    text = st.text_area("🔗 참고 웹사이트", value=value, key=key, height=90,
                        placeholder="https://x.com/... (공지 트윗·인스타·공식 사이트, 한 줄에 하나)",
                        help=f"http:// 또는 https:// 로 시작하는 주소를 최대 {cafe.MAX_LINKS}개까지")
    links, bad = cafe.parse_links(text)
    if bad:
        st.error("웹사이트 주소는 http:// 또는 https:// 로 시작해야 해요: " + ", ".join(bad[:3]))
    if len(links) > cafe.MAX_LINKS:
        st.error(f"참고 웹사이트는 {cafe.MAX_LINKS}개까지 넣을 수 있어요.")
    return links, bool(bad) or len(links) > cafe.MAX_LINKS


def _site_name(url: str) -> str:
    """링크에 보여 줄 짧은 이름 (도메인)."""
    host = re.sub(r"^https?://(www\.)?", "", url, flags=re.I).split("/")[0]
    return host or url


def _wiz_geo(w: dict) -> geo.GeoResult:
    return locate(w["address"], w.get("picked"))


def _step_cafe(w: dict) -> None:
    name = st.text_input("카페명", value=w["cafe_name"], key=f"cafe_{w['v']}",
                         placeholder=_ask("카페명"))

    def pick(c: geo.Candidate) -> None:
        # 카페명이 비어 있으면 가게 이름으로 채운다. v 를 올려 입력칸을 새 값으로 다시 그린다
        w["cafe_name"] = name.strip() or c.name
        w["address"] = c.address
        w["picked"] = _picked(c)
        w["v"] += 1

    addr = address_field(w["address"], key=f"wiz_{w['v']}", on_pick=pick,
                         placeholder=f"{_ask('주소')} (예: 서울 마포구 ...)")

    def save():
        w["cafe_name"], w["address"] = name.strip(), addr.strip()
        g = _wiz_geo(w)
        if not g.ok:
            st.session_state["wiz_err"] = g.note
            return False
        st.session_state["wiz_note"] = f"📍 {g.badge} ({g.matched})"

    bad = _block_sensitive(name, addr)
    _nav(next_ok=bool(name.strip() and addr.strip()) and not bad, on_next=save)


def _thumbs(items: list[bytes], per_row: int = 6) -> None:
    """올린 이미지를 작은 미리보기로 보여 준다."""
    cols = st.columns(per_row)
    for i, data in enumerate(items):
        cols[i % per_row].image(data, width="stretch")


def _step_images(w: dict) -> None:
    """메인 이미지(포스터) 1장 + 추가 이미지 최대 10장. 올린 파일은 등록할 때 저장한다."""
    st.markdown("**메인 이미지 (포스터)** :gray[(1장만)]")
    # 포스터는 한 장. 올리면 바로 담아 두고 업로드 칸(+)은 감춘 채 미리보기와 '변경' 버튼만 보여 준다
    changing = st.session_state.get("poster_changing", False)
    errors = []
    if w["poster"] and not changing:
        thumb, act = st.columns([1, 5], vertical_alignment="center")
        with thumb:
            st.image(w["poster"][1], width="stretch")
        with act:
            st.caption("포스터 미리보기")
            if st.button("변경", key="poster_change", help="다른 이미지로 바꿉니다"):
                st.session_state["poster_changing"] = True
                st.rerun()
    else:
        ver = st.session_state.get("poster_ver", 0)
        up = st.file_uploader(f"메인 이미지 (1장, ~ {images.POSTER_MB} MB)", type=images.TYPES,
                              key=f"poster_up_{ver}", label_visibility="collapsed")
        if up:
            data = up.getvalue()
            if images.too_big(data, images.POSTER_MB):
                errors.append(f"메인 이미지는 {images.POSTER_MB} MB 까지 올릴 수 있습니다.")
            else:
                # 담아 두고 업로드 칸을 비운다 (다시 그리면 미리보기 + 변경 버튼이 보인다)
                w["poster"] = (up.name, data)
                st.session_state["poster_changing"] = False
                st.session_state["poster_ver"] = ver + 1
                st.rerun()
        if changing:
            if st.button("취소", key="poster_change_cancel", help="기존 포스터를 그대로 둡니다"):
                st.session_state["poster_changing"] = False
                st.rerun()
        elif not w["poster"]:
            st.caption("포스터가 없어도 등록할 수 있어요. 있으면 목록에서 훨씬 눈에 띄어요!")
    kept_poster = w["poster"]

    st.markdown(f"**이미지 추가 등록** :gray[(최대 {images.MAX_EXTRAS}장)]")
    extras = st.file_uploader(f"추가 이미지 (~ {images.EXTRA_MB} MB)", type=images.TYPES,
                              accept_multiple_files=True, key=f"extras_{w['v']}",
                              label_visibility="collapsed")
    kept_extras = [(f.name, f.getvalue()) for f in extras] if extras else w["extras"]
    if kept_extras:
        st.caption(f"추가 이미지 미리보기 ({len(kept_extras)}장)"
                   + ("" if extras else " · 앞서 올린 이미지예요."))
        _thumbs([d for _, d in kept_extras[:images.MAX_EXTRAS]])

    if len(extras or []) > images.MAX_EXTRAS:
        errors.append(f"추가 이미지는 {images.MAX_EXTRAS}장까지 올릴 수 있습니다.")
    if any(images.too_big(f.getvalue(), images.EXTRA_MB) for f in extras or []):
        errors.append(f"추가 이미지는 한 장에 {images.EXTRA_MB} MB 까지 올릴 수 있습니다.")
    for e in errors:
        st.error(e)

    def save():
        w["poster"], w["extras"] = kept_poster, kept_extras

    _nav(next_ok=not errors, on_next=save)


def _step_dates(w: dict) -> None:
    d1, d2 = st.columns(2)
    with d1:
        start = st.date_input("시작", value=w["start_date"], key=f"start_{w['v']}")
    with d2:
        end = st.date_input("종료", value=w["end_date"], key=f"end_{w['v']}")
    if end < start:
        st.caption("종료일이 시작일보다 빠릅니다.")

    def save():
        w["start_date"], w["end_date"] = start, end

    _nav(next_ok=end >= start, on_next=save)


def _step_extras(w: dict) -> None:
    perks = st.text_input("특전", value=w["perks"], key=f"perks_{w['v']}",
                          placeholder=f"{_ask('특전')} (예: 랜덤 코스터, 포토카드)", help="쉼표로 구분")
    goods = st.text_input("굿즈", value=w["goods"], key=f"goods_{w['v']}",
                          placeholder=f"{_ask('굿즈')} (예: 아크릴 스탠드, 캔뱃지)", help="쉼표로 구분")

    st.markdown("**이벤트 추가 정보**")
    cols = st.columns(3)
    tags = [t for i, t in enumerate(cafe.EVENT_TAGS)
            if cols[i % 3].checkbox(t, value=t in w["tags"], key=f"tag_{t}_{w['v']}")]

    links, bad_links = _links_field("\n".join(w["links"]), key=f"links_{w['v']}")

    def save():
        w["perks"], w["goods"], w["tags"], w["links"] = perks, goods, tags, links

    _nav(next_ok=not _block_sensitive(perks, goods) and not bad_links, on_next=save)


def _step_confirm(w: dict) -> None:
    """마지막 단계. 앞에서 넣은 정보를 한눈에 보여 주고, 확인되면 등록한다.
    (공지 붙여넣기는 첫 단계의 '공지로 간편등록' 에서만 한다)"""
    span = f"{w['start_date']:%Y.%m.%d} ~ {w['end_date']:%Y.%m.%d}"
    rows = [("작품", w["work"]), ("캐릭터", w["characters"]), ("카페명", w["cafe_name"]),
            ("주소", w["address"]), ("기간", span), ("특전", w["perks"]), ("굿즈", w["goods"]),
            ("이벤트", " · ".join(w["tags"])),
            ("이미지", f"{len([f for f in [w['poster'], *w['extras']] if f])}장")]
    st.markdown("  \n".join(f"**{k}** · {_plain(v)}" for k, v in rows if v))
    st.caption("고칠 곳이 있으면 '이전' 으로 돌아가 바꿔 주세요.")

    entry = CafeEntry(
        cafe_name=w["cafe_name"], work=w["work"], characters=_split(w["characters"]),
        address=w["address"],
        start_date=w["start_date"], end_date=w["end_date"],
        perks=_split(w["perks"]), goods=_split(w["goods"]),
        confidence="high",
    )
    v = guard.validate_cafe(entry, today=TODAY, existing=store.current_rows())
    for warn in v.warnings:
        st.warning(warn)
    for err in v.errors:
        st.error(err)

    def save():
        g = _wiz_geo(w)
        if not g.ok:
            st.session_state["wiz_err"] = g.note
            return False
        files = [f for f in [w["poster"], *w["extras"]] if f]
        saved = [images.save(name, data) for name, data in files]
        store.append(cafe.entry_to_row(entry, g.lat, g.lng, source="직접 등록",
                                       note=f"{g.badge} ({g.matched})",
                                       images=saved, tags=w["tags"], links=w["links"]))
        st.session_state["save_report"] = {"saved": [(entry.cafe_name, g.badge)], "blocked": []}
        st.session_state.pop("wiz", None)
        go("map")

    _nav("등록하기", next_ok=v.ok, on_next=save)


def page_add() -> None:
    w = _wiz()
    step = w["step"]
    title, icon = STEPS[step]

    st.markdown(GLOBAL_CSS + WIZARD_CSS, unsafe_allow_html=True)
    _no_translate()
    _history_guard(on_main=False)
    _live_send()    # 간편등록 '읽어오기' 버튼을 공지 입력칸에 맞춰 바로 켜고 끈다
    # 메인과 같은 상단(제목·문구)이 스크롤해도 떠 있고, 'ANIME POP-UP · CAFE · GOODS' 줄 오른쪽에 홈으로
    with st.container(key="topbar"):
        if _brand(home=True, fixed=True):         # 등록 화면은 로고 고정
            st.session_state.pop("wiz", None)
            go("map")

    back, head, _ = st.columns([1.2, 6, 1.2], vertical_alignment="center")
    with back:
        # 첫 단계에서는 지도로, 그 뒤로는 한 단계 앞으로
        # 첫 단계에서는 돌아갈 곳이 없어 숨긴다 (메인은 위의 홈으로)
        if step > 0 and st.button("돌아가기", key="wiz_back", help="이전 단계로", width="stretch"):
            _move(-1)
    with head:
        # 제목을 누르면 메인(지도)으로 돌아간다
        if st.button("팝업 카페 등록하기", key="home_add", type="tertiary", help="메인으로"):
            st.session_state.pop("wiz", None)
            go("map")

    _, mid, _ = st.columns([1, 2, 1])
    if w.get("quick"):
        # 간편등록은 단계 없이 한 화면. '단계별로 등록' 을 누르면 읽어 온 값을 그대로 들고 1단계로 간다
        with mid, st.container(border=True):
            st.markdown('<div class="wiz-title">공지로 간편등록</div>', unsafe_allow_html=True)
            st.markdown('<div class="wiz-icon">📝</div>', unsafe_allow_html=True)
            _quick(w)
            if st.button("단계별로 등록하기", width="stretch", key="quick_off"):
                w["quick"], w["step"] = False, 0
                w["v"] += 1
                st.rerun()
        return
    with mid:
        pct = (step + 1) / len(STEPS) * 100
        st.markdown(
            f'<div class="wiz-bar"><div style="width:{pct:.0f}%"></div></div>'
            f'<div class="wiz-count">{step + 1} / {len(STEPS)}</div>',
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.markdown(f'<div class="wiz-title">{title}</div>', unsafe_allow_html=True)
            if step in (0, len(STEPS) - 1):
                st.markdown(f'<div class="wiz-icon">{icon}</div>', unsafe_allow_html=True)
            err = st.session_state.pop("wiz_err", None)
            if err:
                st.error(err)
            note = st.session_state.pop("wiz_note", None)
            if note:
                st.caption(note)
            [_step_work, _step_cafe, _step_images, _step_dates, _step_extras,
             _step_confirm][step](w)

# ================================================================ 내 캘린더
# 찜한 팝업을 달마다 달력에 막대로 (연속된 날은 한 막대), 아래에 곧 있는 팝업 목록
CAL_COLORS = ["#14b8a6", "#F59E0B", "#8B5CF6", "#EC4899", "#3B82F6", "#22A06B", "#EF6C4D", "#64748B"]
CAL_CSS = f"""
<style>
/* 달력 머리글: 큰 '2026년 10월' · ‹ › · 테두리 있는 '오늘' */
.st-key-cal_nav {{ align-items:center !important; flex-wrap:nowrap !important; gap:6px !important; margin:4px 0 12px; }}
.st-key-cal_nav > div {{ width:auto !important; flex:0 0 auto !important; }}
.st-key-cal_nav > div:first-child {{ flex:1 1 auto !important; }}
.st-key-cal_nav [data-testid="stMarkdownContainer"] {{ margin:0 !important; }}
.st-key-cal_nav [data-testid="stMarkdownContainer"] p {{ margin:0; }}
.cal-month {{ font-weight:900; font-size:1.6rem; color:#111; letter-spacing:-.01em; white-space:nowrap; }}
.st-key-cal_prev button, .st-key-cal_next button {{ min-height:0 !important; height:40px; width:40px; padding:0 !important; }}
.st-key-cal_prev button p, .st-key-cal_next button p {{ font-size:1.6rem !important; line-height:1 !important;
  color:#26302D !important; font-weight:500; margin:0 !important; }}
.st-key-cal_prev button:hover p, .st-key-cal_next button:hover p {{ color:var(--accent-deep) !important; }}
.st-key-cal_now button {{ min-height:0 !important; height:44px; padding:0 .9rem !important; border-radius:10px !important;
  border:1.5px solid #DDE2E0 !important; background:#fff !important; margin-left:10px; }}
.st-key-cal_now button p {{ font-size:.95rem !important; color:#26302D !important; }}
.st-key-cal_now button:hover {{ border-color:var(--accent) !important; }}
.cal {{ border-top:2px solid #26302D; }}
.cal-dow, .cal-week {{ display:grid; grid-template-columns:repeat(7, 1fr); }}
.cal-dow div {{ text-align:center; font-weight:700; color:#5B6663; padding:8px 0; border:1px solid #E4E8E6;
               border-top:0; margin-left:-1px; background:#FAFBFA; }}
.cal-dow div:first-child {{ color:#E0566B; }} .cal-dow div:last-child {{ color:#4C7BD9; }}
.cal-week {{ position:relative; }}
.cal-day {{ border:1px solid #E4E8E6; border-top:0; margin-left:-1px; padding:6px 8px; font-weight:700;
           color:#3F4A47; font-size:.95rem; background:#fff; }}
.cal-day.out {{ background:#F4F6F5; color:#B5BDBA; }}
.cal-day.sun {{ color:#E0566B; }} .cal-day.sat {{ color:#4C7BD9; }}
.cal-day.out.sun, .cal-day.out.sat {{ color:#C9CFCD; }}
.cal-day.today {{ background:var(--accent-soft); }}
.cal-day.today span {{ background:var(--accent); color:#fff; border-radius:999px; padding:1px 7px; }}
.cal-bar {{ position:absolute; height:20px; line-height:20px; font-size:.78rem; font-weight:700; color:#fff !important;
           padding:0 7px; border-radius:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
           text-decoration:none !important; box-sizing:border-box; }}
.cal-bar:hover {{ filter:brightness(.92); }}
/* 막대에 커서를 올리면 지도의 점처럼 포스터·작품·카페·위치·기간 카드가 막대 아래에 뜬다 */
.cal-pop {{ position:absolute; z-index:30; width:250px; background:#fff; border-radius:14px; padding:8px;
           border-top:3px solid var(--accent); box-shadow:0 8px 24px rgba(0,0,0,.18); display:none; gap:9px;
           pointer-events:none; font-size:12.5px; color:#26302D; line-height:1.4; }}
.cal-bar:hover + .cal-pop {{ display:flex; }}
.cal-pop img {{ width:58px; height:78px; object-fit:cover; border-radius:8px; flex:0 0 auto; background:#F4F6F5; }}
.cal-pop .w {{ font-weight:800; font-size:13.5px; color:var(--accent-deep); margin-bottom:2px; }}
.cal-pop .c {{ font-weight:600; margin-bottom:3px; }}
.cal-pop .a {{ color:#5f6b67; font-size:11.5px; }}
.cal-pop .d {{ color:var(--accent-deep); font-size:11.5px; font-weight:700; }}
.cal-bar.cl {{ border-top-left-radius:0; border-bottom-left-radius:0; }}
.cal-bar.cr {{ border-top-right-radius:0; border-bottom-right-radius:0; }}
.up-head {{ display:flex; align-items:center; gap:14px; margin:34px 0 14px; }}
.up-head b {{ font-family:"Jua", sans-serif; font-size:1.4rem; font-weight:400; color:#1F2A27; white-space:nowrap; }}
.up-head i {{ flex:1; height:1px; background:#D5DBD9; }}
.up-item {{ display:flex; align-items:center; gap:14px; padding:12px 16px; border:1px solid #E4E8E6;
           border-radius:12px; margin-bottom:10px; background:#fff; text-decoration:none !important; color:inherit !important; }}
.up-item:hover {{ border-color:var(--accent); background:var(--accent-soft); }}
.up-thumb {{ flex:0 0 52px; height:52px; border-radius:8px; background:#F4F6F5 center/cover no-repeat; }}
.up-text {{ flex:1; min-width:0; }}
.up-name {{ font-weight:800; font-size:1.02rem; color:#1F2A27; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.up-when {{ color:var(--accent-deep); font-weight:700; font-size:.9rem; margin-top:2px; }}
.up-bar {{ flex:0 0 6px; align-self:stretch; border-radius:3px; }}
.up-state {{ flex:0 0 auto; font-size:.8rem; font-weight:800; padding:.2rem .6rem; border-radius:.5rem; white-space:nowrap; }}
.up-state.green {{ background:#E3F6EA; color:#1F7A44; }} .up-state.blue {{ background:#E5EEFC; color:#2C5BC5; }}
.up-state.red {{ background:#FDE8EC; color:#C23A54; }} .up-state.gray {{ background:#EEF0EF; color:#6B7672; }}
.cal-empty {{ color:#6B7672; font-size:.76rem; background:#F4F6F5; border-radius:8px; padding:6px 10px; margin-bottom:8px; }}
.up-empty {{ color:#6B7672; font-size:.76rem; padding:12px; border:1px dashed #D5DBD9; border-radius:10px; text-align:center; }}
/* 지도 옆 작은 캘린더 */
.st-key-map_cal .cal-month {{ font-size:1.15rem; }}
.st-key-map_cal .st-key-cal_nav {{ margin:0 0 6px; gap:2px !important; }}
.st-key-map_cal .st-key-cal_prev button, .st-key-map_cal .st-key-cal_next button {{ height:28px; width:26px; }}
.st-key-map_cal .st-key-cal_prev button p, .st-key-map_cal .st-key-cal_next button p {{ font-size:1.2rem !important; }}
.st-key-map_cal .st-key-cal_now button {{ height:30px; padding:0 .6rem !important; margin-left:4px; border-radius:8px !important; }}
.st-key-map_cal .st-key-cal_now button p {{ font-size:.78rem !important; }}
.st-key-map_cal .cal-dow div {{ padding:4px 0; font-size:.72rem; }}
.st-key-map_cal .cal-day {{ padding:3px 5px; font-size:.72rem; }}
.st-key-map_cal .cal-day.today span {{ padding:0 5px; }}
.st-key-map_cal .cal-bar {{ height:16px; line-height:16px; font-size:.62rem; padding:0 4px; border-radius:4px; }}
.st-key-map_cal .up-head {{ margin:18px 0 8px; }}
.st-key-map_cal .up-head b {{ font-size:1.05rem; }}
.st-key-map_cal .up-item {{ gap:8px; padding:8px 10px; margin-bottom:6px; border-radius:10px; }}
.st-key-map_cal .up-thumb {{ flex-basis:36px; height:36px; }}
.st-key-map_cal .up-name {{ font-size:.8rem; }}
.st-key-map_cal .up-when {{ font-size:.72rem; }}
.st-key-map_cal .up-state {{ font-size:.66rem; padding:.12rem .4rem; }}
@media (max-width: 640px) {{
  .cal-day {{ padding:4px 4px; font-size:.8rem; }}
  .cal-bar {{ font-size:.66rem; padding:0 4px; height:17px; line-height:17px; }}
  .cal-month {{ font-size:1.25rem; }}
}}
</style>
"""


def _cal_color(work: str) -> str:
    """같은 작품은 늘 같은 색."""
    return CAL_COLORS[int(hashlib.md5(work.encode()).hexdigest(), 16) % len(CAL_COLORS)]


def _cal_html(year: int, month: int, events: list, compact: bool = False) -> str:
    # 막대 한 줄 높이, 날짜 숫자 아래 막대가 시작하는 높이, 날짜 칸 최소 높이 (px). 지도 옆(compact)은 작게
    lane_h, top, min_h = (18, 22, 44) if compact else (23, 32, 86)
    dow = "".join(f"<div>{d}</div>" for d in "일월화수목금토")
    weeks = []
    for w in mycal.month_weeks(year, month, events):
        height = max(min_h, top + w.lanes * lane_h + 8)
        cells = "".join(
            f'<div class="cal-day{" out" if d.month != month else ""}{" sun" if i == 0 else " sat" if i == 6 else ""}'
            f'{" today" if d == TODAY else ""}" style="min-height:{height}px"><span>{d.day}</span></div>'
            for i, d in enumerate(w.days))
        # 연속된 날은 한 막대. 주를 넘어가면 끊긴 쪽 모서리를 각지게 둔다 (.cl / .cr)
        bars = "".join(
            f'<a class="cal-bar{" cl" if b.cont_left else ""}{" cr" if b.cont_right else ""}" href="./?cafe={quote(b.event.cafe_id)}"'
            f' target="_self"'
            f' style="left:calc({b.col} * 100% / 7 + 3px); width:calc({b.span} * 100% / 7 - 6px);'
            f' top:{top + b.lane * lane_h}px; background:{_cal_color(b.event.work)}">'
            f'{escape(b.event.work)}</a>' + _cal_pop(b, top + (b.lane + 1) * lane_h)
            for b in w.bars)
        weeks.append(f'<div class="cal-week">{cells}{bars}</div>')
    return f'<div class="cal"><div class="cal-dow">{dow}</div>{"".join(weeks)}</div>'


def _cal_pop(b, top: int) -> str:
    """막대 바로 아래에 뜨는 미리보기 카드. 오른쪽 칸(목~토)에서 시작하는 막대는 오른쪽 끝에 맞춰 화면 밖으로 안 나가게."""
    e = b.event
    side = (f"right:calc({7 - b.col - b.span} * 100% / 7 + 3px)" if b.col >= 4
            else f"left:calc({b.col} * 100% / 7 + 3px)")
    return (f'<div class="cal-pop" style="{side}; top:{top}px">'
            f'<img src="{_poster_url(e.images)}" alt=""/>'
            f'<div><div class="w">{escape(e.work)}</div><div class="c">{escape(e.cafe_name)}</div>'
            f'<div class="a">{escape(e.address or "-")}</div>'
            f'<div class="d">{e.start:%m.%d} ~ {e.end:%m.%d}</div></div></div>')


def _upcoming_html(events: list) -> str:
    items = []
    for e in mycal.upcoming(events, TODAY):
        label, color = mycal.status(e, TODAY)
        when = _day(e.start, False) + ("" if e.start == e.end else f" - {_day(e.end, False)}")
        items.append(
            f'<a class="up-item" href="./?cafe={quote(e.cafe_id)}" target="_self">'
            f'<span class="up-bar" style="background:{_cal_color(e.work)}"></span>'
            f'<span class="up-thumb" style="background-image:url(\'{_poster_url(e.images)}\')"></span>'
            f'<span class="up-text"><div class="up-name">{escape(e.work)} · {escape(e.cafe_name)}</div>'
            f'<div class="up-when">{when}</div></span>'
            f'<span class="up-state {color}">{escape(label)}</span></a>')
    body = "".join(items) or '<div class="up-empty">곧 있는 팔로우한 팝업이 없어요. 리스트에서 팔로우를 켜 보세요.</div>'
    return f'<div class="up-head"><b>곧 있는 팝업</b><i></i></div>{body}'


def _cal_shift(delta: int) -> None:
    y, m = st.session_state.get("cal_month") or (TODAY.year, TODAY.month)
    m += delta
    st.session_state["cal_month"] = (y + (m - 1) // 12, (m - 1) % 12 + 1)


def page_calendar() -> None:
    st.markdown(GLOBAL_CSS + CAL_CSS, unsafe_allow_html=True)
    _no_translate()
    if _brand(home=True, fixed=True):
        go("map")
    render_calendar()


def render_calendar(compact: bool = False) -> None:
    """내 캘린더 묶음 (월 머리글·이전/다음 달·달력·곧 있는 팝업). compact 면 지도 옆 좁은 칸용으로 칸 높이를 줄인다."""
    _, mine, _ = _fav_state()
    # 기간이 끝나 지도에서 내려간 팔로우도 지난 달력에 남도록, 내린 기록까지 포함한 최신 행에서 고른다
    events = mycal.fav_events(mycal.latest_rows(store.all_rows()), mine, TODAY)

    year, month = st.session_state.get("cal_month") or (TODAY.year, TODAY.month)
    # 머리글 한 줄: '2026년 10월'  ‹  ›  [오늘]
    with st.container(horizontal=True, vertical_alignment="center", key="cal_nav"):
        st.markdown(f'<span class="cal-month">{year}년 {month}월</span>', unsafe_allow_html=True)
        st.button("‹", key="cal_prev", type="tertiary", on_click=_cal_shift, args=(-1,), help="이전 달")
        st.button("›", key="cal_next", type="tertiary", on_click=_cal_shift, args=(1,), help="다음 달")
        st.button("오늘", key="cal_now", on_click=lambda: st.session_state.pop("cal_month", None),
                  help="이번 달로")
    if not events:
        st.markdown('<div class="cal-empty">아직 팔로우한 팝업이 없어요. 리스트에서 팔로우를 켜면 달력에 일정이 채워져요.</div>',
                    unsafe_allow_html=True)
    st.markdown(_cal_html(year, month, events, compact), unsafe_allow_html=True)
    st.markdown(_upcoming_html(events), unsafe_allow_html=True)



# 지도와 등록은 주소가 다른 별개 페이지다 (/, /add). 메뉴는 숨기고 버튼으로만 오간다.
PAGES = {
    "map": st.Page(page_map, title="ANI:WHERE", icon="🗺️", url_path="map", default=True),
    "add": st.Page(page_add, title="팝업 카페 등록하기 · ANI:WHERE", icon="➕", url_path="add"),
    "calendar": st.Page(page_calendar, title="내 캘린더 · ANI:WHERE", icon="📅", url_path="calendar"),
}
st.navigation(list(PAGES.values()), position="hidden").run()
