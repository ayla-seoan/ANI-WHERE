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

import dataclasses
import hashlib
import json
import os
import re
import time
from urllib.parse import quote
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from common import (admin, ai, ask, auth, cafe, catalog, favorite, gallery, geo, guard, images, kakao_map,
                    kakao_postcode, mycal, notice, notion_sync, review, share, stats)
from common import links as links_check   # 참고 웹사이트 확인 (11/18 안정성)
from common import dates as pdates   # 기간 표기: 상시 · 기간 확인 필요 (11/18 안정성)
from common import locate as my_place   # 앱 안의 locate() (주소 → 좌표) 와 이름이 겹쳐서 따로 부른다
from common.schema import CafeEntry
from common.storage import Storage, StorageWriteError

load_dotenv()

ROOT = Path(__file__).resolve().parent
TODAY = date.today()
MAP_HEIGHT = 620
# 제목 로고: 예전 '팝업 카페 등록하기' 화면의 흰 글자 + 민트 테두리 로고로 통일 (11/18 요청, 바꿔 돌리지 않음)
LOGOS = ["logo_add.png"]
FIXED_LOGO = "logo_add.png"
ADD_LOGO = "logo_add.png"          # 등록 화면 로고 (흰 글자 + 민트 테두리)           # 상세·등록 화면에서는 이 로고로 고정
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
@import url('https://cdn.jsdelivr.net/gh/moonspam/NanumSquareRound@1.0/nanumsquareround.min.css');
/* @import 는 맨 앞에 와야 해서(앞에 다른 규칙이 있으면 폰트가 무시된다) 변수는 그 뒤에 둔다 */
/* 이미지가 안 열리면(주소 깨짐·서버 재시작으로 파일 없음) 깨진 아이콘 대신 기본 포스터가 보이게 (11/18 안정성).
   alt 가 빈 <img> 는 실패하면 아무것도 그리지 않아서 뒤의 배경 그림이 보인다 */
img.pst, .apc img, .nh-item img, .cal-pop img, .adm-pcard img, .rv-pics img, .bxr .imgs img {{
  background: #F4F6F5 url('app/static/default_poster.png') center / cover no-repeat; }}
img.rv-av, img.me-avimg, .auth-av img {{ background: #DDF3EC; }}
/* 긴 행사명(「○○○」 팝업스토어 in 홍대 2호점 …)이 모바일에서 화면 밖으로 나가지 않게 */
.dtitle, .dcafe, .daddr, .nh-name, .apc-cafe, .apc-addr {{ overflow-wrap: anywhere; }}
/* 포인트 컬러 변수 (map-template.html 과 같은 값). 지도·등록하기 버튼 등이 쓴다 */
:root {{ --accent: #14b8a6; --accent-soft: #e6fbf7; --accent-deep: #0d9488; }}
html, body, [class*="st-"], .stMarkdown, button, input, textarea {{
  font-family: "NanumSquareRound", "Pretendard", -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; }}
/* 위의 글꼴 지정이 아이콘 글꼴까지 덮지 않게 (안 그러면 '_arrow_right' 같은 이름 글자가 보인다) */
[data-testid="stIconMaterial"], [data-testid="stAlertDynamicIcon"], [data-testid="stExpanderIcon"],
.material-symbols-rounded {{
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
/* (⋯ 가 바로 들어 있는 작은 칸만 오른쪽 정렬. 그냥 :has 로 잡으면 리뷰 칸 전체가 오른쪽으로 붙었다) */
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [class*="st-key-rv_more_"]) > [data-testid="stVerticalBlock"] {{ align-items: flex-end; }}
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
  z-index: 50; background: #fff; padding-bottom: .5rem; box-shadow: none; }}
/* 흰 바탕을 화면 양옆 끝까지 넓힌다 (가운데 폭만 칠하면 스크롤할 때 양옆 여백으로 카드가 비쳐 그림자처럼 보였다).
   clip-path 로 자르면 안에 있는 화면 고정 버튼(오른쪽 아래 '+')까지 잘려 사라져서, 뒤에 깔리는 흰 띠로 칠한다 */
/* (PC 만: 모바일은 상단 묶음이 위에 붙지 않아 기준 칸이 없어서, 띠가 화면 전체를 덮어 카드가 안 보였다) */
@media (min-width: 641px) {{
  [data-testid="stLayoutWrapper"]:has(> .st-key-topbar)::before {{ content: ""; position: absolute; top: 0; bottom: 0;
    left: -100vmax; right: -100vmax; background: #fff; z-index: -1; pointer-events: none; }}
}}
/* 모바일(폭 640px 이하, 칸이 세로로 쌓이는 화면)에서는 위에 붙는 것 없이 그냥 함께 스크롤한다
   (메인·등록 화면의 상단 묶음, 메인의 지도 칸) */
@media (max-width: 640px) {{
  /* 세로로 쌓인 칸은 화면 폭을 다 쓴다. Streamlit 기본값(전체 폭 - 1.5rem)이면 오른쪽만 24px 비어
     지도·리스트가 왼쪽으로 쏠려 보였다. 한 줄로 둔 칸(카드 포스터·상세 제목 등)은 더 구체적인 규칙이 덮어쓴다 */
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
    width: 100% !important; min-width: 100% !important; flex: 1 1 100% !important; }}
  /* 위에 붙지 않으니 흰 바탕도 필요 없다. 바탕이 남아 있으면 바로 아래 '리스트로 보기' 버튼 윗부분을 가렸다 */
  [data-testid="stLayoutWrapper"]:has(> .st-key-topbar) {{ position: static !important; box-shadow: none !important;
    background: transparent !important; pointer-events: none; }}
  [data-testid="stLayoutWrapper"]:has(> .st-key-topbar) > * {{ pointer-events: auto; }}
  [data-testid="stColumn"]:has(iframe[src*="kakao_map"]) {{ position: static !important; }}
}}
/* 메인 '등록하기'·상세 '리스트로 돌아가기'·등록 화면 '홈으로 돌아가기' 버튼:
   포인트 색으로 채운 둥근 사각형, 흰 굵은 글자 (공식 안내 보기 버튼 모양) */
.st-key-add_btn button, .st-key-back_to_list button, .st-key-wiz_home button {{ background: var(--accent) !important; border: 0 !important; border-radius: 10px !important;
  min-height: 0 !important; height: 32px !important; width: auto !important; padding: 0 .9rem !important;
  box-shadow: 0 3px 10px rgba(20,184,166,.3) !important; }}
.st-key-add_btn, .st-key-back_to_list, .st-key-wiz_home, .st-key-add_btn > div, .st-key-back_to_list > div, .st-key-wiz_home > div {{ display: flex !important; justify-content: flex-end !important; }}
.st-key-add_btn button, .st-key-back_to_list button, .st-key-wiz_home button {{ margin-left: auto !important; }}
.st-key-back_to_list button span, .st-key-wiz_home button span {{ color: #fff !important; }}
.st-key-add_btn button p, .st-key-back_to_list button p, .st-key-wiz_home button p {{ color: #fff !important; font-weight: 800 !important; font-size: .92rem !important;
  letter-spacing: .01em; white-space: pre; }}
.st-key-add_btn button:hover, .st-key-back_to_list button:hover, .st-key-wiz_home button:hover {{ background: var(--accent-deep) !important; transform: translateY(-1px); }}
/* 메인 '등록하기': 위쪽이 아니라 화면 오른쪽 아래에 떠 있는 버튼. 포인트(민트)와 구분되게 코랄 색 */
.st-key-add_btn {{ position: fixed !important; right: 28px; bottom: 28px; z-index: 1001; width: auto !important; }}
.st-key-add_btn button {{ background: #FF6B6B !important; width: 56px !important; height: 56px !important; padding: 0 !important;
  border-radius: 50% !important; box-shadow: 0 8px 22px rgba(255,107,107,.45) !important; }}
.st-key-add_btn button {{ display: flex !important; align-items: center !important; justify-content: center !important; }}
.st-key-add_btn button span {{ font-size: 2rem !important; color: #fff !important; margin: 0 !important; }}
.st-key-add_btn button:hover {{ background: #F25454 !important; }}
@media (max-width: 640px) {{
  /* 모바일: 아래 가운데 '필터 / 지도보기' 버튼 위로 비켜 둔다 */
  .st-key-add_btn {{ right: 16px; bottom: 76px; }}
  .st-key-add_btn button {{ width: 50px !important; height: 50px !important; }}
  .st-key-add_btn button span {{ font-size: 1.8rem !important; }}
}}
/* '팔로우' 스위치 (팔로우한 곳만 보기). 키에 'fav_' 를 쓰지 않는다 — 카드 팔로우 버튼 규칙([class*="st-key-fav_"])에 걸리지 않게 */
/* (상세·카드의 북마크 버튼과 같은 모양: 흰 바탕·회색 테두리, 켜지면 포인트 색으로 채움) */
[class*="st-key-folsw"] button {{ min-height: 0 !important; height: 40px; padding: 0 14px !important; gap: 4px;
  border-radius: 999px !important; border: 1.5px solid #DDE2E0 !important; background: #fff !important; }}
[class*="st-key-folsw"] button span {{ font-size: 1.2rem !important; color: #26302D !important; }}
[class*="st-key-folsw"] button p {{ white-space: nowrap; overflow: visible !important; font-size: .88rem !important; font-weight: 800 !important; color: #26302D !important; }}
[class*="st-key-folsw"][class*="_on"] button {{ background: var(--accent) !important; border-color: var(--accent) !important; }}
[class*="st-key-folsw"][class*="_on"] button span, [class*="st-key-folsw"][class*="_on"] button p {{ color: #fff !important; }}
[class*="st-key-folsw"][class*="_off"] button:hover {{ border-color: var(--accent) !important; }}
/* PC 리스트 보기: 북마크 · 지역 고르기 · 최신순을 '지도로 보기' 버튼과 같은 높이(32px)로 */
@media (min-width: 641px) {{
  .st-key-listtools [class*="st-key-folsw"] button {{ height: 32px !important; }}
  /* (Streamlit 1.66 의 고르기 칸: stSelectbox/stMultiSelect > div > div 안에 입력칸·화살표) */
  .st-key-listtools .st-key-sort [data-testid="stSelectbox"] > div:not([data-testid]),
  .st-key-listtools .st-key-sort [data-testid="stSelectbox"] > div:not([data-testid]) > div {{ height: 32px !important; min-height: 32px !important; }}
  .st-key-listtools .st-key-sort input {{ height: 30px !important; font-size: .88rem !important; }}
  .st-key-listtools .st-key-regions [data-testid="stMultiSelect"] > div:not([data-testid]),
  .st-key-listtools .st-key-regions [data-testid="stMultiSelect"] > div:not([data-testid]) > div {{ min-height: 32px !important; }}
  .st-key-listtools .st-key-regions [data-testid="stMultiSelectTagsContainer"] {{ min-height: 30px !important; padding-top: 0 !important;
    padding-bottom: 0 !important; }}
  .st-key-listtools .st-key-regions input {{ height: 26px !important; font-size: .88rem !important; }}
}}
/* 목록 위 '팔로우' 스위치는 칸 오른쪽 끝, 바로 옆 '지역 고르기' 에 붙인다 */
.st-key-listtools [data-testid="stColumn"]:has([class*="st-key-folsw_"]) [data-testid="stVerticalBlock"] {{ align-items: flex-end; }}
/* 보기 전환·필터 아이콘 묶음: 정렬 칸 위 오른쪽 끝. 떠 있어도 원래 자리 높이는 남긴다 */
[data-testid="stLayoutWrapper"]:has(> .st-key-view_tools) {{ min-height: 32px; }}
.st-key-view_tools {{ justify-content: flex-end !important; align-items: center; gap: 6px !important; flex-wrap: nowrap !important; }}
.st-key-view_tools > div {{ width: auto !important; flex: 0 0 auto !important; }}
.st-key-view_tools.pinned button {{ box-shadow: 0 4px 14px rgba(0,0,0,.14) !important; }}
/* 필터 아이콘: 모바일에서만 (예전 '화면 아래 떠 있는 필터 버튼' 규칙을 덮어쓴다) */
.st-key-view_tools .st-key-m_filter_btn {{ position: static !important; transform: none !important; left: auto !important;
  bottom: auto !important; width: auto !important; }}
.st-key-view_tools .st-key-m_filter_btn button {{ min-height: 0 !important; height: 32px; min-width: 32px; width: auto !important;
  padding: 0 9px !important; gap: 2px; border: 1.5px solid var(--accent) !important; border-radius: 10px !important;
  background: #fff !important; box-shadow: none; }}
.st-key-view_tools .st-key-m_filter_btn button span {{ color: var(--accent-deep) !important; font-size: 1.2rem !important; }}
.st-key-view_tools .st-key-m_filter_btn button p {{ color: var(--accent-deep) !important; font-size: .8rem !important; font-weight: 800 !important; }}
/* 리스트 전체보기의 지도 아이콘 버튼: 정렬 칸 위 오른쪽 끝, 테두리 있는 작은 정사각형 */
/* 보기 전환 버튼 위아래 간격을 다른 칸들 사이 간격(16px)과 같게: 버튼 ↔ 정렬 칸, 위(검색 필터 묶음),
   지도보기에서는 버튼 ↔ 데일리 팝업 노트·지도 줄 */
[data-testid="stColumn"]:has(.st-key-map_icon) [data-testid="stVerticalBlock"] {{ gap: 8px; }}   /* 버튼 ↔ 최신순: 반 칸 */
@media (min-width: 641px) {{
  /* PC: 검색 필터 묶음 아래 여백은 반 칸(8px)만 (상단 묶음 아래 안쪽 여백 0 + 칸 사이 간격을 반으로) */
  [data-testid="stLayoutWrapper"]:has(> .st-key-topbar) {{ padding-bottom: 8px !important; }}   /* 날짜 줄 아래 반 칸 */
  [data-testid="stLayoutWrapper"]:has(> .st-key-listtools) {{ margin-top: -8px; }}   /* 검색 줄 아래 반 칸 */
}}
@media (max-width: 640px) {{
  /* 모바일: '함께 만드는 애니 팝업 지도…' 문구 아래 여백을 반으로 (문구 아래 여백 없애고 아래 줄을 조금 끌어올림) */
  .brand-tag {{ margin-bottom: 0 !important; }}
  [data-testid="stLayoutWrapper"]:has(> .st-key-listtools) {{ margin-top: -15px; }}
  /* 모바일 지도보기: 위(상단 묶음)·아래(데일리 팝업 노트·지도 줄)와 16px */
  .stMain:has(.st-key-map_row) [data-testid="stLayoutWrapper"]:has(> .st-key-view_tools) {{ margin-top: -9px; }}
  [data-testid="stLayoutWrapper"]:has(> .st-key-map_row) {{ margin-top: -11px; }}
}}
.st-key-map_icon {{ display: flex !important; justify-content: flex-end; width: 100% !important; min-height: 32px; }}
.st-key-map_icon .stButton {{ width: 100% !important; display: flex !important; justify-content: flex-end !important; }}
/* 크기는 '홈으로 돌아가기' 버튼과 같게 (높이 32px · 좌우 .9rem · 글자 .92rem 굵게) */
.st-key-map_icon button {{ min-height: 0 !important; height: 32px; width: auto !important; flex: 0 0 auto !important;
  padding: 0 .9rem !important; gap: 4px; box-shadow: 0 3px 10px rgba(20,184,166,.3) !important;
  border: 0 !important; border-radius: 10px !important; background: var(--accent) !important; }}
.st-key-map_icon button span {{ color: #fff !important; font-size: 1.2rem !important; }}
.st-key-map_icon button p {{ color: #fff !important; font-size: .92rem !important; font-weight: 800 !important; white-space: nowrap; }}
.st-key-map_icon button:hover {{ background: var(--accent-deep) !important; }}
/* 토스트 알림(북마크·리뷰 등)은 화면 정가운데에 */
[data-testid="stToastContainer"] {{ position: fixed !important; top: 50% !important; left: 50% !important;
  right: auto !important; bottom: auto !important; transform: translate(-50%, -50%) !important;
  align-items: center !important; z-index: 2000 !important; }}
/* 토스트가 여러 개면 위아래로 쌓지 않고 같은 자리에 겹쳐서, 가장 최근 것이 맨 위에 보이게 */
[data-testid="stToastContainer"] {{ display: grid !important; }}
[data-testid="stToastContainer"] > * {{ grid-area: 1 / 1; justify-self: center; align-self: center; }}
[data-testid="stToast"] {{ background: #fff !important; border: 1.5px solid var(--accent) !important; border-radius: 14px !important;
  box-shadow: 0 10px 28px rgba(20,184,166,.28) !important; padding: 12px 16px 12px 18px !important; min-width: 0 !important;
  width: max-content !important; max-width: min(90vw, 420px) !important; }}
[data-testid="stToast"] [data-testid="stMarkdownContainer"] p {{ white-space: normal; word-break: keep-all; }}
[data-testid="stToast"] [data-testid="stMarkdownContainer"] p, [data-testid="stToast"] p {{ color: #1F2A27 !important;
  font-weight: 700 !important; font-size: .95rem !important; margin: 0 !important; }}
/* 토스트 아이콘: 사이트 전체 글꼴(Pretendard) 규칙이 아이콘 글꼴을 덮어써 'bookmark_added' 글자로 보였다 */
[data-testid="stToast"] [data-testid="stToastDynamicIcon"], [data-testid="stToast"] [data-testid="stIconMaterial"] {{
  font-family: "Material Symbols Rounded" !important; color: var(--accent) !important; font-size: 1.4rem !important; }}
/* 아이콘과 글자를 세로 가운데로 맞춘다 (아이콘을 감싼 줄이 위쪽 정렬이라 아이콘이 6px 떠 있었다) */
[data-testid="stToast"] div:has(> span > [data-testid="stToastDynamicIcon"]) {{ align-items: center !important; gap: 10px; }}
[data-testid="stToast"] [data-testid="stToastDynamicIcon"] {{ line-height: 1 !important; }}
[data-testid="stToast"] [data-testid="stMarkdownContainer"] {{ margin: 0 !important; display: flex; align-items: center; }}
[data-testid="stToast"] button {{ display: none !important; }}   /* 토스트는 닫기 버튼 없이 잠깐 떴다 사라진다 */
/* 입력칸에 글자를 쓸 때 오른쪽 아래에 뜨는 'Press Enter / Ctrl+Enter to apply' 안내는 모두 숨긴다 */
[data-testid="InputInstructions"] {{ display: none !important; }}
/* 이모지 대신 쓰는 아이콘 (_mi). 사이트 글꼴 규칙이 아이콘 글꼴을 덮어쓰지 않게 !important */
.mi {{ font-family: "Material Symbols Rounded" !important; font-weight: normal; font-style: normal; font-size: 1.15em;
  line-height: 1; display: inline-block; vertical-align: -0.18em; letter-spacing: normal; text-transform: none;
  white-space: nowrap; direction: ltr; -webkit-font-smoothing: antialiased; color: inherit; margin-right: 3px; }}
/* 흰 바탕 글줄 안의 아이콘(혜택 목록·카드 날짜·위치 등)은 포인트 색, 포스터·배지 위에서는 글자색 그대로 */
.dbox .mi, .cmeta .mi, .ccafe .mi, .dbtn .mi, .wiz-icon .mi {{ color: var(--accent-deep); }}
.wiz-icon .mi {{ font-size: 64px; margin: 0; vertical-align: middle; }}
/* 수정 이력: 왼쪽 세로선 위 점 + 카드 (최근 것이 위, 지금 내용은 포인트 색) */
[class*="st-key-hx_"] {{ position: relative; padding: 4px 0 2px 22px; gap: 10px; }}
[class*="st-key-hx_"]::before {{ content: ""; position: absolute; left: 7px; top: 14px; bottom: 14px; width: 2px;
  background: var(--accent-soft); border-radius: 2px; }}
[class*="st-key-hxi_"], [class*="st-key-hxnow_"] {{ position: relative; overflow: visible; gap: 2px;
  background: #fff; border: 1.5px solid #E6ECEA; border-radius: 14px; padding: 10px 14px; }}
[class*="st-key-hxnow_"] {{ border-color: var(--accent); box-shadow: 0 4px 14px rgba(20,184,166,.12); }}
/* 세로선 위의 점 (지금 것은 포인트 색으로 채움) */
[class*="st-key-hxi_"]::before, [class*="st-key-hxnow_"]::before {{ content: ""; position: absolute; left: -22px; top: 15px;
  width: 12px; height: 12px; border-radius: 50%; background: #fff; border: 2px solid {MINT_LINE}; box-sizing: border-box; }}
[class*="st-key-hxnow_"]::before {{ background: var(--accent); border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }}
/* 이 버전으로 돌아가기: 카드 오른쪽 아래 작은 포인트 색 글자 버튼 */
[class*="st-key-hxi_"] [data-testid="stMarkdownContainer"], [class*="st-key-hxnow_"] [data-testid="stMarkdownContainer"],
[class*="st-key-hxi_"] [data-testid="stMarkdown"], [class*="st-key-hxnow_"] [data-testid="stMarkdown"] {{ margin-bottom: 0 !important; }}
[class*="st-key-restore_"] {{ display: flex; justify-content: flex-end; width: 100% !important; margin-top: 6px; }}
[class*="st-key-restore_"] .stButton {{ width: auto !important; margin-left: auto; }}
[class*="st-key-restore_"] button {{ min-height: 0 !important; padding: 4px 10px !important; border-radius: 999px !important;
  border: 1.5px solid var(--accent) !important; color: var(--accent-deep) !important; background: #fff !important; }}
[class*="st-key-restore_"] button:hover {{ background: var(--accent-soft) !important; }}
[class*="st-key-restore_"] button p {{ font-size: .8rem !important; font-weight: 700; }}
.hx-top {{ display: flex; align-items: center; flex-wrap: wrap; gap: 6px 8px; font-size: .9rem; }}
.hx-top b {{ color: #1F2A27; }}
.hx-when {{ color: #7A8A86; font-size: .82rem; }}
.hx-now {{ background: var(--accent); color: #fff; font-size: .72rem; font-weight: 700; padding: 1px 8px; border-radius: 999px; }}
.hx-src {{ margin-left: auto; background: var(--accent-soft); color: var(--accent-deep); font-size: .78rem; font-weight: 700;
  padding: 2px 10px; border-radius: 999px; }}
.hx-who {{ margin: 4px 0 6px; font-size: .82rem; font-weight: 700; color: #3E4C48; }}
.hx-chg {{ margin: 0 0 4px; font-size: .85rem; font-weight: 700; color: var(--accent-deep); }}
.hx-diff {{ display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 6px; font-size: .84rem; line-height: 1.5;
  padding: 5px 0; border-top: 1px dashed #E6ECEA; word-break: keep-all; overflow-wrap: anywhere; }}
.hx-k {{ flex: 0 0 auto; min-width: 72px; font-weight: 700; color: #3E4C48; }}
.hx-old {{ color: #98A5A1; text-decoration: line-through; }}
.hx-arrow .mi {{ font-size: 1em; margin: 0; }}
.hx-new {{ color: var(--accent-deep); font-weight: 700; }}
.hx-act {{ font-size: .78rem; font-weight: 700; padding: 1px 9px; border-radius: 999px; }}
.hx-act.add {{ background: var(--accent-soft); color: var(--accent-deep); }}
.hx-act.del {{ background: #FDE8EC; color: #C23A54; }}
.hx-act.chg {{ background: #EEF0EF; color: #4F5D59; }}
.hx-meta {{ font-size: .82rem; color: #5B6B67; line-height: 1.6; word-break: keep-all; }}
.hx-card .mi {{ color: var(--accent-deep); font-size: 1.05em; }}
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
.brand-tag {{ margin-top: .4rem; margin-bottom: 1rem; font-family: "Jua", sans-serif; font-size: 1.25rem; color: #26302D; }}   /* 아래 한 칸 띄움 */
.brand-tag span {{ font-family: "NanumSquareRound", "Pretendard", sans-serif; font-size: .78rem; font-weight: 700;
  letter-spacing: .14em; color: {MINT}; }}
/* 누르면 메인으로 가는 로고: 버튼이지만 바탕·테두리 없이 */
.st-key-home_brand button {{ background: none !important; border: 0 !important;
  box-shadow: none !important; padding: 0 !important; min-height: 0; transform: none !important; }}
/* 제목 로고: 버튼 바탕에 로고 그림을 깔고 글자는 숨긴다 (누르면 처음 화면으로) */
/* 로고 그림 아래 'ANIME POP-UP · CAFE · GOODS' 글씨까지 읽히게 로고 칸을 키운다 */
.st-key-home_brand button {{ width: 330px !important; height: 100px !important;
  background: url("app/static/logo_add.png") no-repeat left center / contain !important; }}
.st-key-home_brand button p {{ font-size: 0 !important; color: transparent !important; }}
/* 로고는 눌러도·커서를 올려도 바탕·그림자·밝기 변화 없이 그대로 (모바일 탭 하이라이트도 끈다) */
.st-key-home_brand button, .st-key-home_brand button:hover, .st-key-home_brand button:focus,
.st-key-home_brand button:active, .st-key-home_brand button:focus-visible {{ filter: none !important; box-shadow: none !important;
  outline: none !important; background-color: transparent !important; -webkit-tap-highlight-color: transparent; }}
@media (max-width: 640px) {{
  .st-key-home_brand button {{ width: 240px !important; height: 73px !important; }}
}}
/* 등록 화면 제목 (글자만, 누를 수 없음) */
.add-title {{ text-align: center; font-family: "Jua", sans-serif !important; font-size: 1.8rem; line-height: 1.6;
  color: #26302D; }}
.st-key-home_brand button:hover p {{ color: {MINT}; }}
</style>
"""

st.set_page_config(page_title="ANI:WHERE", page_icon=":material/map:", layout="wide")

store = Storage(worksheet="cafes")
reviews = Storage(worksheet="reviews", headers=review.HEADERS)
favs = Storage(worksheet="favorites", headers=favorite.HEADERS)
members = Storage(worksheet="members", headers=auth.HEADERS)
del_requests = Storage(worksheet="del_requests", headers=admin.REQ_HEADERS)      # 일반 회원의 삭제 요청
alert_rules = Storage(worksheet="alert_rules", headers=admin.RULE_HEADERS)       # 자동 알림 규칙 (관리자가 고침)
notices_store = Storage(worksheet="notices", headers=admin.NOTICE_HEADERS)       # 회원에게 가는 알림·공지
visits = Storage(worksheet="visits", headers=admin.VISIT_HEADERS)                # 회원이 접속한 날
# 실행 번호: 찜 정보를 한 번 그릴 때 한 번만 읽고, 다음 실행에서는 새로 읽게 한다
st.session_state["_run"] = st.session_state.get("_run", 0) + 1


def _fav_state() -> tuple[str, set[str], dict[str, int]]:
    """(나, 내가 찜한 카페들, 카페별 찜 수). 한 번 그릴 때 한 번만 읽도록 실행마다 새로 담아 둔다."""
    run = st.session_state.get("_run", 0)
    cached = st.session_state.get("_fav_cache")
    if cached and cached[0] == run:
        return cached[1]
    me = _fav_user()
    rows = favs.current_rows()
    state = (me, favorite.mine(rows, me), favorite.counts(rows))
    st.session_state["_fav_cache"] = (run, state)
    return state


def _heart(cafe_id: str, where: str, label_count: bool = False) -> None:
    """팔로우 버튼 (북마크 아이콘). 팔로우하면 포인트 색으로 채운 체크 북마크, 아니면 흰 바탕 북마크+.
    where 는 위치(w: 전체보기 카드, s: 반반 카드, d: 상세)."""
    me, mine, counts = _fav_state()
    on = str(cafe_id) in mine
    n = counts.get(str(cafe_id), 0)
    # 글자 대신 북마크 아이콘 (상세·리스트 카드 모두). 팔로우하면 체크된 북마크
    label = f"{n}" if label_count else ""
    icon = ":material/bookmark_added:" if on else ":material/bookmark_add:"
    # 누른 순간 콜백에서 저장하고 한 번만 다시 그린다 (st.rerun 으로 두 번 그리면 화면이 버벅이며 위로 튀었다)
    st.button(label, icon=icon, key=f"fav_{'on' if on else 'off'}_{where}_{cafe_id}",
              on_click=_toggle_fav, args=(str(cafe_id), me, not on))


def _need_login(msg: str) -> None:
    """로그인이 필요한 일을 손님이 눌렀을 때: 다음 그리기에서 로그인 화면으로 옮긴다 (콜백 안에서는 페이지를 못 옮긴다)."""
    st.session_state["_need_login"] = msg


def _login_gate(msg: str, key: str) -> bool:
    """손님이면 안내 + '로그인하기' 버튼을 그리고 True. 회원이면 False (그대로 진행)."""
    if _member():
        return False
    st.markdown(f'<div class="ntf-empty" style="padding:10px 2px">{escape(msg)}</div>', unsafe_allow_html=True)
    st.button("로그인하고 계속하기", icon=":material/login:", key=key, on_click=_need_login, args=(msg,))
    return True


def _toggle_fav(cafe_id: str, me: str, on: bool) -> None:
    if not _member():                       # 북마크는 회원만 (11/18 요청) → 로그인 화면으로
        _need_login("북마크는 로그인하면 쓸 수 있어요.")
        return
    try:
        favorite.toggle(favs, cafe_id, me, on)
    except StorageWriteError:      # 콜백 안의 오류는 페이지의 try 로 잡히지 않아서 여기서 따로 받는다
        st.session_state["flash"] = ("북마크를 저장하지 못했어요. 잠시 뒤 다시 눌러 주세요.", ":material/error:")
        return
    st.session_state.pop("_fav_cache", None)
    # 다시 그릴 때 화면 위에 토스트로 알린다 (page_map 의 flash)
    st.session_state["flash"] = (("북마크했어요. 내 캘린더에서 볼 수 있어요.", ":material/bookmark_added:") if on
                                 else ("북마크를 해제했어요.", ":material/bookmark_remove:"))
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


def _member() -> dict | None:
    """로그인한 회원의 최신 기록. 손님이면 None. 세션에 없으면 쿠키(aw_session)로 되살린다."""
    run = st.session_state.get("_run", 0)
    cached = st.session_state.get("_member_cache")
    if cached and cached[0] == run:
        return cached[1]
    key = st.session_state.get("member_key")
    if key is None and not st.session_state.get("_logged_out"):
        try:
            sess = auth.read_session(st.context.cookies.get(auth.COOKIE))
        except auth.AuthError:            # AUTH_SECRET 이 없으면 로그인 기능 자체가 꺼진 상태
            sess = None
        key = sess["k"] if sess else ""
        st.session_state["member_key"] = key
    row = auth.find(members, key) if key else None
    st.session_state["_member_cache"] = (run, row)
    if row and st.session_state.get("_visit_logged") != (key, TODAY.isoformat()):
        st.session_state["_visit_logged"] = (key, TODAY.isoformat())
        try:
            admin.log_visit(visits, str(key), TODAY)      # 일별 접속 회원 수 (관리자 '이용 지표')
        except Exception:                                   # 기록이 실패해도 화면은 그대로
            pass
    return row


def _fav_user() -> str:
    """북마크 주인: 회원이면 회원 번호, 손님이면 IP 해시."""
    row = _member()
    return f"m:{row['entry_id']}" if row else favorite.user_key(st.context.ip_address)


# 프로필 사진이 없을 때 보여 줄 기본 그림 (민트 동그라미 + 사람 모양). 파일 없이 화면에서만 쓴다
DEFAULT_AVATAR = ("data:image/svg+xml;utf8," + quote(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="32" fill="#DDF3EC"/>'
    '<circle cx="32" cy="25" r="11" fill="#7CCFB8"/><path d="M12 54c3-11 11-16 20-16s17 5 20 16" fill="#7CCFB8"/></svg>'))


def _avatar_url(value) -> str:
    """members.avatar → 화면 주소. 비었거나 'none' 이면 기본 그림."""
    v = auth.clean_avatar(value)
    if not v or v == "none":
        return DEFAULT_AVATAR
    if v.startswith("https://"):
        return v
    found = images.paths(v)
    return images.url(found[0]) if found else DEFAULT_AVATAR


def _avatar_img(value, size: int = 28, cls: str = "av") -> str:
    return (f'<img class="{cls}" src="{escape(_avatar_url(value))}" alt="" width="{size}" height="{size}" '
            f'referrerpolicy="no-referrer" onerror="this.src=\'{DEFAULT_AVATAR}\'">')


def _member_by_tag() -> dict[str, dict]:
    """글에 남은 이름 끝 '#m네 글자' → 그 회원의 지금 기록 (한 번 실행에 한 번 읽음).
    리뷰·수정 이력에 쓸 때의 닉네임이 아니라 회원이 지금 정해 둔 닉네임·사진을 보여 주려고 쓴다."""
    run = st.session_state.get("_run", 0)
    cached = st.session_state.get("_avatar_cache")
    if cached and cached[0] == run:
        return cached[1]
    out = {f'm{str(r["entry_id"])[:4]}': r for r in members.current_rows()}
    st.session_state["_avatar_cache"] = (run, out)
    return out


def _author(name) -> tuple[str, str]:
    """저장된 이름('닉네임#m1a2b') → (화면에 보일 닉네임, 프로필 사진 값).
    회원이면 지금 닉네임(바꿨으면 바뀐 이름), 탈퇴했거나 예전 손님 글이면 저장된 이름에서 꼬리표만 뺀 것."""
    text = str(name or "")
    tag = text.rsplit("#", 1)[-1] if "#" in text else ""
    row = _member_by_tag().get(tag) if tag.startswith("m") else None
    if row and str(row.get("nickname") or "").strip():
        return str(row["nickname"]).strip(), str(row.get("avatar") or "")
    if tag.startswith("m"):                 # 회원 글인데 지금 회원이 아님 = 탈퇴
        return auth.WITHDRAWN, ""
    return (text.rsplit("#", 1)[0].strip() or "익명"), ""


def _nick_only(name) -> str:
    """'닉네임#m1a2b' → 화면에 보일 닉네임 (꼬리표는 저장·내 글 확인에만 쓴다, 11/18 요청)."""
    return _author(name)[0]


def _auto_nick(seed: str) -> str:
    """닉네임을 비워 두면 '꾸밈말 + 캐릭터' 로 짓되, 이미 있는 닉네임·쓸 수 없는 말이면 다른 조합으로."""
    for i in range(30):
        cand = review.auto_nickname(f"{seed}{i or ''}")
        if not auth.validate_nick(cand) and not auth.nick_taken(members, cand):
            return cand
    return review.auto_nickname(f"{seed}{time.time()}")


def _me() -> str:
    """지금 접속한 사람의 이름. 회원이면 '닉네임#회원번호4자', 손님이면 IP 기반 자동 닉네임.
    리뷰 작성자·수정 이력에 남고, 끝의 #네 글자로 '내 글' 을 알아본다."""
    row = _member()
    return auth.display_name(row) if row else review.nickname_for(st.context.ip_address)


def _toast(msg: str, icon: str = ":material/check_circle:") -> None:
    """화면 가운데 잠깐 떴다 사라지는 알림 (사이트 디자인, 닫기 버튼 없음).

    Streamlit 의 st.toast 는 연달아 부르면 새 알림이 안 뜨기도 해서 직접 그린다.
    새 알림이 뜨면 이전 알림은 바로 사라지고 최신 알림만 보인다.
    """
    name = icon.removeprefix(":material/").removesuffix(":")
    payload = json.dumps({"msg": msg, "icon": name, "t": datetime.now().timestamp()})
    components.html("<script>window.parent.eval(" + json.dumps(_TOAST_JS.replace("__P__", payload)) + ");</script>",
                    height=0)


_TOAST_JS = """
(function () {
  const p = __P__;
  if (!document.getElementById('ani-toast-css')) {
    const css = document.createElement('style'); css.id = 'ani-toast-css';
    css.textContent = `
      .ani-toast { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(.96); opacity: 0;
        display: flex; align-items: center; gap: 10px; background: #fff; border: 1.5px solid #14b8a6; border-radius: 14px;
        box-shadow: 0 10px 28px rgba(20,184,166,.28); padding: 12px 18px; max-width: min(90vw, 420px); width: max-content;
        transition: opacity .18s ease, transform .18s ease; pointer-events: none; }
      .ani-toast.show { opacity: 1; transform: translate(-50%, -50%) scale(1); }
      .ani-toast .ic { font-family: "Material Symbols Rounded"; font-size: 1.4rem; line-height: 1; color: #14b8a6; }
      .ani-toast .tx { font-family: "NanumSquareRound", "Pretendard", sans-serif; font-weight: 700; font-size: .95rem; color: #1F2A27;
        word-break: keep-all; line-height: 1.4; }`;
    document.head.appendChild(css);
  }
  document.querySelectorAll('.ani-toast').forEach((t) => t.remove());   // 새 알림이 뜨면 이전 알림은 바로 지운다
  window.__aniToastZ = (window.__aniToastZ || 3000) + 1;
  const box = document.createElement('div'); box.className = 'ani-toast'; box.style.zIndex = window.__aniToastZ;
  const ic = document.createElement('span'); ic.className = 'ic'; ic.textContent = p.icon;
  const tx = document.createElement('span'); tx.className = 'tx'; tx.textContent = p.msg;
  box.append(ic, tx); document.body.appendChild(box);
  requestAnimationFrame(() => box.classList.add('show'));
  setTimeout(() => box.classList.remove('show'), 2800);
  setTimeout(() => box.remove(), 3100);
})();
"""


def _mi(name: str, cls: str = "") -> str:
    """이모지 대신 쓰는 아이콘 (Material Symbols). HTML 문자열 안에 넣는다. 크기·색은 둘러싼 글자를 따른다."""
    return f'<span class="mi {cls}" aria-hidden="true">{name}</span>'


def _period(r, fmt=lambda d: f"{d.month}.{d.day}", show_raw: bool = True) -> str:
    """기간 글자. 끝이 없는 팝업은 '11.20 ~ 상시', 기간을 못 읽은 팝업은 '기간 확인 필요 · 원문 ...'."""
    tags = _split(r.get("tags") or "") if not isinstance(r.get("tags"), list) else r.get("tags")
    if pdates.TAG_CHECK in tags:
        raw = pdates.raw_from_note(r.get("note"))
        return "기간 확인 필요" + (f" · 원문 '{raw}'" if show_raw and raw and not raw.startswith("(") else "")
    s_, e_ = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
    if not s_:
        return "기간 확인 필요"
    if not e_ or pdates.is_always(e_):
        return f"{fmt(s_)} ~ 상시"
    return f"{fmt(s_)} ~ {fmt(e_)}"


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


def _intro_body(text: str) -> str:
    """팝업 소개 본문 HTML. 줄 맨 앞의 '[배경]' 같은 소제목은 굵게 (나머지는 글자 그대로).
    빈 줄을 HTML 안에 그대로 두면 Streamlit 이 그 뒤를 따로 된 문단으로 처리해 간격이 크게 벌어져서,
    줄은 <br>, 빈 줄(문단 사이)은 작은 간격 칸으로 바꾼다."""
    parts = []
    for line in text.splitlines():
        if not line.strip():
            parts.append('<span class="dintro-gap"></span>')
            continue
        parts.append(re.sub(r"^\[([^\]]{1,40})\]", r'<b class="dintro-h">\1</b>', escape(line)) + "<br>")
    return "".join(parts)


@st.cache_data(ttl=86400, show_spinner=False)
def _link_status(urls: tuple[str, ...]) -> dict:
    """참고 웹사이트가 열리는지 (True/False/None). 같은 링크는 하루 동안 다시 확인하지 않는다."""
    try:
        return links_check.check_many(list(urls))
    except Exception:
        return {}


def _detail_info_html(current: dict) -> str:
    """상세 정보 블록: 위치(주소 + 지도에서 확인하기) · 일정 → 혜택(특전·굿즈·이벤트) → 참고 웹사이트 카드 → 팝업 소개."""
    # 위치 · 일정: 왼쪽에 항목 이름, 오른쪽에 내용 (오른쪽 정렬)
    addr = str(current.get("address") or "-")
    start, end = pd.to_datetime(current.get("start_date")), pd.to_datetime(current.get("end_date"))
    span = f"{_day(start, True)} - {_day(end, end.year != start.year)}"
    if pdates.is_always(end) or pdates.TAG_CHECK in _split(current.get("tags") or ""):
        span = _period(current, lambda d: _day(d, True))
    # 위치: 카페 이름을 크고 굵게 맨 위에, 그 아래 주소, 그 아래 '지도에서 확인하기'
    # '방문 전 확인' 회색 상자: 왼쪽 항목 이름(고정 폭), 오른쪽 내용(왼쪽 정렬)
    rows = (
        '<div class="dinfo-title">방문 전 확인</div>'
        # 위치 줄: 항목 이름 | 카페 이름·주소 | (같은 줄 오른쪽 끝) 지도에서 확인하기
        '<div class="drow"><div class="dlabel">위치</div><div class="dval">'
        f'<div class="dcafe">{escape(str(current.get("cafe_name") or "-"))}</div>'
        f'<div class="daddr">{escape(addr)}</div></div>'
        f'<a class="dbtn" href="{escape(_map_link(current))}" target="_blank" rel="noopener">{_mi("location_on")}지도에서 확인하기</a>'
        '</div>'
        f'<div class="drow"><div class="dlabel">일정</div><div class="dval">{escape(span)}</div></div>'
    )
    # 혜택: 특전 · 굿즈 · 이벤트마다 검은 알약 라벨, 그 옆에 회색 상자 안 목록 (라벨 | 내용 한 줄)
    groups = [("특전", _mi("redeem"), _split(current.get("perks") or "")),
              ("굿즈", _mi("shopping_bag"), _split(current.get("goods") or "")),
              ("이벤트", _mi("celebration"), _split(current.get("tags") or ""))]
    perks = "".join(
        f'<div class="dgroup"><span class="dpill">{name}</span><ul class="dbox">'
        + "".join(f"<li>{icon} {escape(x)}</li>" for x in items) + "</ul></div>"
        for name, icon, items in groups if items)
    perks_html = (f'<div class="dsec"><div class="dsec-title">혜택</div>{perks}</div>' if perks else
                  '<div class="dsec"><div class="dsec-title">혜택</div><div class="dnone">등록된 특전·굿즈가 없어요</div></div>')
    # 참고 웹사이트: 연회색 카드 (사이트 이름 + 주소 + ↗), 카드 전체를 누르면 새 탭
    # recal.kr 은 맨 뒤로 (다른 사이트가 없으면 그대로 첫 번째) — 예전에 가져온 행사에도 같은 순서로 보인다
    links = cafe.order_links(cafe.parse_links(current.get("links") or "")[0])
    link_html = ""
    if links:
        status = _link_status(tuple(links))      # 깨진 공식 링크는 '링크 확인 필요' (하루 동안 기억)
        cards = "".join(
            f'<a class="dlink{" broken" if status.get(u) is False else ""}" href="{escape(u)}" target="_blank" rel="noopener">'
            f'<div class="dlink-text"><div class="dlink-title">{escape(_site_name(u))}'
            + (f' <span class="dlink-warn">{_mi("link_off")} 링크 확인 필요</span>' if status.get(u) is False else "")
            + f'</div><div class="dlink-url">{escape(u)}</div></div><span class="dlink-go">↗</span></a>'
            for u in links)
        link_html = f'<div class="dsec"><div class="dsec-title">참고 웹사이트</div>{cards}</div>'
    # 팝업 소개: 쓴 글(간편등록은 공지)을 줄바꿈 그대로. 없으면 칸을 만들지 않는다
    intro = str(current.get("intro") or "").strip()
    src = str(current.get("intro_src") or "").strip()
    src_btn = (f'<a class="dsrc" href="{escape(src)}" target="_blank" rel="noopener">'
               f'{_mi("open_in_new")}출처 보기</a>' if src.startswith(("http://", "https://")) else "")
    # 출처 보기는 소개 상자 안 오른쪽 맨 아래
    src_foot = f'<div class="dintro-foot">{src_btn}</div>' if src_btn else ""
    intro_html = (f'<div class="dsec"><div class="dsec-title">팝업 소개</div>'
                  f'<div class="dintro">{_intro_body(intro)}{src_foot}</div></div>' if intro else "")
    return f'<div class="dinfo">{rows}</div><div class="dband"></div>{perks_html}{link_html}{intro_html}'


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
           + f'<span class="dregion" style="color:{color}">{_mi("location_on") + escape(area) if area else ""}</span>'
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
    tab_review, tab_edit = st.tabs([f":material/chat_bubble: 리뷰 {n}", ":material/edit: 수정하기"], key=f"detail_tabs_{entry_id}",
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
    if _login_gate("리뷰는 로그인하면 쓸 수 있어요.", f"lg_rv_{cafe_id}_{parent_id}"):
        return
    slot = f"rv_{cafe_id}_{parent_id or 'top'}"
    n = st.session_state.get(f"{slot}_n", 0)
    kind = ""
    nick = _me()
    # 닉네임 → 종류 → 내용 순으로 한 줄씩, 같은 왼쪽 선에 맞춰 둔다
    me_row = _member() or {}
    st.markdown(f'<div class="rv-me">{_avatar_img(me_row.get("avatar"), 28, "rv-av")}<b>{escape(_nick_only(nick))}</b></div>',
                unsafe_allow_html=True)
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
    # 사진 첨부 (선택, 원글만 — 답글 칸은 가볍게 둔다). 처음엔 작은 '사진 첨부' 버튼만, 누르면 올리는 칸이 열린다.
    # 저장은 등록을 누를 때 한다
    photos = []
    if not parent_id:
        open_key = f"{slot}_pic_open_{n}"
        opened = st.session_state.get(open_key, False)
        # 열고 나면 버튼은 감추고 올리는 칸만 둔다
        if not opened:
            st.button("+ 사진 첨부", key=f"{slot}_pic_btn_{n}", type="tertiary",
                      on_click=lambda: st.session_state.update({open_key: True}))
        else:
            photos = list(st.file_uploader(
                f"최대 {review.MAX_IMAGES}장 · 한 장 {review.IMAGE_MB}MB", type=images.TYPES,
                accept_multiple_files=True, key=f"{slot}_img_{n}") or [])
    if len(photos) > review.MAX_IMAGES:
        st.caption(f":red[사진은 {review.MAX_IMAGES}장까지 올릴 수 있어요. 앞의 {review.MAX_IMAGES}장만 올라갑니다.]")
        photos = photos[:review.MAX_IMAGES]
    heavy = [p.name for p in photos if images.too_big(p.getvalue(), review.IMAGE_MB)]
    if heavy:
        st.caption(f":red[{review.IMAGE_MB}MB 를 넘는 사진은 올릴 수 없어요: {', '.join(heavy)}]")
        bad = True

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
        # 다녀온 후기는 별점만 골라도, 사진만 올려도 등록할 수 있다 (내용은 비워도 된다)
        v = review.validate(body, nick, allow_empty=kind == review.RATED_KIND and (rating is not None or bool(photos)))
        if not v.ok:
            for err in v.errors:
                st.error(err)
            return
        try:
            saved = [images.save(p.name, p.getvalue()) for p in photos]
        except ValueError as err:
            st.error(str(err))
            return
        reviews.append(review.to_row(cafe_id, body, nick, kind or "", parent_id, rating=rating, images=saved))
        st.session_state[f"{slot}_n"] = n + 1
        st.session_state["flash"] = "답글을 남겼습니다." if parent_id else "리뷰를 남겼습니다."
        st.rerun()


# 리뷰 종류마다 배지 색을 달리한다 (기타는 회색)
KIND_COLORS = {"다녀온 후기": "green", "기대평": "blue", "기타": "gray"}


@st.dialog("삭제 요청")
def delete_request_dialog(target_type: str, target_id: str, title: str) -> None:
    """일반 회원이 게시글 삭제를 요청한다. 관리자가 '관리자 > 삭제 요청'에서 승인/거부하고 결과는 알림으로 간다."""
    st.markdown(f"**{escape(admin.TARGET_LABEL.get(target_type, '게시글'))}** · {escape(title[:60])}")
    reason = st.text_area("삭제를 요청하는 이유", key=f"dr_reason_{target_id}", max_chars=admin.MAX_REASON,
                          placeholder="예: 잘못된 정보예요 / 광고·도배 글이에요 / 이미 끝난 행사예요")
    if st.button("요청 보내기", type="primary", width="stretch", key=f"dr_send_{target_id}"):
        me = _member()
        errors = admin.validate_reason(reason)
        if not me:
            errors = ["로그인한 회원만 삭제를 요청할 수 있어요."]
        elif admin.pending_for(del_requests.current_rows(), target_id, str(me["entry_id"])):
            errors = ["이 글에 보낸 요청이 아직 처리 중이에요."]
        if errors:
            st.warning(errors[0], icon=":material/error:")
            return
        admin.request_delete(del_requests, target_type, target_id, title, reason, str(me["entry_id"]), _me())
        st.session_state["flash"] = ("삭제 요청을 보냈어요. 처리 결과는 알림으로 알려 드려요.", ":material/check_circle:")
        st.rerun()


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
        if row and _is_admin():
            reviews.soft_delete(entry_id)       # 저장소는 지우지 않고 '삭제됨' 행을 쌓는다
            st.session_state["flash"] = "삭제했습니다."
        else:
            st.session_state["flash"] = "게시글 삭제는 관리자만 할 수 있어요."
        st.rerun()


def _review_card(r: dict, reply: bool = False, replies: int = 0) -> None:
    who, pic = _author(r.get("nickname"))
    head = _avatar_img(pic, 26, "rv-av") + f" **{_plain(who)}**"
    if r.get("kind"):
        head = f":{KIND_COLORS.get(r['kind'], 'gray')}-badge[{r['kind']}] " + head
    if reply:
        head = ":gray-badge[답글] " + head
    eid = str(r["entry_id"])
    when = f" · :gray[{_when(r.get('updated_at'))}]"
    if int(r.get("revision") or 1) > 1:
        when += " :gray[(수정됨)]"
    # 내가 쓴 글(접속 IP 로 정해진 닉네임이 같은 글)에만 '⋯' 를 보여 주고, 누르면 수정·삭제를 고른다
    mine = bool(_member()) and review.can_delete(r, _me())
    is_admin = _is_admin()
    member = bool(_member())
    if mine or is_admin or member:
        # 수정은 쓴 사람(회원)만, 삭제는 관리자만 (11/18 권한)
        t, b = st.columns([6, 1], vertical_alignment="center")
        t.markdown(head + when, unsafe_allow_html=True)
        with b.popover("⋯", key=f"rv_more_{eid}", type="tertiary"):
            if mine and st.button("수정", key=f"rv_edit_{eid}", width="stretch"):
                st.session_state["rv_editing"] = eid
                st.rerun()
            if is_admin and st.button("삭제 (관리자)", key=f"rv_del_{eid}", width="stretch"):
                confirm_review_delete(eid, replies)
            if member and not is_admin and st.button("삭제 요청", key=f"rv_req_{eid}", width="stretch"):
                delete_request_dialog("review", eid, str(r.get("body") or r.get("kind") or "리뷰")[:40])
    else:
        st.markdown(head + when, unsafe_allow_html=True)
    # 다녀온 후기 별점: 머리 줄 다음 줄에, 내용보다 위에 크게
    rated = review.stars(r.get("rating")) if r.get("kind") == review.RATED_KIND else ""
    if rated and not (mine and st.session_state.get("rv_editing") == eid):
        st.markdown(f'<div class="rv-stars">{rated}</div>', unsafe_allow_html=True)
    if mine and st.session_state.get("rv_editing") == eid:
        _review_edit_box(r)
    elif str(r.get("body") or "").strip():
        st.markdown(_plain(r.get("body", "")))
    pics = images.paths(r.get("images"))
    if pics:
        st.markdown('<div class="rv-pics">' + "".join(
            f'<a href="{images.url(p)}" target="_blank" rel="noopener"><img src="{images.url(p)}" alt="리뷰 사진"/></a>'
            for p in pics) + "</div>", unsafe_allow_html=True)


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
        nick = _me()
        current = next((x for x in reviews.current_rows() if str(x["entry_id"]) == eid), None)
        # 저장하는 순간에도 내 글인지 한 번 더 확인한다
        if not current or not review.can_delete(current, nick):
            st.error("내가 쓴 글만 수정할 수 있어요.")
            return
        v = review.validate(body, nick, allow_empty=kind == review.RATED_KIND and rating is not None)
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


def _review_lightbox() -> None:
    """리뷰 사진 확대 보기. 바깥 페이지에서 직접 돌아서(eval), 사진을 누르면 새 탭 대신 팝업으로 연다."""
    components.html(f"<script>window.parent.eval({json.dumps(_REVIEW_LIGHTBOX_JS)});</script>", height=0)


_REVIEW_LIGHTBOX_JS = """
(function () {
  if (window.__aniLightbox) return;
  window.__aniLightbox = true;
  const css = document.createElement('style');
  css.textContent = `
    .ani-lb { position: fixed; inset: 0; z-index: 3000; background: rgba(15,20,19,.86); display: flex;
      align-items: center; justify-content: center; overflow: hidden; touch-action: none; }
    .ani-lb img { max-width: 92vw; max-height: 86vh; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,.45);
      transform-origin: center center; transition: transform .15s ease; cursor: zoom-in; user-select: none; -webkit-user-drag: none; }
    .ani-lb.zoomed img { cursor: grab; transition: none; }
    .ani-lb button { position: absolute; border: 0; cursor: pointer; background: rgba(255,255,255,.95); color: #1F2A27;
      width: 42px; height: 42px; border-radius: 50%; font-size: 22px; line-height: 42px; text-align: center; padding: 0;
      box-shadow: 0 4px 14px rgba(0,0,0,.25); }
    .ani-lb button:hover { background: #fff; color: #0d9488; }
    .ani-lb .x { top: 18px; right: 18px; font-size: 26px; }
    .ani-lb .tools { position: absolute; bottom: 22px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; }
    .ani-lb .tools button { position: static; }
    .ani-lb .prev { left: 18px; top: 50%; transform: translateY(-50%); }
    .ani-lb .next { right: 18px; top: 50%; transform: translateY(-50%); }
    .ani-lb .count { position: absolute; top: 26px; left: 50%; transform: translateX(-50%); color: #fff; font-weight: 700;
      font-size: 14px; background: rgba(0,0,0,.35); padding: 3px 10px; border-radius: 999px; }`;
  document.head.appendChild(css);

  const open = (urls, start) => {
    let i = start, scale = 1, tx = 0, ty = 0, drag = null;
    const box = document.createElement('div'); box.className = 'ani-lb';
    const img = document.createElement('img'); img.alt = '리뷰 사진';
    const btn = (cls, text, label) => { const b = document.createElement('button'); b.className = cls; b.textContent = text; b.setAttribute('aria-label', label); return b; };
    const x = btn('x', '×', '닫기');
    const tools = document.createElement('div'); tools.className = 'tools';
    const zin = btn('in', '+', '확대'), zout = btn('out', '−', '축소'), reset = btn('reset', '⟲', '원래 크기');
    tools.append(zout, reset, zin);
    const count = document.createElement('div'); count.className = 'count';
    const prev = btn('prev', '‹', '이전 사진'), next = btn('next', '›', '다음 사진');
    box.append(img, x, tools);
    if (urls.length > 1) box.append(prev, next, count);
    const apply = () => { img.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`; box.classList.toggle('zoomed', scale > 1); };
    const zoom = (k) => { scale = Math.min(5, Math.max(1, scale * k)); if (scale === 1) { tx = 0; ty = 0; } apply(); };
    const show = () => { img.src = urls[i]; scale = 1; tx = 0; ty = 0; apply(); count.textContent = `${i + 1} / ${urls.length}`; };
    const close = () => { box.remove(); document.removeEventListener('keydown', onKey, true); };
    const onKey = (e) => { if (e.key === 'Escape') close(); if (e.key === 'ArrowLeft') { prev.click(); } if (e.key === 'ArrowRight') { next.click(); } };
    x.onclick = close;
    zin.onclick = (e) => { e.stopPropagation(); zoom(1.4); };
    zout.onclick = (e) => { e.stopPropagation(); zoom(1 / 1.4); };
    reset.onclick = (e) => { e.stopPropagation(); scale = 1; tx = 0; ty = 0; apply(); };
    prev.onclick = (e) => { e.stopPropagation(); i = (i - 1 + urls.length) % urls.length; show(); };
    next.onclick = (e) => { e.stopPropagation(); i = (i + 1) % urls.length; show(); };
    // 사진 밖(어두운 곳)을 누르면 닫고, 사진을 누르면 확대 ↔ 원래 크기
    box.onclick = (e) => { if (e.target === box) close(); };
    img.onclick = (e) => { e.stopPropagation(); if (drag && drag.moved) return; if (scale > 1) { scale = 1; tx = 0; ty = 0; apply(); } else zoom(2); };
    box.addEventListener('wheel', (e) => { e.preventDefault(); zoom(e.deltaY < 0 ? 1.15 : 1 / 1.15); }, { passive: false });
    // 확대했을 때 끌어서 보기 (마우스·손가락)
    img.addEventListener('pointerdown', (e) => { if (scale <= 1) return; drag = { x: e.clientX - tx, y: e.clientY - ty, moved: false }; img.setPointerCapture(e.pointerId); });
    img.addEventListener('pointermove', (e) => { if (!drag) return; tx = e.clientX - drag.x; ty = e.clientY - drag.y; drag.moved = true; apply(); });
    img.addEventListener('pointerup', () => { setTimeout(() => { drag = null; }, 0); });
    document.addEventListener('keydown', onKey, true);
    document.body.appendChild(box);
    show();
  };

  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('.rv-pics a');
    if (!a) return;
    e.preventDefault();
    const links = [...a.closest('.rv-pics').querySelectorAll('a')];
    open(links.map((l) => l.href), links.indexOf(a));
  }, true);
})();
"""


def _avg_rating_html(avg: float, n: int) -> str:
    """평균 별점 요약: 큰 숫자 + 평균만큼 채운 별 다섯 개 + '다녀온 후기 N개 평균'."""
    pct = max(0.0, min(100.0, avg / 5 * 100))
    return (f'<div class="rv-avg"><span class="rv-avg-num">{avg:.1f}</span>'
            f'<span class="rv-avg-stars" aria-label="5점 만점에 {avg:.1f}점">'
            f'<span class="rv-avg-bg">★★★★★</span><span class="rv-avg-fg" style="width:{pct:.0f}%">★★★★★</span></span>'
            f'<span class="rv-avg-cnt">다녀온 후기 {n}개 평균</span></div>')


def render_reviews(cafe_id: str) -> None:
    _review_lightbox()      # 리뷰 사진을 누르면 확대 보기 팝업
    # 맨 위 리뷰 쓰기: 닉네임·종류·별점·입력칸·리뷰 등록 버튼을 처음부터 펼쳐 둔다. 그 아래에 리뷰를 보여 준다
    with st.container(border=True, key=f"rvbox_{cafe_id}"):
        _write_box(cafe_id)

    threads = review.threads(reviews.current_rows(), cafe_id)
    if not threads:
        st.caption("아직 리뷰가 없습니다. 다녀온 후기나 기대하는 점을 처음으로 남겨 보세요.")
        return

    # 다녀온 후기에 별점이 있으면 목록 위에 평균 별점
    avg, n_rated = review.average_rating(threads)
    if n_rated:
        st.markdown(_avg_rating_html(avg, n_rated), unsafe_allow_html=True)

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
        if st.button("삭제", type="primary", width="stretch", key=f"delete_ok_{entry_id}") and _is_admin():
            store.soft_delete(entry_id, extra={"source": "지도에서 내림", "editor": _me()})
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
        note.caption(f":material/delete: {len(removed)}장 삭제 예정 · **수정 저장**을 눌러야 반영돼요.")
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
        st.caption(":material/check_circle: 새 포스터로 변경돼요. **수정 저장**을 눌러야 반영돼요.")
        st.image(poster[1], width=160)
    result = (([poster] + keep[1:]) if poster else keep) + [(f.name, f.getvalue()) for f in extras or []]
    if len(result) - 1 > images.MAX_EXTRAS:
        errors.append(f"추가 이미지는 {images.MAX_EXTRAS}장까지 둘 수 있습니다. 몇 장 지워 주세요.")
    for e in errors:
        st.error(e)
    return result, errors


def _clear_buttons() -> None:
    """메인 검색칸·수정하기·등록하기 글자 입력칸 오른쪽 안에 × 를 붙여, 누르면 내용을 한 번에 비운다 (내용이 있을 때만 보임)."""
    components.html(f"<script>window.parent.eval({json.dumps(_CLEAR_JS)});</script>", height=0)


_CLEAR_JS = """
(function () {
  if (window.__aniClear) return;
  window.__aniClear = true;
  // 위젯 키로 고른다. 수정하기: 카페명·주소·특전·굿즈·참고 웹사이트 / 등록하기: 단계별(cafe_·wiz_ 주소)·간편등록(quick_)
  // 메인: 상단 검색칸(f_query) — 지우면 바로 검색 결과에 반영(입력칸을 벗어나 값을 확정)한다
  const SEL = ['name_', 'edit_', 'perks_', 'goods_', 'links_', 'intro_', 'cafe_', 'wiz_', 'quick_', 'f_query']
    .map((k) => `[class*="st-key-${k}"] input[type="text"], [class*="st-key-${k}"] textarea`).join(', ');
  const css = document.createElement('style');
  css.textContent = `
    .ani-clear { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); z-index: 2;
      width: 22px; height: 22px; border: 0; border-radius: 50%; padding: 0; cursor: pointer;
      background: #E6ECEA; color: #5B6B67; display: none; align-items: center; justify-content: center; }
    .ani-clear.on { display: flex; }
    .ani-clear:hover { background: #14b8a6; color: #fff; }
    .ani-clear svg { width: 12px; height: 12px; }
    .ani-clear.ta { top: 10px; transform: none; }
    .ani-has-clear input, .ani-has-clear textarea { padding-right: 36px !important; }`;
  document.head.appendChild(css);
  const setValue = (el, v) => {
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v);
    el.dispatchEvent(new Event('input', { bubbles: true }));
  };
  const attach = (el) => {
    if (el.dataset.aniClear) return;
    el.dataset.aniClear = '1';
    const box = el.closest('[data-baseweb="input"], [data-baseweb="textarea"]') || el.parentElement;
    box.style.position = 'relative';
    box.classList.add('ani-has-clear');
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'ani-clear' + (el.tagName === 'TEXTAREA' ? ' ta' : '');
    b.setAttribute('aria-label', '입력 내용 지우기');
    b.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    const sync = () => b.classList.toggle('on', !!el.value);
    // 누르는 순간 입력칸이 포커스를 잃지 않게(mousedown 막기) 하고, 비운 뒤 바로 다시 입력할 수 있게 포커스를 둔다
    b.addEventListener('mousedown', (e) => e.preventDefault());
    const commit = !!el.closest('.st-key-f_query');
    b.addEventListener('click', (e) => {
      e.preventDefault(); e.stopPropagation(); setValue(el, ''); sync();
      if (commit) { el.focus(); el.blur(); } else el.focus();
    });
    el.addEventListener('input', sync);
    box.appendChild(b);
    sync();
    // 초기화 버튼 등으로 값이 바뀌어도 × 가 맞게 보이도록 가끔 다시 확인
    setInterval(sync, 700);
  };
  const scan = () => document.querySelectorAll(SEL).forEach(attach);
  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  scan();
})();
"""


def _keep_notion(note: str, current: dict) -> str:
    """고쳐 저장해도 Notion 에서 가져온 표시('| notion:…')는 남긴다 (다음 가져오기 때 같은 팝업으로 알아보게)."""
    m = re.search(r"\|\s*notion:\S+", str(current.get("note") or ""))
    out = f"{note} {m.group(0)}" if m else note
    raw = pdates.raw_from_note(current.get("note"))
    return f"{out} | {pdates.RAW_MARK}{raw}" if raw else out


def render_edit(current: dict) -> None:
    entry_id = str(current["entry_id"])
    if _login_gate("팝업 정보 수정은 로그인하면 할 수 있어요.", f"lg_ed_{entry_id}"):
        return
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
    old_start, old_end = pd.to_datetime(current["start_date"]).date(), pd.to_datetime(current["end_date"]).date()
    was_always = pdates.is_always(old_end)
    always = st.checkbox("종료일 없음 (상시)", value=was_always, key=f"always_{k}")
    with d2:
        new_end = st.date_input("종료", value=(old_start + timedelta(days=30)) if was_always else old_end,
                                key=f"end_{k}", disabled=always)
    if always:
        new_end = pdates.ALWAYS_END
    old_flags = [t for t in _split(current.get("tags") or "") if t in cafe.PERIOD_TAGS]
    if pdates.TAG_CHECK in old_flags:
        raw = pdates.raw_from_note(current.get("note"))
        st.warning("기간을 정확히 읽지 못한 팝업이에요" + (f" (원문: '{raw}')" if raw and not raw.startswith("(") else "")
                   + ". 공식 공지를 보고 시작·종료일을 고쳐 주세요.", icon=":material/event_busy:")
    new_perks = st.text_input("특전", value=str(current.get("perks", "")), key=f"perks_{k}",
                              help="쉼표로 구분")
    new_goods = st.text_input("굿즈", value=str(current.get("goods", "")), key=f"goods_{k}",
                              help="쉼표로 구분")
    new_tags = st.pills("이벤트 추가 정보", cafe.EVENT_TAGS, selection_mode="multi",
                        default=[t for t in _split(current.get("tags") or "") if t in cafe.EVENT_TAGS],
                        key=f"tags_{k}")
    new_links, bad_links = _links_field("\n".join(cafe.parse_links(current.get("links") or "")[0]),
                                        key=f"links_{k}")
    new_intro = _intro_field(str(current.get("intro") or ""), key=f"intro_{k}")
    new_images, img_errors = _edit_images(current, k)
    _clear_buttons()
    bad = _block_sensitive(new_name, new_addr, new_perks, new_goods, new_intro)
    # 수정 저장 · 지도에서 내리기를 한 줄에 (가로 묶음이라 모바일에서도 세로로 쌓이지 않는다)
    with st.container(horizontal=True, key=f"edit_btns_{k}"):
        submitted = st.button("수정 저장", type="primary", width="stretch", key=f"save_{k}",
                              disabled=bad or bool(img_errors) or bad_links)
        if _is_admin() and st.button("지도에서 내리기 (관리자)", width="stretch", key=f"delete_{k}"):
            confirm_delete(entry_id)
        if not _is_admin() and st.button("삭제 요청", width="stretch", key=f"dreq_{k}"):
            delete_request_dialog("cafe", entry_id, f'{current.get("work") or ""} · {current.get("cafe_name") or ""}')

    if submitted:
        entry = CafeEntry(
            cafe_name=new_name, work=new_work, characters=new_chars, address=new_addr,
            start_date=new_start, end_date=new_end,
            perks=_split(new_perks), goods=_split(new_goods),
            confidence="high",
        )
        # 기간 표시: 상시면 '상시', 사람이 기간을 고쳤으면 '기간 확인 필요' 를 지운다 (안 고쳤으면 그대로)
        dates_changed = (new_start, new_end) != (old_start, old_end)
        new_tags = list(new_tags) + ([pdates.TAG_ALWAYS] if always else []) \
            + ([pdates.TAG_CHECK] if pdates.TAG_CHECK in old_flags and not dates_changed else [])
        v = guard.validate_cafe(entry, today=TODAY)
        g = locate(entry.address, picked)
        if not g.ok:
            v.fail(g.note)
        if v.ok:
            # 새로 올린 파일만 저장한다. 지운 이미지 파일은 남겨 둔다 (되돌리기가 옛 행을 쓸 수 있다)
            saved = [name if data is None else images.save(name, data) for name, data in new_images]
            store.append(cafe.entry_to_row(entry, g.lat, g.lng, source="직접 수정", note=_keep_notion(g.badge, current), editor=_me(), intro=new_intro,
                                           intro_src=str(current.get("intro_src") or "") if new_intro.strip() else "",
                                           images=saved, tags=new_tags, links=new_links),
                         entry_id=entry_id)
            # 저장해도 상세에 그대로 머물고, 맨 위로 올려 바뀐 내용을 처음부터 보여 준다
            st.session_state["flash"] = "수정했습니다."
            st.session_state["scroll_top"] = True
            st.rerun()
        for err in v.errors:
            st.error(err)

    with st.expander("수정 이력"):
        history = [r for r in store.all_rows() if str(r["entry_id"]) == entry_id]
        history.sort(key=lambda r: int(r["revision"]), reverse=True)
        # 기록 하나가 카드 하나. 지금 것 말고는 카드 안에 '이 버전으로 돌아가기' 버튼을 둔다
        with st.container(key=f"hx_{entry_id}"):
            for i, r in enumerate(history):
                rev = int(r["revision"])
                older = history[i + 1] if i + 1 < len(history) else None
                with st.container(key=f"{'hxnow' if i == 0 else 'hxi'}_{entry_id}_{rev}"):
                    st.markdown(_history_card_html(r, older, now=i == 0), unsafe_allow_html=True)
                    if i > 0 and r.get("status") != "deleted" and st.button(
                            "이 버전으로 돌아가기", icon=":material/restore:", type="tertiary",
                            key=f"restore_{entry_id}_{rev}"):
                        store.restore(entry_id, rev, extra={"source": f"{rev}번째로 되돌리기", "editor": _me()})
                        st.session_state["flash"] = (f"{rev}번째 버전으로 되돌렸어요.", ":material/restore:")
                        st.session_state["scroll_top"] = True
                        st.rerun()


# 수정 이력에 보이는 '방법' 이름과 아이콘. 저장된 값은 그대로 두고(append-only) 보여 줄 때만 바꾼다
_SOURCE_VIEW = {
    "노션 자동 수집": ("AI 자동 수집", "auto_awesome"),
    "AI 자동 수집": ("AI 자동 수집", "auto_awesome"),
    "직접 등록": ("직접 등록", "add_circle"),
    "직접 수정": ("직접 수정", "edit"),
    "간편 등록": ("간편 등록", "edit_note"),
    "붙여넣기": ("붙여넣기", "content_paste"),
    "되돌리기": ("되돌리기", "undo"),
    "지도에서 내림": ("지도에서 내림", "visibility_off"),
    "기간 종료": ("기간 종료", "event_busy"),
    "샘플": ("샘플", "science"),
}
# 바로 앞 기록과 비교해서 '(이전) → (이후)' 로 보여 줄 칸
_HISTORY_FIELDS = [("status", "상태"), ("cafe_name", "카페명"), ("work", "작품"), ("characters", "캐릭터"),
                   ("address", "주소"), ("start_date", "시작일"), ("end_date", "종료일"), ("perks", "특전"),
                   ("goods", "굿즈"), ("tags", "이벤트"), ("images", "사진"), ("links", "참고 웹사이트"),
                   ("intro", "팝업 소개"), ("intro_src", "소개 출처")]


def _editor(r: dict) -> str:
    """기록을 남긴 사람. editor 칸이 생기기 전 기록은 방법으로 짐작한다."""
    who = str(r.get("editor") or "").strip()
    if who:
        return who
    return {"노션 자동 수집": "AI", "AI 자동 수집": "AI", "샘플": "샘플"}.get(str(r.get("source") or ""), "닉네임 기록 전")


def _history_value(col: str, value) -> str:
    """바뀐 칸의 값을 짧게: 사진은 장 수, 참고 웹사이트는 사이트 이름, 긴 글은 줄여서."""
    text = str(value or "").strip()
    if col == "status":
        return {"active": "지도에 표시", "deleted": "지도에서 내림"}.get(text, text or "없음")
    if not text:
        return "없음"
    if col == "images":
        return f"{len([x for x in text.split(',') if x.strip()])}장"
    if col == "links":
        return ", ".join(_site_name(u) for u in text.split())
    if col in ("start_date", "end_date"):
        return text[:10].replace("-", ".")
    return text if len(text) <= 60 else text[:60] + "…"


def _image_changes(old, new) -> list[tuple[str, str, str]]:
    """사진 칸이 어떻게 바뀌었는지 [(포스터|이미지, add|del|chg, '포스터 삭제' 같은 글)]. 첫 장이 포스터, 나머지가 이미지."""
    before, after = images.split(old), images.split(new)
    p0, p1 = (before[:1] or [""])[0], (after[:1] or [""])[0]
    out = []
    if p0 != p1:
        if p0 and (not p1 or (p1 in before and p0 not in after)):
            # 포스터를 지우면 다음 이미지가 포스터 자리로 올라온다 → 그래도 '포스터 삭제'
            out.append(("포스터", "del", "포스터 삭제"))
        elif p1 and not p0:
            out.append(("포스터", "add", "포스터 추가"))
        else:
            out.append(("포스터", "chg", "포스터 변경"))
    # 포스터 자리로 옮겨 간(또는 포스터였다 내려온) 파일은 이미지 추가·삭제로 세지 않는다
    moved = {p0, p1} - {""}
    gone = [x for x in before[1:] if x not in after and x not in moved]
    came = [x for x in after[1:] if x not in before and x not in moved]
    if gone:
        out.append(("이미지", "del", f"이미지 {len(gone)}장 삭제"))
    if came:
        out.append(("이미지", "add", f"이미지 {len(came)}장 추가"))
    if not out:
        out.append(("이미지", "chg", "이미지 순서 변경"))
    return out


def _history_card_html(r: dict, older: dict | None, now: bool) -> str:
    """수정 이력 카드 안쪽. 처음 기록만 카페·기간·주소를 다 보여 주고,
    그다음 기록부터는 바로 앞 기록과 달라진 칸만 '(이전) → (이후)' 로 보여 준다."""
    source = str(r.get("source") or "")
    label, icon = _SOURCE_VIEW.get(source, (source or "기록", "undo" if source.endswith("되돌리기") else "history"))
    when = pd.to_datetime(r["updated_at"], utc=True).tz_convert("Asia/Seoul").strftime("%Y.%m.%d %H:%M")
    if older is None:
        period = _period(r, lambda d: f"{d:%Y.%m.%d}")
        body = (f'<div class="hx-chg">처음 등록</div>'
                f'<div class="hx-meta">{_mi("local_cafe")}{escape(str(r.get("cafe_name") or "-"))}'
                f' · {escape(str(r.get("work") or "-"))}</div>'
                f'<div class="hx-meta">{_mi("calendar_month")}{period}</div>'
                f'<div class="hx-meta">{_mi("location_on")}{escape(str(r.get("address") or "-"))}</div>')
    else:
        rows = []
        for col, name in _HISTORY_FIELDS:
            if str(r.get(col) or "") == str(older.get(col) or ""):
                continue
            if col == "images":
                # 사진은 '사진 1장 → 2장' 대신 포스터·이미지 중 무엇을 지우고 넣었는지로
                rows += [f'<div class="hx-diff"><span class="hx-k">{"포스터" if what == "포스터" else "이미지"}</span>'
                         f'<span class="hx-act {kind}">{escape(text)}</span></div>'
                         for what, kind, text in _image_changes(older.get(col), r.get(col))]
                continue
            a, b = _history_value(col, older.get(col)), _history_value(col, r.get(col))
            rows.append(f'<div class="hx-diff"><span class="hx-k">{name}</span>'
                        f'<span class="hx-old">{escape(a)}</span><span class="hx-arrow">{_mi("arrow_forward")}</span>'
                        f'<span class="hx-new">{escape(b)}</span></div>')
        body = "".join(rows) or '<div class="hx-meta">바뀐 내용 없음</div>'
    return (f'<div class="hx-card">'
            f'<div class="hx-top"><b>{int(r["revision"])}번째</b><span class="hx-when">{when}</span>'
            + ('<span class="hx-now">지금</span>' if now else "")
            + f'<span class="hx-src">{_mi(icon)}{escape(label)}</span></div>'
            f'<div class="hx-who">{_mi("person")}{escape(_nick_only(_editor(r)))}</div>'
            f'{body}</div>')


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
    flags = [t for t in all_tags if t in (pdates.TAG_ALWAYS, pdates.TAG_CHECK)]
    all_tags = [t for t in all_tags if t not in flags]
    tags = [f'<span class="chip {"warn" if t == pdates.TAG_CHECK else "tag"}">{escape(t)}</span>' for t in flags] if full else []
    tags += [f'<span class="chip tag">{escape(t)}</span>' for t in (all_tags if full else all_tags[:2])]
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
        line(_mi("theater_comedy"), "캐릭터", r.get("characters"))
        + line(_mi("location_on"), "주소", r.get("address"))
        + (f'<div class="m"><b>{_mi("redeem")} 특전</b><ul>{perks}</ul></div>' if perks else "")
        + (f'<div class="m"><b>{_mi("sell")} 이벤트 · 굿즈</b><div class="chips">{_chips(r, full=True)}</div></div>'
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
<div class="pcard" style="background-image:url('{_poster_url(r.get("images"))}'), url('{images.DEFAULT_POSTER_URL}')">
  {_area_badge(r.get("address"), cls="area")}
  <span class="state">{escape(label)}</span>
  <div class="info">
    <div class="t">{escape(str(r['work']))}</div>
    <div class="s">{_mi("local_cafe")}{escape(str(r['cafe_name']))}</div>
    <div class="d"><span class="d-long">{escape(_period(r, lambda d: f"{d:%m월 %d일}", show_raw=False))}</span><span class="d-short">{escape(_period(r, lambda d: f"{d:%m/%d}", show_raw=False))}</span></div>
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
    # 리스트 전체보기 ↔ 지도보기 전환은 정렬(최신순) 칸 위 오른쪽 끝의 아이콘 버튼 (_view_icon_button)


def _view_icon_button(wide: bool, active: int = 0, m_open: bool = False) -> None:
    """보기 전환 아이콘: 리스트 전체보기에서는 '지도로 보기'(→ 지도보기), 지도보기에서는 '리스트로 보기'(→ 리스트 전체보기).
    정렬(최신순) 칸 위 오른쪽 끝, 두 화면에서 같은 자리. 모바일에서는 그 왼쪽에 필터 아이콘도 둔다
    (누르면 검색 필터 판이 열린다. 걸린 조건 수가 있으면 아이콘 옆에 숫자). 둘이 함께 화면 위에 붙는다 (_pin_view_icon)."""
    tools = st.container(horizontal=True, key="view_tools")
    with tools:
        if st.button(str(active) if active else "", icon=":material/close:" if m_open else ":material/tune:",
                     key="m_filter_btn"):
            st.session_state["m_filters"] = not m_open
            st.rerun()
        _view_switch(wide)
        if _member():
            st.button("", icon=":material/calendar_month:", key="m_cal_btn", on_click=_gnb_go, args=("cal",))


def _view_switch(wide: bool) -> None:
    if st.button("지도로 보기" if wide else "리스트로 보기",
                 icon=":material/map:" if wide else ":material/format_list_bulleted:", key="map_icon"):
        st.session_state["list_only"] = not wide
        if not wide:
            st.session_state["selected"] = None    # 상세를 보던 중이면 닫고 리스트로
        st.session_state["scroll_top"] = True    # 화면 길이가 바뀌어도 맨 위부터 보이게
        st.rerun()


def render_list(view: pd.DataFrame, wide: bool = False, df_all: pd.DataFrame | None = None,
                fcond: dict | None = None) -> None:
    """카페 카드 목록. wide 면 지도 없이 화면 전체에 4열로 깐다."""
    if view.empty:
        if df_all is not None:
            _empty_state(df_all, fcond or {})
        else:
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
                    st.markdown(f'<div class="thumb" style="background-image:url(\'{_poster_url(r.get("images"))}\'), url(\'{images.DEFAULT_POSTER_URL}\')"></div>',
                                unsafe_allow_html=True)
                with top:
                    # 📍 지역은 시마다 다른 색 (CITY_COLORS). 진행 상태는 아래 작품 이름 오른쪽에
                    badge = _area_badge(r.get("address"))
                    if badge:
                        st.markdown(badge.replace('">', '">' + _mi("location_on"), 1), unsafe_allow_html=True)
                    chars = str(r.get("characters") or "").strip()
                    # 포스터 옆: 작품(굵게) · 캐릭터(민트) → 카페 이름(회색) → 날짜 · 위치.
                    # 한 덩어리로 그려 카페 이름과 날짜 사이에 칸 간격(빈 줄)이 생기지 않게 한다
                    meta = [f"{_mi('calendar_month')} {r['start_date']} ~ {r['end_date']}",
                            f"{_mi('location_on')} {escape(str(r['address'] or '-'))}"
                            + ("" if pd.notna(r["lat"]) else " · 지도 표시 안 됨")]
                    if n_reviews.get(r["entry_id"]):
                        meta.append(f"{_mi('chat_bubble')} 리뷰 {n_reviews[r['entry_id']]}")
                    st.markdown(
                        f'<p class="ctitle"><strong>{escape(str(r["work"]))}</strong>'
                        + f' <span class="cstate {color}">{escape(label)}</span>'
                        + (f'<br/><span class="cchars">{escape(chars)}</span>' if chars else "")
                        + f'<br/><span class="ccafe">{_mi("local_cafe")}{escape(str(r["cafe_name"]))}</span></p>'
                        + f'<p class="cmeta">{"<br/>".join(meta)}</p>',
                        unsafe_allow_html=True)
                # 포스터 아래(카드 전체 폭): 이벤트 정보·굿즈 칩, 그 아래 특전 칩.
                # 두 줄을 한 묶음(.cbottom)으로 그려, 어느 줄만 있든 카드 아래 테두리와 같은 여백을 둔다
                chips = _chips(r)
                gifts = "".join(f'<span class="chip perk">{_mi("redeem")}{escape(x)}</span>'
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
[class*="st-key-card_w_"] .pcard .info {{ padding-right:52px; }}
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
/* 리스트 카드의 팔로우는 스위치가 아니라 그냥 버튼: 회색 바탕 '팔로우' → 누르면 포인트 색 '팔로잉' */
[class*="st-key-card_"] [class*="st-key-fav_"] button {{ width:30px; height:30px; min-width:0; padding:0 !important;
  border-radius:8px !important; background:#fff !important; }}
[class*="st-key-card_"] [class*="st-key-fav_"] button::before {{ display:none; }}
[class*="st-key-card_"] [class*="st-key-fav_on_"] button {{ padding:0 !important; background:var(--accent) !important; }}
[class*="st-key-card_"] [class*="st-key-fav_"] button span {{ font-size:1.25rem !important; color:#26302D !important; }}
[class*="st-key-card_"] [class*="st-key-fav_on_"] button span {{ color:#fff !important; }}
[class*="st-key-card_"] [class*="st-key-fav_off_"] button:hover {{ background:#fff !important; box-shadow:0 0 0 2px var(--accent); }}
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
.st-key-m_only, .st-key-m_sheet_head, .st-key-m_sheet_foot, [data-testid="stLayoutWrapper"]:has(> .st-key-m_only),
[data-testid="stLayoutWrapper"]:has(> .st-key-m_sheet_head), [data-testid="stLayoutWrapper"]:has(> .st-key-m_sheet_foot) {{ display: none !important; }}
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
  .st-key-wide_grid .pcard .info {{ height: 90px; padding: 8px 9px 14px 11px; }}   /* 아래·왼쪽 여백을 조금 더 */
  .st-key-wide_grid .pcard .t {{ font-size: 14.5px; }}
  .st-key-wide_grid .pcard .s {{ font-size: 11.5px; }}
  .st-key-wide_grid .pcard .d {{ font-size: 12px; margin: 2px 0 0; white-space: nowrap; }}
  .st-key-wide_grid .pcard .d-long {{ display: none; }}
  [class*="st-key-card_w_"]:hover .st-key-wide_grid .pcard .info, .st-key-wide_grid [class*="st-key-card_w_"]:hover .pcard .info {{ padding-top: 30px; }}
  .st-key-wide_grid [class*="st-key-card_w_"]:hover .pcard .t {{ font-size: 13px; }}
  .st-key-wide_grid .pcard .more .m {{ font-size: 10.5px; line-height: 1.4; margin: 0 0 5px; }}
  .st-key-wide_grid .pcard .more .m b {{ font-size: 10px; margin-bottom: 1px; }}
  .st-key-wide_grid .pcard .more ul {{ padding-left: .9em; }}
  .st-key-wide_grid .pcard .more .chip {{ font-size: 9.5px; padding: 1px 6px; }}
  .st-key-wide_grid .pcard .d-short {{ display: inline; }}
  .st-key-wide_grid .pcard .chips {{ display: none; }}
  .st-key-wide_grid .pcard .area {{ top: 6px; left: 6px; font-size: 10.5px; padding: 2px 6px; }}
  .st-key-wide_grid .pcard .state {{ top: 6px; right: 6px; font-size: 10.5px; padding: 2px 7px; }}
  .st-key-wide_grid [class*="st-key-fav_"] {{ top: auto !important; bottom: 8px !important; right: 12px !important; }}
  .st-key-wide_grid .pcard .info {{ padding-right: 40px; }}
  .st-key-wide_grid [class*="st-key-fav_"] button {{ width: 26px; height: 26px; padding: 0 !important; }}
  .st-key-wide_grid [class*="st-key-fav_"] button span {{ font-size: 1.1rem !important; }}
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
/* 리뷰 카드의 별점 줄 (★ 채움은 노랑, ☆ 빈 칸은 연한 회색으로 보이게 글꼴 크게) */
/* 반짝이는 효과: 별 위로 밝은 빛줄기가 지나가고(rvShine), 노란 빛이 은은하게 커졌다 작아진다(rvGlow) */
.rv-av {{ width: 26px; height: 26px; border-radius: 50%; object-fit: cover; vertical-align: middle; margin-right: 4px;
  border: 1px solid #E3E8E6; background: #DDF3EC; }}
.rv-me {{ display: flex; align-items: center; gap: 6px; font-size: .9rem; color: #26302D; margin-bottom: 4px; }}
.rv-me .rv-av {{ width: 28px; height: 28px; margin: 0; }}
.rv-stars {{ display: inline-block; font-size: 1.35rem; letter-spacing: 2px; line-height: 1; margin: 2px 0 12px;
  color: #14b8a6; background: linear-gradient(110deg, #14b8a6 35%, #9FF0E1 48%, #FFFFFF 50%, #9FF0E1 52%, #14b8a6 65%);
  background-size: 250% 100%; -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  animation: rvShine 2.6s ease-in-out infinite, rvGlow 1.8s ease-in-out infinite alternate; }}
@keyframes rvShine {{ 0% {{ background-position: 150% 0; }} 60%, 100% {{ background-position: -100% 0; }} }}
@keyframes rvGlow {{ from {{ filter: drop-shadow(0 0 1px rgba(20,184,166,.4)); }}
                    to {{ filter: drop-shadow(0 0 7px rgba(20,184,166,.85)); }} }}
@media (prefers-reduced-motion: reduce) {{ .rv-stars {{ animation: none; }} }}
/* 리뷰 목록 위 평균 별점: 큰 숫자 · 평균만큼 채운 별(회색 별 위에 민트 별을 폭만큼 겹침) · 후기 수 */
.rv-avg {{ display: flex; align-items: center; gap: 10px; padding: 12px 16px; margin: 4px 0 10px;
  background: var(--accent-soft); border-radius: 14px; }}
.rv-avg-num {{ font-size: 1.7rem; font-weight: 800; color: var(--accent-deep); line-height: 1; }}
.rv-avg-stars {{ position: relative; display: inline-block; font-size: 1.3rem; letter-spacing: 2px; line-height: 1; }}
.rv-avg-bg {{ color: #D5DBD9; }}
.rv-avg-fg {{ position: absolute; left: 0; top: 0; overflow: hidden; white-space: nowrap; color: var(--accent); }}
.rv-avg-cnt {{ margin-left: auto; font-size: .82rem; color: #5B6B67; }}
/* 리뷰 사진: 내용 아래 작은 정사각 썸네일, 누르면 원본 */
.rv-pics {{ display:flex; gap:6px; flex-wrap:wrap; margin:-4px 0 6px; }}
.rv-pics img {{ width:84px; height:84px; object-fit:cover; border-radius:8px; border:1px solid #E4E8E6; display:block; }}
.rv-pics a:hover img {{ border-color:var(--accent); }}
/* 리뷰 '+ 사진 첨부' 버튼: 내용 아래 왼쪽에 작은 테두리 버튼 (누르면 사라지고 올리는 칸이 열린다) */
[class*="st-key-rv_"][class*="_pic_btn_"] button {{ min-height:0 !important; height:26px; min-width:30px; padding:0 10px !important;
  border:1.5px solid var(--accent) !important; border-radius:8px !important; background:#fff !important; }}
[class*="st-key-rv_"][class*="_pic_btn_"] button:hover {{ background:var(--accent-soft) !important; }}
[class*="st-key-rv_"][class*="_pic_btn_"] button p {{ font-size:.8rem !important; font-weight:700; color:var(--accent-deep) !important; }}
/* 리뷰 사진 올리는 칸: 작게 */
[class*="st-key-rv_"][class*="_img_"] [data-testid="stFileUploaderDropzone"] {{ padding:.5rem .75rem; min-height:0; }}
[class*="st-key-rv_"][class*="_img_"] label p {{ font-size:.82rem; color:#6B7672; }}
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
  color: var(--accent); transition: color .12s; }}
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
  color: var(--accent) !important; }}
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
.upd {{ color:#8A9592; font-size:.78rem; margin:-4px 0 6px; display:flex; align-items:center; gap:4px; }}
.upd .mi {{ font-size:.95rem; }}
.upd.warn {{ color:#C2560C; background:#FFF4EA; border-radius:10px; padding:6px 10px; margin:0 0 8px; }}
.empty-box {{ text-align:center; padding:40px 16px 14px; }}
.empty-ic .mi {{ font-size:3.4rem; color:#C9D6D2; }}
.empty-t {{ font-family:"Jua", sans-serif; font-size:1.35rem; color:#26302D; margin-top:6px; }}
.empty-s {{ color:#7A8582; font-size:.9rem; margin-top:4px; }}
.st-key-empty_relax {{ gap:8px !important; flex-wrap:wrap; margin-bottom:28px; }}
.chip.warn {{ background:#FFF1E6; color:#C2560C; border-color:#F5C9A6; font-weight:700; }}
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
/* 상세 팔로우: 글자 대신 팔로우 아이콘, 옆 공유 버튼과 같은 28px 정사각형 (흰 바탕·회색 테두리).
   팔로우하면 포인트 색으로 채우고 흰 아이콘 */
.st-key-detail_actions [class*="st-key-fav_"] button {{ width: 34px !important; min-width: 34px !important; height: 34px !important;
  min-height: 34px !important; padding: 0 !important; border-radius: 8px !important; display: flex !important;
  align-items: center !important; justify-content: center !important; border: 1.5px solid #DDE2E0 !important; background: #fff !important;
  box-shadow: none !important; transform: none !important; }}
.st-key-detail_actions [class*="st-key-fav_"] button::before {{ display: none; }}
.st-key-detail_actions [class*="st-key-fav_"] button span {{ font-size: 1.4rem !important; color: #26302D !important; margin: 0 !important; }}
/* 공유(iframe)·북마크 칸 높이를 버튼 높이(34px)로 딱 맞춰 세로 위치를 같게 */
.st-key-detail_actions [data-testid="stColumn"]:not(:first-child) [data-testid="stElementContainer"] {{ height: 34px; }}
.st-key-detail_actions [class*="st-key-fav_"] .stButton {{ line-height: 0; }}
.st-key-detail_actions [class*="st-key-fav_on_"] button {{ background: var(--accent) !important; border-color: var(--accent) !important; }}
.st-key-detail_actions [class*="st-key-fav_on_"] button span {{ color: #fff !important; }}
.st-key-detail_actions [class*="st-key-fav_off_"] button:hover {{ border-color: var(--accent) !important; background: #fff !important; }}
/* 2줄을 화면 폭과 상관없이 한 줄에: 작품 이름 칸이 남는 폭, 공유·찜 칸은 버튼 크기(40px)만큼 오른쪽 끝.
   공유를 누르면 공유 칸이 넓어진다(공유 컴포넌트가 바깥 칸 폭을 직접 바꾼다) */
.st-key-detail_actions [data-testid="stHorizontalBlock"] {{ flex-direction: row !important; flex-wrap: nowrap !important;
  gap: 8px !important; align-items: flex-start !important; }}   /* 공유·북마크는 작품 이름 윗선에 맞춘다 */
/* 작품 이름 글자는 줄 높이 때문에 상자 위쪽에 7px 쯤 빈 곳이 있어서, 버튼도 그만큼 내려 글자 윗선과 맞춘다 */
.st-key-detail_actions [data-testid="stColumn"]:not(:first-child) {{ margin-top: 7px; }}
.st-key-detail_actions [data-testid="stColumn"]:first-child {{ flex: 1 1 auto !important; width: auto !important;
  min-width: 0 !important; }}
.st-key-detail_actions [data-testid="stColumn"]:not(:first-child) {{ flex: 0 0 34px !important; width: 34px !important;
  min-width: 0 !important; transition: flex-basis .2s, width .2s; }}
.st-key-detail_actions [data-testid="stColumn"]:last-child {{ flex: 0 0 34px !important; width: 34px !important; }}
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
.dintro-foot {{ display:flex; justify-content:flex-end; margin-top:10px; }}
.dsrc {{ flex:0 0 auto; display:inline-flex; align-items:center; gap:2px; height:30px; padding:0 12px; border-radius:999px;
  border:1.5px solid var(--accent); color:var(--accent-deep) !important; background:#fff; font-size:.82rem; font-weight:700;
  text-decoration:none !important; }}
.dsrc:hover {{ background:var(--accent-soft); }}
.dsrc .mi {{ font-size:1.05em; margin-right:2px; }}
.dintro-h {{ color:var(--accent-deep); font-weight:800; margin-right:4px; }}
.dintro {{ background:#F4F6F5; border-radius:14px; padding:14px 18px; font-size:.95rem; line-height:1.7; color:#2E3A37;
  word-break:keep-all; overflow-wrap:anywhere; }}
.dintro-gap {{ display:block; height:8px; }}
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
.dlink.broken {{ background:#FFF4EA; }}
.dlink-warn {{ display:inline-flex; align-items:center; gap:2px; font-size:.75rem; font-weight:800; color:#C2560C;
  background:#fff; border:1px solid #F5C9A6; border-radius:999px; padding:1px 8px; margin-left:6px; vertical-align:2px; }}
.dlink-warn .mi {{ font-size:.9rem; }}
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
/* 기간: PC 는 '10월 30일 - 11월 22일', 모바일 리스트는 짧게 '10/30-11/22' (아래 모바일 규칙) */
.pcard .d-short {{ display:none; }}
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
              + ' [role=tabpanel], [data-baseweb=tab-panel], [class*=st-key-fav_], [class*=st-key-folsw]';
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


def _pin_view_icon() -> None:
    """보기 전환 아이콘(지도·리스트)을 스크롤해도 화면 위에 붙어 있게 한다.

    PC 는 위에 붙어 있는 상단 묶음(제목·검색 필터) 바로 아래, 모바일은 상단 묶음이 같이 스크롤되므로 화면 맨 위.
    모바일에서 위에 붙는 건 이 아이콘 하나뿐이다. 원래 자리에는 칸 높이를 남겨 두어 목록이 들썩이지 않는다.
    """
    components.html(f"<script>window.parent.eval({json.dumps(_PIN_ICON_JS)});</script>", height=0)


_PIN_ICON_JS = """
(function () {
  if (window.__aniPinIcon) return;
  window.__aniPinIcon = true;
  const update = () => {
    const btn = document.querySelector('.st-key-view_tools');      // 필터·보기 전환 아이콘 묶음
    const box = btn && btn.parentElement;                          // 원래 자리 (높이를 남겨 둔다)
    if (!btn || !box) return;
    const r = box.getBoundingClientRect();
    if (!r.width) return;                       // 상세 화면처럼 숨어 있으면 그대로
    const mobile = window.innerWidth <= 640;
    const bar = document.querySelector('.st-key-topbar');
    // 원래 자리가 위에 붙은 상단 묶음(PC) / 화면 맨 위(모바일) 밑으로 들어가기 시작하면 붙이고, 붙일 때는 조금 띄운다
    const edge = mobile ? 0 : (bar ? Math.max(bar.getBoundingClientRect().bottom, 0) : 0);
    const limit = edge + 10;
    if (r.top < edge) {
      btn.style.position = 'fixed';
      btn.style.top = limit + 'px';
      btn.style.width = 'auto';
      btn.style.left = (r.right - btn.offsetWidth) + 'px';
      btn.style.zIndex = '1002';
      btn.classList.add('pinned');
    } else if (btn.style.position) {
      ['position', 'top', 'left', 'width', 'zIndex'].forEach((k) => { btn.style[k] = ''; });
      btn.classList.remove('pinned');
    }
  };
  // 메인 칸이 스크롤된다. 다시 그리면 버튼이 새로 생기므로 화면이 바뀔 때마다도 확인한다
  document.addEventListener('scroll', update, true);
  window.addEventListener('resize', update);
  new MutationObserver(() => requestAnimationFrame(update)).observe(document.body, { childList: true, subtree: true });
})();
"""


_LIVE_SEND_JS = """
(function () {
  if (window.__aniLiveSend) return;
  window.__aniLiveSend = true;
  // 입력칸에 한 글자라도 있으면 버튼을 켜고, 비면 끈다 (칸을 벗어나지 않아도 바로).
  // 다녀온 후기는 별점을 골랐으면 내용이 비어도 켠다 (rated)
  const toggle = (b, ta, rated) => {
    if (!b || !ta) return;
    if (!ta.value.trim() && !rated) { if (!b.disabled) { b.disabled = true; b.dataset.aniEmpty = '1'; } }
    else if (b.dataset.aniEmpty) { b.disabled = false; delete b.dataset.aniEmpty; }
  };
  const sync = () => {
    // 리뷰·답글: rv_..._body_N 입력칸 ↔ rv_..._send_N 버튼
    document.querySelectorAll('[class*="st-key-rv_"][class*="_send_"] button').forEach((b) => {
      const box = b.closest('[class*="_send_"]');
      const cls = [...box.classList].find((c) => c.startsWith('st-key-rv_') && c.includes('_send_'));
      // 다녀온 후기: 별점을 골랐거나 사진을 올렸으면 내용이 비어도 켠다 (사진 칸은 다녀온 후기일 때 별점 칸과 함께 있다)
      const rateBox = cls && document.querySelector('.' + CSS.escape(cls.replace('_send_', '_rate_box_')));
      const rated = rateBox && (rateBox.querySelector('[data-testid="stFeedbackButtonActive"]')
        || document.querySelector('.' + CSS.escape(cls.replace('_send_', '_img_'))
                                  + ' [data-testid="stFileChip"], .' + CSS.escape(cls.replace('_send_', '_img_'))
                                  + ' [data-testid="stFileUploaderFile"]'));
      toggle(b, cls && document.querySelector('.' + CSS.escape(cls.replace('_send_', '_body_')) + ' textarea'), !!rated);
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
  // 처음엔 기본 로고(LOGOS 의 첫 번째), 그 뒤로는 누를 때마다 다음 로고로. 서버를 거치면 클릭 한 번에 화면이
  // 두 번 그려져 바뀌었다 되돌아가기도 해서, 바깥 페이지에서 직접 바꾼다
  const s = document.createElement('style');
  document.head.appendChild(s);
  let i = 0;
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


def _brand(home: bool = False, fixed: bool = False, logo: str = FIXED_LOGO) -> bool:
    """ANI:WHERE 제목 + 문구. 제목(또는 home 일 때 '홈으로')을 눌렀으면 True.

    home 이면 문구 줄 오른쪽 끝에 홈으로 돌아가기 버튼을 둔다 (등록 화면).
    """
    # 글자 대신 로고 그림을 보여 준다 (GLOBAL_CSS 의 .st-key-home_brand). 글자는 화면 읽기용으로 남긴다.
    # 로고 주소는 포스터처럼 'app/static/…' 상대 주소로 둔다 ('/' 로 시작하면 하위 경로에 배포했을 때 못 찾는다)
    # 화면 어디든 누를 때마다 로고가 다른 것으로 바뀐다 (_logo_swap — 브라우저에서 처리).
    # 상세·등록 화면은 바뀌지 않고 늘 같은 로고(FIXED_LOGO). 더 강한 선택자로 덮어써서, 목록으로 돌아가면 다시 바뀐다
    _logo_swap()
    if fixed:
        st.markdown(f'<style>html body .st-key-home_brand button {{ background-image: url("app/static/{logo}")'
                    ' !important; }</style>', unsafe_allow_html=True)
    clicked = st.button("ANI:WHERE", key="home_brand", type="tertiary")
    if not home:
        st.markdown('<div class="brand-tag">함께 만드는 애니 팝업 지도!! 찾고, 공유하고, 함께 기록해요!</div>',
                    unsafe_allow_html=True)
        return clicked
    # 등록 화면: 문구 줄 오른쪽 끝에 홈으로 돌아가기
    sub, btn = st.columns([5, 1], vertical_alignment="center")
    sub.markdown('<div class="brand-tag">함께 만드는 애니 팝업 지도!! 찾고, 공유하고, 함께 기록해요!</div>',
                 unsafe_allow_html=True)
    with btn:
        clicked = st.button("홈으로 돌아가기", icon=":material/arrow_back:", key="wiz_home") or clicked
    return clicked


def _follow_switch(key: str) -> None:
    """'북마크한 곳만' 버튼 (북마크 아이콘 + '북마크'). 켜지면 포인트 색으로 채운다.
    목록 위(PC)와 모바일 필터 판에 같은 스위치를 두고, 둘 다 같은 값(fav_only)을 바꾼다."""
    on = bool(st.session_state.get("fav_only"))
    st.button("북마크", icon=":material/bookmark_added:" if on else ":material/bookmark:",
              key=f"{key}_{'on' if on else 'off'}",
              on_click=lambda: st.session_state.update(fav_only=not on))


# 모바일 필터 시트 (필터 아이콘을 눌렀을 때만 page_map 이 붙인다). PC 에는 머리·아래 줄을 늘 숨긴다
MOBILE_SHEET_CSS = """
.st-key-filters { position: fixed !important; left: 0; right: 0; top: 44px; bottom: 0; z-index: 1005;
  overflow-y: auto; background: #fff; border-radius: 22px 22px 0 0; padding: 18px 20px 0 !important;
  box-shadow: 0 0 0 100vmax rgba(0,0,0,.38); gap: 0 !important; }
.st-key-filters > div, .st-key-filters [data-testid="stHorizontalBlock"] { gap: 0 !important; }
.st-key-m_sheet_head { display: flex !important; flex-direction: row !important; align-items: center;
  justify-content: space-between; margin-bottom: 6px; }
.st-key-filters > [data-testid="stLayoutWrapper"]:has(> .st-key-m_sheet_head), .st-key-filters > .st-key-m_sheet_head { order: -2; display: block !important; }
.st-key-filters > [data-testid="stLayoutWrapper"]:has(> .st-key-m_sheet_foot) { display: block !important; }
.st-key-m_sheet_head > div { width: auto !important; }
.sheet-title { font-size: 1.6rem; font-weight: 800; color: #111; }
.st-key-m_sheet_close button { min-height: 0 !important; padding: 4px !important; }
.st-key-m_sheet_close button span { font-size: 1.6rem !important; color: #111 !important; }
/* 항목마다: 굵은 제목, 아래 구분선 */
.st-key-filters [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
.st-key-filters .st-key-m_only > div { padding: 14px 0 16px; border-bottom: 1px solid #ECEFEE; }
.st-key-filters label p, .st-key-filters [data-testid="stWidgetLabel"] p { font-size: 1.05rem !important;
  font-weight: 800 !important; color: #1F2A27 !important; }
.st-key-filters .st-key-m_only > div { width: 100% !important; }
.st-key-filters [class*="st-key-folsw"] button { width: auto !important; min-width: 0 !important; }
/* 시트가 열려 있는 동안 위에 붙은 필터·보기 아이콘은 감춘다 (시트의 × 로 닫는다) */
.st-key-view_tools { display: none !important; }
/* 시트에서는 아래 줄의 '전체 삭제' 가 대신해서 '초기화' 칸은 숨긴다 */
.st-key-filters [data-testid="stColumn"]:has(.st-key-filter_reset) { display: none !important; }
/* 맨 아래 고정 줄 */
.st-key-filters > [data-testid="stLayoutWrapper"]:has(> .st-key-m_sheet_foot) { position: sticky; bottom: 0; z-index: 2;
  order: 10; margin-top: 8px; }
.st-key-m_sheet_foot { display: flex !important; flex-direction: column !important; align-items: stretch !important;
  gap: 6px !important; background: #fff; border-top: 1px solid #ECEFEE; padding: 10px 0 16px;
  box-shadow: 20px 0 0 #fff, -20px 0 0 #fff; }   /* 양옆 시트 여백까지 흰 바탕으로 덮는다 */
.st-key-m_sheet_foot > div, .st-key-m_sheet_foot .stButton, .st-key-m_sheet_foot [class*="st-key-m_sheet_"] { width: 100% !important; }
.st-key-m_sheet_reset button { width: 100% !important; min-height: 0 !important; height: 40px; }
.st-key-m_sheet_reset button p { font-size: 1rem !important; font-weight: 700 !important; color: #26302D !important; }
.st-key-m_sheet_done button { width: 100% !important; min-height: 0 !important; height: 50px; border-radius: 12px !important;
  background: #26302D !important; border: 0 !important; }
.st-key-m_sheet_done button p { font-size: 1.02rem !important; font-weight: 700 !important; color: #fff !important; }
"""


def _update_note() -> None:
    """목록 위 '마지막 업데이트 ○월 ○일 HH:MM'. 수집이 실패했거나 2일 넘게 새 정보가 없으면 주황색으로 알린다.
    (소스 사이트가 죽어도 조용히 빈 화면이 되지 않게: 기존 데이터는 그대로 보여 준다)"""
    last = notion_sync.last_update(store.all_rows())
    if last is None:
        return
    kst = last.astimezone(timezone(timedelta(hours=9)))
    stamp = f"{kst.month}월 {kst.day}일 {kst:%H:%M}"
    failed = st.session_state.get("_sync_failed") or bool(notion_sync.last_status().get("error"))
    stale = (datetime.now(timezone.utc) - last) > timedelta(days=2)
    if failed or stale:
        msg = (f"최신 정보를 가져오지 못했어요. 마지막 업데이트 {stamp} 기준으로 보여 드려요."
               if failed else f"마지막 업데이트 {stamp} — 새 정보가 이틀 넘게 없어요. 기간은 공식 공지에서 한 번 더 확인해 주세요.")
        st.markdown(f'<div class="upd warn">{_mi("sync_problem")} {escape(msg)}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="upd">{_mi("update")} 마지막 업데이트 {stamp} · 매일 아침 자동 수집</div>',
                    unsafe_allow_html=True)


def _filter_view(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """검색 조건(f) 으로 거른다. 빈 화면에서 '이 조건만 풀면 몇 곳' 을 세는 데도 같은 함수를 쓴다."""
    view = df
    query = str(f.get("query") or "")
    if query.strip():
        q = re.sub(r"\s+", "", query)
        hit = lambda col: view[col].astype(str).str.replace(r"\s+", "", regex=True).str.contains(q, case=False, regex=False)
        view = view[hit("cafe_name") | hit("work") | hit("characters") | hit("address")]
    if f.get("work", "전체") != "전체":
        view = view[view["work"] == f["work"]]
    if f.get("chars"):
        same = lambda a, b: a == b or a in b or b in a
        view = view[view["characters"].fillna("").apply(
            lambda v: any(same(p, c) for p in f["chars"] for c in _split(v)))]
    span = f.get("span", "진행중 + 예정")
    if span == "진행중 + 예정":
        view = view[view["end_date"] >= TODAY]
    elif span == "예정":
        view = view[view["start_date"] > TODAY]
    elif span == "진행중":
        view = view[(view["start_date"] <= TODAY) & (view["end_date"] >= TODAY)]
    if f.get("day"):
        view = view[(view["start_date"] <= f["day"]) & (view["end_date"] >= f["day"])]
    if f.get("regions"):
        view = view[view["area"].isin(f["regions"])]
    if f.get("fav"):
        view = view[view["entry_id"].astype(str).isin(_fav_state()[1])]
    return view


def _relax(what: str) -> None:
    """빈 화면의 '조건 풀기' 버튼. 그 조건 하나만 처음 값으로 돌린다."""
    ss = st.session_state
    if what == "regions":
        ss["regions"], ss["regions_m"] = [], []
    elif what == "day":
        ss.pop(f"f_date_{ss.get('date_ver', 0)}", None)
        ss["date_ver"] = ss.get("date_ver", 0) + 1
    elif what == "span":
        ss["f_span"] = "진행중 + 예정"
    elif what == "soon":
        ss["f_span"] = "예정"
    elif what == "work":
        ss["f_work"] = "전체"
        for k in [k for k in ss if str(k).startswith("filter_chars_")]:
            ss[k] = []
    elif what == "chars":
        for k in [k for k in ss if str(k).startswith("filter_chars_")]:
            ss[k] = []
    elif what == "query":
        ss["f_query"] = ""
    elif what == "fav":
        ss["fav_only"] = False


def _empty_state(df: pd.DataFrame, f: dict) -> None:
    """조건에 맞는 팝업이 0곳일 때: 빈 표 대신 이유와 '조건 하나 풀기' 버튼 (각 버튼에 풀면 몇 곳인지)."""
    live_or_soon = df[df["end_date"] >= TODAY]
    live = df[(df["start_date"] <= TODAY) & (df["end_date"] >= TODAY)]
    soon = df[df["start_date"] > TODAY]
    if live_or_soon.empty:
        title, sub = "지금은 열려 있거나 예정된 팝업이 없어요", "새 팝업은 매일 아침 자동으로 모아요. 내일 다시 들러 주세요."
    elif f.get("span") == "진행중" and live.empty:
        title, sub = "지금 진행 중인 팝업이 없어요", f"곧 열리는 팝업은 {len(soon)}곳 있어요."
    else:
        title, sub = "이 조건엔 행사가 없어요", "조건을 하나씩 풀어 보세요. 버튼 옆 숫자는 풀었을 때 보이는 팝업 수예요."
    st.markdown(f'<div class="empty-box"><div class="empty-ic">{_mi("search_off")}</div>'
                f'<div class="empty-t">{escape(title)}</div><div class="empty-s">{escape(sub)}</div></div>',
                unsafe_allow_html=True)
    options = []
    if f.get("span") == "진행중" and live.empty and len(soon):
        options.append(("soon", f"곧 열리는 팝업 보기 ({len(soon)}곳)"))
    for what, label, changed in (
        ("regions", "지역만 풀기", {"regions": []}),
        ("day", "날짜 풀기", {"day": None}),
        ("span", "진행 여부 풀기", {"span": "진행중 + 예정"}),
        ("chars", "캐릭터 풀기", {"chars": []}),
        ("work", "작품 풀기", {"work": "전체", "chars": []}),
        ("query", "검색어 지우기", {"query": ""}),
        ("fav", "북마크만 보기 끄기", {"fav": False}),
    ):
        key = {"chars": "chars", "work": "work", "query": "query", "fav": "fav", "regions": "regions",
               "day": "day", "span": "span"}[what]
        cur = f.get(key)
        if not cur or cur in ("전체", "진행중 + 예정"):
            continue
        n = len(_filter_view(df, {**f, **changed}))
        if n:
            options.append((what, f"{label} ({n}곳)"))
    with st.container(horizontal=True, horizontal_alignment="center", key="empty_relax"):
        for what, label in options:
            st.button(label, key=f"relax_{what}", on_click=_relax, args=(what,))
        if _active_filters():
            st.button("조건 모두 초기화", key="relax_all", type="primary", on_click=_reset_filters)


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


# ------------------------------------------------------------ 상단 메뉴바 (로고 · 보기 탭 · 검색 / 알림 / 로그인)
GNB_CSS = """
<style>
.st-key-gnb { align-items: center !important; gap: 4px !important; flex-wrap: nowrap; padding: 6px 0 2px; }
/* 로고: 메뉴바 안에서는 작게 */
.st-key-gnb .st-key-home_brand button { width: 155px !important; height: 47px !important; }   /* 11/18 로고 조금 작게 */
/* 보기 탭: 글자 + 아래 밑줄 (고른 탭만 진하게) */
.st-key-gnb { position: relative; background: #E9F7F2; border-radius: 0 0 28px 28px;
  padding: 10px 28px !important; margin: 0 -28px; box-sizing: content-box; }
/* 메뉴바가 있는 화면은 페이지 위 여백을 없애 메뉴바를 화면 맨 위에 붙인다 */
.stMainBlockContainer { padding-top: 0 !important; }
/* 오른쪽 아이콘: 둥근 굵은 선 그림(검색·종) + 둥근 글꼴 '로그인' (11/18 사용자 요청) */
.st-key-gnb_right [class*="st-key-gnb_search_"] button span[data-testid="stIconMaterial"],
.st-key-gnb_right [data-testid="stPopover"] button span[data-testid="stIconMaterial"] { display: none !important; }
html body .st-key-gnb_right [class*="st-key-gnb_search_"] button,
html body .st-key-gnb_right [data-testid="stPopover"] button { background-color: transparent !important; background-repeat: no-repeat !important; background-size: 27px 27px !important;
  min-width: 42px; min-height: 42px; }
html body .st-key-gnb_right .st-key-gnb_search_off button { background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%234B5260' stroke-width='2.3' stroke-linecap='round'><circle cx='10.5' cy='10.5' r='6.6'/><path d='M15.6 15.6L20 20'/></svg>") !important; background-position: center !important; }
html body .st-key-gnb_right .st-key-gnb_search_on button { background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%234B5260' stroke-width='2.3' stroke-linecap='round'><path d='M6.5 6.5l11 11M17.5 6.5l-11 11'/></svg>") !important; background-position: center !important; }
html body .st-key-gnb_right [data-testid="stPopover"] button { position: relative; background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%234B5260' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'><path d='M6.3 16.4V11.2a5.7 5.7 0 0 1 11.4 0v5.2'/><path d='M4.6 16.6c0 .3.3.5.6.5h13.6c.3 0 .6-.2.6-.5'/><path d='M10.2 19.6a1.9 1.9 0 0 0 3.6 0'/></svg>") !important; background-position: center !important;
  padding: 0 !important; width: 42px !important; }
.st-key-gnb_right [data-testid="stPopover"] button p { margin-left: -6px !important; font-size: .85rem !important; }
.st-key-gnb_right [class*="st-key-gnb_search_"] button p, .st-key-gnb_right [data-testid="stPopover"] button p {
  font-family: "NanumSquareRound", "Jua", sans-serif !important; color: #2E9C82 !important; font-weight: 800 !important; }
.st-key-gnb_right .st-key-admin_btn button { background: #fff !important; border: 1.5px solid #9EDDCC !important;
  border-radius: 999px !important; padding: 2px 12px !important; min-height: 0 !important; }
.st-key-gnb_right .st-key-admin_btn button p { font-family: "NanumSquareRound", sans-serif !important; font-weight: 800 !important;
  color: #2E9C82 !important; font-size: .88rem !important; }
.st-key-gnb_right .st-key-admin_btn button span { color: #2E9C82 !important; font-size: 1.1rem !important; }
.st-key-gnb_right .st-key-login_btn button p { font-family: "NanumSquareRound", sans-serif !important; font-weight: 700 !important;
  color: #4B5260 !important; font-size: 1.02rem !important; letter-spacing: -.01em; }
.st-key-gnb_tabs button p { font-family: "NanumSquareRound", sans-serif !important; }
/* 메뉴바 묶음 안의 보이지 않는 칸(스타일·높이 0 iframe·위치 받기)이 간격만 차지하지 않게 */
.st-key-topbar { gap: 0 !important; }
.st-key-topbar > [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style:only-child),
.st-key-topbar [data-testid="stElementContainer"]:has(iframe[height="0"]) { display: none !important; }
.st-key-topbar .st-key-filters { margin-top: 10px; }
.st-key-gnb_loc_box { display: none !important; }
/* 탭은 메뉴바 정가운데 (로고·오른쪽 아이콘 폭과 상관없이) */
.st-key-gnb_tabs { gap: 0 !important; width: auto !important; flex: 0 0 auto; position: absolute !important;
  left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 2; }
.st-key-gnb_tabs button { background: transparent !important; border: 0 !important; border-radius: 0 !important;
  box-shadow: none !important; padding: 10px 16px 9px !important; border-bottom: 3px solid transparent !important; }
.st-key-gnb_tabs button p { font-size: 1.05rem !important; font-weight: 600 !important; color: #8A9592 !important; }
.st-key-gnb_tabs button:hover p { color: #26302D !important; }
.st-key-gnb_tabs [class*="st-key-gnbtab_on_"] button { border-bottom-color: #26302D !important; }
.st-key-gnb_tabs [class*="st-key-gnbtab_on_"] button p { color: #26302D !important; font-weight: 800 !important; }
/* 오른쪽 끝: 검색 · 알림 · 로그인 */
.st-key-gnb_right { margin-left: auto; width: auto !important; flex: 0 0 auto; gap: 2px !important; align-items: center; }
.st-key-gnb_right [class*="st-key-gnb_search_"] button { background: transparent !important; border: 0 !important;
  box-shadow: none !important; }
.st-key-gnb_right [class*="st-key-gnb_search_"] button span[data-testid="stIconMaterial"] { font-size: 1.6rem !important; }
.st-key-gnb_search_on button { border-radius: 999px !important; }
.st-key-gnb_right [data-testid="stPopover"] button, .st-key-gnb_right .st-key-login_btn button {
  background: transparent !important; border: 0 !important; box-shadow: none !important; }
.st-key-gnb_right [data-testid="stPopover"] button span[data-testid="stIconMaterial"] { font-size: 1.6rem !important; }
.st-key-gnb_right [data-testid="stPopover"] button svg { display: none; }       /* 펼침 화살표 숨김 */
.st-key-gnb_right .st-key-login_btn button p { font-size: 1rem !important; }
.gnb-tag { color: #6B7672; font-size: .82rem; margin: -2px 0 6px; font-family: "Jua", sans-serif; }
/* 예전 '지도로 보기 / 리스트로 보기' 버튼은 위 탭이 대신한다. 모바일용 캘린더 아이콘도 PC 에서는 숨김 */
.st-key-m_cal_btn { display: none !important; }
.st-key-map_icon { display: none !important; }
.ntf-item { padding: 8px 10px 8px 22px; border-radius: 10px; font-size: .88rem; line-height: 1.5; position: relative;
  background: #F1FAF7; }
.ntf-item::before { content: ""; position: absolute; left: 9px; top: 15px; width: 7px; height: 7px; border-radius: 50%;
  background: #FF6B6B; }
.ntf-item b { color: #2E9C82; }
.ntf-item.read { background: transparent; color: #8A9592; }
.ntf-item.read::before { background: transparent; }
.ntf-item.read b { color: #8A9592; }
.ntf-item .ntf-st { float: right; font-size: .72rem; font-weight: 700; color: #FF6B6B; }
.ntf-item.read .ntf-st { color: #A9B3B0; }
.ntf-why { display: flex; align-items: center; gap: 3px; font-size: .74rem; color: #8A9592; margin-top: 2px; line-height: 1.35; }
.ntf-why .material-symbols-rounded, .ntf-why span { font-size: .82rem; }
[class*="st-key-ntfc_"] { position: relative; margin-bottom: 4px; }
[class*="st-key-ntfb_"] { position: absolute !important; inset: 0; z-index: 2; width: 100% !important; height: 100% !important; }
[class*="st-key-ntfb_"] > div, [class*="st-key-ntfb_"] .stButton { width: 100% !important; height: 100% !important; }
[class*="st-key-ntfb_"] button { width: 100% !important; height: 100% !important; opacity: 0 !important; cursor: pointer; }
[class*="st-key-ntfc_"]:hover .ntf-item { outline: 1.5px solid var(--accent); }
.ntf-item.plain { margin-bottom: 4px; cursor: default; }
.ntf-empty { color: #8A9592; font-size: .88rem; padding: 6px 2px; }
.st-key-gnb_loc_box { height: 0 !important; overflow: hidden !important; margin: 0 !important; }
@media (max-width: 640px) {
  /* 모바일: 메뉴바의 글자 탭은 숨기고, 필터 아이콘 옆 '보기 전환 아이콘'(지도 ↔ 리스트)으로 — 위에 늘 붙어 있다 (11/18 요청) */
  .st-key-gnb > *:has(.st-key-gnb_tabs), html body .st-key-gnb .st-key-gnb_tabs { display: none !important; }
  html body .st-key-view_tools .st-key-map_icon { display: block !important; width: auto !important; min-height: 0 !important; }
  html body .st-key-view_tools .st-key-map_icon .stButton { width: auto !important; }
  html body .st-key-view_tools .st-key-map_icon button { height: 32px !important; min-width: 32px; width: auto !important;
    padding: 0 9px !important; border: 1.5px solid var(--accent) !important; border-radius: 10px !important;
    background: #fff !important; box-shadow: none; }
  html body .st-key-view_tools .st-key-map_icon button p { display: none !important; }
  /* 세 아이콘(지도/리스트 · 캘린더 · 필터) 같은 크기 40×34, 같은 간격, 필터는 맨 오른쪽 */
  html body .st-key-view_tools { gap: 8px !important; }
  html body .st-key-view_tools > * { margin: 0 !important; }
  html body .st-key-view_tools .st-key-map_icon button, html body .st-key-view_tools .st-key-m_cal_btn button,
  html body .st-key-view_tools .st-key-m_filter_btn button { width: 40px !important; min-width: 40px !important;
    height: 34px !important; padding: 0 !important; justify-content: center !important; }
  html body .st-key-view_tools .st-key-map_icon .stButton, html body .st-key-view_tools .st-key-map_icon,
  html body .st-key-view_tools .st-key-m_cal_btn, html body .st-key-view_tools .st-key-m_filter_btn {
    width: 40px !important; min-width: 40px !important; flex: 0 0 40px !important; }
  html body .st-key-view_tools > .st-key-map_icon, html body .st-key-view_tools > *:has(.st-key-map_icon) { order: 1; }
  html body .st-key-view_tools > .st-key-m_cal_btn, html body .st-key-view_tools > *:has(.st-key-m_cal_btn) { order: 2; }
  html body .st-key-view_tools > .st-key-m_filter_btn, html body .st-key-view_tools > *:has(.st-key-m_filter_btn) { order: 3; }
  html body .st-key-view_tools .st-key-m_box_btn { display: block !important; width: auto !important; }
  html body .st-key-view_tools .st-key-m_box_btn button { height: 32px !important; min-width: 32px; padding: 0 9px !important;
    border: 1.5px solid var(--accent) !important; border-radius: 10px !important; background: #fff !important; min-height: 0 !important; }
  html body .st-key-view_tools .st-key-m_box_btn button span { color: var(--accent-deep) !important; font-size: 1.2rem !important; margin: 0 !important; }
  html body .st-key-view_tools .st-key-m_cal_btn { display: block !important; width: auto !important; }
  html body .st-key-view_tools .st-key-m_cal_btn button { height: 32px !important; min-width: 32px; padding: 0 9px !important;
    border: 1.5px solid var(--accent) !important; border-radius: 10px !important; background: #fff !important; min-height: 0 !important; }
  html body .st-key-view_tools .st-key-m_cal_btn button span { color: var(--accent-deep) !important; font-size: 1.2rem !important; margin: 0 !important; }
  html body .st-key-view_tools .st-key-map_icon button span { color: var(--accent-deep) !important; font-size: 1.2rem !important;
    margin: 0 !important; }
  /* 모바일: 첫 줄 = 로고 + (검색·알림·로그인) */
  .st-key-gnb { flex-wrap: wrap !important; flex-direction: row !important; row-gap: 2px !important; }
  .st-key-gnb .st-key-home_brand { flex: 0 0 auto !important; width: auto !important; }
  .st-key-gnb .st-key-home_brand button { width: 118px !important; height: 37px !important; }
  .st-key-gnb > *:has(.st-key-gnb_right), .st-key-gnb > .st-key-gnb_right { order: 2; margin-left: auto !important; }
  .st-key-gnb > *:has(.st-key-gnb_tabs), .st-key-gnb > .st-key-gnb_tabs { order: 3; flex: 1 1 100% !important; width: 100% !important; }
  .st-key-gnb_right { flex-wrap: nowrap !important; }
  .st-key-gnb_tabs { order: 3; flex: 1 1 100% !important; width: 100% !important; justify-content: center !important;
    flex-wrap: nowrap !important; position: static !important; transform: none !important; }
  .st-key-gnb_tabs > div { width: auto !important; flex: 0 0 auto !important; }
  .st-key-gnb_tabs button { white-space: nowrap; padding: 8px 14px 7px !important; }
  .st-key-gnb_tabs button p { font-size: .95rem !important; }
  .st-key-gnb_right .st-key-login_btn button p { font-size: .85rem !important; }
}</style>
"""


ASK_FAB_CSS = """
<style>
.st-key-ask_fab { display: none; }
@media (max-width: 640px) {
  /* 등록(+) 버튼과 같은 크기(50px)·같은 오른쪽 줄, 그 바로 위 (+ 는 right 16px · bottom 76px) */
  .st-key-ask_fab { display: block; position: fixed !important; right: 16px; bottom: calc(76px + 50px + 12px);
    z-index: 1003; width: 50px !important; height: 50px; }
  .st-key-ask_fab button { width: 50px !important; height: 50px !important; min-height: 0 !important; border-radius: 50% !important;
    padding: 0 !important; background: #14B8A6 !important; border: 0 !important; box-shadow: 0 6px 16px rgba(20,184,166,.4) !important;
    display: flex !important; align-items: center !important; justify-content: center !important; }
  .st-key-ask_fab button span { font-size: 1.55rem !important; color: #fff !important; margin: 0 !important; }
}</style>
"""


def _gnb_go(view: str) -> None:
    """탭: 지도로 보기 / 리스트로 보기 / 물어보기."""
    if view == "ask":
        st.session_state["_gnb_ask"] = True
        return
    st.session_state["_gnb_to_map"] = True
    st.session_state["cal_view"] = view == "cal"
    st.session_state["box_view"] = view == "box"
    if view not in ("cal", "box"):
        st.session_state["list_only"] = view == "list"
    st.session_state["selected"] = None
    st.session_state["scroll_top"] = True


def _active_filters() -> int:
    """지금 걸려 있는 검색 조건 수 (검색어·작품·진행여부·날짜·캐릭터·지역·북마크)."""
    ss = st.session_state
    return sum([
        bool(str(ss.get("f_query") or "").strip()), ss.get("f_work", "전체") != "전체",
        ss.get("f_span", "진행중 + 예정") != "진행중 + 예정",
        bool(ss.get(f"f_date_{ss.get('date_ver', 0)}")),
        any(ss.get(k) for k in list(ss) if str(k).startswith("filter_chars_")),
        bool(ss.get("regions")), bool(ss.get("fav_only")),
    ])


def _toggle_search() -> None:
    ss = st.session_state
    ss["pc_filters"] = not ss.get("pc_filters", False)
    ss["m_filters"] = ss["pc_filters"]          # 모바일은 같은 버튼으로 필터 시트
    if ss["pc_filters"]:
        ss["_focus_search"] = True


def _gnb_search() -> None:
    # 위 검색칸에 쓴 글자를 아래 필터의 검색칸(f_query)으로 넘긴다 (리스트에서 바로 걸러진다)
    st.session_state["f_query"] = st.session_state.get("gnb_q", "")
    st.session_state["list_only"] = True
    st.session_state["selected"] = None


def _my_loc() -> dict | None:
    """내 위치 {'lat','lng'} (지도보기 데일리 노트 또는 메뉴바에서 받은 값). 모르면 None."""
    for key in ("_my_loc", "gnb_loc"):
        loc = st.session_state.get(key)
        if isinstance(loc, dict) and "lat" in loc:
            return loc
    return None


def _rules() -> dict[str, dict]:
    """자동 알림 규칙의 지금 값 (한 번 실행에 한 번 읽음). 표가 아직 없으면(007 전) 기본값."""
    run = st.session_state.get("_run", 0)
    cached = st.session_state.get("_rules_cache")
    if cached and cached[0] == run:
        return cached[1]
    try:
        rows = alert_rules.all_rows()
    except Exception:
        rows = []
    val = admin.rule_settings(rows)
    st.session_state["_rules_cache"] = (run, val)
    return val


def _why_html(key: str) -> str:
    return f'<div class="ntf-why">{_mi("info")} {escape(admin.why(key, _rules()))}</div>'


def _inbox(member_key: str) -> list[dict]:
    """관리자가 보낸 알림 중 켜진 규칙 것만 (공지는 정한 기간·개수만큼)."""
    rules = _rules()
    rows = admin.notices_for(notices_store.current_rows(), member_key, days=60)
    out, n_notice = [], 0
    for r in rows:
        key = admin.KIND_RULE.get(str(r.get("kind")), "notice")
        if not rules[key]["enabled"]:
            continue
        if key == "notice":
            d = admin._day(r.get("updated_at"))
            if d and (TODAY - d).days > rules["notice"]["days"]:
                continue
            n_notice += 1
            if n_notice > rules["notice"]["max_items"]:
                continue
        out.append(r)
    return out


def _notices() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """알림 두 묶음 (글자 HTML, cafe_id).
    1) 북마크한 팝업: 오픈 D-3 ~ 당일, 그리고 3일 안에 끝나는 것
    2) 내 위치 기반 추천: 지금 열려 있는 팝업 중 가까운 3곳 (북마크한 곳은 빼고)"""
    _, mine, _ = _fav_state()
    rules = _rules()
    od, ed = rules["open"]["days"], rules["end"]["days"]
    rows = [r for r in mycal.latest_rows(store.all_rows()) if r.get("status") != "deleted"]
    marks: list[tuple[str, str]] = []
    for r in rows:
        eid = str(r.get("entry_id"))
        if eid not in mine:
            continue
        s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        name = escape(f'{r.get("work") or ""} · {r.get("cafe_name") or ""}'.strip(" ·"))
        if rules["open"]["enabled"] and s and 0 <= (s - TODAY).days <= od:
            d = (s - TODAY).days
            marks.append((f"<b>{'오늘 오픈' if d == 0 else f'오픈 D-{d}'}</b> · {name}" + _why_html("open"), eid))
        elif rules["end"]["enabled"] and e and s and s <= TODAY and 0 <= (e - TODAY).days <= ed:
            d = (e - TODAY).days
            marks.append((f"<b>{'오늘 종료' if d == 0 else f'종료 D-{d}'}</b> · {name}" + _why_html("end"), eid))
    marks.sort(key=lambda t: t[0])
    near: list[tuple[str, str]] = []
    loc = _my_loc() if rules["near"]["enabled"] else None
    if loc:
        me = (float(loc["lat"]), float(loc["lng"]))
        cand = []
        for r in rows:
            s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
            try:
                pt = (float(r.get("lat")), float(r.get("lng")))
            except (TypeError, ValueError):
                continue
            if str(r.get("entry_id")) in mine or not (s and e and s <= TODAY <= e):
                continue
            cand.append((my_place._km(me, pt), r))
        for km, r in sorted(cand, key=lambda t: t[0])[:rules["near"]["max_items"]]:
            name = escape(f'{r.get("work") or ""} · {r.get("cafe_name") or ""}'.strip(" ·"))
            dist = f"{km * 1000:.0f}m" if km < 1 else f"{km:.1f}km"
            near.append((f"<b>내 주변 {dist}</b> · {name}" + _why_html("near"), str(r.get("entry_id"))))
    opens = [m for m in marks if "오픈" in m[0].split("</b>")[0]][:rules["open"]["max_items"]]
    ends = [m for m in marks if "종료" in m[0].split("</b>")[0]][:rules["end"]["max_items"]]
    return sorted(opens + ends, key=lambda t: t[0]), near


def _gnb_open(cafe_id: str) -> None:
    st.session_state["selected"] = str(cafe_id)
    st.session_state["scroll_top"] = True


NTF_COOKIE = "aw_ntf_read"


def _ntf_id(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def _ntf_read() -> set[str]:
    """읽은 알림 번호들 (브라우저 쿠키에 남겨 다시 열어도 읽음으로 보인다)."""
    if "_ntf_read" not in st.session_state:
        raw = str(st.context.cookies.get(NTF_COOKIE) or "")
        st.session_state["_ntf_read"] = {x for x in raw.split(".") if len(x) == 8}
    return st.session_state["_ntf_read"]


def _ntf_mark(ids: list[str]) -> None:
    _ntf_read().update(ids)
    st.session_state["_ntf_cookie"] = True


def _ntf_click(nid: str, cafe_id: str | None) -> None:
    """알림 칸을 누름 → 읽음 처리, 팝업이면 그 팝업 상세로 (다른 화면이면 메인으로 옮겨서)."""
    _ntf_mark([nid])
    if cafe_id:
        st.session_state.update(cal_view=False, box_view=False, _gnb_to_map=True)
        _gnb_open(cafe_id)


def _ntf_cell(nid: str, html: str, cafe_id: str | None) -> None:
    read = nid in _ntf_read()
    item = (f'<div class="ntf-item{" read" if read else ""}"><span class="ntf-st">{"읽음" if read else "새 알림"}</span>'
            f'{html}</div>')
    if not cafe_id:          # 삭제 요청 승인/거부·공지처럼 갈 팝업이 없는 알림은 글만 (누를 수 없음, '모두 읽음'으로 읽음 처리)
        st.markdown(item.replace('class="ntf-item', 'class="ntf-item plain'), unsafe_allow_html=True)
        return
    with st.container(key=f"ntfc_{nid}"):
        st.markdown(item, unsafe_allow_html=True)
        st.button("열기", key=f"ntfb_{nid}", on_click=_ntf_click, args=(nid, cafe_id))


def _gnb(current: dict | None, on_map: bool = True) -> None:
    if st.session_state.get("_cookie_pending"):     # 방금 로그인했으면 쿠키를 심는다 (메인으로 옮긴 뒤에도)
        _set_cookie(st.session_state.pop("_cookie_pending"), auth.SESSION_DAYS)
    msg = st.session_state.pop("_need_login", None)
    if msg:                                  # 손님이 북마크·리뷰·수정을 누름 → 로그인 화면으로
        st.session_state["flash"] = (msg, ":material/login:")
        go("login")
    # 상단 메뉴바: [로고] … [지도로 보기 · 리스트로 보기] (가운데) … [검색] [알림] [로그인]
    # 물어보기는 리스트 옆 대화창으로 (탭에서는 뺐다).
    if st.session_state.pop("_gnb_ask", False):
        go("ask")
    if st.session_state.pop("_gnb_to_map", False) and not on_map:
        go("map")                            # 다른 화면에서 지도·리스트·내 캘린더 탭을 누름 (메인이면 표시만 지운다)
    st.markdown(GNB_CSS, unsafe_allow_html=True)
    wide = bool(st.session_state.get("list_only"))
    with st.container(horizontal=True, key="gnb"):
        _logo_swap()
        if current:
            st.markdown(f'<style>html body .st-key-home_brand button {{ background-image: url("app/static/{FIXED_LOGO}")'
                        ' !important; }</style>', unsafe_allow_html=True)
        if st.button("ANI:WHERE", key="home_brand", type="tertiary"):
            st.session_state["selected"] = None
            st.session_state["scroll_top"] = True
            if not on_map:                     # 로그인·내 계정·등록하기 등에서 로고 → 리스트 보기 (11/18)
                st.session_state.update(list_only=True, cal_view=False, box_view=False)
                go("map")
            st.rerun()
        with st.container(horizontal=True, key="gnb_tabs"):
            cal = bool(st.session_state.get("cal_view"))
            box = bool(st.session_state.get("box_view"))
            if not on_map:
                current = {"_": "다른 화면"}       # 탭 밑줄을 모두 끈다
            tab_map = not wide and not current and not cal and not box      # (on_map 과 이름을 나눔 — 겹쳐서 +·물어보기 버튼이 사라졌다)
            on_list = wide and not current and not cal and not box
            on_cal = cal and not current
            on_box = box and not current
            st.button("지도로 보기", key=f"gnbtab_{'on_' if tab_map else ''}map", on_click=_gnb_go, args=("map",))
            st.button("리스트로 보기", key=f"gnbtab_{'on_' if on_list else ''}list", on_click=_gnb_go, args=("list",))
            if _member():                       # 내 캘린더(알림·찜·다녀온)는 로그인한 사람만
                st.button("내 캘린더", key=f"gnbtab_{'on_' if on_cal else ''}cal", on_click=_gnb_go, args=("cal",))
        if not _member():   # 알림은 로그인한 사람만: 손님이면 알림 칸(과 그것을 감싼 칸)을 숨긴다
            st.markdown("<style>.st-key-bell_guest, .st-key-gnb_right > *:has(.st-key-bell_guest) "
                        "{ display: none !important; }</style>", unsafe_allow_html=True)
        with st.container(horizontal=True, key="gnb_right"):
            # 검색 아이콘: 누르면 아래 검색 필터 줄(검색·작품·캐릭터·진행여부·날짜)을 펼치고 접는다.
            # 걸어 둔 조건이 있으면 아이콘 옆에 그 수. 모바일에서는 필터 시트를 연다
            n_on = _active_filters()
            opened = bool(st.session_state.get("pc_filters"))
            st.button(str(n_on) if n_on and not opened else "", icon=":material/close:" if opened else ":material/search:",
                      key=f"gnb_search_{'on' if opened else 'off'}", on_click=_toggle_search)
            marks, near = _notices() if _member() else ([], [])
            inbox = _inbox(str(_member()["entry_id"])) if _member() else []
            # 알림마다 번호 (같은 날 같은 글이면 같은 번호 → 읽음 유지). 종 아이콘에는 숫자 대신 안 읽은 게 있을 때만 빨간 점
            items_inbox = [(_ntf_id("i" + str(r.get("row_id"))), f'<b>{escape(str(r.get("title") or ""))}</b><br>'
                            f'{escape(str(r.get("body") or ""))}' + _why_html(admin.KIND_RULE.get(str(r.get("kind")), "notice")),
                            None) for r in inbox[:10]]
            items_marks = [(_ntf_id(f"m{TODAY}{eid}{text}"), text, eid) for text, eid in marks]
            items_near = [(_ntf_id(f"n{TODAY}{eid}"), text, eid) for text, eid in near]
            all_items = items_inbox + items_marks + items_near
            unread = [nid for nid, _, _ in all_items if nid not in _ntf_read()]
            if st.session_state.pop("_ntf_cookie", False):
                js = (f"window.parent.document.cookie = {json.dumps(NTF_COOKIE + '=' + '.'.join(sorted(_ntf_read())[-200:]))}"
                      " + '; path=/; max-age=5184000; SameSite=Lax';")
                components.html(f"<script>{js}</script>", height=0)
            if unread:
                st.markdown('<style>html body .st-key-gnb_right [data-testid="stPopover"] button::after { content: ""; '
                            'position: absolute; top: 7px; right: 7px; width: 9px; height: 9px; border-radius: 999px; '
                            'background: #FF6B6B; }</style>', unsafe_allow_html=True)
            with (st.popover("", icon=":material/notifications:") if _member() else st.container(key="bell_guest")):
                if unread:
                    st.button("모두 읽음", icon=":material/done_all:", key="ntf_all_read", type="tertiary",
                              on_click=_ntf_mark, args=(unread,))
                if items_inbox:
                    st.markdown("**받은 알림**")
                    for nid, html, cid in items_inbox:
                        _ntf_cell(nid, html, cid)
                st.markdown("**북마크한 팝업**")
                if not marks:
                    st.markdown('<div class="ntf-empty">오픈 3일 전부터 당일까지, 그리고 끝나기 3일 전부터 알려 드려요. '
                                '팝업을 북마크해 보세요.</div>', unsafe_allow_html=True)
                for nid, html, cid in items_marks:
                    _ntf_cell(nid, html, cid)
                st.markdown("**내 주변 추천**")
                if not _my_loc():
                    st.markdown('<div class="ntf-empty">위치를 허용하면 지금 열려 있는 가까운 팝업을 추천해 드려요. '
                                '브라우저 주소창의 위치 권한을 허용해 주세요.</div>', unsafe_allow_html=True)
                elif not near:
                    st.markdown('<div class="ntf-empty">지금 주변에 열려 있는 팝업이 없어요.</div>', unsafe_allow_html=True)
                for nid, html, cid in items_near:
                    _ntf_cell(nid, html, cid)
            if _is_admin() and st.button("관리자", icon=":material/admin_panel_settings:", key="admin_btn"):
                go("data")
            who = _member()
            if st.button(who["nickname"] if who else "로그인", key="login_btn"):
                go("login")
    with st.container(key="gnb_loc_box"):
        my_place.my_location(key="gnb_loc")
    # 상세에서 돌아가기는 위 '리스트로 보기 / 지도로 보기' 탭이나 로고로 (별도 '리스트로 돌아가기' 버튼은 뺐다, 11/18 요청)
    # 모바일: 등록 + 위에 물어보기 플로팅 버튼 → 팝업 대화창 (PC 는 리스트 옆 대화창이 있어 숨긴다)
    if not on_map:
        return
    st.markdown(ASK_FAB_CSS, unsafe_allow_html=True)
    if st.button("", icon=":material/forum:", key="ask_fab"):
        ask_dialog()
    # 오른쪽 아래 코랄색 + (등록) — 화면에 떠 있다 (CSS .st-key-add_btn)
    # 등록(+)은 로그인한 사람에게만 보인다 (11/18)
    if not current and _member() and st.button("", icon=":material/add:", key="add_btn", type="primary"):
        st.session_state.pop("wiz", None)     # 늘 1단계부터 시작
        go("add")


# ------------------------------------------------------------ '내 캘린더' 탭: 캘린더 + 알림 받은 내역
MYCAL_CSS = """
<style>
.mc-title { font-family: "Jua", sans-serif; font-size: 1.35rem; color: #26302D; margin: 4px 0 2px; }
.mc-sub { color: #8A9592; font-size: .82rem; margin-bottom: 10px; }
.st-key-mycal_box, .st-key-ntf_box, .st-key-keep_box { border: 1.5px solid #E3E8E6; border-radius: 16px; padding: 14px 16px !important;
  background: #fff; }
.nh-day { color: #8A9592; font-size: .78rem; font-weight: 700; margin: 14px 0 6px; }
.nh-item { display: flex; gap: 12px; align-items: center; padding: 10px 12px; border-radius: 12px; background: #F4F8F6;
  line-height: 1.45; word-break: keep-all; }
.nh-item > div { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.nh-item .nh-tag { align-self: flex-start; }
.nh-name { overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
/* 알림 받은 내역 = 데일리 팝업 노트 모양: 둥근 포스터 · 작은 태그 · 굵은 이름 한 줄, 점선으로 잇기 */
.st-key-ntf_box { padding: 12px 12px !important; }
.st-key-ntf_box .mc-title { font-family: inherit; text-align: center; color: #6B7672; font-size: .78rem; font-weight: 700; margin: 0 0 2px; }
.st-key-ntf_box .mc-sub { text-align: center; font-size: .7rem; line-height: 1.4; margin-bottom: 6px; }
.st-key-ntf_box .nh-day { font-size: .7rem; margin: 12px 0 6px; }
.st-key-ntf_box .nh-item { background: transparent; padding: 0 0 12px; gap: 10px; border-radius: 0; position: relative; }
.st-key-ntf_box [class*="st-key-nh_"]:not(:last-child) .nh-item::before { content: ""; position: absolute; left: 17px;
  top: 38px; bottom: 2px; border-left: 1.5px dashed #C9D1CE; }
.st-key-ntf_box .nh-item img { width: 36px; height: 36px; flex: 0 0 36px; border-radius: 50%; border: 1px solid #E4E8E6; }
.st-key-ntf_box .nh-item > div { gap: 3px; }
.st-key-ntf_box .nh-tag { font-size: .62rem; padding: 0 .4rem; border-radius: 5px; line-height: 1.5; margin: 0; }
.st-key-ntf_box .nh-name { font-size: .8rem; line-height: 1.25; display: block; white-space: nowrap; -webkit-line-clamp: unset; }
.st-key-ntf_box .nh-cafe { font-size: .7rem; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.st-key-ntf_box .nh-item.msg { background: #F4F8F6; border-radius: 10px; padding: 8px 10px; margin-bottom: 8px; }
.st-key-ntf_box .nh-item.msg .nh-cafe { white-space: normal; }
.st-key-ntf_box [class*="st-key-nh_"] { margin-bottom: 0; }
.st-key-ntf_box [class*="st-key-nh_"]:hover .nh-name { color: var(--accent-deep); }
.st-key-mycal_box .st-key-cal_nav { flex-wrap: nowrap; gap: 0 !important; margin-bottom: 4px; }
.st-key-mycal_box .st-key-cal_nav > * { flex-shrink: 0; }
.st-key-mycal_box .st-key-cal_nav > *:first-child { flex-shrink: 1; min-width: 0; }
.st-key-mycal_box .cal-label { font-size: .72rem; padding: .12rem .45rem; margin-right: 5px; }
.st-key-mycal_box .st-key-cal_prev button, .st-key-mycal_box .st-key-cal_next button { width: 28px; }
.st-key-mycal_box .st-key-cal_now button { height: 34px; padding: 0 .6rem !important; margin-left: 4px; }
.st-key-mycal_box .st-key-cal_now button p { font-size: .82rem !important; }
.st-key-mycal_box .cal-nick { margin: 0 0 10px; }
.st-key-mycal_box .cal-month { font-size: 1.2rem; }
/* 찜·다녀온·최근 본: 조금 작게 */
.st-key-keep_box .bxc { gap: 10px; padding: 8px; border-radius: 14px; }
.st-key-keep_box .bxc img.pst { width: 60px; height: 80px; flex-basis: 60px; border-radius: 8px; }
.st-key-keep_box .bxc .t { gap: 3px; justify-content: center; }
.st-key-keep_box .bxc .w { font-size: 1rem; }
.st-key-keep_box .bxc .c { font-size: .84rem; }
.st-key-keep_box .bxc .d { font-size: .78rem; }
.st-key-keep_box .bx-tip { padding: 9px 12px; font-size: .84rem; }
.nh-item img { width: 44px; height: 58px; object-fit: cover; border-radius: 8px; flex: 0 0 44px; }
.nh-tag { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: .72rem; font-weight: 800;
  background: #E6F6F0; color: #2E9C82; margin-bottom: 2px; }
.nh-tag.end { background: #FFECEC; color: #E05555; }
.nh-name { font-weight: 800; font-size: .92rem; color: #26302D; }
.nh-cafe { color: #6B7672; font-size: .8rem; }
.nh-why { color: #9AA5A1; font-size: .72rem; line-height: 1.35; white-space: normal; }
.nh-why::before { content: "왜? "; color: #2E9C82; font-weight: 800; }
.nh-item.msg .nh-why::before { content: ""; }
[class*="st-key-nh_"] { position: relative; margin-bottom: 6px; }
[class*="st-key-nh_btn_"] { position: absolute !important; inset: 0; z-index: 2; width: 100% !important; height: 100% !important; }
[class*="st-key-nh_btn_"] > div, [class*="st-key-nh_btn_"] .stButton { width: 100% !important; height: 100% !important; }
[class*="st-key-nh_btn_"] button { width: 100% !important; height: 100% !important; opacity: 0 !important; }
@media (max-width: 640px) {
  html body .st-key-view_tools .st-key-m_cal_btn { display: block !important; width: auto !important; }
  html body .st-key-view_tools .st-key-m_cal_btn button { height: 32px !important; min-width: 32px; padding: 0 9px !important;
    border: 1.5px solid var(--accent) !important; border-radius: 10px !important; background: #fff !important; min-height: 0 !important; }
  html body .st-key-view_tools .st-key-m_cal_btn button span { color: var(--accent-deep) !important; font-size: 1.2rem !important; }
  .st-key-mycal_mnav button { border: 1.5px solid var(--accent) !important; border-radius: 10px !important; }
}
</style>
"""


def _notice_history(days_back: int = 30) -> list[tuple[date, str, str, dict]]:
    """알림 받은 내역: 북마크한 팝업마다 '오픈 D-3 ~ 당일', '종료 D-3 ~ 당일' 알림이 생긴 날을 거꾸로 계산한다.
    (저장하지 않아도 북마크·기간만으로 같은 내역이 다시 나온다) → (알림 날, 종류, 글자, 행)"""
    _, mine, _ = _fav_state()
    rules = _rules()
    out: list[tuple[date, str, str, dict]] = []
    for r in mycal.latest_rows(store.all_rows()):
        if str(r.get("entry_id")) not in mine:
            continue
        s_, e_ = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        for kind, base in (("open", s_), ("end", e_)):
            if not base or not rules[kind]["enabled"]:
                continue
            for d in range(rules[kind]["days"], -1, -1):
                day = base - timedelta(days=d)
                if day > TODAY or (TODAY - day).days > days_back:
                    continue
                if kind == "end" and s_ and day < s_:
                    continue
                label = ("오늘 오픈" if d == 0 else f"오픈 D-{d}") if kind == "open" else ("오늘 종료" if d == 0 else f"종료 D-{d}")
                out.append((day, kind, label, r))
    out.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return out


def render_my_calendar_view() -> None:
    st.markdown(CAL_CSS + MYCAL_CSS + BOX_CSS, unsafe_allow_html=True)
    # 모바일은 메뉴바 탭이 없어서 리스트·지도로 돌아가는 아이콘을 둔다
    with st.container(horizontal=True, horizontal_alignment="right", key="mycal_mnav"):
        st.button("", icon=":material/format_list_bulleted:", key="mycal_to_list", on_click=_gnb_go, args=("list",))
        st.button("", icon=":material/map:", key="mycal_to_map", on_click=_gnb_go, args=("map",))
    st.markdown("<style>@media (min-width: 641px) { .st-key-mycal_mnav { display: none !important; } }</style>",
                unsafe_allow_html=True)
    # 순서 (11/18 요청): 왼쪽 = 내 캘린더(가장 넓게) · 가운데 = 찜·다녀온·최근 본(조금 작게) · 오른쪽 = 알림 받은 내역
    # 캘린더는 지도 보기 오른쪽 캘린더와 같은 크기, 알림은 데일리 팝업 노트와 같은 폭·모양
    left, mid, right = st.columns([1.55, 3.0, 0.9], gap="medium")
    with right, st.container(key="ntf_box"):
        st.markdown('<div class="mc-title">알림 받은 내역</div>', unsafe_allow_html=True)
        _render_notice_history()
    with left, st.container(key="mycal_box"):
        render_calendar()
    with mid, st.container(key="keep_box"):
        tab = st.session_state.get("box_tab", "fav")
        if tab not in ("fav", "visited", "recent"):
            tab = "fav"
        with st.container(horizontal=True, key="box_tabs"):
            for t, label in (("fav", "찜"), ("visited", "다녀온"), ("recent", "최근 본")):
                st.button(label, key=f"boxtab_{'on_' if tab == t else ''}{t}", on_click=_box_tab, args=(t,))
        render_box_view(tab)


def _render_notice_history() -> None:
    me = _member()
    rules = _rules()
    inbox = _inbox(str(me["entry_id"])) if me else []
    for r in inbox[:20]:                    # 공지 · 삭제 요청 처리 결과 (관리자가 보냄)
        tag = "end" if r.get("kind") == "삭제 거부" else ""
        why = admin.why(admin.KIND_RULE.get(str(r.get("kind")), "notice"), rules)
        st.markdown(f'<div class="nh-item msg" style="display:block"><span class="nh-tag {tag}">{escape(str(r.get("kind") or "알림"))}</span>'
                    f'<div class="nh-name">{escape(str(r.get("title") or ""))}</div>'
                    f'<div class="nh-cafe">{escape(str(r.get("body") or ""))}</div>'
                    f'<div class="nh-why">왜 왔나요? {escape(why)}</div>'
                    f'<div class="nh-cafe">{escape(_when(str(r.get("updated_at", ""))))}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="mc-sub">북마크한 팝업의 오픈 {rules["open"]["days"]}일 전 · 종료 {rules["end"]["days"]}일 전부터 '
                '당일까지 알림 (최근 30일)</div>', unsafe_allow_html=True)
    hist = _notice_history()
    if not hist:
        st.markdown('<div class="ntf-empty">아직 받은 알림이 없어요. 리스트에서 팝업을 북마크하면 오픈·종료가 가까울 때 '
                    '여기에 쌓여요.</div>', unsafe_allow_html=True)
    last_day = None
    for n, (day, kind, label, r) in enumerate(hist[:40]):
        if day != last_day:
            st.markdown(f'<div class="nh-day">{"오늘" if day == TODAY else f"{day.month}월 {day.day}일"}</div>',
                        unsafe_allow_html=True)
            last_day = day
        eid = str(r.get("entry_id"))
        with st.container(key=f"nh_{n}_{eid}"):
            st.markdown(
                f'<div class="nh-item"><img src="{escape(_poster_url(r.get("images")))}" alt="">'
                f'<div><span class="nh-tag{" end" if kind == "end" else ""}">{escape(label)}</span>'
                f'<div class="nh-name">{escape(str(r.get("work") or ""))}</div>'
                f'<div class="nh-cafe">{escape(str(r.get("cafe_name") or ""))}</div>'
                f'<div class="nh-why">{escape(admin.why(kind, rules))}</div></div></div>',
                unsafe_allow_html=True)
            st.button(f"{r.get('work')} 상세", key=f"nh_btn_{n}_{eid}", on_click=_gnb_open, args=(eid,))


# ------------------------------------------------------------ '보관함' 탭: 찜 · 다녀온(내가 쓴 다녀온 후기) · 최근 본
BOX_CSS = """
<style>
.bx-title { font-family: "Jua", sans-serif; font-size: 1.7rem; color: #26302D; margin: 6px 0 4px; }
.st-key-box_tabs { gap: 0 !important; border-bottom: 1.5px solid #E3E8E6; margin-bottom: 14px; }
.st-key-box_tabs button { background: transparent !important; border: 0 !important; border-radius: 0 !important; box-shadow: none !important;
  padding: 8px 16px 9px !important; border-bottom: 3px solid transparent !important; margin-bottom: -1.5px; }
.st-key-box_tabs button p { font-size: 1.1rem !important; font-weight: 700 !important; color: #9AA5A1 !important; }
.st-key-box_tabs [class*="st-key-boxtab_on_"] button { border-bottom-color: #26302D !important; }
.st-key-box_tabs [class*="st-key-boxtab_on_"] button p { color: #26302D !important; font-weight: 800 !important; }
.bx-tip { display: flex; align-items: center; gap: 8px; background: #F4F8F6; border-radius: 14px; padding: 12px 16px;
  color: #4B5260; font-size: .9rem; margin-bottom: 14px; }
.bx-empty { text-align: center; padding: 56px 12px 40px; }
.bx-empty .ic { font-family: "Material Symbols Rounded"; font-size: 4.2rem; color: #C9D6D2; line-height: 1; }
.bx-empty h4 { margin: 14px 0 4px; }
.bx-empty p { color: #8A9592; font-size: .92rem; margin: 0; }
[class*="st-key-bx_"] { position: relative; }
.bxc { display: flex; gap: 12px; background: #fff; border: 1.5px solid #E3E8E6; border-radius: 16px; padding: 10px; }
.bxc img.pst { width: 82px; height: 110px; object-fit: cover; border-radius: 10px; flex: 0 0 82px; }
.bxc .t { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.bxc .w { font-family: "Jua", sans-serif; font-size: 1.15rem; color: #2E9C82; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bxc .c { font-weight: 800; font-size: .92rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bxc .d { color: #2E9C82; font-weight: 800; font-size: .85rem; }
.bxc .st { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: .72rem; font-weight: 800; background: #E6F6F0;
  color: #2E9C82; width: fit-content; }
.bxc .st.end { background: #EEF1F0; color: #8A9592; }
.bxr { margin-top: 8px; background: #F4F8F6; border-radius: 12px; padding: 10px 12px; font-size: .88rem; line-height: 1.55; }
.bxr .stars { color: #F5A623; letter-spacing: 1px; font-size: .95rem; }
.bxr .when { color: #9AA5A1; font-size: .75rem; margin-left: 6px; }
.bxr .imgs { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.bxr .imgs img { width: 56px; height: 56px; object-fit: cover; border-radius: 8px; }
[class*="st-key-bxbtn_"] { position: absolute !important; inset: 0; z-index: 2; width: 100% !important; height: 100% !important; }
[class*="st-key-bxbtn_"] > div, [class*="st-key-bxbtn_"] .stButton { width: 100% !important; height: 100% !important; }
[class*="st-key-bxbtn_"] button { width: 100% !important; height: 100% !important; opacity: 0 !important; }
</style>
"""


def _remember_recent(cafe_id: str) -> None:
    """최근 본 팝업 (이 브라우저 세션 안에서, 최신 20개)."""
    rec = [x for x in st.session_state.get("recent_seen", []) if x != cafe_id]
    st.session_state["recent_seen"] = ([cafe_id] + rec)[:20]


def _box_tab(t: str) -> None:
    st.session_state["box_tab"] = t


def _box_card(r: dict, key: str, review_html: str = "") -> None:
    eid = str(r.get("entry_id"))
    s_, e_ = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
    md = lambda d: f"{d.month}.{d.day}" if d else ""          # noqa: E731
    state = ("종료" if e_ and e_ < TODAY else "예정" if s_ and s_ > TODAY else "진행 중") if s_ else ""
    with st.container(key=f"bx_{key}_{eid}"):
        st.markdown(
            f'<div class="bxc"><img class="pst" src="{escape(_poster_url(r.get("images")))}" alt="">'
            f'<div class="t"><span class="st{" end" if state == "종료" else ""}">{state}</span>'
            f'<div class="w">{escape(str(r.get("work") or ""))}</div><div class="c">{escape(str(r.get("cafe_name") or ""))}</div>'
            f'<div class="d">{escape(_period(r))}</div></div></div>{review_html}', unsafe_allow_html=True)
        st.button(f"{r.get('work')} 상세", key=f"bxbtn_{key}_{eid}", on_click=_gnb_open, args=(eid,))


def _box_empty(title: str, hint: str, icon: str) -> None:
    st.markdown(f'<div class="bx-empty"><div class="ic">{icon}</div><h4>{title}</h4><p>{hint}</p></div>',
                unsafe_allow_html=True)


def _box_grid(items: list[tuple[dict, str]], key: str) -> None:
    """카드 목록 (캘린더 옆 칸이라 한 줄에 한 장)."""
    for r, review_html in items:
        _box_card(r, key, review_html)


def render_box_view(tab: str) -> None:
    """내 캘린더 오른쪽 칸의 찜 · 다녀온 · 최근 본."""
    latest = {str(r.get("entry_id")): r for r in mycal.latest_rows(store.all_rows())}

    if tab == "fav":
        st.markdown(f'<div class="bx-tip">{_mi("notifications")} 찜한 팝업은 오픈·종료 3일 전부터 알림으로 알려 드려요.</div>',
                    unsafe_allow_html=True)
        _, mine, _ = _fav_state()
        rows = sorted((latest[i] for i in mine if i in latest),
                      key=lambda r: (str(r.get("end_date") or "") < TODAY.isoformat(), str(r.get("start_date") or "")))
        if not rows:
            _box_empty("아직 찜한 팝업이 없어요", "리스트나 상세에서 북마크 아이콘을 누르면 여기에 모여요.", "bookmark_add")
            return
        _box_grid([(r, "") for r in rows], "fav")

    elif tab == "visited":
        st.markdown(f'<div class="bx-tip">{_mi("rate_review")} \'다녀온 후기\'를 쓴 팝업이 여기에 모여요. 쓴 후기도 함께 보여요.</div>',
                    unsafe_allow_html=True)
        me = _me()
        mine_reviews = [r for r in reviews.current_rows()
                        if r.get("kind") == review.RATED_KIND and not r.get("parent_id") and review.can_delete(r, me)]
        by_cafe: dict[str, list[dict]] = {}
        for rv in sorted(mine_reviews, key=lambda x: str(x.get("updated_at", "")), reverse=True):
            by_cafe.setdefault(str(rv.get("cafe_id")), []).append(rv)
        items = []
        for cid, rvs in by_cafe.items():
            if cid not in latest:
                continue
            html_parts = []
            for rv in rvs:
                pics = images.paths(rv.get("images"))        # 리뷰 화면과 같은 방법으로 사진 경로를 고른다
                imgs = "".join(f'<img src="{escape(images.url(x))}" alt="">' for x in pics[:4])
                html_parts.append(
                    f'<div class="bxr"><span class="stars">{review.stars(rv.get("rating"))}</span>'
                    f'<span class="when">{escape(_when(str(rv.get("updated_at", ""))))}</span>'
                    f'<div>{escape(str(rv.get("body") or ""))}</div>'
                    f'{f"<div class=imgs>{imgs}</div>" if imgs else ""}</div>')
            items.append((latest[cid], "".join(html_parts)))
        if not items:
            _box_empty("다녀온 팝업이 없어요", "팝업 상세의 리뷰 탭에서 '다녀온 후기'를 쓰면 여기에 기록돼요.", "where_to_vote")
            return
        _box_grid(items, "visited")

    else:
        ids = [i for i in st.session_state.get("recent_seen", []) if i in latest]
        st.markdown(f'<div class="bx-tip">{_mi("history")} 이 브라우저에서 최근에 연 팝업 상세예요 (최대 20개).</div>',
                    unsafe_allow_html=True)
        if not ids:
            _box_empty("최근 본 팝업이 없어요", "리스트나 지도에서 팝업을 눌러 상세를 열면 여기에 남아요.", "history")
            return
        _box_grid([(latest[i], "") for i in ids], "recent")


def page_map() -> None:
    st.markdown(GLOBAL_CSS + LIST_CSS, unsafe_allow_html=True)
    _no_translate()
    _history_guard(on_main=True)
    _clear_buttons()    # 상단 검색칸 오른쪽 × 로 검색어 한 번에 지우기
    _keep_scroll()
    _pin_view_icon()
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
        _toast(f"노션에서 {len(synced['added'])}곳을 새로 가져왔어요", ":material/cloud_download:")
    if synced and synced.get("error"):
        st.session_state["_sync_failed"] = True       # 수집 실패: 기존 데이터를 그대로 보여 주고 아래 안내를 띄운다
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
        _gnb(current)

    report = st.session_state.pop("save_report", None)
    if report:
        show_report(report)
    if st.session_state.pop("scroll_top", False):
        _scroll_top()
    flash = st.session_state.pop("flash", None)
    if flash:
        # ('문구', 아이콘) 이면 아이콘과 함께, 글자만이면 기본 체크 아이콘
        msg, icon = flash if isinstance(flash, tuple) else (flash, ":material/check_circle:")
        _toast(msg, icon)

    if current:
        _remember_recent(str(current["entry_id"]))
    if st.session_state.get("cal_view") and not _member():
        st.session_state["cal_view"] = False
    if st.session_state.get("cal_view") and not current:
        render_my_calendar_view()
        return

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
    # 모바일 필터 버튼은 보기 전환 아이콘(지도·리스트) 바로 왼쪽의 필터 아이콘 (_view_icon_button)
    # 열면 필터 묶음이 화면을 거의 다 덮는 시트로 보인다 (MOBILE_SHEET_CSS). 닫으면 모바일에서는 숨긴다
    sheet = MOBILE_SHEET_CSS
    st.markdown(
        "<style>.st-key-m_filter_btn { display: none; }"
        "@media (max-width: 640px) { .st-key-m_filter_btn { display: block; }"
        + (sheet if m_open else " .st-key-filters { display: none !important; }") + " }</style>",
        unsafe_allow_html=True,
    )

    # PC: 검색 필터 줄은 메뉴바의 검색 아이콘을 눌렀을 때만 보인다 (접어도 걸어 둔 조건은 그대로 걸린다)
    if not ss.get("pc_filters"):
        st.markdown("<style>@media (min-width: 641px) { .st-key-filters { display: none !important; } }"
                    " :root { --apn-top: 96px; }</style>", unsafe_allow_html=True)
    with top:
        fbox = st.container(key="filters")      # 모바일 전용 칸(찜·지역)도 아래에서 이 묶음에 넣는다
    if ss.pop("_focus_search", False):
        components.html("<script>setTimeout(()=>{const i=window.parent.document.querySelector('.st-key-f_query input');"
                        "if(i){i.focus();}},350);</script>", height=0)
    with fbox, st.container(key="m_sheet_head"):
        # 모바일 필터 시트 머리: '필터' 제목과 닫기(×). PC 에서는 숨긴다
        st.markdown('<div class="sheet-title">필터</div>', unsafe_allow_html=True)
        st.button("", icon=":material/close:", key="m_sheet_close", type="tertiary",
                  on_click=lambda: ss.update(m_filters=False))
    with fbox:
        c0, c1, c4, c2, c3, c5 = st.columns([2.4, 2, 2, 2, 2, 1.1], vertical_alignment="bottom")
    with c5:
        # 검색어·작품·캐릭터·기간·특전과 목록 위의 지역·찜 필터를 한 번에 처음 값으로 돌린다 (정렬은 그대로)
        st.button("↺ 초기화", key="filter_reset", width="stretch", on_click=_reset_filters)
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
        st.multiselect("지역", areas, key="regions_m", placeholder="지역 고르기 (여러 곳 가능)",
                       on_change=lambda: ss.update(regions=ss["regions_m"]))

    # 띄어쓰기는 보지 않는다 · '아냐' 는 '아냐 포저' 로도 찾힌다 (_filter_view)
    # 팔로우한 곳만·지역·정렬은 리스트 전체보기에서만 보이고 걸린다 (지도보기에서는 숨기기만 해서 고른 값은 남는다)
    wide = bool(st.session_state.get("list_only")) and not current
    fcond = {"query": query, "work": pick_work, "chars": pick_chars, "span": span, "day": pick_day,
             "regions": st.session_state.get("regions", []) if wide else [],
             "fav": bool(st.session_state.get("fav_only")) if wide else False}
    view = _filter_view(df, fcond)
    if wide:
        view = _sort_view(view, st.session_state.get("sort", SORTS[0]))
    else:
        # 칸을 위젯으로 집어서 숨긴다 (':not(:first-child)' 로 잡으면 '팝업 카페 N곳' 칸 안의 리스트 전체보기 버튼 칸까지 숨는다)
        # 정렬 칸은 남기고(보기 전환 아이콘이 그 위에 있다) 정렬 고르기만 숨긴다
        st.markdown("<style>.st-key-listtools [data-testid='stColumn']:has([class*='st-key-folsw_'], .st-key-regions),"
                    " .st-key-listtools .st-key-sort, .st-key-m_only { display: none !important; }</style>",
                    unsafe_allow_html=True)

    # 모바일 필터 시트 맨 아래 고정 줄: 조건을 모두 지우기 + 지금 조건에 맞는 수로 결과 보기(시트 닫기)
    with fbox, st.container(horizontal=True, key="m_sheet_foot"):
        st.button("전체 삭제", key="m_sheet_reset", type="tertiary", on_click=_reset_filters)
        st.button(f"팝업 {len(view)}곳 표시", key="m_sheet_done", type="primary",
                  on_click=lambda: ss.update(m_filters=False))

    mapped = view.dropna(subset=["lat", "lng"])
    # 조건에 맞는 수·지도 표시 수·안내는 '팝업 카페 N곳' 옆 도움말(?)에 커서를 올리면 보인다
    note = (f"조건에 맞는 카페 {len(view)}곳 · 지도에 표시 가능 {len(mapped)}곳"
            + (f" · 좌표 없음 {len(view) - len(mapped)}곳" if len(view) > len(mapped) else "")
            + " · 카드나 지도의 점을 누르면 상세를 보고 리뷰를 남기거나 수정할 수 있습니다.")
    # '팝업 카페 N곳' 과 찜·지역·정렬을 목록 바로 위 한 줄에 (상단 고정 묶음에는 넣지 않고 목록과 함께 스크롤한다)
    with st.container(key="listtools"):
        # 정렬 칸 위에 보기 전환 아이콘이 있어서, 팔로우·지역 고르기는 아래(정렬과 같은 줄)에 맞춘다
        head, fav_only, region, sort = st.columns([3.2, 0.9, 2, 1.3], vertical_alignment="bottom")
    with head, st.container(key="listbar"):
        _list_bar(len(view), wide, note)
    with fav_only:
        _follow_switch("folsw")
    with region:
        # 지금 등록된 카페가 있는 지역만, 카드 배지와 같은 이름으로. 여러 곳을 함께 고를 수 있다
        st.multiselect("지역", areas, key="regions", label_visibility="collapsed",
                       placeholder="지역 고르기 (여러 곳 가능)")
    with sort:
        _view_icon_button(wide, active, m_open)
        st.selectbox("정렬", SORTS, key="sort", label_visibility="collapsed")

    _update_note()
    # '리스트 전체보기' 를 누르면 지도 없이 리스트만 크게 본다. '지도보기' 를 누르면 다시 반반으로
    if wide:
        # 리스트 전체보기: 왼쪽 목록 + 오른쪽 '팝업에게 물어보기' 대화창 (PC). 모바일은 대화창을 숨기고 위 '물어보기' 버튼으로
        lst, chat = st.columns([3.3, 1.35], gap="medium")
        with lst:
            render_list(view, wide=True, df_all=df, fcond=fcond)
        with chat, st.container(key="ask_panel"):
            render_ask_panel()
        return

    def draw_map() -> None:
        if mapped.empty:
            _empty_state(df, fcond)
            return
        clicked = kakao_map.kakao_map(
            # 점에 커서를 올리면 포스터 · 작품 · 카페 · 위치 · 기간 카드가 뜬다
            points=[{"id": str(r["entry_id"]), "lat": float(r["lat"]), "lng": float(r["lng"]),
                     "work": str(r["work"]), "cafe": str(r["cafe_name"]),
                     "address": str(r["address"] or "-"),
                     "dates": _period(r, lambda d: f"{d:%m.%d}"),
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
        with col_cal, st.container(key="ask_panel"):     # 내 캘린더 자리 → 물어보기 (캘린더는 '내 캘린더' 탭으로)
            render_ask_panel()

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
.dn-list {{ margin-top:12px; padding:0 2px; }}   /* 스크롤 없이 아래로 모두 보인다 */
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
/* 위의 보이지 않는 칸들(스타일·내 위치 칸) 사이 기본 간격 때문에 머리 상자가 16px 내려가 있었다.
   칸 사이 간격을 없애서 지도·캘린더와 위쪽 선을 맞춘다 (목록과의 사이는 .dn-list 의 margin-top) */
.st-key-map_daily {{ gap: 0 !important; }}
.st-key-map_daily .dn-list {{ margin-top: 14px; }}
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
            st.button("‹", key="daily_prev", type="tertiary", on_click=_daily_shift, args=(-1,))
            st.markdown(('<span class="dn-today">오늘</span>' if off == 0 else "")
                        + f'<span class="dn-date">{day:%y. %m. %d.} {_WEEKDAYS[day.weekday()]}</span>',
                        unsafe_allow_html=True)
            st.button("›", key="daily_next", type="tertiary", on_click=_daily_shift, args=(1,))
        with st.container(horizontal=True, key="daily_areas"):
            st.button("‹", key="daily_area_prev", type="tertiary", on_click=_daily_area_shift,
                      args=(-1, len(choices)), disabled=len(choices) < 2)
            st.markdown(f'<span class="dn-area">{escape(area)}<span>{count}</span></span>', unsafe_allow_html=True)
            st.button("›", key="daily_area_next", type="tertiary", on_click=_daily_area_shift,
                      args=(1, len(choices)), disabled=len(choices) < 2)

    if area != "전체":
        open_ = open_[open_["area"].replace("", "기타") == area]
    if open_.empty:
        st.markdown('<div class="dn-empty">이날 열려 있는 팝업이 없어요.</div>', unsafe_allow_html=True)
        return
    _, _, fcounts = _fav_state()
    rows = sorted(open_.to_dict("records"), key=lambda r: (-fcounts.get(str(r["entry_id"]), 0), r["start_date"]))
    items = "".join(
        f'<a class="dn-item" data-id="{escape(str(r["entry_id"]))}" href="./?cafe={quote(str(r["entry_id"]))}" target="_self"'
        f'>'
        f'<span class="dn-thumb" style="background-image:url(\'{_poster_url(r.get("images"))}\'), url(\'{images.DEFAULT_POSTER_URL}\')"></span>'
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
    ("작품 · 캐릭터", "movie"),
    ("카페 정보", "local_cafe"),
    ("이미지", "image"),
    ("기간", "calendar_month"),
    ("특전 · 굿즈", "redeem"),
    ("팝업 소개", "article"),
    ("등록 확인", "task_alt"),
]
ACCENT = MINT

WIZARD_CSS = f"""
<style>
.wiz-bar {{ height:6px; background:#eceff0; border-radius:2px; overflow:hidden; margin-bottom:.4rem; }}
.wiz-bar > div {{ height:100%; background:{ACCENT}; transition:width .3s; }}
.wiz-count {{ text-align:right; font-size:.8rem; color:#8a8d96; margin-bottom:.6rem; }}
/* 단계 표시줄: 동그라미(번호/체크)를 선으로 잇고 아래에 단계 이름 */
.wiz-steps {{ list-style:none; display:flex; margin:.2rem 0 1rem; padding:0; counter-reset:none; }}
.wiz-steps li {{ flex:1 1 0; position:relative; display:flex; flex-direction:column; align-items:center; gap:6px; min-width:0; }}
.wiz-steps li::before {{ content:""; position:absolute; top:14px; left:-50%; width:100%; height:3px; background:#E6ECEA; z-index:0; }}
.wiz-steps li:first-child::before {{ display:none; }}
.wiz-steps li.ws-done::before, .wiz-steps li.ws-now::before {{ background:var(--accent); }}
.ws-dot {{ position:relative; z-index:1; width:30px; height:30px; border-radius:50%; display:flex; align-items:center;
  justify-content:center; font-weight:800; font-size:.85rem; background:#fff; border:2px solid #D5DBD9; color:#98A5A1; }}
.ws-dot .mi {{ margin:0; font-size:18px; color:#fff; vertical-align:middle; }}
.ws-done .ws-dot {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
.ws-now .ws-dot {{ background:#fff; border-color:var(--accent); color:var(--accent-deep); box-shadow:0 0 0 5px var(--accent-soft); }}
.ws-name {{ font-size:.74rem; color:#98A5A1; text-align:center; word-break:keep-all; line-height:1.3; }}
.ws-done .ws-name {{ color:#4F5D59; }}
.ws-now .ws-name {{ color:var(--accent-deep); font-weight:800; }}
@media (max-width:640px) {{
  /* 좁은 화면: 지금 단계 이름만 동그라미 아래에 (나머지는 동그라미만) */
  .ws-name {{ display:none; }}
  .ws-now .ws-name {{ display:block; position:absolute; top:38px; white-space:nowrap; }}
  .wiz-steps {{ margin-bottom:1.7rem; }}
  .ws-dot {{ width:26px; height:26px; font-size:.78rem; }}
  .wiz-steps li::before {{ top:12px; }}
}}
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
            "intro": "",                # 팝업 소개 글 (간편등록은 붙여넣은 공지)
        }
    st.session_state["wiz"].setdefault("intro", "")   # 이 칸이 생기기 전에 시작한 등록도 이어서 쓸 수 있게
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
    if st.button("공지로 간편등록", icon=":material/edit_note:", width="stretch", key="quick_start"):
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
                "intro": raw.strip(),   # 붙여넣은 공지 그대로를 팝업 소개로 (칸 값은 따로 뽑는다)
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
    intro = _intro_field(w.get("intro", ""), key=f"quick_intro_{v_}")
    st.caption("붙여넣은 공지가 그대로 팝업 소개로 보여요. 필요하면 고쳐 주세요.")
    w["intro"] = intro      # '단계별로 등록하기' 로 넘어가도 고친 소개가 따라간다
    # 이미지: 단계별 등록과 같은 구성 (메인 이미지 1장 + 추가 이미지). 없어도 등록할 수 있다
    st.markdown(":material/image: **메인 이미지 (포스터)** :gray[(1장만)]")
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
    bad = _block_sensitive(name, addr, perks, goods, intro)

    if st.button("등록하기", type="primary", width="stretch", key="quick_save",
                 disabled=not ready or bad or bad_links or big):
        g = locate(entry.address, w.get("picked") if addr.strip() == w["address"] else None)
        if not g.ok:
            st.error(g.note)
            return
        # 첫 장이 포스터. 포스터 없이 추가 이미지만 올리면 그 첫 장이 포스터가 된다 (단계별 등록과 같다)
        files = ([(poster.name, poster.getvalue())] if poster else []) + [(f.name, f.getvalue()) for f in extras]
        saved = [images.save(name, data) for name, data in files]
        store.append(cafe.entry_to_row(entry, g.lat, g.lng, source="간편 등록", editor=_me(),
                                       note=f"{g.badge} ({g.matched})", intro=intro,
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
    text = st.text_area(":material/link: 참고 웹사이트", value=value, key=key, height=90,
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
        st.session_state["wiz_note"] = f":material/location_on: {g.badge} ({g.matched})"

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
            if st.button("변경", key="poster_change"):
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
            if st.button("취소", key="poster_change_cancel"):
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
    always = st.checkbox("종료일 없음 (상시)", value=pdates.is_always(w["end_date"]), key=f"always_{w['v']}")
    with d2:
        end = st.date_input("종료", value=w["start_date"] + timedelta(days=30) if pdates.is_always(w["end_date"]) else w["end_date"],
                            key=f"end_{w['v']}", disabled=always)
    if always:
        end = pdates.ALWAYS_END
    if end < start:
        st.caption("종료일이 시작일보다 빠릅니다.")

    def save():
        w["start_date"], w["end_date"] = start, end
        w["tags"] = [t for t in w["tags"] if t != pdates.TAG_ALWAYS] + ([pdates.TAG_ALWAYS] if always else [])

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


def _intro_field(value: str, key: str, label: str = "visible") -> str:
    """팝업 소개 입력칸. 등록(단계별·간편)·수정하기가 함께 쓴다."""
    return st.text_area(
        "팝업 소개", value=(value or "")[:cafe.MAX_INTRO], key=key, height=220, max_chars=cafe.MAX_INTRO,
        placeholder="어떤 팝업인지 자유롭게 소개해 주세요 (콘셉트, 메뉴, 운영 방식, 입장 방법 등)",
        help="상세 화면의 '팝업 소개' 에 그대로 보여요. 비워 둬도 등록할 수 있어요", label_visibility=label)


def _step_intro(w: dict) -> None:
    intro = _intro_field(w["intro"], key=f"intro_{w['v']}", label="collapsed")   # 카드 제목이 이미 '팝업 소개'

    st.caption("비워 둬도 괜찮아요. 쓴 내용은 상세 화면에 '팝업 소개' 로 보여요.")

    def save():
        w["intro"] = intro

    _nav(next_ok=not _block_sensitive(intro), on_next=save)


def _step_confirm(w: dict) -> None:
    """마지막 단계. 앞에서 넣은 정보를 한눈에 보여 주고, 확인되면 등록한다.
    (공지 붙여넣기는 첫 단계의 '공지로 간편등록' 에서만 한다)"""
    span = f"{w['start_date']:%Y.%m.%d} ~ {w['end_date']:%Y.%m.%d}"
    rows = [("작품", w["work"]), ("캐릭터", w["characters"]), ("카페명", w["cafe_name"]),
            ("주소", w["address"]), ("기간", span), ("특전", w["perks"]), ("굿즈", w["goods"]),
            ("이벤트", " · ".join(w["tags"])),
            ("이미지", f"{len([f for f in [w['poster'], *w['extras']] if f])}장"),
            ("팝업 소개", (w["intro"][:60] + "…") if len(w["intro"]) > 60 else w["intro"])]
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
        store.append(cafe.entry_to_row(entry, g.lat, g.lng, source="직접 등록", editor=_me(),
                                       note=f"{g.badge} ({g.matched})", intro=w["intro"],
                                       images=saved, tags=w["tags"], links=w["links"]))
        st.session_state["save_report"] = {"saved": [(entry.cafe_name, g.badge)], "blocked": []}
        st.session_state.pop("wiz", None)
        go("map")

    _nav("등록하기", next_ok=v.ok, on_next=save)


def _stepper_html(step: int) -> str:
    """등록 단계 표시줄: 번호 동그라미 + 단계 이름이 선으로 이어지고, 끝난 단계는 체크, 지금 단계는 포인트 색."""
    items = []
    for i, (name, _) in enumerate(STEPS):
        state = "done" if i < step else "now" if i == step else "todo"
        mark = _mi("check") if state == "done" else str(i + 1)
        items.append(f'<li class="ws-{state}"><span class="ws-dot">{mark}</span><span class="ws-name">{name}</span></li>')
    return f'<ol class="wiz-steps">{"".join(items)}</ol>'


def page_add() -> None:
    if not _member():               # 팝업 등록은 로그인한 사람만 (주소로 바로 들어와도 로그인 화면으로)
        st.session_state["flash"] = ("팝업 등록은 로그인하면 할 수 있어요.", ":material/login:")
        go("login")
    w = _wiz()
    step = w["step"]
    title, icon = STEPS[step]

    st.markdown(GLOBAL_CSS + WIZARD_CSS, unsafe_allow_html=True)
    _no_translate()
    _history_guard(on_main=False)
    _live_send()    # 간편등록 '읽어오기' 버튼을 공지 입력칸에 맞춰 바로 켜고 끈다
    _clear_buttons()    # 입력칸 오른쪽 × 로 한 번에 지우기
    # 메인과 같은 상단(제목·문구)이 스크롤해도 떠 있고, 문구 줄 오른쪽에 홈으로
    with st.container(key="topbar"):
        _gnb(None, on_map=False)      # 메인과 같은 메뉴바 ('홈으로 돌아가기' 는 뺐다 — 로고·탭으로 돌아간다)

    back, head, _ = st.columns([1.2, 6, 1.2], vertical_alignment="center")
    with back:
        # 첫 단계에서는 지도로, 그 뒤로는 한 단계 앞으로
        # 첫 단계에서는 돌아갈 곳이 없어 숨긴다 (메인은 위의 홈으로)
        if step > 0 and st.button("돌아가기", key="wiz_back", width="stretch"):
            _move(-1)
    with head:
        # 제목은 글자만 (누를 수 없다. 메인으로는 위의 '홈으로 돌아가기')
        st.markdown('<div class="add-title">팝업 카페 등록하기</div>', unsafe_allow_html=True)

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
        st.markdown(_stepper_html(step), unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f'<div class="wiz-title">{title}</div>', unsafe_allow_html=True)
            if step in (0, len(STEPS) - 1):
                st.markdown(f'<div class="wiz-icon">{_mi(icon)}</div>', unsafe_allow_html=True)
            err = st.session_state.pop("wiz_err", None)
            if err:
                st.error(err)
            note = st.session_state.pop("wiz_note", None)
            if note:
                st.caption(note)
            [_step_work, _step_cafe, _step_images, _step_dates, _step_extras, _step_intro,
             _step_confirm][step](w)

# ================================================================ 내 캘린더
# 찜한 팝업을 달마다 달력에 막대로 (연속된 날은 한 막대), 아래에 곧 있는 팝업 목록
CAL_COLORS = ["#14b8a6", "#F59E0B", "#8B5CF6", "#EC4899", "#3B82F6", "#22A06B", "#EF6C4D", "#64748B"]
CAL_CSS = f"""
<style>
/* 달력 머리글: 큰 '2026년 10월' · ‹ › · 테두리 있는 '이번달' */
.st-key-cal_nav {{ align-items:center !important; flex-wrap:nowrap !important; gap:6px !important; margin:4px 0 12px; }}
.st-key-cal_nav > div {{ width:auto !important; flex:0 0 auto !important; }}
.st-key-cal_nav > div:first-child {{ flex:1 1 auto !important; }}
.st-key-cal_nav [data-testid="stMarkdownContainer"] {{ margin:0 !important; }}
.st-key-cal_nav [data-testid="stMarkdownContainer"] p {{ margin:0; }}
/* 달력 제목 옆 ? : 커서를 올리거나(모바일은 누르면) 안내 말풍선 */
.cal-help {{ position:relative; display:inline-flex; align-items:center; justify-content:center; width:15px; height:15px;
  margin-left:6px; border:1px solid #B5BDBA; border-radius:50%; color:#8A9490; font-size:.66rem; font-weight:700;
  line-height:1; cursor:help; vertical-align:4px; }}
.cal-tip {{ display:none; position:absolute; top:calc(100% + 6px); left:0; z-index:60; width:210px; padding:8px 10px;
  border-radius:8px; background:#26302D; color:#fff; font-size:.74rem; font-weight:500; line-height:1.45;
  letter-spacing:0; white-space:normal; word-break:keep-all; box-shadow:0 4px 12px rgba(0,0,0,.18); }}
.cal-help:hover .cal-tip, .cal-help:focus .cal-tip {{ display:block; }}
.cal-label {{ font-weight:800; font-size:.9rem; color:var(--accent-deep); background:var(--accent-soft);
  border-radius:999px; padding:.15rem .6rem; margin-right:8px; vertical-align:4px; white-space:nowrap; }}
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
.cal-nick {{ color:#98A5A1; font-size:.78rem; margin:-12px 0 6px; }}
.cal-empty {{ color:#6B7672; font-size:.76rem; background:#F4F6F5; border-radius:8px; padding:6px 10px; margin-bottom:8px; }}
.up-empty {{ color:#6B7672; font-size:.76rem; padding:12px; border:1px dashed #D5DBD9; border-radius:10px; text-align:center; }}
/* 지도 옆 작은 캘린더 */
.st-key-map_cal .cal-month {{ font-size:1.1rem; }}
.st-key-map_cal .cal-label {{ font-size:.74rem; padding:.12rem .5rem; margin-right:6px; vertical-align:3px; }}
.st-key-cal_nav [data-testid="stMarkdownContainer"] p {{ white-space: nowrap; }}
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
            f'<div class="d">{e.start:%m.%d} ~ {"상시" if pdates.is_always(e.end) else f"{e.end:%m.%d}"}</div></div></div>')


def _upcoming_html(events: list) -> str:
    items = []
    for e in mycal.upcoming(events, TODAY):
        label, color = mycal.status(e, TODAY)
        when = _day(e.start, False) + ("" if e.start == e.end else " - 상시" if pdates.is_always(e.end) else f" - {_day(e.end, False)}")
        items.append(
            f'<a class="up-item" href="./?cafe={quote(e.cafe_id)}" target="_self">'
            f'<span class="up-bar" style="background:{_cal_color(e.work)}"></span>'
            f'<span class="up-thumb" style="background-image:url(\'{_poster_url(e.images)}\'), url(\'{images.DEFAULT_POSTER_URL}\')"></span>'
            f'<span class="up-text"><div class="up-name">{escape(e.work)} · {escape(e.cafe_name)}</div>'
            f'<div class="up-when">{when}</div></span>'
            f'<span class="up-state {color}">{escape(label)}</span></a>')
    body = "".join(items) or '<div class="up-empty">곧 있는 북마크한 팝업이 없어요. 리스트에서 북마크해 보세요.</div>'
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
        st.markdown(f'<span class="cal-label">내 캘린더</span><span class="cal-month">{year}년 {month}월</span>'
                    '<span class="cal-help" tabindex="0">?<span class="cal-tip">내가 북마크한 팝업만 달력에 보여요. '
                    '리스트나 상세의 북마크 아이콘을 누르면 여기에 추가돼요.</span></span>', unsafe_allow_html=True)
        st.button("‹", key="cal_prev", type="tertiary", on_click=_cal_shift, args=(-1,))
        st.button("›", key="cal_next", type="tertiary", on_click=_cal_shift, args=(1,))
        st.button("이번달", key="cal_now", on_click=lambda: st.session_state.pop("cal_month", None))
    # '내 캘린더' 줄 바로 아래: 내 닉네임(리뷰와 같은 IP 기반). 북마크도 이 사람 것만 보인다
    st.markdown(f'<div class="cal-nick">{escape(_nick_only(_me()))}</div>', unsafe_allow_html=True)
    if not events:
        st.markdown('<div class="cal-empty">아직 북마크한 팝업이 없어요. 리스트에서 북마크하면 달력에 일정이 채워져요.</div>',
                    unsafe_allow_html=True)
    st.markdown(_cal_html(year, month, events, compact), unsafe_allow_html=True)
    st.markdown(_upcoming_html(events), unsafe_allow_html=True)



# ------------------------------------------------------------ 2차: 간편 회원가입·로그인 (/login, /auth)
AUTH_CSS = """
<style>
.auth-title { font-family: "Jua", sans-serif; font-size: 1.6rem; color: #26302D; margin: .4rem 0 .2rem; }
.auth-sub { color: #6B7672; font-size: .9rem; margin-bottom: 1rem; line-height: 1.6; }
.auth-btn { display: flex; align-items: center; justify-content: center; gap: .5rem; width: 100%; max-width: 380px;
  height: 48px; border-radius: 12px; font-weight: 700; font-size: 1rem; text-decoration: none !important; margin: .5rem 0; }
.auth-btn.kakao { background: #FEE500; color: rgba(0,0,0,.85) !important; }
.auth-btn.naver { background: #03C75A; color: #fff !important; }
.auth-btn.off { background: #EEF1F0; color: #9AA5A1 !important; pointer-events: none; }
.auth-note { color: #6B7672; font-size: .8rem; line-height: 1.6; max-width: 420px; }
.auth-or { display: flex; align-items: center; gap: .6rem; max-width: 380px; color: #9AA5A1; font-size: .8rem;
  margin: 1rem 0 .3rem; }
.me-av { margin-bottom: 8px; }
.consent-box { background: #F4F8F6; border-radius: 12px; padding: 10px 12px; margin: 6px 0 8px; font-size: .82rem; color: #3A4542; }
.consent-box table { width: 100%; border-collapse: collapse; margin: 6px 0; }
.consent-box th { width: 44px; text-align: left; color: #2E9C82; font-weight: 800; padding: 3px 6px 3px 0; vertical-align: top; border: 0; }
.consent-box td { padding: 3px 0; border: 0; line-height: 1.5; }
.consent-box span { color: #7A8582; font-size: .76rem; }
.consent-link { font-size: .76rem; color: #8A9592; margin: 2px 0 8px; }
.consent-link a { color: #2E9C82 !important; font-weight: 700; }
.st-key-privacy_wrap { max-width: 860px; margin: 0 auto; }
.st-key-privacy_wrap table { font-size: .88rem; }
.me-avimg { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 2px solid #DDF3EC; background: #DDF3EC; }
.auth-av { display: flex; align-items: center; gap: 10px; margin: 0 0 10px; font-size: .86rem; color: #6B7672; }
.auth-av img { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; border: 1px solid #E3E8E6; }
.auth-or::before, .auth-or::after { content: ""; flex: 1; border-top: 1px solid #E3E8E6; }
/* 로그인·회원가입: 가운데 좁은 칸 (PC 에서 왼쪽으로 쏠리지 않게) */
.st-key-auth_wrap { width: 100%; max-width: 420px; margin-left: auto !important; margin-right: auto !important; }
.st-key-auth_wrap .auth-title, .st-key-auth_wrap .auth-sub, .st-key-auth_wrap .auth-note { text-align: center; }
.st-key-auth_wrap .auth-btn, .st-key-auth_wrap .auth-or, .st-key-auth_wrap .auth-card,
.st-key-auth_wrap .auth-note { max-width: 100%; margin-left: auto; margin-right: auto; }
.st-key-auth_tabs { align-items: center !important; }
.st-key-auth_wrap .auth-sub, .st-key-auth_wrap .auth-note { word-break: keep-all; }
.st-key-auth_wrap [data-testid="stPageLink"] { display: flex; justify-content: center; }
.auth-card { border: 1.5px solid #9EDDCC; border-radius: 14px; padding: 1rem 1.1rem; max-width: 460px; background: #fff; }
</style>
"""


def _set_cookie(value: str, days: int) -> None:
    """로그인 쿠키를 브라우저에 심는다 (다음에 열어도 로그인 유지). 서버는 st.context.cookies 로 읽는다."""
    secure = "; Secure" if auth.base_url().startswith("https") else ""
    js = (f"window.parent.document.cookie = {json.dumps(auth.COOKIE + '=' + value)} + "
          f"'; path=/; max-age={days * 86400}; SameSite=Lax{secure}';")
    components.html(f"<script>{js}</script>", height=0)


def _login_done(row: dict, msg: str) -> None:
    st.session_state["member_key"] = str(row["entry_id"])
    st.session_state.pop("_logged_out", None)
    st.session_state.pop("_member_cache", None)
    st.session_state.pop("_fav_cache", None)
    st.session_state["_cookie_pending"] = auth.make_session(str(row["entry_id"]), str(row.get("provider", "")))
    st.session_state["flash"] = (msg, ":material/waving_hand:")


PRIVACY_URL = "./privacy"
PRIVACY_FILE = Path(__file__).resolve().parent / "docs" / "privacy-policy.md"


def page_privacy() -> None:
    """개인정보처리방침 · 이용약관 (상시 공개, 로그인 없이 누구나). 내용은 docs/privacy-policy.md 한 곳."""
    st.markdown(GLOBAL_CSS + AUTH_CSS, unsafe_allow_html=True)
    _no_translate()
    with st.container(key="topbar"):
        _gnb(None, on_map=False)
    with st.container(key="privacy_wrap"):
        try:
            st.markdown(PRIVACY_FILE.read_text(encoding="utf-8"))
        except OSError:
            st.warning("개인정보처리방침을 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.", icon=":material/error:")


def page_login() -> None:
    st.markdown(GLOBAL_CSS + AUTH_CSS, unsafe_allow_html=True)
    _no_translate()
    with st.container(key="topbar"):
        _gnb(None, on_map=False)      # 메인과 같은 메뉴바
    if st.session_state.get("_cookie_pending"):          # 방금 로그인했으면 쿠키를 심는다
        _set_cookie(st.session_state.pop("_cookie_pending"), auth.SESSION_DAYS)
    flash = st.session_state.pop("flash", None)
    if flash:
        if isinstance(flash, tuple):
            _toast(*flash)
        else:
            _toast(flash)
    with st.container(key="auth_wrap"):         # 로그인·회원가입은 화면 가운데 좁은 칸에
        _login_body()


def _login_body() -> None:
    row = _member()
    if row:
        _my_account(row)
        return
    with st.container(key="auth_tabs"):        # 탭을 가운데에 두려고 따로 묶는다
        mode = st.segmented_control("로그인 또는 회원가입", ["로그인", "회원가입"], default="로그인",
                                    label_visibility="collapsed", key="auth_mode") or "로그인"
    if mode == "로그인":
        st.markdown('<div class="auth-title">다시 오셨네요</div>'
                    '<div class="auth-sub">아이디로 가입했다면 아래에, 카카오·네이버로 가입했다면 그 버튼으로 로그인해요.</div>',
                    unsafe_allow_html=True)
        _password_login_form()
        st.markdown('<div class="auth-or">또는 간편 로그인</div>', unsafe_allow_html=True)
        verb = "로그인"
    else:
        st.markdown('<div class="auth-title">3초 만에 회원가입</div>'
                    '<div class="auth-sub"><b>아이디·비밀번호·닉네임</b>만 있으면 가입돼요. 이메일·전화번호는 받지 않아요.<br>'
                    '카카오·네이버 계정이 있으면 아래 간편 가입으로 비밀번호 없이도 가입할 수 있어요.<br>'
                    '가입하면 북마크·리뷰가 <b>어느 기기에서나</b> 내 것으로 남고, 손님일 때 해 둔 북마크도 옮겨 와요.</div>',
                    unsafe_allow_html=True)
        _password_signup_form()
        st.markdown('<div class="auth-or">또는 간편 가입</div>', unsafe_allow_html=True)
        verb = "가입하기"
    for prov in ("kakao", "naver"):
        label = auth.PROVIDERS[prov]["label"]
        if auth.enabled(prov):
            # 새 탭으로 연다: 배포 사이트(Streamlit Cloud)는 앱을 iframe 안에 띄우는데, 카카오·네이버 로그인 화면은
            # iframe 안에서 열리기를 거부하고("연결을 거부했습니다"), 그 iframe 은 바깥 창 이동(_top)도 막는다
            # (sandbox 에 allow-top-navigation 없음, allow-popups 는 있음). 로그인이 끝나면 새 탭에서 로그인된 상태가 된다
            st.markdown(f'<a class="auth-btn {prov}" href="{escape(auth.authorize_url(prov))}" target="_blank" rel="noopener">'
                        f'{label}로 {verb}</a>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="auth-btn off">{label} {verb} 준비 중</span>', unsafe_allow_html=True)
    st.markdown('<div class="auth-note">로그인하지 않아도 지금처럼 둘러보고 북마크할 수 있어요.</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="auth-note">받는 정보: <b>별명(닉네임)</b>과 계정 고유 번호뿐이에요. 고유 번호는 알아볼 수 없게 '
                '바꿔서(해시) 저장하고, 이메일·전화번호·실명은 받지도 저장하지도 않아요.</div>', unsafe_allow_html=True)
    if not (auth.enabled("kakao") or auth.enabled("naver")):
        st.caption("관리자 안내: .env 에 AUTH_SECRET · KAKAO_LOGIN_CLIENT_ID · NAVER_LOGIN_CLIENT_ID/SECRET 을 넣으면 "
                   "버튼이 켜져요 (docs/login.md).")


def _password_login_form() -> None:
    """아이디·비밀번호 로그인. 5번 틀리면 5분 동안 잠근다 (무작위 대입 늦추기)."""
    ss = st.session_state
    locked = ss.get("_pw_lock_until", 0) - time.time()
    with st.form("pw_login", border=False):
        lid = st.text_input("아이디", max_chars=20, autocomplete="username")
        pw = st.text_input("비밀번호", type="password", max_chars=auth.PW_MAX, autocomplete="current-password")
        go_in = st.form_submit_button("로그인", type="primary", icon=":material/login:", width="stretch")
    if not go_in:
        return
    if locked > 0:
        st.warning(f"비밀번호를 여러 번 틀려서 잠시 막았어요. {int(locked // 60) + 1}분 뒤 다시 시도해 주세요.",
                   icon=":material/lock_clock:")
        return
    try:
        key = auth.check_password(lid, pw)
    except auth.AuthError as e:
        st.warning(str(e), icon=":material/error:")
        return
    row = auth.find(members, key) if key else None
    if not row:
        ss["_pw_fails"] = ss.get("_pw_fails", 0) + 1
        if ss["_pw_fails"] >= auth.MAX_FAILS:
            ss["_pw_lock_until"], ss["_pw_fails"] = time.time() + auth.LOCK_SECONDS, 0
        st.warning("아이디나 비밀번호가 맞지 않아요.", icon=":material/error:")   # 어느 쪽이 틀렸는지는 알려 주지 않는다
        return
    ss.pop("_pw_fails", None)
    _login_done(row, f"{row['nickname']}님, 다시 오셨네요!")
    go("map")                                # 로그인하면 메인으로 (11/18)


PRIVACY_TABLE = {
    "local": "아이디 · 일방향 암호화한 비밀번호 · 닉네임 · 동의 시각",
    "social": "로그인 수단 · 계정 번호를 되돌릴 수 없게 바꾼 값 · 닉네임 · 동의 시각",
}


def _consent_boxes(kind: str, key: str, photo_label: str | None = None) -> dict:
    """가입 동의: 필수(만 14세 이상 · 이용약관 · 개인정보 수집·이용)와 선택(프로필 사진)을 따로 받는다.
    무엇을·왜·얼마나 보관하는지 바로 보이게 표로 고지한다 (11/18 개인정보 설계)."""
    st.markdown(
        '<div class="consent-box"><b>개인정보 수집·이용 안내</b>'
        '<table><tr><th>항목</th><td>' + PRIVACY_TABLE[kind] + '</td></tr>'
        '<tr><th>목적</th><td>회원 식별·로그인, 리뷰 작성자 표시, 북마크·알림</td></tr>'
        '<tr><th>보관</th><td><b>탈퇴할 때까지</b> (탈퇴하면 지난 기록까지 바로 지워요)</td></tr></table>'
        '<span>이메일·전화번호·실명은 받지 않아요. 동의하지 않으면 가입할 수 없지만, 로그인 없이도 둘러볼 수 있어요.</span></div>',
        unsafe_allow_html=True)
    out = {
        "age": st.checkbox("[필수] 만 14세 이상이에요", key=f"{key}_age"),
        "terms": st.checkbox("[필수] 이용약관에 동의해요", key=f"{key}_terms"),
        "privacy": st.checkbox("[필수] 위 개인정보 수집·이용에 동의해요", key=f"{key}_priv"),
        "photo": st.checkbox(photo_label, key=f"{key}_photo") if photo_label else False,
    }
    st.markdown(f'<div class="consent-link">전문 보기: <a href="{PRIVACY_URL}" target="_blank">개인정보처리방침 · 이용약관</a>'
                ' · 만 14세 미만은 가입할 수 없어요 (법정대리인 동의 절차를 갖추지 않았어요)</div>', unsafe_allow_html=True)
    return out


def _consent_error(c: dict) -> str:
    if not c["age"]:
        return "만 14세 이상만 가입할 수 있어요."
    if not (c["terms"] and c["privacy"]):
        return "필수 항목(이용약관 · 개인정보 수집·이용)에 동의해야 가입할 수 있어요."
    return ""


def _password_signup_form() -> None:
    """일반 회원가입: 필수 정보(아이디·비밀번호·닉네임·동의)만 받는다."""
    with st.form("pw_signup", border=False):
        lid = st.text_input("아이디 (필수)", max_chars=20, placeholder="영어 소문자·숫자·_ 4~20자",
                            autocomplete="username")
        pw = st.text_input("비밀번호 (필수)", type="password", max_chars=auth.PW_MAX,
                           placeholder="영문+숫자 8자 이상", autocomplete="new-password")
        pw2 = st.text_input("비밀번호 확인 (필수)", type="password", max_chars=auth.PW_MAX, autocomplete="new-password")
        nick = st.text_input("닉네임 (필수)", max_chars=auth.MAX_NICK,
                             placeholder="2~16자 · 비워 두면 '느긋한 품바' 처럼 자동으로 지어 드려요")
        st.caption("다른 회원과 같은 닉네임, 욕설·음란한 말, 관리자·운영자처럼 보이는 이름은 쓸 수 없어요.")
        consent = _consent_boxes("local", "pwc")
        st.caption("이메일·전화번호를 받지 않아서 비밀번호를 잊으면 찾을 수 없어요. 꼭 기억해 두세요. "
                   "프로필 사진(선택)은 가입한 뒤 마이페이지에서 올릴 수 있어요.")
        done = st.form_submit_button("가입하기", type="primary", icon=":material/person_add:", width="stretch")
    if not done:
        return
    err = _consent_error(consent)
    if err:
        st.warning(err, icon=":material/error:")
        return
    try:
        if not " ".join(str(nick or "").split()):      # 닉네임을 비워 두면 '꾸밈말 + 캐릭터' 로 자동 (11/18)
            nick = _auto_nick(str(lid).strip().lower())
        row = auth.register_password(members, lid, pw, pw2, nick)
    except auth.AuthError as e:
        st.warning(str(e), icon=":material/error:")
        return
    moved = _move_guest_favs(row)
    _login_done(row, "가입했어요!" + (f" 북마크 {moved}개도 옮겼어요." if moved else ""))
    go("map")


def _move_guest_favs(row: dict) -> int:
    """손님일 때 해 둔 북마크를 회원 계정으로 옮긴다 (지우지 않고 회원 쪽에 새로 쌓음)."""
    guest = favorite.user_key(st.context.ip_address)
    moved = sorted(favorite.mine(favs.current_rows(), guest))
    for cid in moved:
        favorite.toggle(favs, cid, f"m:{row['entry_id']}", True)
    return len(moved)


def _logout() -> None:
    _set_cookie("", 0)
    st.session_state.update({"member_key": "", "_logged_out": True})
    st.session_state.pop("_member_cache", None)
    st.session_state.pop("_fav_cache", None)


def _avatar_saved(msg: str) -> None:
    st.session_state["_av_n"] = st.session_state.get("_av_n", 0) + 1      # 올리기 칸 비우기
    st.session_state.pop("_member_cache", None)
    st.session_state.pop("_avatar_cache", None)
    st.session_state["flash"] = (msg, ":material/check_circle:")
    st.rerun()


def _my_account(row: dict) -> None:
    prov = auth.PROVIDER_LABEL.get(str(row.get("provider")), "")
    st.markdown(f'<div class="auth-title">내 계정</div><div class="auth-card">'
                f'<div class="me-av">{_avatar_img(row.get("avatar"), 72, "me-avimg")}</div>'
                f'<b>{escape(_nick_only(auth.display_name(row)))}</b><br><span class="auth-note">{escape(prov)} 계정으로 로그인 중 · '
                f'가입 {escape(str(row.get("agreed_at", ""))[:10])}<br>회원 번호 <code>{escape(str(row["entry_id"]))}</code>'
                f'{" · 관리자" if _is_admin() else ""}</span></div>', unsafe_allow_html=True)
    with st.expander("프로필 사진 바꾸기"):
        st.caption("리뷰 옆에 동그랗게 보여요. 선택이에요 — 없으면 기본 그림이 보여요. 사람 얼굴·개인정보가 든 사진은 피해 주세요.")
        n = st.session_state.get("_av_n", 0)
        up = st.file_uploader("사진 올리기 (png·jpg·webp, 5MB까지)", type=["png", "jpg", "jpeg", "webp"], key=f"av_up_{n}")
        ok_photo = st.checkbox("[선택] 프로필 사진 수집·이용에 동의해요 — 리뷰 옆 표시용, '기본 그림으로'를 누르면 바로 지워요",
                               key=f"av_agree_{n}")
        c1, c2 = st.columns(2)
        if c1.button("이 사진으로 저장", type="primary", width="stretch", disabled=up is None or not ok_photo, key="av_save"):
            data = up.getvalue()
            if images.too_big(data, 5):
                st.warning("5MB 이하 사진만 올릴 수 있어요.", icon=":material/error:")
            else:
                auth.set_avatar(members, row, images.save(up.name, data))
                _avatar_saved("프로필 사진을 바꿨어요.")
        if c2.button("기본 그림으로", width="stretch", key="av_default"):
            auth.set_avatar(members, row, "none")
            _avatar_saved("기본 그림으로 바꿨어요.")
        if row.get("provider") in ("kakao", "naver"):
            st.caption(f'{auth.PROVIDER_LABEL[row["provider"]]} 프로필 사진은 가입할 때 [선택] 항목에 동의하면 불러와요.')
    with st.form("rename", border=False):
        nick = st.text_input("닉네임 바꾸기", value=row.get("nickname", ""), max_chars=auth.MAX_NICK)
        if st.form_submit_button("저장", icon=":material/check:"):
            try:
                auth.rename(members, row, nick)
                st.session_state.pop("_member_cache", None)
                st.session_state["flash"] = ("닉네임을 바꿨어요.", ":material/check_circle:")
                st.rerun()
            except auth.AuthError as e:
                st.warning(str(e), icon=":material/error:")
    local = row.get("provider") == "local"
    if local:
        with st.expander("비밀번호 바꾸기"):
            with st.form("pw_change", border=False):
                lid = st.text_input("아이디", max_chars=20)
                old = st.text_input("지금 비밀번호", type="password")
                new = st.text_input("새 비밀번호", type="password", placeholder="영문+숫자 8자 이상")
                new2 = st.text_input("새 비밀번호 확인", type="password")
                if st.form_submit_button("바꾸기", icon=":material/check:"):
                    try:
                        auth.change_password(lid, old, new, new2)
                        st.session_state["flash"] = ("비밀번호를 바꿨어요.", ":material/check_circle:")
                        st.rerun()
                    except auth.AuthError as e:
                        st.warning(str(e), icon=":material/error:")
    st.markdown(f'<div class="consent-link"><a href="{PRIVACY_URL}" target="_blank">개인정보처리방침 · 이용약관</a></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("로그아웃", icon=":material/logout:", width="stretch"):
        _logout()
        st.session_state["flash"] = ("로그아웃했어요.", ":material/logout:")
        st.rerun()
    with c2.popover("탈퇴하기", icon=":material/person_remove:", width="stretch"):
        st.write("닉네임·프로필 사진·아이디와 비밀번호·접속 기록을 **지난 기록까지 바로 지워요**. "
                 "쓴 리뷰는 다른 이용자를 위해 '탈퇴한 회원'으로 남아요 (지우고 싶은 글은 먼저 삭제 요청해 주세요).")
        if local:
            st.caption("아이디로 가입했다면 확인을 위해 아이디·비밀번호를 넣어 주세요. 비밀번호 기록도 지워요.")
            w_id = st.text_input("아이디", key="w_id")
            w_pw = st.text_input("비밀번호", type="password", key="w_pw")
        if st.button("탈퇴할게요", type="primary"):
            if local:
                try:
                    auth.drop_password(w_id, w_pw)
                except auth.AuthError as e:
                    st.warning(str(e), icon=":material/error:")
                    st.stop()
            auth.withdraw(members, row)
            auth.purge_withdrawn(str(row["entry_id"]))     # 개인정보 파기 (지난 기록까지)
            _logout()
            st.session_state["flash"] = ("탈퇴했어요. 그동안 고마웠어요.", ":material/check_circle:")
            st.rerun()


def page_auth() -> None:
    """카카오·네이버가 돌려보내는 곳. 처음 온 사람은 여기서 간편 가입(닉네임·동의)을 한다."""
    st.markdown(GLOBAL_CSS + AUTH_CSS, unsafe_allow_html=True)
    _no_translate()
    with st.container(key="topbar"):
        _gnb(None, on_map=False)      # 메인과 같은 메뉴바
    with st.container(key="auth_wrap"):
        _auth_body()


def _auth_body() -> None:
    qp = st.query_params
    if qp.get("error"):            # 동의 화면에서 '취소' — 중간 이탈
        st.query_params.clear()
        st.info("로그인을 취소했어요. 로그인하지 않아도 둘러보고 북마크할 수 있어요.", icon=":material/info:")
        st.page_link(PAGES["map"], label="홈으로", icon=":material/home:")
        return
    if qp.get("code") and qp.get("state"):
        code, state = qp["code"], qp["state"]
        st.query_params.clear()        # code 는 한 번만 쓸 수 있다. 새로고침해도 다시 쓰지 않게 주소에서 지운다
        try:
            ident = auth.exchange(code, state)
        except auth.AuthError as e:
            st.warning(str(e), icon=":material/error:")
            st.page_link(PAGES["login"], label="다시 로그인하기", icon=":material/login:")
            return
        row = auth.find(members, ident.member_key)
        if row:
            _login_done(row, f"{row['nickname']}님, 다시 오셨네요!")
            go("map")
            return
        st.session_state["_pending_ident"] = ident
    ident = st.session_state.get("_pending_ident")
    if not ident:
        st.info("로그인 화면에서 시작해 주세요.", icon=":material/info:")
        st.page_link(PAGES["login"], label="로그인하기", icon=":material/login:")
        return
    label = auth.PROVIDERS[ident.provider]["label"]
    st.markdown(f'<div class="auth-title">거의 다 됐어요</div><div class="auth-sub">{label} 계정으로 처음 오셨어요. '
                '앱에서 쓸 닉네임만 정하면 가입이 끝나요.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="auth-av">{_avatar_img(ident.avatar, 48, "")}'
                + (f"{label} 프로필 사진이 있어요. 아래 [선택] 항목에 동의하면 리뷰 옆에 보여요." if ident.avatar
                   else "프로필 사진은 선택이에요. 마이페이지에서 언제든 올릴 수 있어요.") + '</div>', unsafe_allow_html=True)
    with st.form("signup", border=False):
        nick = st.text_input("닉네임", value=ident.nickname, max_chars=auth.MAX_NICK,
                             placeholder="2~16자 · 비워 두면 '느긋한 품바' 처럼 자동으로 지어 드려요")
        st.caption("다른 회원과 같은 닉네임, 욕설·음란한 말, 관리자·운영자처럼 보이는 이름은 쓸 수 없어요.")
        consent = _consent_boxes("social", "soc", f"[선택] {label} 프로필 사진을 불러와 리뷰 옆에 보여 줘요 (사진 주소 저장, "
                                 "마이페이지에서 언제든 지울 수 있어요)" if ident.avatar else None)
        done = st.form_submit_button("가입하고 시작하기", type="primary", icon=":material/check:")
    if done:
        err = _consent_error(consent)
        if err:
            st.warning(err, icon=":material/error:")
            return
        if not consent["photo"]:                 # 사진은 선택 동의한 경우에만 저장
            ident = dataclasses.replace(ident, avatar="none")
        try:
            if not " ".join(str(nick or "").split()):
                nick = _auto_nick(ident.member_key)
            row = auth.signup(members, ident, nick)
        except auth.AuthError as e:
            st.warning(str(e), icon=":material/error:")
            return
        # 손님일 때 해 둔 북마크를 회원 계정으로 옮긴다 (지우지 않고 회원 쪽에 새로 쌓음)
        guest = favorite.user_key(st.context.ip_address)
        moved = sorted(favorite.mine(favs.current_rows(), guest))
        for cid in moved:
            favorite.toggle(favs, cid, f"m:{row['entry_id']}", True)
        st.session_state.pop("_pending_ident", None)
        _login_done(row, "가입했어요!" + (f" 북마크 {len(moved)}개도 옮겼어요." if moved else ""))
        go("map")


# ------------------------------------------------------------ 2차: 데이터 보기 (/data)
DATA_TABLES = {"cafes": "팝업", "reviews": "리뷰", "favorites": "북마크", "members": "회원",
               "del_requests": "삭제 요청", "notices": "알림", "visits": "접속"}
DATA_HIDE = {"members": [], "favorites": ["user"], "reviews": [], "cafes": [], "del_requests": [], "notices": [],
             "visits": []}


DEFAULT_ADMIN = "f37119a9dd2d4c0b"        # 관리자 회원 번호 (공개돼도 되는 값: 로그인해야 그 회원이 된다)


def _is_admin() -> bool:
    """관리자: ADMIN_MEMBER_KEYS(쉼표로 구분한 회원 번호)에 든 회원만. 비워 두면 기본 관리자 한 명 (11/18 지정).
    나머지 가입자는 모두 일반 회원이다."""
    row = _member()
    keys = {k.strip() for k in (os.getenv("ADMIN_MEMBER_KEYS") or DEFAULT_ADMIN).split(",") if k.strip()}
    return bool(row) and str(row["entry_id"]) in keys


# ------------------------------------------------------------ 관리자 대시보드 (/data)
ADMIN_CSS = """
<style>
.adm-eyebrow { font-size: .72rem; letter-spacing: .14em; color: #8A9592; font-weight: 700; margin-top: 6px; }
.adm-title { font-family: "Jua", sans-serif; font-size: 2rem; color: #26302D; line-height: 1.15; margin: 2px 0 2px; }
.adm-sub { color: #6B7672; font-size: .88rem; margin-bottom: 12px; }
/* 큰 보기 탭 */
.st-key-adm_tabs { gap: 0 !important; border-bottom: 2px solid #DDE5E2; margin: 6px 0 14px; flex-wrap: wrap; }
.st-key-adm_tabs button { background: transparent !important; border: 0 !important; border-radius: 0 !important; box-shadow: none !important;
  padding: 10px 18px 9px !important; border-bottom: 3px solid transparent !important; margin-bottom: -2px; }
.st-key-adm_tabs button p { font-size: 1rem !important; font-weight: 700 !important; color: #8A9592 !important; }
.st-key-adm_tabs [class*="st-key-admtab_on_"] button { border-bottom-color: #14B8A6 !important; }
.st-key-adm_tabs [class*="st-key-admtab_on_"] button p { color: #26302D !important; font-weight: 800 !important; }
/* 숫자 카드 */
.adm-kpis { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
.adm-kpi { background: #fff; border: 1px solid #DDE5E2; border-radius: 12px; padding: 12px 14px; display: grid; gap: 2px; }
.adm-kpi b { font-size: 1.6rem; font-weight: 800; color: #26302D; line-height: 1.1; font-variant-numeric: tabular-nums; }
.adm-kpi span { font-size: .78rem; color: #6B7672; }
.adm-kpi b small { font-size: .95rem; font-weight: 700; color: #6B7672; margin-left: 3px; }
.adm-kpi em { font-style: normal; font-size: .72rem; color: #9AA5A1; }
.adm-kpi.alert b { color: #E05555; }
.st-key-adm_kpis { gap: 10px !important; flex-wrap: wrap; margin-bottom: 14px; }
.st-key-adm_kpis > * { flex: 1 1 150px !important; min-width: 0; }
[class*="st-key-admk_"] { position: relative; }
[class*="st-key-admk_"] .adm-kpi { cursor: pointer; transition: border-color .15s; }
[class*="st-key-admk_"]:hover .adm-kpi { border-color: #14B8A6; }
[class*="st-key-admk_on_"] .adm-kpi { border: 2px solid #14B8A6; background: #F1FAF7; }
[class*="st-key-admkb_"], [class*="st-key-admlb_"] { position: absolute !important; inset: 0; z-index: 2; width: 100% !important; height: 100% !important; }
[class*="st-key-admkb_"] > div, [class*="st-key-admkb_"] .stButton, [class*="st-key-admlb_"] > div, [class*="st-key-admlb_"] .stButton {
  width: 100% !important; height: 100% !important; }
[class*="st-key-admkb_"] button, [class*="st-key-admlb_"] button { width: 100% !important; height: 100% !important; opacity: 0 !important; cursor: pointer; }
[class*="st-key-admli_"] { position: relative; }
[class*="st-key-admli_"]:hover .adm-card { border-color: #14B8A6; }
a.adm-link, a.adm-link:visited { text-decoration: none !important; color: inherit !important; }
a.adm-card.adm-link { cursor: pointer; }
a.adm-card.adm-pcard { display: flex !important; gap: 14px !important; align-items: center; }
a.adm-card.adm-pcard img { width: 44px; height: 60px; object-fit: cover; border-radius: 6px; flex: 0 0 44px; background: #F4F6F5;
  margin-right: 2px; }
.adm-pcard > div { min-width: 0; display: grid; gap: 1px; }
a.adm-card.adm-link:hover { border-color: #14B8A6; }
.gt-lab a.adm-link:hover b { color: #14B8A6; text-decoration: underline; }
.adm-kpilist { margin: 0 0 10px; }
.adm-kgrid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.adm-kgrid .adm-card { margin: 0; }
@media (max-width: 900px) { .adm-kgrid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .adm-kgrid { grid-template-columns: 1fr; } }
.adm-kpi span { display: flex; justify-content: space-between; align-items: center; }
.adm-kpi .kpi-arr { font-size: 1.1rem; color: #9AA5A1; }
[class*="st-key-admk_on_"] .adm-kpi .kpi-arr { color: #14B8A6; }
.st-key-adm_kpi_foot { margin-bottom: 14px; }
.adm-card .adm-go { float: right; color: #9AA5A1; font-size: .74rem; }
@media (max-width: 900px) { .adm-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
/* 칸반 */
.adm-col { background: #F6F9F8; border: 1px solid #DDE5E2; border-radius: 12px; padding: 10px; min-height: 120px; }
.adm-colhead { display: flex; justify-content: space-between; align-items: center; font-weight: 800; font-size: .95rem;
  padding: 2px 4px 8px; border-bottom: 3px solid var(--c); margin-bottom: 8px; color: #26302D; }
.adm-colhead small { font-size: .8rem; color: #6B7672; font-weight: 700; }
.adm-card { background: #fff; border: 1px solid #E3E8E6; border-radius: 10px; padding: 8px 10px; margin-bottom: 6px; display: grid; gap: 1px; }
.adm-card b { font-size: .86rem; color: #26302D; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.adm-card span { font-size: .76rem; color: #6B7672; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.adm-card em { font-style: normal; font-size: .74rem; color: #2E9C82; font-weight: 700; }
.adm-empty { color: #9AA5A1; font-size: .82rem; padding: 10px 4px; }
/* 패널 · 요청 줄 */
.adm-panel-h { font-weight: 800; font-size: 1rem; color: #26302D; margin: 4px 0 6px; }
.adm-req { display: grid; grid-template-columns: 4px minmax(0, 1fr); gap: 10px; border: 1px solid #DDE5E2; border-radius: 12px;
  padding: 10px 12px; background: #fff; margin-bottom: 4px; }
.adm-req .rail { border-radius: 2px; background: var(--st); }
.adm-req .t { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: .9rem; font-weight: 700; }
.adm-req .d { font-size: .8rem; color: #6B7672; margin-top: 2px; }
.adm-pill { display: inline-block; font-size: .7rem; font-weight: 800; border-radius: 999px; padding: 1px 8px; border: 1px solid var(--st); color: var(--st); }
.adm-info { background: #F4F8F6; border-radius: 12px; padding: 12px 14px; font-size: .86rem; line-height: 1.7; color: #3A4542; }
.adm-info b { color: #2E9C82; }
/* 주 단위 간트 */
.gt { border: 1px solid #DDE5E2; border-radius: 12px; background: #fff; padding: 10px 12px; margin: 4px 0 14px; }
.gt-row { display: grid; grid-template-columns: minmax(120px, 230px) minmax(0, 1fr); gap: 10px; align-items: center; min-height: 26px; }
.gt-row + .gt-row { border-top: 1px dashed #EEF1F0; }
.gt-lab { font-size: .8rem; color: #26302D; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gt-lab b { font-weight: 800; }
.gt-lab span { color: #8A9592; }
.gt-track { position: relative; height: 26px; }
.gt-wk { position: absolute; top: 0; bottom: 0; background: #E6F6F0; }
.gt-today { position: absolute; top: 0; bottom: 0; width: 2px; background: #FF6B6B; }
.gt-bar { position: absolute; top: 6px; height: 14px; border-radius: 4px; background: var(--c); }
.gt-head .gt-track { height: 20px; }
.gt-tick { position: absolute; top: 0; font-size: .72rem; color: #6B7672; font-weight: 700; transform: translateX(-50%); white-space: nowrap; }
.gt-grid { position: absolute; top: 0; bottom: 0; width: 1px; background: #EEF1F0; }
.gt-bar.cl { border-top-left-radius: 0; border-bottom-left-radius: 0; }
.gt-bar.cr { border-top-right-radius: 0; border-bottom-right-radius: 0; }
.gt-legend { display: flex; flex-wrap: wrap; gap: 12px; font-size: .76rem; color: #6B7672; margin: 6px 0 0; }
.gt-legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 4px; vertical-align: -1px; }
.adm-metric-h { display: flex; justify-content: space-between; align-items: baseline; margin: 14px 0 2px; }
.adm-metric-h b { font-weight: 800; font-size: 1rem; color: #26302D; }
.adm-metric-h span { font-size: .86rem; color: #6B7672; }
.adm-metric-h span strong { font-size: 1.1rem; color: #26302D; }
</style>
"""
ADMIN_TABS = [("board", "팝업 현황"), ("usage", "이용 지표"), ("requests", "삭제 요청"), ("notices", "알림 관리"),
              ("members", "회원 정보"), ("raw", "원본 데이터")]
ST_COLOR = {"pending": "#D9821B", "approved": "#23866A", "rejected": "#C8352A"}
ST_LABEL = {"pending": "대기", "approved": "승인", "rejected": "거부"}


def _adm_tab(t: str) -> None:
    st.session_state["adm_tab"] = t


def _adm_week(delta: int) -> None:
    st.session_state["adm_week"] = st.session_state.get("adm_week", 0) + delta


def _adm_pick_week(key: str) -> None:
    picked = st.session_state.get(key)
    if isinstance(picked, date):
        st.session_state["adm_week"] = (admin.week_of(picked)[0] - admin.week_of(TODAY)[0]).days // 7


def _week_nav(key: str) -> date:
    """‹ [달력] › : 달력에서 아무 날이나 고르면 그 날이 든 주(월~일)를 본다."""
    off = st.session_state.get("adm_week", 0)
    mon, sun = admin.week_of(TODAY + timedelta(weeks=off))
    pick = f"admwk_pick_{key}"
    st.session_state[pick] = mon                     # 화살표로 옮겼을 때 달력도 같이
    with st.container(horizontal=True, vertical_alignment="center", key=f"admwk_{key}"):
        st.button("", icon=":material/chevron_left:", key=f"admwk_prev_{key}", type="tertiary", on_click=_adm_week, args=(-1,))
        st.date_input("주 고르기", key=pick, format="YYYY.MM.DD", label_visibility="collapsed", width=150,
                      on_change=_adm_pick_week, args=(pick,))
        st.button("", icon=":material/chevron_right:", key=f"admwk_next_{key}", type="tertiary", on_click=_adm_week, args=(1,))
        st.markdown(f"**{mon.month}/{mon.day}(월) ~ {sun.month}/{sun.day}(일)**" + (" · 이번 주" if off == 0 else ""))
        if off:
            st.button("이번 주", key=f"admwk_now_{key}", on_click=lambda: st.session_state.update(adm_week=0))
    return mon


def _adm_href(r: dict) -> str:
    """팝업 이름 링크 → 메인의 그 팝업 상세 (공유 링크와 같은 ?cafe=<번호>)."""
    return f"./?cafe={quote(str(r.get('entry_id') or ''))}"


GANTT_COLOR = {"예정": "#3672BD", "진행": "#14B8A6", "종료": "#A9B3B0"}


def _admin_gantt(mon: date) -> None:
    """고른 주(월~일) 하루 단위 팝업 일정. 주 밖으로 이어지면 막대 끝을 ‹ › 로, 오늘 칸은 연한 민트."""
    start, end = mon, mon + timedelta(days=6)
    span = (end - start).days + 1
    rows = admin.gantt_rows(store.all_rows(), start, end, limit=80)

    def pct(d: date) -> float:
        return max(0.0, min(100.0, (d - start).days / span * 100))

    wk = (f'<div class="gt-wk" style="left:{pct(TODAY):.2f}%;width:{100 / span:.2f}%"></div>'
          if start <= TODAY <= end else "")
    grid = "".join(f'<div class="gt-grid" style="left:{pct(start + timedelta(days=i)):.2f}%"></div>' for i in range(1, span))
    wd = "월화수목금토일"
    ticks = "".join(f'<div class="gt-tick" style="left:{(i + .5) / span * 100:.2f}%">'
                    f'{(start + timedelta(days=i)).month}/{(start + timedelta(days=i)).day}({wd[i]})</div>'
                    for i in range(span))
    today = ""
    html = [f'<div class="gt"><div class="gt-row gt-head"><div class="gt-lab"><b>팝업 {len(rows)}곳</b></div>'
            f'<div class="gt-track">{ticks}</div></div>']
    for r in rows:
        s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        kind = "예정" if s > TODAY else ("종료" if e < TODAY else "진행")
        left, right = pct(max(s, start)), pct(min(e, end) + timedelta(days=1))
        html.append(
            f'<div class="gt-row"><div class="gt-lab"><a class="adm-link" href="{_adm_href(r)}" target="_self">'
            f'<b>{escape(str(r.get("work") or ""))}</b></a> '
            f'<span>{escape(str(r.get("cafe_name") or ""))} · {s.month}/{s.day}~{e.month}/{e.day}</span></div>'
            f'<div class="gt-track">{wk}{grid}<div class="gt-bar{" cl" if s < start else ""}{" cr" if e > end else ""}" '
            f'style="--c:{GANTT_COLOR[kind]};left:{left:.2f}%;width:{max(right - left, 0.8):.2f}%"></div></div></div>')
    if not rows:
        html.append('<div class="adm-empty">이 기간에 걸친 팝업이 없어요.</div>')
    html.append('<div class="gt-legend">' + "".join(f'<span><i style="background:{c}"></i>{k}</span>'
                                                     for k, c in GANTT_COLOR.items())
                + '<span><i style="background:#E6F6F0"></i>오늘</span><span>막대가 칸 끝에 붙어 있으면 이 주 앞뒤로 이어져요</span></div></div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def _admin_board() -> None:
    mon = _week_nav("board")
    st.markdown('<div class="adm-panel-h">이 주 일정 (간트 차트 · 하루 단위)</div>', unsafe_allow_html=True)
    _admin_gantt(mon)
    st.markdown('<div class="adm-panel-h">고른 주 현황</div>', unsafe_allow_html=True)
    board = admin.popup_board(store.all_rows(), mon)
    colors = {"새로 생성": "#14B8A6", "예정": "#3672BD", "진행": "#23866A", "종료": "#8A9592"}
    cols = st.columns(4, gap="small")
    for col, (name, rows) in zip(cols, board.items()):
        with col:
            cards = "".join(
                f'<a class="adm-card adm-link adm-pcard" href="{_adm_href(r)}" target="_self">'
                f'<img src="{escape(_poster_url(r.get("images")))}" alt="" loading="lazy"><div>'
                f'<b>{escape(str(r.get("work") or ""))}</b>'
                f'<span>{escape(str(r.get("cafe_name") or ""))}</span>'
                f'<em>{escape(str(r.get("start_date") or "")[5:])} ~ {escape(str(r.get("end_date") or "")[5:])}</em></div></a>'
                for r in rows[:40]) or '<div class="adm-empty">없어요</div>'
            st.markdown(f'<div class="adm-col" style="--c:{colors[name]}"><div class="adm-colhead">{name}'
                        f'<small>{len(rows)}곳</small></div>{cards}</div>', unsafe_allow_html=True)
    st.caption("새로 생성 = 그 주에 처음 등록 · 예정 = 그 주가 끝난 뒤 4주 안에 시작 · 진행 = 그 주에 열려 있고 다음 주에도 이어짐 · 종료 = 그 주에 끝남")


def _admin_usage() -> None:
    mon = _week_nav("usage")
    ev = admin.member_events(members.all_rows())
    charts = [
        ("신규 이용자 수", admin.daily_events(ev, "가입", mon), MINT, "명"),
        ("일별 접속 회원", admin.daily_active(visits.all_rows(), mon).rename(columns={"접속 회원": "명"}), "#3672BD", "명 (연인원)"),
        ("탈퇴한 회원 수", admin.daily_events(ev, "탈퇴", mon), "#C8352A", "명"),
    ]
    for title, df, color, unit in charts:
        total = int(df["명"].sum())
        st.markdown(f'<div class="adm-metric-h"><b>{title}</b><span>이 주 합계 <strong>{total}</strong>{unit}</span></div>',
                    unsafe_allow_html=True)
        st.bar_chart(df, x="날", y="명", color=color, sort=False, height=200, x_label="", y_label="")
    st.caption("신규 = 그날 가입한 회원 · 접속 회원 = 그날 로그인한 상태로 한 번 이상 들어온 회원 (같은 날 여러 번 와도 1명, "
               "손님은 세지 않아요) · 탈퇴 = 그날 탈퇴한 회원. 날짜는 한국 시간.")


def _admin_decide(req: dict, approve: bool) -> None:
    reason = st.session_state.get(f"adm_rj_{req['entry_id']}", "")
    if not approve and len(" ".join(reason.split())) < 2:
        st.session_state["flash"] = ("거부 사유를 적어 주세요.", ":material/error:")
        return
    if approve:                             # 승인 → 게시글 삭제 (지우지 않고 '삭제됨' 행)
        target = reviews if req.get("target_type") == "review" else store
        extra = {} if req.get("target_type") == "review" else {"source": "삭제 요청 승인", "editor": _me()}
        try:
            target.soft_delete(str(req.get("target_id")), extra=extra or None)
        except Exception:                   # 이미 지워진 글이어도 요청 처리는 끝낸다
            pass
    admin.decide(del_requests, notices_store, req, approve, reason,
                 notify=_rules()["del_ok" if approve else "del_no"]["enabled"])
    st.session_state["flash"] = (("승인했어요. 게시글을 삭제하고 요청자에게 알렸어요." if approve
                                  else "거부했어요. 요청자에게 사유를 알렸어요."), ":material/check_circle:")


def _admin_requests() -> None:
    rows = sorted(del_requests.current_rows(), key=lambda r: str(r.get("updated_at", "")), reverse=True)
    pending = [r for r in rows if r.get("decision") == "pending"]
    done = [r for r in rows if r.get("decision") != "pending"]
    st.markdown(f'<div class="adm-panel-h">처리 대기 {len(pending)}건</div>', unsafe_allow_html=True)
    if not pending:
        st.markdown('<div class="adm-empty">처리할 삭제 요청이 없어요.</div>', unsafe_allow_html=True)
    for r in pending:
        eid = str(r["entry_id"])
        st.markdown(
            f'<div class="adm-req" style="--st:{ST_COLOR["pending"]}"><div class="rail"></div><div>'
            f'<div class="t"><span class="adm-pill">대기</span>{escape(admin.TARGET_LABEL.get(r.get("target_type"), "글"))} · '
            f'{escape(str(r.get("target_title") or ""))}</div>'
            f'<div class="d">요청 {escape(str(r.get("requester_nick") or ""))} · {escape(_when(str(r.get("updated_at", ""))))}</div>'
            f'<div class="d">사유: {escape(str(r.get("reason") or ""))}</div></div></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 3, 1], vertical_alignment="bottom")
        c1.button("승인 (삭제)", key=f"adm_ok_{eid}", type="primary", width="stretch", on_click=_admin_decide, args=(r, True))
        c2.text_input("거부 사유", key=f"adm_rj_{eid}", placeholder="거부할 때 요청자에게 보낼 사유", label_visibility="collapsed",
                      max_chars=admin.MAX_REASON)
        c3.button("거부", key=f"adm_no_{eid}", width="stretch", on_click=_admin_decide, args=(r, False))
    with st.expander(f"처리한 요청 {len(done)}건"):
        for r in done[:50]:
            d = r.get("decision")
            st.markdown(
                f'<div class="adm-req" style="--st:{ST_COLOR.get(d, "#8A9592")}"><div class="rail"></div><div>'
                f'<div class="t"><span class="adm-pill">{ST_LABEL.get(d, d)}</span>'
                f'{escape(str(r.get("target_title") or ""))}</div>'
                f'<div class="d">요청 {escape(str(r.get("requester_nick") or ""))} · 사유 {escape(str(r.get("reason") or ""))}</div>'
                + (f'<div class="d">거부 사유: {escape(str(r.get("admin_reason") or ""))}</div>' if d == "rejected" else "")
                + '</div></div>', unsafe_allow_html=True)


def _admin_notice_save(entry_id: str | None) -> None:
    k = entry_id or "new"
    title = " ".join(str(st.session_state.get(f"adm_nt_t_{k}", "")).split())
    body = str(st.session_state.get(f"adm_nt_b_{k}", "")).strip()
    if len(title) < 2 or not body:
        st.session_state["flash"] = ("제목(2자 이상)과 내용을 적어 주세요.", ":material/error:")
        return
    if guard.scan(f"{title} {body}"):
        st.session_state["flash"] = ("알림에 전화번호·이메일 같은 개인정보는 넣을 수 없어요.", ":material/error:")
        return
    admin.send(notices_store, "all", "공지", title, body, entry_id=entry_id)
    st.session_state.pop("adm_nt_edit", None)
    for key in (f"adm_nt_t_{k}", f"adm_nt_b_{k}"):      # 저장했으면 입력칸을 비운다
        st.session_state.pop(key, None)
    st.session_state["flash"] = ("공지를 저장했어요. 모든 회원의 알림에 보여요.", ":material/check_circle:")


def _admin_notice_delete(row: dict) -> None:
    notices_store.soft_delete(str(row["entry_id"]))
    st.session_state["flash"] = ("공지를 삭제했어요.", ":material/check_circle:")


def _admin_rule_save(key: str, enabled: bool) -> None:
    d = admin.RULES[key]
    days = st.session_state.get(f"adm_rule_days_{key}") if d["days"] is not None else None
    mx = st.session_state.get(f"adm_rule_max_{key}") if d["max_items"] is not None else None
    try:
        admin.save_rule(alert_rules, key, enabled, days, mx)
    except Exception:
        st.session_state["flash"] = ("저장하지 못했어요. Supabase 에 007_alert_rules.sql 을 먼저 돌려 주세요.", ":material/error:")
        return
    st.session_state.pop("_rules_cache", None)
    st.session_state["flash"] = (f"'{d['name']}' 규칙을 {'저장했어요' if enabled else '껐어요'}.", ":material/check_circle:")


def _admin_rule_editor(rules: dict[str, dict]) -> None:
    """규칙 하나를 골라 며칠 전부터 · 최대 몇 개 · 켜기/끄기(삭제). 기록은 지우지 않고 쌓인다."""
    keys = list(admin.RULES)
    opened = bool(st.session_state.get("adm_rule_open"))
    # 빨간 '수정하기' 버튼을 누르면 고칠 규칙 칸이 펼쳐지고, 한 번 더 누르면 접힌다 (11/18 요청)
    st.markdown('<style>.st-key-adm_rule_toggle button { background: #E05555 !important; border-color: #E05555 !important; }'
                '.st-key-adm_rule_toggle button:hover { background: #C8352A !important; border-color: #C8352A !important; }'
                '.st-key-adm_rule_toggle button p, .st-key-adm_rule_toggle button span { color: #fff !important; }</style>',
                unsafe_allow_html=True)
    st.button("수정 닫기" if opened else "수정하기", icon=":material/expand_less:" if opened else ":material/edit:",
              type="primary", key="adm_rule_toggle",
              on_click=lambda: st.session_state.update(adm_rule_open=not st.session_state.get("adm_rule_open")))
    if not opened:
        return
    with st.container(border=True):
        k = st.selectbox("고칠 규칙", keys, format_func=lambda x: f'{admin.RULES[x]["name"]} '
                         f'({"켜짐" if rules[x]["enabled"] else "꺼짐"})', key="adm_rule_pick")
        d, cur = admin.RULES[k], rules[k]
        c1, c2 = st.columns(2)
        if d["days"] is not None:
            c1.number_input("며칠 전부터 (공지는 며칠 동안)", min_value=0, max_value=30, value=int(cur["days"]), step=1,
                            key=f"adm_rule_days_{k}")
        else:
            c1.markdown('<div class="adm-empty">이 규칙은 일수가 없어요.</div>', unsafe_allow_html=True)
        if d["max_items"] is not None:
            c2.number_input("최대 노출 개수", min_value=1, max_value=30, value=int(cur["max_items"]), step=1,
                            key=f"adm_rule_max_{k}")
        else:
            c2.markdown('<div class="adm-empty">처리할 때마다 1건씩 가요.</div>', unsafe_allow_html=True)
        b1, b2, _ = st.columns([1, 1, 2])
        b1.button("저장" if cur["enabled"] else "저장하고 다시 켜기", type="primary", width="stretch",
                  key=f"adm_rule_save_{k}", on_click=_admin_rule_save, args=(k, True))
        if cur["enabled"]:
            b2.button("이 알림 끄기 (삭제)", width="stretch", key=f"adm_rule_off_{k}", on_click=_admin_rule_save, args=(k, False))
        st.caption("끈 규칙은 회원에게 더 이상 나가지 않아요. 기록은 남아서 언제든 다시 켤 수 있어요. 주간 브리핑 메일은 Apps Script 에서 고쳐요.")


def _admin_notices() -> None:
    st.markdown('<div class="adm-panel-h">자동으로 나가는 알림</div>', unsafe_allow_html=True)
    rules = _rules()
    st.dataframe(admin.rules_table(rules), hide_index=True, width="stretch")
    _admin_rule_editor(rules)
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    rows = sorted([r for r in notices_store.current_rows() if r.get("target") == "all"],
                  key=lambda r: str(r.get("updated_at", "")), reverse=True)
    left, right = st.columns([1.4, 1], gap="medium")
    with right:
        editing = st.session_state.get("adm_nt_edit")
        cur = next((r for r in rows if str(r["entry_id"]) == editing), None) if editing else None
        k = str(cur["entry_id"]) if cur else "new"
        st.markdown(f'<div class="adm-panel-h">{"공지 수정" if cur else "새 공지 추가"}</div>', unsafe_allow_html=True)
        st.text_input("제목", key=f"adm_nt_t_{k}", value=str(cur.get("title", "")) if cur else "", max_chars=60)
        st.text_area("내용", key=f"adm_nt_b_{k}", value=str(cur.get("body", "")) if cur else "", max_chars=500, height=120)
        c1, c2 = st.columns(2)
        c1.button("저장", key=f"adm_nt_save_{k}", type="primary", width="stretch", on_click=_admin_notice_save,
                  args=(str(cur["entry_id"]) if cur else None,))
        if cur:
            c2.button("취소", key="adm_nt_cancel", width="stretch", on_click=lambda: st.session_state.pop("adm_nt_edit", None))
        st.caption("저장하면 모든 회원의 종 알림과 '내 캘린더 > 알림 받은 내역'에 보여요.")
    with left:
        st.markdown(f'<div class="adm-panel-h">공지 알림 {len(rows)}개</div>', unsafe_allow_html=True)
        if not rows:
            st.markdown('<div class="adm-empty">아직 보낸 공지 알림이 없어요. 오른쪽에서 추가해 보세요.</div>', unsafe_allow_html=True)
        for r in rows:
            eid = str(r["entry_id"])
            st.markdown(
                f'<div class="adm-req" style="--st:#14B8A6"><div class="rail"></div><div>'
                f'<div class="t">{escape(str(r.get("title") or ""))}</div>'
                f'<div class="d">{escape(str(r.get("body") or ""))}</div>'
                f'<div class="d">{escape(_when(str(r.get("updated_at", ""))))} · 수정 {int(r.get("revision") or 1) - 1}회</div>'
                '</div></div>', unsafe_allow_html=True)
            c1, c2, _ = st.columns([1, 1, 3])
            c1.button("수정", key=f"adm_nt_ed_{eid}", width="stretch",
                      on_click=lambda e=eid: st.session_state.update(adm_nt_edit=e))
            c2.button("삭제", key=f"adm_nt_del_{eid}", width="stretch", on_click=_admin_notice_delete, args=(r,))


def _admin_members() -> None:
    st.markdown(
        '<div class="adm-info"><b>수집하는 정보</b> — 닉네임 · 로그인 수단(카카오/네이버/아이디) · 회원 번호(계정 고유 번호를 '
        '알아볼 수 없게 바꾼 값) · 약관 동의 시각 · 프로필 사진(선택: 카카오·네이버 사진 주소 또는 직접 올린 사진) · '
        '아이디 가입이면 아이디와 <b>암호화한</b> 비밀번호 · 접속한 날(일별 접속 수)<br>'
        '<b>수집하지 않는 정보</b> — 이메일 · 전화번호 · 실명 · 생일 · 카카오/네이버 고유 번호 원래 값</div>',
        unsafe_allow_html=True)
    rows = members.all_rows()
    latest = mycal.latest_rows(rows)
    first = {}
    for r in rows:
        if int(r.get("revision") or 0) == 1:
            d = admin._day(r.get("updated_at"))          # 한국 시간 기준 가입일
            first[str(r["entry_id"])] = d.isoformat() if d else ""
    last = admin.last_visit(visits.all_rows())
    keys = {k.strip() for k in (os.getenv("ADMIN_MEMBER_KEYS") or DEFAULT_ADMIN).split(",") if k.strip()}
    table = pd.DataFrame([{
        "회원 번호": str(r["entry_id"]), "닉네임": r.get("nickname") or "(탈퇴)",
        "로그인 수단": auth.PROVIDER_LABEL.get(str(r.get("provider")), "-"),
        "가입일": first.get(str(r["entry_id"]), ""), "약관 동의": str(r.get("agreed_at") or "")[:16].replace("T", " "),
        "최근 접속": last.get(str(r["entry_id"]), "-"),
        "상태": "탈퇴" if r.get("status") == "deleted" else "활동",
        "권한": "관리자" if str(r["entry_id"]) in keys else "일반 회원",
    } for r in latest])
    st.markdown(f'<div class="adm-panel-h" style="margin-top:12px">회원 {len(table)}명</div>', unsafe_allow_html=True)
    if table.empty:
        st.markdown('<div class="adm-empty">아직 가입한 회원이 없어요.</div>', unsafe_allow_html=True)
    else:
        st.dataframe(table.sort_values("가입일", ascending=False), hide_index=True, width="stretch")


ADM_KPIS = [("new", "이번 주 새로 등록", "곳"), ("live", "진행 중", "곳"), ("soon", "예정", "곳"),
            ("members", "회원 (활동)", "명"), ("requests", "삭제 요청 대기", "건")]


def _adm_kpi_pick(k: str) -> None:
    if k in ("members", "requests"):           # 회원 · 삭제 요청은 그 탭으로
        st.session_state.update(adm_tab=k, adm_kpi=None)
        return
    st.session_state["adm_kpi"] = None if st.session_state.get("adm_kpi") == k else k


def _adm_open_popup(cafe_id: str) -> None:
    """관리자 목록에서 팝업을 누름 → 메인(리스트 보기)으로 가서 그 팝업 상세."""
    st.session_state.update(list_only=True, cal_view=False, box_view=False, _gnb_to_map=True)
    _gnb_open(cafe_id)


def _admin_kpis(pop_rows: list[dict], pend: int, n_members: int) -> None:
    mon, _ = admin.week_of(TODAY)
    live, soon = [], []
    for r in pop_rows:
        if r.get("status") == "deleted":
            continue
        s_, e_ = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        if s_ and e_ and s_ <= TODAY <= e_:
            live.append(r)
        elif s_ and s_ > TODAY:
            soon.append(r)
    lists = {"new": [r for r in admin.popup_board(store.all_rows(), mon)["새로 생성"] if r.get("status") != "deleted"],
             "live": sorted(live, key=lambda r: str(r.get("end_date") or "")),
             "soon": sorted(soon, key=lambda r: str(r.get("start_date") or ""))}
    nums = {"new": len(lists["new"]), "live": len(live), "soon": len(soon), "members": n_members, "requests": pend}
    picked = st.session_state.get("adm_kpi")
    with st.container(horizontal=True, key="adm_kpis"):
        for k, label, unit in ADM_KPIS:
            alert = " alert" if k == "requests" and pend else ""
            with st.container(key=f"admk_{'on_' if picked == k else ''}{k}"):
                arrow = ("expand_less" if picked == k else "expand_more") if k in ("new", "live", "soon") else "chevron_right"
                st.markdown(f'<div class="adm-kpi{alert}"><span>{label}{_mi(arrow, "kpi-arr")}</span>'
                            f'<b>{nums[k]}<small>{unit}</small></b></div>', unsafe_allow_html=True)
                st.button("보기", key=f"admkb_{k}", on_click=_adm_kpi_pick, args=(k,))
    if picked not in lists:
        return
    rows = lists[picked]
    label = dict((k, l) for k, l, _ in ADM_KPIS)[picked]
    # '고른 주 현황' 칸반과 같은 모양 (색 띠 머리 + 포스터 카드). 숫자 카드를 다시 누르면 접힌다
    color = {"new": "#14B8A6", "live": "#23866A", "soon": "#3672BD"}[picked]
    show_all = bool(st.session_state.get(f"adm_kpi_all_{picked}"))
    shown = rows if show_all else rows[:12]
    cards = "".join(
        f'<a class="adm-card adm-link adm-pcard" href="{_adm_href(r)}" target="_self">'
        f'<img src="{escape(_poster_url(r.get("images")))}" alt="" loading="lazy"><div>'
        f'<b>{escape(str(r.get("work") or ""))}</b><span>{escape(str(r.get("cafe_name") or ""))}</span>'
        f'<em>{escape(_period(r, lambda d: f"{d:%m-%d}", show_raw=False))}</em></div></a>'
        for r in shown) or '<div class="adm-empty">해당하는 팝업이 없어요.</div>'
    st.markdown(f'<div class="adm-col adm-kpilist" style="--c:{color}"><div class="adm-colhead">{label}'
                f'<small>{len(rows)}곳 · 누르면 상세로</small></div><div class="adm-kgrid">{cards}</div></div>',
                unsafe_allow_html=True)
    with st.container(horizontal=True, horizontal_alignment="center", key="adm_kpi_foot"):
        if len(rows) > 12:
            st.button("접기" if show_all else f"{len(rows) - 12}곳 더 보기",
                      icon=":material/expand_less:" if show_all else ":material/expand_more:", key=f"adm_kpi_more_{picked}",
                      on_click=lambda k=f"adm_kpi_all_{picked}": st.session_state.update({k: not st.session_state.get(k)}))
        st.button("목록 닫기", icon=":material/close:", key="adm_kpi_close", type="tertiary",
                  on_click=lambda: st.session_state.update(adm_kpi=None))


def page_data() -> None:
    """관리자 대시보드. 관리자(지정한 회원 번호)만."""
    st.markdown(GLOBAL_CSS + STATS_CSS + ADMIN_CSS, unsafe_allow_html=True)
    _no_translate()
    with st.container(key="topbar"):
        _gnb(None, on_map=False)      # 메인과 같은 메뉴바
    flash = st.session_state.pop("flash", None)
    if flash:
        if isinstance(flash, tuple):
            _toast(*flash)
        else:
            _toast(flash)
    if not _is_admin():
        st.markdown('<div class="stats-title">관리자 전용</div><div class="stats-sub">이 화면은 관리자만 볼 수 있어요. '
                    '관리자 계정으로 로그인해 주세요.</div>', unsafe_allow_html=True)
        st.page_link(PAGES["login"], label="로그인하기", icon=":material/login:")
        return
    rows = stats.popups(store.all_rows())
    status = stats.status_counts(rows, TODAY)
    mon, sun = admin.week_of(TODAY)
    new_week = len(admin.popup_board(store.all_rows(), mon)["새로 생성"])
    pend = sum(1 for r in del_requests.current_rows() if r.get("decision") == "pending")
    n_members = sum(1 for r in members.current_rows())
    st.markdown(f'<div class="adm-eyebrow">ANI:WHERE ADMIN · {TODAY:%Y.%m.%d}</div>'
                '<div class="adm-title">관리자 대시보드</div>'
                f'<div class="adm-sub">저장소: {escape(store.mode)} · 모든 기록은 지우지 않고 쌓여요 (append-only)</div>'
                , unsafe_allow_html=True)
    _admin_kpis(rows, pend, n_members)
    tab = st.session_state.get("adm_tab", "board")
    with st.container(horizontal=True, key="adm_tabs"):
        for t, label in ADMIN_TABS:
            lab = f"{label} {pend}" if t == "requests" and pend else label
            st.button(lab, key=f"admtab_{'on_' if tab == t else ''}{t}", on_click=_adm_tab, args=(t,))
    if tab == "board":
        _admin_board()
    elif tab == "usage":
        _admin_usage()
    elif tab == "requests":
        _admin_requests()
    elif tab == "notices":
        _admin_notices()
    elif tab == "members":
        _admin_members()
    else:
        _admin_raw()


def _admin_raw() -> None:
    """원본 데이터: 저장소에 실제로 쌓인 기록 (append-only 라서 수정·삭제도 행으로 보인다)."""
    where = {"local": "내 컴퓨터의 data/*.json 파일", "sheets": "Google Sheets",
             "supabase": "Supabase 클라우드 (PostgreSQL)"}.get(store.mode, store.mode)
    st.markdown(f'<div class="stats-title">데이터 보기</div><div class="stats-sub">지금 저장소: <b>{where}</b> '
                f'(STORAGE_MODE={escape(os.getenv("STORAGE_MODE", "local"))})</div>', unsafe_allow_html=True)
    if getattr(store, "fallback_reason", ""):
        st.warning(f"Supabase 에 연결하지 못해 로컬 파일을 보여 주고 있어요: {store.fallback_reason[:200]}",
                   icon=":material/cloud_off:")
    if store.mode == "local":
        st.caption("Supabase 로 옮기면 같은 표가 Supabase 대시보드 → Table Editor 에도 보여요 (db.md 6절).")
    stores = {"cafes": store, "reviews": reviews, "favorites": favs, "members": members,
              "del_requests": del_requests, "notices": notices_store, "visits": visits}
    cols = st.columns(len(stores))
    for col, (name, s_) in zip(cols, stores.items()):
        col.metric(f"{DATA_TABLES[name]} ({name})", f"{len(s_.all_rows())}행",
                   f"지금 {len(s_.current_rows())}건", delta_color="off", border=True)
    tab = st.segmented_control("표", list(DATA_TABLES), format_func=lambda n: DATA_TABLES[n], default="cafes",
                               key="data_tab") or "cafes"
    rows = stores[tab].all_rows()
    if not rows:
        st.info("아직 기록이 없어요.", icon=":material/info:")
        return
    df = pd.DataFrame(rows).drop(columns=DATA_HIDE[tab], errors="ignore")
    q = st.text_input("찾기", placeholder="entry_id · 이름 · 작품 등", key="data_q")
    if q.strip():
        df = df[df.astype(str).apply(lambda r: r.str.contains(q.strip(), case=False, regex=False)).any(axis=1)]
    if st.toggle("최신 기록만 (수정 이력 숨기기)", key="data_now") and "entry_id" in df:
        df = df.sort_values("revision").groupby("entry_id", as_index=False).tail(1)
    if "updated_at" in df:
        df = df.sort_values("updated_at", ascending=False)
    st.caption(f"{len(df)}행 · 최근 쓴 순서")
    st.dataframe(df, hide_index=True, width="stretch", height=520)


# ------------------------------------------------------------ 리스트 옆 '팝업에게 물어보기' 대화창
ASK_PANEL_CSS = """
<style>
[data-testid="stColumn"]:has(> div > .st-key-ask_panel), [data-testid="stColumn"]:has(.st-key-ask_panel) {
  position: sticky !important; top: var(--apn-top, 172px); align-self: flex-start !important; z-index: 5; }
/* 위 고정줄(메뉴·검색 필터) 아래에 붙고, 대화창 전체가 화면 안에 들어오게:
   대화창 = 세로 flex, 높이는 (화면 - 위 고정줄 - 여백)까지. 대화 기록만 남는 공간을 쓰고 넘치면 그 안에서 스크롤 */
.st-key-ask_panel { display: flex !important; flex-direction: column !important;
  max-height: calc(100vh - var(--apn-top, 172px) - 16px); }
.st-key-ask_panel > * { flex: 0 0 auto; }
.st-key-ask_panel > *:has(.st-key-apn_log), .st-key-ask_panel > .st-key-apn_log {
  flex: 1 1 auto !important; min-height: 0 !important; display: flex; flex-direction: column; }
.st-key-apn_log { flex: 1 1 auto !important; height: auto !important; max-height: none !important;
  min-height: 90px !important; overflow-y: auto !important; }
.st-key-ask_panel { border: 1.5px solid #E3E8E6; border-radius: 16px; background: #fff;
  padding: 0 !important; gap: 0 !important; overflow: hidden; box-shadow: 0 4px 18px rgba(38,48,45,.06); }
.st-key-ask_panel > div { padding-left: 14px; padding-right: 14px; }
.apn-head { display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  padding: 14px 0 6px; }
.apn-title { font-family: "Jua", sans-serif; font-size: 1.25rem; color: #26302D; }
.apn-sub { color: #9AA5A1; font-size: .78rem; white-space: nowrap; }
.apn-who { color: #6B7672; font-size: .78rem; margin: 10px 0 4px; }
.apn-row { display: flex; align-items: flex-start; gap: 8px; margin: 12px 0 4px; }
.apn-ava { width: 38px; height: 38px; flex: 0 0 38px; border-radius: 50%; border: 1.5px solid #CDEDE3; background: #EAF8F3; }
.apn-col { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.apn-name { color: #6B7672; font-size: .74rem; font-weight: 700; }
.apn-bot { background: #EEF1F0; border: 0; border-radius: 4px 18px 18px 18px; padding: 10px 14px;
  color: #26302D; font-size: .9rem; line-height: 1.6; word-break: keep-all; align-self: flex-start; }
/* 찾은 팝업 카드는 말풍선과 같은 줄에서 시작 (캐릭터 폭만큼 들여쓰기) */
[class*="st-key-apn_card_"], [class*="st-key-apd_card_"] { margin-left: 46px !important; }
.apn-me { display: flex; justify-content: flex-end; margin: 10px 0 2px; }
.apn-me span { background: var(--accent, #56C2A7); color: #fff; border-radius: 12px 12px 2px 12px; padding: 8px 12px;
  font-size: .9rem; max-width: 85%; word-break: keep-all; }
.apn-badge { display: inline-block; margin-top: 6px; padding: 1px 8px; border-radius: 999px; font-size: .7rem;
  font-weight: 700; border: 1px solid #9EDDCC; color: #2E9C82; background: #fff; }
.apn-badge.fb { border-color: #C9D1CE; color: #6B7672; }
/* 찾은 팝업 카드: 왼쪽 포스터 · 오른쪽 작품(민트) · 매장(굵게) · 주소(회색) · 기간(민트 굵게) */
[class*="st-key-apn_card_"], [class*="st-key-apd_card_"] { position: relative; gap: 0 !important; margin: 6px 0; }
.apc { display: flex; gap: 12px; align-items: stretch; background: #E9F7F2; border-radius: 16px; padding: 10px;
  transition: background .12s; }
[class*="st-key-apn_card_"]:hover .apc, [class*="st-key-apd_card_"]:hover .apc { background: #DCF2EA; }
.apc img { width: 78px; height: 106px; flex: 0 0 78px; object-fit: cover; border-radius: 8px; background: #fff; }
.apc-txt { min-width: 0; display: flex; flex-direction: column; justify-content: center; gap: 2px; }
.apc-work { font-family: "Jua", sans-serif; font-size: 1.2rem; line-height: 1.25; color: #2E9C82;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.apc-cafe { font-weight: 800; font-size: .95rem; color: #26302D; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.apc-addr { color: #7A8582; font-size: .82rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden; }
.apc-date { color: #2E9C82; font-weight: 800; font-size: .9rem; margin-top: 2px; }
/* 카드 전체를 덮는 투명 버튼 (글자는 화면 읽기용으로만 남는다) */
[class*="st-key-apn_hit_"], [class*="st-key-apd_hit_"] { position: absolute !important; inset: 0; z-index: 2;
  width: 100% !important; height: 100% !important; }
[class*="st-key-apn_hit_"] > div, [class*="st-key-apd_hit_"] > div, [class*="st-key-apn_hit_"] .stButton,
[class*="st-key-apd_hit_"] .stButton { width: 100% !important; height: 100% !important; }
[class*="st-key-apn_hit_"] button, [class*="st-key-apd_hit_"] button { width: 100% !important; height: 100% !important;
  opacity: 0 !important; cursor: pointer; }
.st-key-apn_unused_hit button { justify-content: flex-start; text-align: left; font-size: .8rem;
  min-height: 0; padding: 4px 10px; border-radius: 10px; }
.st-key-apn_chips, .st-key-apd_chips { padding-top: 10px; border-top: 1px solid #EEF1F0; gap: 6px !important; flex-wrap: wrap; }
.st-key-apn_chips button, .st-key-apd_chips button { border-radius: 999px !important; font-size: .78rem; min-height: 0; padding: 4px 12px; }
.st-key-apn_form [data-testid="stForm"], .st-key-apd_form [data-testid="stForm"] { padding: 10px 0 14px; }
.st-key-apn_form [data-testid="stFormSubmitButton"] button, .st-key-apd_form [data-testid="stFormSubmitButton"] button { background: #E0895A !important; border-color: #E0895A !important;
  color: #fff !important; font-weight: 800; }
@media (max-width: 640px) { .st-key-ask_panel { display: none !important; } }
</style>
"""
ASK_PANEL_CHIPS = ["이번 주말 성수", "주술회전 어디서 해?", "부산 팝업", "오늘 열린 팝업", "12월 시작", "다음 주 서울 팝업"]


def _ask_panel_send(question: str) -> None:
    """질문을 대화 기록에 쌓고 답을 만든다 (버튼·입력 모두 여기로)."""
    q = (question or "").strip()
    if not q:
        return
    chat = st.session_state.setdefault("ask_chat", [])
    chat.append({"role": "me", "text": q[:ask.MAX_QUESTION]})
    errors = [e for e in ask.validate(q) if "개인정보" not in e]
    if errors:
        chat.append({"role": "bot", "text": errors[0], "ids": [], "badge": ""})
    else:
        res = ask.answer(q, stats.popups(store.all_rows()), TODAY, ctx=_ask_ctx())
        if not res.hits:
            # 규칙(의도)이 준 안내가 있으면 그대로 (위치 모름·사용법 등), 없으면 기본 안내
            text = res.text or ("조건에 맞는 팝업을 찾지 못했어요. 작품 이름을 줄이거나(예: 주술회전) 날짜·지역 조건을 하나 빼 보세요. "
                                "없는 팝업이면 오른쪽 아래 + 로 직접 등록할 수 있어요.")
            chat.append({"role": "bot", "text": text, "ids": [], "badge": "규칙 기반 대체"})
        else:
            limit = 5 if res.query.intent else 3
            used = [i for i in res.used_ids] or [str(h.row.get("entry_id")) for h in res.hits[:limit]]
            rows = {str(h.row.get("entry_id")): h.row for h in res.hits}
            cards = [_ask_card(i, rows[i], res.distances.get(i)) for i in used[:limit] if i in rows]
            chat.append({"role": "bot", "text": res.text, "badge": res.badge, "ids": cards,
                         "head": res.summary or _ASK_HEADS.get(res.query.intent, "")})
            _ask_log(q)
    del chat[:-20]                 # 너무 길어지지 않게 최근 20개만


_ASK_HEADS = {"near": "내 위치에서 가까운 순", "recommend": "추천 (별점 → 리뷰 많은 순)", "ending": "곧 끝나는 순",
              "upcoming": "곧 열리는 순", "popular": "북마크 많은 순", "reviewed": "후기 많은 순"}
_ASK_LOG = Path(__file__).resolve().parent / "logs" / "ask_questions.jsonl"
ASK_DEFAULT_CHIPS = ["내 주변 가까운 팝업", "팝업 추천해줘", "지금 진행 중인 서울 팝업", "곧 끝나는 팝업", "이번 주말 성수 팝업"]


def _ask_ctx() -> dict:
    """물어보기 규칙에 넘길 값: 내 위치, 팝업별 (평균 별점, 다녀온 후기 수), 팝업별 북마크 수."""
    agg: dict[str, list[int]] = {}
    for r in reviews.current_rows():
        if r.get("kind") == review.RATED_KIND and not r.get("parent_id"):
            try:
                n = int(r.get("rating"))
            except (TypeError, ValueError):
                continue
            if 1 <= n <= 5:
                agg.setdefault(str(r.get("cafe_id")), []).append(n)
    ratings = {k: (sum(v) / len(v), len(v)) for k, v in agg.items()}
    return {"loc": _my_loc(), "ratings": ratings, "favs": favorite.counts(favs.current_rows())}


def _ask_log(question: str) -> None:
    """답을 찾은 질문만 남긴다 (개인정보는 가려서). '많이 물어본 질문' 칩에 쓴다."""
    try:
        _ASK_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _ASK_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"),
                                "q": guard.mask(" ".join(question.split()))[:60]}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ask_chips() -> list[str]:
    """사용자들이 가장 많이 물어본 질문 최대 5개. 기록이 모자라면 기본 질문으로 채운다."""
    counts: dict[str, int] = {}
    try:
        for line in _ASK_LOG.read_text(encoding="utf-8").splitlines()[-2000:]:
            q = json.loads(line).get("q", "").strip()
            if 2 <= len(q) <= 30:
                counts[q] = counts.get(q, 0) + 1
    except (OSError, ValueError):
        pass
    top = [q for q, n in sorted(counts.items(), key=lambda kv: -kv[1]) if n >= 2][:5]
    for d in ASK_DEFAULT_CHIPS:
        if len(top) >= 5:
            break
        if d not in top:
            top.append(d)
    return top[:5]


def _ask_card(cafe_id: str, r: dict, km: float | None = None) -> dict:
    """대화창 카드 한 장에 필요한 값."""
    def md(v) -> str:
        d = mycal._day(v)
        return f"{d.month}.{d.day}" if d else ""
    dates = _period(r)
    if km is not None:
        dates = (f"{km * 1000:.0f}m" if km < 1 else f"{km:.1f}km") + " · " + dates
    return {"id": str(cafe_id), "work": str(r.get("work") or ""), "cafe": str(r.get("cafe_name") or ""),
            "address": str(r.get("address") or ""), "dates": dates, "poster": _poster_url(r.get("images"))}


def _ask_panel_submit(prefix: str = "apn") -> None:
    _ask_panel_send(st.session_state.get(f"{prefix}_q", ""))
    st.session_state[f"{prefix}_q"] = ""


def _ask_panel_open(cafe_id: str) -> None:
    st.session_state["selected"] = str(cafe_id)
    st.session_state["scroll_top"] = True


ASK_AVATAR = "app/static/ask_avatar.png"      # 로고의 토끼를 동그랗게 자른 그림


def _ask_bot(html: str) -> str:
    """ANI:WHERE 말풍선: 왼쪽에 동그란 로고 캐릭터, 오른쪽에 둥근 회색 말풍선 (11/18 요청)."""
    return (f'<div class="apn-row"><img class="apn-ava" src="{ASK_AVATAR}" alt="ANI:WHERE">'
            f'<div class="apn-col"><div class="apn-name">ANI:WHERE</div><div class="apn-bot">{html}</div></div></div>')


def _ask_chat_body(prefix: str, log_height: int, in_dialog: bool = False) -> None:
    """대화 기록 · 예시 칩 · 입력칸. PC 옆 대화창(apn)과 모바일 팝업(apd)이 같은 기록(ask_chat)을 쓴다."""
    with st.container(height=log_height, border=False, key=f"{prefix}_log"):
        st.markdown(_ask_bot('안녕하세요. 지금 등록된 팝업에서 찾아 드릴게요. <b>작품 · 지역 · 날짜</b>로 물어보면 더 정확해요.'),
                    unsafe_allow_html=True)
        for n, m in enumerate(st.session_state.get("ask_chat", [])):
            if m["role"] == "me":
                st.markdown(f'<div class="apn-me"><span>{escape(m["text"])}</span></div>', unsafe_allow_html=True)
                continue
            # 대화창에서는 'AI 산출 / 규칙 기반 대체' 배지를 보이지 않는다 (사용자 요청 11/18). /ask 화면에는 남아 있다
            # 찾은 팝업이 있으면 요약 문장(회색 상자)은 아래 버튼과 겹쳐서 숨기고 'N곳' 만 (사용자 요청 11/18)
            if m.get("ids"):
                head = f' · {escape(m["head"])}' if m.get("head") else ""
                st.markdown(_ask_bot(f'찾은 팝업 <b>{len(m["ids"])}곳</b>{head}'), unsafe_allow_html=True)
            else:
                st.markdown(_ask_bot(escape(m["text"])), unsafe_allow_html=True)
            for card in m.get("ids", []):
                if not isinstance(card, dict):          # 예전 모양 (id, 이름) 기록
                    card = {"id": card[0], "work": card[1], "cafe": "", "address": "", "dates": "",
                            "poster": images.DEFAULT_POSTER_URL}
                cid = card["id"]
                with st.container(key=f"{prefix}_card_{n}_{cid}"):
                    st.markdown(
                        f'<div class="apc"><img src="{escape(card["poster"])}" alt="">'
                        f'<div class="apc-txt"><div class="apc-work">{escape(card["work"])}</div>'
                        f'<div class="apc-cafe">{escape(card["cafe"])}</div>'
                        f'<div class="apc-addr">{escape(card["address"])}</div>'
                        f'<div class="apc-date">{escape(card["dates"])}</div></div></div>', unsafe_allow_html=True)
                    key = f"{prefix}_hit_{n}_{cid}"
                    if in_dialog:
                        # 팝업 안에서는 상세로 옮기려면 팝업을 닫고 앱 전체를 다시 그려야 한다
                        if st.button(f"{card['work']} 상세 보기", key=key):
                            _ask_panel_open(cid)
                            st.rerun()
                    else:
                        st.button(f"{card['work']} 상세 보기", key=key, on_click=_ask_panel_open, args=(cid,))
    with st.container(horizontal=True, key=f"{prefix}_chips"):
        for i, chip in enumerate(_ask_chips()):
            st.button(chip, key=f"{prefix}_chip_{i}", on_click=_ask_panel_send, args=(chip,))
    with st.container(key=f"{prefix}_form"):
        with st.form(prefix, border=False, clear_on_submit=False):
            c1, c2 = st.columns([4, 1.4], vertical_alignment="bottom")
            c1.text_input("질문", key=f"{prefix}_q", max_chars=ask.MAX_QUESTION, label_visibility="collapsed",
                          placeholder="예: 이번 주말 홍대 근처 팝업 있어?")
            c2.form_submit_button("보내기", on_click=_ask_panel_submit, args=(prefix,), width="stretch")


def render_ask_panel() -> None:
    """PC 리스트 옆 대화창 (모바일에서는 숨기고 플로팅 버튼 → 팝업으로)."""
    st.markdown(ASK_PANEL_CSS, unsafe_allow_html=True)
    st.markdown('<div class="apn-head"><span class="apn-title">ANI:WHERE에게 물어보기</span></div>', unsafe_allow_html=True)
    _ask_chat_body("apn", 430)


@st.dialog("ANI:WHERE에게 물어보기", width="small")
def ask_dialog() -> None:
    """모바일: 오른쪽 아래 물어보기 플로팅 버튼을 누르면 뜨는 팝업."""
    st.markdown(ASK_PANEL_CSS, unsafe_allow_html=True)
    _ask_chat_body("apd", 360, in_dialog=True)


# ------------------------------------------------------------ 2차: 팝업 Q&A (/ask)
ASK_CSS = """
<style>
.ask-q { font-family: "Jua", sans-serif; font-size: 1.5rem; color: #26302D; margin: .2rem 0 .1rem; }
.ask-sub { color: #6B7672; font-size: .9rem; margin-bottom: .6rem; }
.ask-badge { display: inline-block; padding: .1rem .55rem; border-radius: 999px; font-size: .75rem; font-weight: 700;
  border: 1.5px solid var(--accent, #14b8a6); color: var(--accent-deep, #0f766e); background: #fff; margin-right: .3rem; }
.ask-badge.fb { border-color: #9AA5A1; color: #4B5552; }
.ask-answer { background: #F4F7F6; border-radius: 12px; padding: .9rem 1rem; line-height: 1.65; margin: .5rem 0; }
.ask-cond { color: #6B7672; font-size: .8rem; }
</style>
"""
ASK_EXAMPLES = ["이번 주말 성수에서 하는 팝업 있어?", "주술회전 팝업 어디서 해?", "부산 팝업 알려줘", "12월에 시작하는 팝업"]


def _ask_pick(q: str) -> None:
    st.session_state["ask_q"] = q


def _ask_open(cafe_id: str) -> None:
    # 콜백 안에서는 페이지를 옮기지 않고 표시만 해 둔다 (다음 그리기에서 page_ask 가 옮긴다)
    st.session_state["selected"] = str(cafe_id)
    st.session_state["_ask_go"] = True


def page_ask() -> None:
    if st.session_state.pop("_ask_go", False):
        go("map")
    st.markdown(GLOBAL_CSS + ASK_CSS, unsafe_allow_html=True)
    _no_translate()
    with st.container(key="topbar"):
        _gnb(None, on_map=False)      # 메인과 같은 메뉴바
    st.markdown('<div class="ask-q">팝업에게 물어보기</div><div class="ask-sub">앱에 모인 팝업 정보 안에서만 찾아 답해요. '
                '작품·지역·날짜를 함께 적으면 더 정확해요.</div>', unsafe_allow_html=True)
    with st.container(horizontal=True):
        for i, ex in enumerate(ASK_EXAMPLES):
            st.button(ex, key=f"ask_ex_{i}", on_click=_ask_pick, args=(ex,), type="tertiary")
    with st.form("ask_form", border=False):
        q = st.text_input("질문", key="ask_q", max_chars=ask.MAX_QUESTION, label_visibility="collapsed",
                          placeholder="예: 이번 주말 홍대 근처 주술회전 팝업 있어?")
        sent = st.form_submit_button("물어보기", icon=":material/send:", type="primary")
    if not sent:
        return
    errors = ask.validate(q)
    if any("개인정보" not in e for e in errors):
        for e in errors:
            st.warning(e, icon=":material/error:")
        return
    if errors:            # 개인정보는 가리고 계속 찾는다
        st.info(errors[0], icon=":material/shield:")
    with st.spinner("팝업을 찾는 중이에요..."):
        rows = stats.popups(store.all_rows())
        res = ask.answer(q, rows, TODAY)
    st.markdown(f'<div class="ask-cond">질문에서 읽은 조건: {escape(res.query.describe())}</div>', unsafe_allow_html=True)
    if not res.hits:
        # 0건일 때 빈 화면 대신 다음 할 일을 안내한다
        st.markdown('<div class="ask-answer">조건에 맞는 팝업을 찾지 못했어요.<br>'
                    '· 작품 이름을 줄여서(예: <b>주술회전</b>) 다시 물어보거나<br>'
                    '· 날짜·지역 조건을 하나 빼 보세요.<br>'
                    '· 아직 등록되지 않은 팝업이라면 첫 화면 오른쪽 위 <b>+</b> 로 직접 등록할 수 있어요.</div>',
                    unsafe_allow_html=True)
        return
    cls = "ask-badge" if res.source == "ai" else "ask-badge fb"
    low = '<span class="ask-badge fb">딱 맞는 팝업은 없음</span>' if res.confidence == "low" else ""
    st.markdown(f'<span class="{cls}">{res.badge}</span>{low}'
                f'<div class="ask-answer">{escape(res.text)}</div>', unsafe_allow_html=True)
    if res.dropped_ids:
        st.caption(f"AI 가 후보에 없는 팝업 {len(res.dropped_ids)}건을 근거로 들어 지웠어요.")
    st.markdown("**찾은 팝업** — 누르면 상세로 이동해요")
    used = set(res.used_ids)
    for h in sorted(res.hits, key=lambda h: str(h.row.get("entry_id")) not in used):
        r = h.row
        label = (f'{r.get("work")} · {r.get("cafe_name")}  |  {r.get("start_date")} ~ {r.get("end_date")}  |  '
                 f'{geo.area_name(str(r.get("address") or "")) or "지역 미상"}')
        st.button(label, key=f"ask_hit_{r.get('entry_id')}", icon=":material/location_on:",
                  on_click=_ask_open, args=(r.get("entry_id"),), width="stretch",
                  type="primary" if str(r.get("entry_id")) in used else "secondary")


# ------------------------------------------------------------ 2차: PO 지표 (/stats)
STATS_CSS = """
<style>
.stats-title { font-family: "Jua", sans-serif; font-size: 1.6rem; color: #26302D; margin: .2rem 0 .1rem; }
.stats-sub { color: #6B7672; font-size: .9rem; margin-bottom: .8rem; }
</style>
"""
STATS_BEFORE = "#B8C2BF"      # 개선 전: 회색 (덜 눈에 띄게)


def page_stats() -> None:
    st.markdown(GLOBAL_CSS + STATS_CSS, unsafe_allow_html=True)
    _no_translate()
    with st.container(key="topbar"):
        _gnb(None, on_map=False)      # 메인과 같은 메뉴바
    all_rows = store.all_rows()
    rows = stats.popups(all_rows)
    st.markdown('<div class="stats-title">ANI:WHERE 지표</div>'
                f'<div class="stats-sub">팝업 {len(rows)}건 · 기준일 {TODAY:%Y-%m-%d} · '
                '저장소가 append-only 라서 과거 시점의 상태를 그대로 다시 계산해요.</div>', unsafe_allow_html=True)
    if not rows:
        st.info("아직 팝업이 없어요. 첫 화면 오른쪽 위 + 로 팝업을 등록하면 지표가 채워져요.", icon=":material/info:")
        return

    now = stats.completeness(rows)
    before = stats.completeness(stats.popups(all_rows, until=stats.NOTION_CUTOFF))
    status = stats.status_counts(rows, TODAY)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("방문 전 정보 완결률", f"{now['complete']:.0f}%",
              f"{now['complete'] - before['complete']:+.0f}%p (Notion 주간 수집 전 대비)" if before["n"] else None,
              border=True)
    c2.metric("지금 갈 수 있는 팝업", f"{status['진행 중']}곳", border=True)
    c3.metric("7일 안에 시작", f"{stats.starting_within(rows, TODAY)}곳", border=True)
    days = stats.durations(rows)
    c4.metric("평균 진행 기간", f"{sum(days) / len(days):.0f}일" if days else "-", border=True)

    st.markdown("#### 개선 전후: 방문 전 정보가 채워진 비율")
    st.caption(f"이전 = {stats.NOTION_CUTOFF} 전까지 쌓인 기록 ({before['n']}건) · 지금 = 모든 기록 ({now['n']}건). "
               "방문 전 정보 = 기간·주소·지도 좌표·참고 링크·포스터가 모두 있음. 회색 막대 = 이전, 민트 막대 = 지금")
    ba = stats.before_after(all_rows)
    if before["n"]:
        wide = ba.pivot(index="항목", columns="시점", values="비율")[["이전", "지금"]].reset_index()
        # 순서: 북극성 지표(방문 전 정보 모두)를 맨 위, 나머지는 원래 순서
        wide["순서"] = wide["항목"].map({n: i for i, n in enumerate(dict.fromkeys(ba["항목"]))})
        wide = wide.sort_values("순서").drop(columns="순서")
        st.bar_chart(wide, x="항목", y=["이전", "지금"], color=[STATS_BEFORE, MINT], stack=False,
                     horizontal=True, sort=False, height=420, y_label="채워진 비율(%)", x_label="")
        with st.expander("표로 보기"):
            st.dataframe(ba.pivot(index="항목", columns="시점", values="비율")[["이전", "지금"]],
                         width="stretch")
    else:
        st.info("비교할 이전 기록이 없어요.", icon=":material/info:")

    st.markdown("#### 팝업은 어디에, 무엇이 많이 열리나")
    left, right = st.columns(2)
    with left:
        st.caption("지역별 팝업 수 (상위 10, 나머지는 '그 외')")
        st.bar_chart(stats.by_city(rows), x="지역", y="팝업 수", horizontal=True, sort="-팝업 수",
                     color=MINT, height=340, x_label="", y_label="")
    with right:
        st.caption("작품별 팝업 수 (상위 10)")
        st.bar_chart(stats.by_work(rows), x="작품", y="팝업 수", horizontal=True, sort="-팝업 수",
                     color=MINT, height=340, x_label="", y_label="")
    left, right = st.columns(2)
    with left:
        st.caption("시작 월별 팝업 수")
        st.bar_chart(stats.by_month(rows), x="월", y="팝업 수", color=MINT, height=260, x_label="", y_label="")
    with right:
        st.caption("진행 기간 분포")
        st.bar_chart(stats.duration_buckets(days), x="기간", y="팝업 수", sort=False, color=MINT, height=260,
                     x_label="", y_label="")

    st.markdown("#### 참여")
    review_rows = reviews.current_rows()
    fav_rows = favs.current_rows()
    eng = stats.engagement(fav_rows, review_rows)
    cols = st.columns(len(eng))
    for col, (k, v) in zip(cols, eng.items()):
        col.metric(k, v, border=True)
    left, right = st.columns(2)
    with left:
        st.caption("다녀온 후기 별점 분포")
        st.bar_chart(stats.rating_dist(review_rows), x="별점", y="후기 수", sort=False, color=MINT, height=240,
                     x_label="", y_label="")
    with right:
        st.caption("북마크가 많은 팝업")
        top = stats.top_bookmarked(fav_rows, rows)
        if top.empty:
            st.info("아직 북마크가 없어요.", icon=":material/info:")
        else:
            st.dataframe(top, hide_index=True, width="stretch")


# 지도와 등록은 주소가 다른 별개 페이지다 (/, /add). 메뉴는 숨기고 버튼으로만 오간다.
PAGES = {
    "map": st.Page(page_map, title="ANI:WHERE", icon=":material/map:", url_path="map", default=True),
    "add": st.Page(page_add, title="팝업 카페 등록하기 · ANI:WHERE", icon=":material/add:", url_path="add"),
    "calendar": st.Page(page_calendar, title="내 캘린더 · ANI:WHERE", icon=":material/calendar_month:", url_path="calendar"),
    "ask": st.Page(page_ask, title="팝업에게 물어보기 · ANI:WHERE", icon=":material/forum:", url_path="ask"),
    "stats": st.Page(page_stats, title="지표 · ANI:WHERE", icon=":material/insights:", url_path="stats"),
    "login": st.Page(page_login, title="로그인 · ANI:WHERE", icon=":material/login:", url_path="login"),
    "auth": st.Page(page_auth, title="가입 · ANI:WHERE", icon=":material/person_add:", url_path="auth"),
    "data": st.Page(page_data, title="데이터 보기 · ANI:WHERE", icon=":material/database:", url_path="data"),
    "privacy": st.Page(page_privacy, title="개인정보처리방침 · ANI:WHERE", icon=":material/policy:", url_path="privacy"),
}
try:
    st.navigation(list(PAGES.values()), position="hidden").run()
except StorageWriteError as exc:
    # Supabase 가 쓰기를 거절함 (RLS: 남의 리뷰 수정·민감정보·동시 수정 충돌, 또는 연결 끊김). 화면이 멈추지 않게 안내만
    st.error("저장하지 못했어요. 잠시 뒤 다시 시도해 주세요. 내가 쓴 글이 아니거나 개인정보가 들어 있으면 저장되지 않아요.",
             icon=":material/error:")
    st.caption(f"자세한 이유: {str(exc)[:200]}")
