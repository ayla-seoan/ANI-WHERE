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

import contextlib
import dataclasses
import base64
import hashlib
import json
import os
import re
import time
import uuid
from urllib.parse import urlparse, quote
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from common import (admin, ai, ask, auth, cafe, catalog, favorite, gallery, geo, guard, images, kakao_map,
                    kakao_postcode, mycal, notice, notion_sync, review, share, stats)
from common import blog     # 블로그 후기 (네이버 블로그 검색 · API HUB)
from common import season   # 계절 배경 그림 (내 캘린더, 11/18)
from common import favwork  # 스토리 줄 '내가 관심있는 작품' (11/18)
from common import cookie_bridge   # 브라우저 로그인 쿠키 → 서버 (배포에서 st.context.cookies 에 안 옴, 11/18)
from common import links as links_check   # 참고 웹사이트 확인 (11/18 안정성)
from common import dates as pdates   # 기간 표기: 상시 · 기간 확인 필요 (11/18 안정성)
from common import locate as my_place   # 앱 안의 locate() (주소 → 좌표) 와 이름이 겹쳐서 따로 부른다
from common.schema import CafeEntry
from common import storage as storage_mod
from common.storage import Storage, StorageWriteError

load_dotenv()

ROOT = Path(__file__).resolve().parent
TODAY = date.today()
MAP_HEIGHT = 620
# 제목 로고: 민트 로고 하나로 고정 (11/18 요청: 흰 글자 로고 → 다시 민트 로고, 크기는 그대로)
LOGOS = ["logo_mint.png"]          # 연한 메뉴바 + 초록 로고로 되돌림 (11/18 요청)
FIXED_LOGO = "logo_mint.png"
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
/* 프로필 사진이 다 받아지기 전에는 동그라미 안이 반짝인다 (11/18 요청: 로딩이 보이게) */
img.av-wait {{ background: linear-gradient(100deg, #DDF3EC 20%, #F4FBF8 45%, #DDF3EC 70%) !important;
  background-size: 220% 100% !important; animation: av-shine 1.1s linear infinite; }}
@keyframes av-shine {{ from {{ background-position: 120% 0; }} to {{ background-position: -120% 0; }} }}
.av-preview {{ display: flex; align-items: center; gap: 12px; margin: 4px 0 10px; }}
.av-preview img {{ width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 2px solid var(--accent-soft); }}
.av-preview span {{ font-size: .8rem; color: #6B7672; }}
/* 물어보기 '더보기' 로 온 리스트: 위에 결과 표시 (11/18) */
.st-key-ask_only_bar {{ background: var(--accent-soft); border: 1px solid #BFEDE3; border-radius: 12px; padding: 6px 12px; margin: 4px 0 8px; }}
.ask-only {{ font-size: .9rem; color: #26302D; display: flex; align-items: center; gap: 6px; }}
.ask-only .mi {{ color: var(--accent-deep); font-size: 1.1rem; }}
.ask-only span {{ color: var(--accent-deep); font-weight: 800; }}
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
  /* 고른 지역 칩이 칸(32px)보다 커서 위로 삐져나왔다 → 칩을 칸 안에 맞추고 위아래 가운데로 (11/18 요청) */
  .st-key-listtools .st-key-regions [data-testid="stMultiSelectTagsContainer"] {{ align-items: center !important; }}
  .st-key-listtools .st-key-regions [role="group"] {{ align-items: center !important; }}
  .st-key-listtools .st-key-regions [data-tag] {{ height: 24px !important; margin-top: 0 !important; margin-bottom: 0 !important;
    padding-top: 0 !important; padding-bottom: 0 !important; font-size: .8rem !important; display: inline-flex !important; align-items: center !important; }}
  .st-key-listtools .st-key-regions [data-tag] span {{ line-height: 24px !important; }}
}}
/* 목록 위 '팔로우' 스위치는 칸 오른쪽 끝, 바로 옆 '지역 고르기' 에 붙인다 */
.st-key-listtools [data-testid="stColumn"]:has([class*="st-key-folsw_"]) [data-testid="stVerticalBlock"] {{ align-items: flex-end; }}
/* 보기 전환·필터 아이콘 묶음: 정렬 칸 위 오른쪽 끝. 떠 있어도 원래 자리 높이는 남긴다 */
[data-testid="stLayoutWrapper"]:has(> .st-key-view_tools) {{ min-height: 32px; }}
/* PC 에서는 이 아이콘 묶음이 비어 있다(필터·보기 전환은 모바일 전용) → 자리도 없애서 '팝업 카페 N곳' 줄이 위로 붙게 (11/18 요청) */
@media (min-width: 641px) {{ [data-testid="stLayoutWrapper"]:has(> .st-key-view_tools), .st-key-view_tools {{ display: none !important; }} }}
/* PC 리스트 위: 정렬 칸은 글자 수(최대 6자)에 맞게, 지역 고르기도 짧게 — 남는 폭은 '팝업 카페 N곳' 쪽으로 (11/18 요청) */
@media (min-width: 641px) {{
  .st-key-listtools [data-testid="stColumn"]:has(.st-key-sort) {{ flex: 0 0 150px !important; width: 150px !important; min-width: 0 !important; }}
  /* 지역 고르기: 처음엔 240px, 지역을 더 고르면 왼쪽으로 늘어난다 (북마크 버튼도 함께 밀림) — 최대 '팝업 카페 N곳' 바로 옆까지 */
  .st-key-listtools [data-testid="stHorizontalBlock"]:has(.st-key-regions) {{ flex-wrap: nowrap !important; }}
  .st-key-listtools [data-testid="stColumn"]:has(.st-key-regions) {{ flex: 0 1 auto !important; width: auto !important; min-width: 240px !important; }}
  .st-key-listtools .st-key-regions, .st-key-listtools .st-key-regions [data-testid="stMultiSelect"] {{ width: max-content !important;
    min-width: 240px !important; max-width: 100% !important; margin-left: auto; }}
  .st-key-listtools .st-key-regions [data-testid="stMultiSelectTagsContainer"] {{ flex-wrap: wrap !important; }}
  /* 지역을 고른 뒤 입력 커서 칸이 다음 줄로 내려가 칩이 위로 뜨지 않게: 커서 칸은 남는 폭만 쓴다 */
  .st-key-listtools .st-key-regions [data-testid="stMultiSelectTagsContainer"]:has([data-tag]) > input {{ flex: 1 1 0 !important; min-width: 4px !important; width: 4px !important; }}
  .st-key-listtools [data-testid="stColumn"]:has(.st-key-listbar) {{ flex: 0 0 auto !important; min-width: max-content !important; width: auto !important; }}
  .st-key-listtools .st-key-listbar h4 {{ white-space: nowrap !important; }}
  .st-key-listtools [data-testid="stColumn"]:has([class*="st-key-folsw_"]) {{ flex: 0 0 auto !important; width: auto !important; margin-left: auto !important; }}
}}
/* 리스트 '더 보기': 카드 아래 여백 두고 가운데. 모바일은 아이콘만 (11/18 요청) */
.st-key-list_more {{ width: 100% !important; justify-content: center !important; justify-items: center !important;
  grid-template-columns: 1fr !important; margin-top: 18px !important; }}
[data-testid="stLayoutWrapper"]:has(> .st-key-list_more) {{ width: 100% !important; flex: 1 1 100% !important; }}
/* 회색 바탕 + 아래 화살표 + 'N건 더보기' (PC·모바일 같게, 11/18 요청) */
[class*="st-key-adm_more_"] button {{ border-radius: 999px !important; background: #F2F4F3 !important; border: 1px solid #E3E8E6 !important; }}
[class*="st-key-adm_more_"] button p, [class*="st-key-adm_more_"] button span {{ color: #5F6B67 !important; font-size: .85rem !important; font-weight: 700 !important; }}
.st-key-list_more button {{ border-radius: 999px !important; background: #F2F4F3 !important; border: 1px solid #E3E8E6 !important;
  padding: 4px 18px !important; min-height: 0 !important; }}
.st-key-list_more button p {{ color: #5F6B67 !important; font-size: .88rem !important; font-weight: 700 !important; }}
.st-key-list_more button span {{ color: #5F6B67 !important; }}
.st-key-list_more button:hover {{ background: #E8ECEA !important; }}
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
  /* 관심 작품 줄 아래 '마지막 업데이트' 가 지도 칸 위에 겹치지 않게 (11/18) */
  /* 모바일 지도 보기: 지도 칸을 탭 바로 아래로 올리고, 필터 아이콘은 지도 위에 겹쳐 띄운다 (11/18 요청) */
  .stMain:has(.st-key-m_filter_btn) [data-testid="stLayoutWrapper"]:has(> .st-key-map_row) {{ margin-top: -34px; }}
  .st-key-view_tools {{ position: relative; z-index: 20; }}
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
  background: url("app/static/logo_mint.png") no-repeat left center / contain !important; }}
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
api_usage = Storage(worksheet="api_usage", headers=blog.USAGE_HEADERS)            # 블로그 검색 호출 수 (한 달 한도)
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
WEEK_MAX = 2     # 요일마다 2곳까지, 나머지는 더보기 (11/18 요청)


def _member() -> dict | None:
    """로그인한 회원의 최신 기록. 손님이면 None. 세션에 없으면 쿠키(aw_session)로 되살린다."""
    run = st.session_state.get("_run", 0)
    cached = st.session_state.get("_member_cache")
    if cached and cached[0] == run:
        return cached[1]
    key = st.session_state.get("member_key")
    # 손님(빈 값)이어도 쿠키를 다시 본다: 간편 로그인 작은 창에서 로그인하면 원래 창은 쿠키만 새로 받는다.
    # 배포(Streamlit Cloud)에서는 새로고침해도 예전 세션에 다시 붙어 '손님' 기억이 남아 로그인이 안 됐다 (11/18).
    # 방금 로그아웃한 세션(_logged_out)은 다시 보지 않는다 (지운 쿠키가 남아 있어도 되살리지 않게)
    if not key and not st.session_state.get("_logged_out"):
        # 서버가 받은 쿠키가 먼저, 없으면 브라우저에서 읽어 넘겨준 값(cookie_bridge).
        # ANIWHERE_COOKIE_BRIDGE_ONLY=1 이면 서버 쿠키를 무시한다 (배포처럼 쿠키가 안 오는 상황을 로컬에서 시험)
        raw = None if os.getenv("ANIWHERE_COOKIE_BRIDGE_ONLY") else st.context.cookies.get(auth.COOKIE)
        raw = raw or st.session_state.get(cookie_bridge.KEY)
        try:
            sess = auth.read_session(raw)
        except auth.AuthError:            # AUTH_SECRET 이 없으면 로그인 기능 자체가 꺼진 상태
            sess = None
        key = sess["k"] if sess else ""
        if key and st.session_state.get("member_key") == "":
            _clear_user_state()           # 손님일 때 기억한 북마크·알림 등을 비우고 회원 것으로
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
    # 사진이 다 받아지기 전에는 동그라미 안이 반짝인다(.av-wait), 다 받으면 멈춘다 (11/18 요청: 로딩이 보이게)
    return (f'<img class="{cls} av-wait" src="{escape(_avatar_url(value))}" alt="" width="{size}" height="{size}" '
            f'referrerpolicy="no-referrer" loading="lazy" decoding="async" onload="this.classList.remove(\'av-wait\')" '
            f'onerror="this.classList.remove(\'av-wait\');this.src=\'{DEFAULT_AVATAR}\'">')


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


# 닉네임 칸 옆 ? 안내 (11/18 요청: 닉네임은 선택, 안 쓰면 자동)
NICK_HELP = ("입력하지 않으면 칸에 흐리게 보이는 닉네임(꾸밈말 + 애니 캐릭터 이름)으로 자동으로 정해져요. "
             "2~16자, 다른 회원과 같은 닉네임 · 욕설·음란한 말 · 관리자·운영자처럼 보이는 이름은 쓸 수 없어요. "
             "가입한 뒤 마이페이지에서 언제든 바꿀 수 있어요.")


def _suggest_nick(final: bool = False) -> str:
    """가입 화면 닉네임 칸에 흐리게 보여 줄 랜덤 닉네임 (이 화면에서는 늘 같은 것).
    칸을 비워 두고 가입하면 바로 이 닉네임으로 정한다 — 그사이 누가 먼저 썼으면 새로 짓는다 (11/18 요청)."""
    cur = st.session_state.get("_suggest_nick")
    if not cur or (final and (auth.validate_nick(cur) or auth.nick_taken(members, cur))):
        cur = _auto_nick(uuid.uuid4().hex)
        st.session_state["_suggest_nick"] = cur
    if final:
        st.session_state.pop("_suggest_nick", None)       # 쓴 닉네임은 다음 가입 화면에서 새로
    return cur


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


@st.cache_data(ttl=86400, show_spinner=False)
def _blog_posts(entry_id: str, work: str, cafe_name: str, start_date: str, address: str = "") -> tuple[list, str]:
    """팝업별 네이버 블로그 후기 (하루 동안 기억 → 같은 팝업은 하루 한 번만 검색)."""
    posts, err = blog.search({"work": work, "cafe_name": cafe_name, "start_date": start_date, "address": address}, limit=15,
                             usage=api_usage)        # 한 달 30,000번이 넘으면 부르지 않음
    return [{**p.__dict__, "thumb": th} for p, th in blog.with_thumbs(posts)], err


_BLOG_COUNT: dict[str, int] = {}     # 팝업별 블로그 글 수 (탭 이름 '블로그 후기 (N)' 에 씀)
_BLOG_WARM = {"day": None}            # 미리 세기를 한 날 (서버마다 하루 한 번)


def _row_key(r: dict) -> tuple:
    return (str(r.get("entry_id")), str(r.get("work") or ""), str(r.get("cafe_name") or ""),
            str(r.get("start_date") or "")[:10], str(r.get("address") or ""))


def _warm_blog_counts(rows: list[dict]) -> None:
    """속도 (11/18): 상세를 열 때 블로그 검색을 기다리지 않게, 지금 열린·예정 팝업의 블로그 글 수를 뒤에서 미리 센다.
    팝업마다 검색 1번(대표 사진은 탭을 열 때). 하루 한 번, 한 달 호출 한도(blog.MONTHLY_LIMIT) 안에서만."""
    import threading

    if not blog.enabled() or _BLOG_WARM["day"] == TODAY:
        return
    _BLOG_WARM["day"] = TODAY
    todo = [_row_key(r) for r in rows if str(r.get("end_date") or "")[:10] >= TODAY.isoformat()]

    def run() -> None:
        for eid, work, cafe_name, start, addr in todo:
            if eid in _BLOG_COUNT:
                continue
            try:
                posts, err = blog.search({"work": work, "cafe_name": cafe_name, "start_date": start, "address": addr},
                                         limit=15, usage=api_usage)
            except Exception:
                continue
            if err == "limit":
                break
            if not err:
                _BLOG_COUNT[eid] = len(posts)

    threading.Thread(target=run, daemon=True, name="blog-warm").start()


def _blog_list(current: dict) -> list[dict]:
    if not blog.enabled():
        return []
    try:
        posts, _ = _blog_posts(str(current.get("entry_id")), str(current.get("work") or ""),
                               str(current.get("cafe_name") or ""), str(current.get("start_date") or "")[:10],
                               str(current.get("address") or ""))
    except Exception:
        return []
    _BLOG_COUNT[str(current.get("entry_id"))] = len(posts)
    return posts


def _bcard(p: dict) -> str:
    day = f'{p["day"]:%Y. %m. %d}' if p.get("day") else ""
    pic = (f'<img class="bcard-img" src="{escape(p["thumb"])}" alt="" loading="lazy" referrerpolicy="no-referrer">'
           if p.get("thumb") else "")
    return (f'<a class="bcard" href="{escape(p["link"])}" target="_blank" rel="noopener"><div class="bcard-txt">'
            f'<div class="bcard-t">{escape(p["title"])}</div><div class="bcard-d">{escape(p["desc"])}</div>'
            f'<div class="bcard-m"><span>{escape(p["blogger"] or "블로그")}</span><span>{day}</span></div></div>{pic}</a>')


def _render_blog_tab(current: dict, posts: list[dict]) -> None:
    """'블로그 후기' 탭: 안내 한 줄 + 카드 (제목 · 요약 2줄 · 블로거 · 날짜, 오른쪽 대표 사진). 누르면 원문 새 탭."""
    st.markdown(f'<div class="blog-note">{_mi("check_circle")} 네이버 블로그 검색 결과예요. '
                '부정확한 결과가 포함될 수 있으니 참고로만 봐 주세요.</div>', unsafe_allow_html=True)
    if not blog.enabled():
        st.markdown('<div class="blog-empty">블로그 후기는 네이버 검색을 연결한 뒤에 보여요.</div>', unsafe_allow_html=True)
        return
    if not posts:
        st.markdown('<div class="blog-empty">아직 이 팝업의 블로그 후기를 찾지 못했어요.</div>', unsafe_allow_html=True)
        return
    # <a> 로 시작하면 마크다운이 첫 카드를 문단으로 쪼개서, 바깥을 <div> 로 감싼다
    st.markdown('<div class="bcards">' + "".join(_bcard(p) for p in posts) + '</div>', unsafe_allow_html=True)


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



SIMILAR_MAX = 8


def _work_key(text) -> str:
    """작품 이름 비교용: 띄어쓰기·기호·대소문자를 빼고 본다 ('주술회전' = '주술 회전')."""
    return re.sub(r"[^0-9a-z가-힣ぁ-んァ-ン一-龥]", "", str(text or "").lower())


def similar_popups(current: dict, df: pd.DataFrame, limit: int = SIMILAR_MAX) -> list:
    """비슷한 팝업 (11/18 요청): 같은 작품의 다른 팝업 — 같은 행사의 다른 지역 지점이 먼저, 그다음 같은 작품의 다른 행사.
    끝난 팝업은 빼고, 진행 중 → 오픈 예정 순, 그 안에서는 빨리 여는 순."""
    key = _work_key(current.get("work"))
    if len(key) < 2 or df.empty:
        return []
    me = str(current["entry_id"])
    my_area = geo.area_name(str(current.get("address") or ""))
    my_cafe = _work_key(current.get("cafe_name"))
    out = []
    for _, r in df.iterrows():
        if str(r["entry_id"]) == me:
            continue
        k = _work_key(r.get("work"))
        if not k or not (k == key or (min(len(k), len(key)) >= 3 and (k in key or key in k))):
            continue
        label, _, rank = _status(r)
        if rank == 2:
            continue
        # 같은 행사(카페 이름이 같음)의 다른 지역 지점이 먼저
        other_branch = _work_key(r.get("cafe_name")) == my_cafe and geo.area_name(str(r.get("address") or "")) != my_area
        out.append((0 if other_branch else 1, rank, str(r.get("start_date") or ""), r))
    out.sort(key=lambda t: t[:3])
    return [t[3] for t in out[:limit]]


def nearby_popups(current: dict, df: pd.DataFrame, limit: int = 8, max_km: float = 30.0) -> list[tuple]:
    """이 근처 다른 팝업: 지금 팝업 자리에서 가까운 순 (30km 안, 끝난 것 빼고). [(행, km)]."""
    try:
        here = (float(current.get("lat")), float(current.get("lng")))
    except (TypeError, ValueError):
        return []
    if any(pd.isna(x) for x in here):
        return []
    me = str(current["entry_id"])
    out = []
    for _, r in df.dropna(subset=["lat", "lng"]).iterrows():
        if str(r["entry_id"]) == me or _status(r)[2] == 2:
            continue
        km = my_place._km(here, (float(r["lat"]), float(r["lng"])))
        if km <= max_km:
            out.append((km, r))
    out.sort(key=lambda t: t[0])
    return [(r, km) for km, r in out[:limit]]


def _km_text(km: float) -> str:
    if km < 0.05:
        return "같은 건물"            # 좌표가 같은 곳은 '거리 0m' 대신
    return "거리 " + (f"{round(km * 1000)}m" if km < 1 else f"{km:.1f}km")


def _poster_row(sec: str, title: str, icon: str, items: list[tuple], tip: str = "") -> None:
    """상세 아래 포스터 줄 하나. items = [(행, 제목, 둘째 줄)]. 옆으로 넘겨 본다."""
    if not items:
        return
    with st.container(key=f"simsec_{sec}"):
        # 제목 옆 ? 에 커서를 올리면 어떤 팝업을 모았는지 보인다 (11/18 요청)
        st.markdown(f'<div class="sim-head">{_mi(icon)}{escape(title)}</div>', unsafe_allow_html=True, help=tip or None)
        with st.container(horizontal=True, key=f"sim_row_{sec}"):
            for r, name, meta in items:
                eid = str(r["entry_id"])
                label, color, _ = _status(r)
                with st.container(key=f"card_sim_{sec}_{eid}"):
                    st.markdown(
                        f'<div class="simc"><div class="simp" style="background-image:url(\'{_poster_url(r.get("images"))}\'),'
                        f' url(\'{images.DEFAULT_POSTER_URL}\')"><span class="sims {color}">{escape(label)}</span>'
                        f'<span class="simr">{_area_badge(r.get("address"), "area")}</span></div>'
                        f'<div class="simt">{escape(name)}</div>'
                        f'<div class="simm">{escape(_period(r, lambda d: f"{d:%m.%d}", show_raw=False))}</div>'
                        + (f'<div class="simm">{escape(meta)}</div>' if meta else "") + '</div>', unsafe_allow_html=True)
                    if st.button("자세히 보기", key=f"open_sim_{sec}_{eid}", width="stretch"):
                        st.session_state["selected"] = eid
                        st.session_state["scroll_top"] = True
                        st.rerun()


def render_similar(current: dict, df: pd.DataFrame) -> None:
    """상세 아래 추천 줄 (11/18 요청): 비슷한 팝업 · 이 근처 다른 팝업. 비어 있는 줄은 그리지 않는다.
    ('다른 사람들이 많이 본 팝업' 줄은 같은 날 요청으로 뺐다)"""
    with st.container(key="similar"):
        _poster_row("same", "비슷한 팝업", "auto_awesome",
                    [(r, str(r.get("cafe_name") or r.get("work") or ""), "") for r in similar_popups(current, df)],
                    tip="이 팝업과 같은 작품의 다른 팝업이에요. 같은 행사의 다른 지역 지점이 먼저 오고, "
                        "그다음 같은 작품의 다른 행사예요. 끝난 팝업은 빼고, 진행 중 → 오픈 예정 순이에요.")
        _poster_row("near", "이 근처 다른 팝업", "location_on",
                    [(r, str(r.get("work") or ""), f'{r.get("cafe_name") or ""} · {_km_text(km)}'.strip(" ·"))
                     for r, km in nearby_popups(current, df)],
                    tip="이 팝업 자리에서 30km 안에 있는 다른 팝업을 가까운 순으로 모았어요. 끝난 팝업은 빼요.")


def render_detail_tabs(current: dict) -> None:
    """상세 화면 오른쪽: 리뷰 / 수정하기 탭."""
    entry_id = str(current["entry_id"])
    n = review.counts(reviews.current_rows()).get(entry_id, 0)
    # 키를 주고 고른 탭을 서버가 기억하게 한다. 그렇지 않으면 수정하기에서 이미지를 지우거나 올려
    # 다시 그릴 때마다 첫 탭(리뷰)으로 돌아가 버린다
    tab_review, tab_edit = st.tabs([f":material/chat_bubble: 리뷰 {n}", ":material/edit: 수정하기"], key=f"detail_tabs_{entry_id}",
                                   on_change="rerun")
    with tab_review:
        sub = st.session_state.get(f"rvsub_{entry_id}", "review")
        # 블로그 글 목록(대표 사진 포함)은 '블로그 후기' 탭을 열 때만. 건수는 미리 센 값(_warm_blog_counts)을 쓰고,
        # 아직 못 셌으면 그 자리에서 검색해서라도 늘 보여 준다 (11/18 요청: 건수가 안 보임)
        posts = _blog_list(current) if sub == "blog" or entry_id not in _BLOG_COUNT else None
        n_blog = len(posts) if posts is not None else _BLOG_COUNT.get(entry_id)

        def subtabs() -> bool:
            # 리뷰 쓰기 칸 아래에 '리뷰 후기 / 블로그 후기' (11/18 요청)
            with st.container(horizontal=True, key="rv_subtabs"):
                for k, label in (("review", f"리뷰 후기 ({n})"), ("blog", f"블로그 후기 ({n_blog or 0})")):
                    st.button(label, key=f"rvsub_{'on_' if sub == k else ''}{k}_{entry_id}",
                              on_click=lambda k=k: st.session_state.update({f"rvsub_{entry_id}": k}))
            if sub == "blog":
                _render_blog_tab(current, posts)
                return False
            return True

        render_reviews(entry_id, after_write=subtabs)
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
                f"최대 {review.MAX_IMAGES}장 · 한 장 {review.IMAGE_MB}MB · 다른 사람 얼굴·영수증·연락처가 보이는 사진은 올리지 말아 주세요 "
                "(사진 속 위치 정보는 자동으로 지워요)", type=images.TYPES,
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


@st.dialog("리뷰 삭제", on_dismiss=lambda: st.session_state.pop("_rv_del", None))
def confirm_review_delete(entry_id: str, replies: int, as_admin: bool = False) -> None:
    """리뷰 삭제 (11/18 권한): 쓴 사람은 내 글만, 관리자는 모든 글. 관리자가 지울 땐 사유를 적고, 쓴 회원에게 알림이 간다."""
    st.write("이 글을 삭제할까요? 삭제하면 다시 볼 수 없어요."
             + (f" 달린 답글 {replies}개도 함께 안 보이게 돼요." if replies else ""))
    reason = ""
    if as_admin:
        reason = st.text_area("삭제 사유 (쓴 사람에게 알림으로 가요)", key=f"rv_del_reason_{entry_id}", height=80, max_chars=200,
                              placeholder="예: 다른 팝업과 관계없는 광고 글이에요")
    c1, c2 = st.columns(2)
    if c1.button("취소", width="stretch", key=f"rv_del_no_{entry_id}"):
        st.session_state.pop("_rv_del", None)
        st.rerun()
    if c2.button("삭제", type="primary", width="stretch", key=f"rv_del_ok_{entry_id}"):
        st.session_state.pop("_rv_del", None)
        # 버튼이 보였더라도 지우는 순간 한 번 더 확인한다
        row = next((r for r in reviews.current_rows() if str(r["entry_id"]) == entry_id), None)
        if not row:
            st.session_state["flash"] = "이미 지워진 글이에요."
            st.rerun()
        mine = bool(_member()) and review.can_delete(row, _me())
        if as_admin and _is_admin():
            if len(" ".join(reason.split())) < 2:
                st.error("삭제 사유를 두 글자 이상 적어 주세요. 쓴 사람에게 알림으로 가요.")
                return
            reviews.soft_delete(entry_id)       # 저장소는 지우지 않고 '삭제됨' 행을 쌓는다
            images.remove(row.get("images"))    # 붙은 사진 파일은 실제로 지운다 (11/18 개인정보)
            tag = str(row.get("nickname") or "").rsplit("#", 1)[-1] if "#" in str(row.get("nickname") or "") else ""
            writer = _member_by_tag().get(tag) if tag.startswith("m") else None
            if writer and not mine and _rules().get("rv_del", {}).get("enabled", True):
                try:
                    admin.review_removed(notices_store, str(writer["entry_id"]), str(row.get("body") or row.get("kind") or "")[:30], reason)
                except StorageWriteError:
                    pass
            st.session_state["flash"] = "삭제했어요." + (" 쓴 사람에게 사유를 알림으로 보냈어요." if writer and not mine else "")
        elif mine:
            reviews.soft_delete(entry_id)
            images.remove(row.get("images"))    # 붙은 사진 파일은 실제로 지운다 (11/18 개인정보)
            st.session_state["flash"] = "삭제했어요."
        else:
            st.session_state["flash"] = "내가 쓴 리뷰만 삭제할 수 있어요."
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
    if mine or is_admin:
        # 권한 (11/18 요청): 수정·삭제는 내가 쓴 글만. 관리자는 모든 글을 삭제할 수 있고, 사유를 적으면 쓴 사람에게 알림
        t, b = st.columns([6, 1], vertical_alignment="center")
        t.markdown(head + when, unsafe_allow_html=True)
        with b.popover("⋯", key=f"rv_more_{eid}", type="tertiary"):
            if mine and st.button("수정", key=f"rv_edit_{eid}", width="stretch"):
                st.session_state["rv_editing"] = eid
                st.rerun()
            # 창은 '⋯' 칸 밖에서 연다 (칸 안 버튼으로 열면 창 안의 '삭제' 누름이 다음 그리기에서 사라졌다)
            if mine:
                st.button("삭제", key=f"rv_delmine_{eid}", width="stretch",
                          on_click=lambda: st.session_state.update(_rv_del=(eid, replies, False)))
            if is_admin and not mine:
                st.button("삭제 (관리자)", key=f"rv_del_{eid}", width="stretch",
                          on_click=lambda: st.session_state.update(_rv_del=(eid, replies, True)))
        pend = st.session_state.get("_rv_del")
        if pend and pend[0] == eid:
            confirm_review_delete(eid, pend[1], as_admin=pend[2])
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
    # 사진 (11/18 요청): 원래 사진이 없었어도 고칠 때 새로 붙일 수 있다. 있던 사진은 '빼기' 로 뺄 수 있다 (원글만)
    keep: list[str] = []
    photos = []
    if not str(r.get("parent_id") or ""):
        old = [x.name for x in images.paths(r.get("images"))]
        if old:
            st.caption("붙어 있는 사진 (뺄 사진은 체크를 풀어요)")
            cols = st.columns(min(len(old), 4))
            for i, name in enumerate(old):
                with cols[i % len(cols)]:
                    st.image(images.url(images.IMAGE_DIR / name), width="stretch")
                    if st.checkbox("남기기", value=True, key=f"rv_edit_keep_{eid}_{i}"):
                        keep.append(name)
        room = review.MAX_IMAGES - len(keep)
        if room > 0:
            photos = list(st.file_uploader(f"사진 추가 (최대 {room}장 · 한 장 {review.IMAGE_MB}MB)", type=images.TYPES,
                                           accept_multiple_files=True, key=f"rv_edit_img_{eid}") or [])
            if len(photos) > room:
                st.caption(f":red[사진은 모두 {review.MAX_IMAGES}장까지예요. 앞의 {room}장만 올라가요.]")
                photos = photos[:room]
            heavy = [x.name for x in photos if images.too_big(x.getvalue(), review.IMAGE_MB)]
            if heavy:
                st.caption(f":red[{review.IMAGE_MB}MB 가 넘는 사진은 올릴 수 없어요: {', '.join(heavy)}]")
                bad = True
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
            try:
                added = [images.save(x.name, x.getvalue()) for x in photos]
            except ValueError as err:
                st.error(str(err))
                return
            payload["images"] = ",".join(keep + added)
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


def render_reviews(cafe_id: str, after_write=None) -> None:
    """after_write: 리뷰 쓰기 칸 바로 아래에 그릴 것 ('리뷰 후기 / 블로그 후기' 탭). False 를 돌려주면 리뷰 목록은 그리지 않는다."""
    _review_lightbox()      # 리뷰 사진을 누르면 확대 보기 팝업
    # 맨 위 리뷰 쓰기: 닉네임·종류·별점·입력칸·리뷰 등록 버튼을 처음부터 펼쳐 둔다. 그 아래에 리뷰를 보여 준다
    with st.container(border=True, key=f"rvbox_{cafe_id}"):
        _write_box(cafe_id)
    if after_write is not None and after_write() is False:
        return

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
            try:
                saved = [name if data is None else images.save(name, data) for name, data in new_images]
            except ValueError as err:          # 그림으로 읽을 수 없는 파일 (위치 정보 지우기 단계에서 걸림)
                st.error(str(err), icon=":material/error:")
                return
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
    if (end - TODAY).days <= 3:                 # 끝나는 날까지 3일 이하: '마감임박' 빨간 글씨 (11/18 요청)
        return "마감임박", "red", 0
    return "진행 중", "green", 0


def _poster_url(value) -> str:
    """카드에 쓸 포스터 주소. 포스터가 없으면 기본 그림 (포스터를 올린 카드와 똑같이 보인다)."""
    poster = images.poster(value)
    return images.url(poster) if poster else images.DEFAULT_POSTER_URL


def _chips(r, full: bool = False) -> str:
    """이벤트 정보는 민트로 채운 칩, 굿즈는 민트 테두리 칩. full 이 아니면 몇 개만 보이고 나머지는 +N 으로 줄인다.
    카드(full 아님)에서는 칩 글자가 12자를 넘으면 '…' 로 줄인다 — 카드 밖으로 잘려 보였다 (11/18)."""
    cut = (lambda t: t if full or len(t) <= 12 else t[:11].rstrip() + "…")
    all_tags, goods = _split(r.get("tags") or ""), _split(r.get("goods") or "")
    flags = [t for t in all_tags if t in (pdates.TAG_ALWAYS, pdates.TAG_CHECK)]
    all_tags = [t for t in all_tags if t not in flags]
    tags = [f'<span class="chip {"warn" if t == pdates.TAG_CHECK else "tag"}">{escape(t)}</span>' for t in flags] if full else []
    tags += [f'<span class="chip tag">{escape(cut(t))}</span>' for t in (all_tags if full else all_tags[:2])]
    shown = [f'<span class="chip">{escape(cut(g))}</span>' for g in (goods if full else goods[:3])]
    if not full:               # 카드 위에는 첫 번째 칩 하나만 (11/18 요청). 전부는 커서 올림·상세에서
        return "".join((tags + shown)[:1])
    return "".join(tags + shown)


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
    if cls == "area":          # 포스터 위: 사진에 묻히지 않게 시 색을 진하게 채우고 그림자 (11/18 요청)
        return (f'<span class="{cls}" style="background:{color}E6;border:1.5px solid #ffffffCC;color:#fff;'
                f'text-shadow:0 1px 2px rgba(0,0,0,.35);box-shadow:0 2px 8px rgba(0,0,0,.28)">{escape(area)}</span>')
    return (f'<span class="{cls}" style="background:{color}1A;border:1.5px solid {color};color:{color}">'
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


def _poster_card(r, label: str, color: str = "green") -> str:
    return f"""
<div class="pcard" style="background-image:url('{_poster_url(r.get("images"))}'), url('{images.DEFAULT_POSTER_URL}')">
  {_area_badge(r.get("address"), cls="area")}
  <span class="state {color}">{escape(label)}</span>
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
    if not wide:
        # 모바일 지도보기: 필터 버튼을 리스트로 보기와 같은 높이에 두고, 비는 자리에 '마지막 업데이트' 줄을 왼쪽에 붙인다 (11/18 요청)
        st.markdown("<style>@media (max-width: 640px) { html:not(.aw-scrolled) body .st-key-view_tools { margin-top: var(--aw-map-fgap, 21px) !important; }"
                    " html:not(.aw-scrolled) body [data-testid=\"stElementContainer\"]:has(.upd:not(.warn)) { margin-top: -36px !important; padding-right: 52px; } }</style>",
                    unsafe_allow_html=True)
    if wide:
        # 모바일 리스트 보기: 필터 아이콘을 '팝업 카페 N곳' 줄 오른쪽 위에, 글자 높이만큼 작게 (11/18 요청)
        st.markdown("<style>@media (max-width: 640px) { html:not(.aw-scrolled) body .st-key-view_tools { margin-top: -70px !important; }"
                    # '팝업 카페 N곳' ↔ 정렬 ↔ 카드 사이 여백 반으로 (11/18 요청)
                    " .st-key-sort { margin-top: -31px !important; }"
                    " [data-testid='stLayoutWrapper']:has(> .st-key-listtools) { margin-bottom: -13px !important; }"
                    " html body .st-key-view_tools .st-key-m_filter_btn button { width: 30px !important; min-width: 30px !important;"
                    "   height: 26px !important; border-radius: 8px !important; }"
                    " html body .st-key-view_tools .st-key-m_filter_btn button span { font-size: 1rem !important; }"
                    " html body .st-key-view_tools .st-key-m_filter_btn { width: 30px !important; min-width: 30px !important; flex: 0 0 30px !important; } }</style>",
                    unsafe_allow_html=True)
    else:
        # 모바일 지도 보기: 필터 아이콘은 뺐다 (11/18 요청)
        st.markdown("<style>@media (max-width: 640px) { html body .st-key-view_tools { display: none !important; } }</style>",
                    unsafe_allow_html=True)
    tools = st.container(horizontal=True, key="view_tools")
    with tools:
        if st.button(str(active) if active else "", icon=":material/close:" if m_open else ":material/tune:",
                     key="m_filter_btn"):
            st.session_state["m_filters"] = not m_open
            st.rerun()
        if not wide:              # 모바일 리스트 보기에서는 지도·캘린더 아이콘을 뺐다 (11/18 요청, 메뉴바 탭으로)
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


LIST_PAGE = 24         # 리스트 보기에서 처음 보여 줄 카드 수 (4열 × 6줄). '더 보기' 로 24장씩 더


# ================================================================ 홈 (11/18 요청)
HOME_WEEK_DAYS = 7          # 실시간 인기: 최근 7일 북마크·리뷰


def _created_map() -> dict[str, str]:
    """팝업별 처음 등록한 시각 (첫 기록)."""
    out: dict[str, str] = {}
    for r in store.all_rows():
        eid, at = str(r.get("entry_id")), str(r.get("updated_at") or "")
        if eid not in out or at < out[eid]:
            out[eid] = at
    return out


def _recent(rows: list[dict], days: int) -> list[dict]:
    since = (datetime.now().astimezone() - timedelta(days=days)).isoformat()
    return [r for r in rows if str(r.get("updated_at") or "") >= since]


def _home_rank(live: list[dict]) -> list[dict]:
    """실시간 인기 급상승: 최근 7일 북마크 × 2 + 리뷰·답글 수, 같으면 전체 기간 점수. 0점은 오픈 임박 순으로 채운다."""
    frows, rrows = favs.current_rows(), reviews.current_rows()
    f7, r7 = favorite.counts(_recent(frows, HOME_WEEK_DAYS)), review.counts(_recent(rrows, HOME_WEEK_DAYS))
    fa, ra = favorite.counts(frows), review.counts(rrows)
    score = lambda e: (f7.get(e, 0) * 2 + r7.get(e, 0), fa.get(e, 0) * 2 + ra.get(e, 0))
    return sorted(live, key=lambda r: (tuple(-x for x in score(str(r["entry_id"]))), str(r.get("start_date") or "")))


def _is_reserve(r: dict) -> bool:
    text = " ".join(str(r.get(k) or "") for k in ("tags", "goods", "note"))
    return bool(re.search(r"사전\s*예약|예약제|사전\s*예매", text))


def _home_areas(rows: list[dict], n: int = 3) -> list[str]:
    cnt: dict[str, int] = {}
    for r in rows:
        a = geo.area_name(str(r.get("address") or ""))
        if a:
            cnt[a] = cnt.get(a, 0) + 1
    return [a for a, _ in sorted(cnt.items(), key=lambda t: -t[1])[:n]]


def _home_card(sec: str, r: dict, rank: int | None = None, badge: str = "", tall: bool = False) -> None:
    """홈 포스터 카드: 포스터(순위 숫자 · 배지 · 북마크) · 이름 · 기간 · 지역/상태 칩. 누르면 상세."""
    eid = str(r["entry_id"])
    label, color, _ = _status(r)
    area = geo.area_name(str(r.get("address") or ""))
    with st.container(key=f"card_h{sec}_{eid}"):
        st.markdown(
            f'<div class="hc{" tall" if tall else ""}"><div class="hcp" style="background-image:url(\'{_poster_url(r.get("images"))}\'), url(\'{images.DEFAULT_POSTER_URL}\')">'
            + (f'<span class="hcbadge{" res" if badge.startswith("사전예약") else ""}">{escape(badge)}</span>' if badge else "")
            + (f'<span class="hcrank">{rank}</span>' if rank else "")
            + f'</div><div class="hct">{escape(str(r.get("work") or ""))}</div>'
            f'<div class="hcd">{escape(_period(r, lambda d: f"{d:%m.%d}", show_raw=False))}</div>'
            f'<div class="hcchips">' + (f'<span>{escape(area)}</span>' if area else "")
            + f'<span class="st {color}">{escape(label)}</span></div></div>', unsafe_allow_html=True)
        if st.button("자세히 보기", key=f"open_h{sec}_{eid}", width="stretch"):
            st.session_state.update(selected=eid, scroll_top=True)
            st.rerun()
        _heart(eid, f"h{sec}")


def _open_btn(key: str, eid: str) -> None:
    if st.button("자세히 보기", key=key, width="stretch"):
        st.session_state.update(selected=eid, scroll_top=True)
        st.rerun()


def _home_slide(r: dict, rank: int, total: int) -> None:
    """랭킹 배너 한 장: 흐린 포스터 바탕 + 오른쪽 포스터 + 왼쪽 글 (순위 · 작품 · 장소 · 기간 · 칩)."""
    eid = str(r["entry_id"])
    label, _, _ = _status(r)
    area = geo.area_name(str(r.get("address") or ""))
    url = _poster_url(r.get("images"))
    period = _period(r, lambda d: f"{d:%m.%d}", show_raw=False)
    chips = (f'<span>{escape(area)}</span>' if area else "") + f'<span>{escape(label)}</span>'
    with st.container(key=f"card_hb_{eid}"):
        st.markdown(
            f'<div class="hb"><div class="hbbg" style="background-image:url(&quot;{url}&quot;)"></div>'
            f'<div class="hbpic" style="background-image:url(&quot;{url}&quot;), url(&quot;{images.DEFAULT_POSTER_URL}&quot;)"></div>'
            f'<div class="hbtitle">{_mi("local_fire_department")}실시간 인기 급상승 랭킹</div>'
            f'<div class="hbtxt"><div class="hbrank">{rank}<small>위</small></div>'
            f'<div class="hbt">{escape(str(r.get("work") or ""))}</div>'
            f'<div class="hbd">{escape(str(r.get("cafe_name") or ""))} · {escape(period)}</div>'
            f'<div class="hbchips">{chips}</div></div>'
            '</div>', unsafe_allow_html=True)
        _open_btn(f"open_hb_{eid}", eid)


def _home_rank_rows(rows: list[dict]) -> None:
    """오른쪽 랭킹 목록: 순위 숫자 · 작품 · 장소 · 상태. 줄을 누르면 왼쪽 배너가 그 순위로 바뀐다 (11/18 요청,
    _DRAG_JS 가 처리 — 서버를 다시 부르지 않아 바로 바뀐다). 팝업 상세는 배너를 눌러서 연다."""
    out = []
    for i, r in enumerate(rows):
        label, color, _ = _status(r)
        out.append(f'<div class="hl{" on" if i == 0 else ""}" data-i="{i}"><b class="hln">{i + 1}</b><div class="hlb">'
                   f'<div class="hlt">{escape(str(r.get("work") or ""))}</div>'
                   f'<div class="hls">{escape(str(r.get("cafe_name") or ""))}</div></div>'
                   f'<span class="hlst {color}">{escape(label)}</span></div>')
    st.markdown(f'<div class="hls-wrap">{"".join(out)}</div>', unsafe_allow_html=True)


WEEKDAYS = "월화수목금토일"


def _home_week(df: pd.DataFrame) -> None:
    """월~일 일곱 칸. 칸 머리: 요일 · (오늘) · 그날 끝나는 팝업 수. 지난 요일 칸은 이미 끝난 팝업이라 흐리게."""
    monday = TODAY - timedelta(days=TODAY.weekday())
    rows = df.to_dict("records")
    with st.container(horizontal=True, key="home_week"):
        for i in range(7):
            day = monday + timedelta(days=i)
            ends = sorted([r for r in rows if pd.to_datetime(r["end_date"]).date() == day
                           and pd.to_datetime(r["start_date"]).date() <= day], key=lambda r: str(r.get("work") or ""))
            cls = "today" if day == TODAY else ("past" if day < TODAY else "")
            with st.container(key=f"wk_{i}"):
                st.markdown(f'<div class="wkh {cls}"><b>{WEEKDAYS[i]}{" · 오늘" if day == TODAY else ""}</b>'
                            f'<span class="wkd">{day.month}.{day.day}</span><span class="wkn">{len(ends)}</span></div>',
                            unsafe_allow_html=True)
                # 칸이 너무 길어지지 않게 요일마다 3곳까지, 나머지는 '+N건 더보기' 를 누르면 그 칸에서 펼친다 (11/18 요청)
                opened = bool(st.session_state.get(f"wk_open_{i}"))
                for r in ends if opened else ends[:WEEK_MAX]:
                    d = (day - TODAY).days
                    _home_card("w", r, badge="오늘 종료" if d == 0 else ("종료" if d < 0 else f"D-{d}"), tall=True)
                if len(ends) > WEEK_MAX and not opened:
                    st.button(f"+{len(ends) - WEEK_MAX}건 더보기", key=f"wk_more_{i}", icon=":material/expand_more:",
                              on_click=lambda i=i: st.session_state.update({f"wk_open_{i}": True}))


RV_KIND_CLASS = {"다녀온 후기": "visit", "기대평": "hope", "기타": "etc"}     # 후기 모음 카드의 종류 칩 (11/18 요청)


def _home_reviews(df: pd.DataFrame, limit: int = 12) -> None:
    """꿀팁 가득! 실시간 후기 모음 (11/18 요청): 최신 리뷰 순, 사진 있는 리뷰가 먼저. 답글은 빼고, 지금 있는 팝업 것만.
    카드: 팝업(포스터 · 작품 · 상태 · 지역) + 리뷰(사진 · 닉네임 · 날짜 · 별점 · 본문 · 사진 2장). 누르면 그 팝업 상세."""
    by_id = {str(r["entry_id"]): r for r in df.to_dict("records")}
    rows = [r for r in reviews.current_rows() if not str(r.get("parent_id") or "") and str(r.get("cafe_id")) in by_id
            and str(r.get("body") or "").strip()]
    rows.sort(key=lambda r: (bool(images.paths(r.get("images"))), str(r.get("updated_at") or "")), reverse=True)
    rows = rows[:limit]
    if not rows:
        st.markdown('<div class="home-empty">아직 후기가 없어요. 다녀온 팝업에 첫 후기를 남겨 보세요.</div>', unsafe_allow_html=True)
        return
    with st.container(horizontal=True, key="home_row_rv"):
        for rv in rows:
            pop = by_id[str(rv["cafe_id"])]
            label, color, _ = _status(pop)
            area = geo.area_name(str(pop.get("address") or ""))
            who, pic = _author(rv.get("nickname"))
            pics = images.paths(rv.get("images"))[:2]
            stars = ""
            if rv.get("rating") not in (None, ""):
                try:
                    n = max(0, min(5, int(float(rv["rating"]))))
                    stars = (f'<div class="rvs">{"★" * n}<span class="off">{"★" * (5 - n)}</span>'
                             f'<b>{n:.1f}</b><span class="of"> / 5.0</span></div>')
                except (TypeError, ValueError):
                    stars = ""
            photos = "".join(f'<div class="rvp" style="background-image:url(&quot;{images.url(x)}&quot;)"></div>' for x in pics)
            with st.container(key=f"card_hv_{rv['entry_id']}"):
                st.markdown(
                    f'<div class="rvc"><div class="rvtop"><div class="rvth" style="background-image:url(&quot;{_poster_url(pop.get("images"))}&quot;)"></div>'
                    f'<div class="rvtt"><div class="rvw">{escape(str(pop.get("work") or ""))}</div><div class="rvchips">'
                    f'<span class="st {color}">{escape(label)}</span>' + (f'<span>{escape(area)}</span>' if area else "")
                    + '</div></div></div><div class="rvbox"><div class="rvme">' + _avatar_img(pic, 34, "rv-av")
                    + f'<div class="rvwho"><b>{escape(_nick_only(who))}</b>{stars}</div><span class="rvdate">{escape(_when(rv.get("updated_at")))}</span></div>'
                    + (f'<span class="rvkind {RV_KIND_CLASS.get(str(rv.get("kind")), "etc")}">{escape(str(rv.get("kind")))}</span>' if rv.get("kind") else "")
                    + f'<div class="rvbody">{escape(str(rv.get("body") or ""))}</div>'
                    + (f'<div class="rvpics">{photos}</div>' if photos else "") + '</div></div>', unsafe_allow_html=True)
                _open_btn(f"open_hv_{rv['entry_id']}", str(rv["cafe_id"]))


def _home_more(sort: str, reserve: bool = False) -> None:
    """'더보기' → 리스트 보기 (정렬을 맞춰서). reserve 면 사전예약 팝업만."""
    st.session_state.update(home_view=False, list_only=True, sort=sort, selected=None, scroll_top=True, res_only=reserve)


def _home_head(title: str, icon: str, more_sort: str = "", key: str = "", reserve: bool = False) -> None:
    with st.container(horizontal=True, vertical_alignment="center", key=f"hh_{key}"):
        st.markdown(f'<div class="home-h">{_mi(icon)}{escape(title)}</div>', unsafe_allow_html=True)
        if more_sort:
            st.button("더보기", key=f"hmore_{key}", type="tertiary", on_click=_home_more, args=(more_sort, reserve))


def _home_area_pills(key: str, areas: list[str]) -> str:
    pick = st.pills("지역", ["전체"] + areas, default="전체", key=f"hp_{key}", label_visibility="collapsed")
    return pick or "전체"


def render_home(df: pd.DataFrame) -> None:
    """홈 (11/18 요청): 내가 관심있는 작품 · 실시간 인기 급상승 랭킹 · 따끈따끈 신규 등록 · 이번 주에 끝나는 · 사전예약 팝업."""
    live = _live_rows(df)
    areas = _home_areas(live)
    by_area = lambda rows, a: rows if a == "전체" else [r for r in rows if geo.area_name(str(r.get("address") or "")) == a]
    with st.container(key="home"):
        render_stories(df)

        # 실시간 인기 급상승 랭킹 (5위까지, 11/18 요청): 왼쪽 큰 배너(‹ › 로 넘김 · 5초마다 넘어감) + 오른쪽 1~5위 목록
        # (제목은 배너 안 왼쪽 위에 크게, 11/18 요청)
        top = _home_rank(live)[:5]          # (지역 고르기 버튼은 11/18 요청으로 뺐다)
        if top:
            ban, lst = st.columns([2.3, 1], gap="medium")
            with ban, st.container(horizontal=True, key="home_banner"):
                for i, r in enumerate(top, 1):
                    _home_slide(r, i, len(top))
            with lst, st.container(key="home_ranklist"):
                _home_rank_rows(top)

        # 따끈따끈 신규 등록 (먼저 등록한 시각이 늦은 순)
        _home_head("따끈따끈 신규 등록 팝업", "fiber_new", more_sort="최신순", key="new")
        a = _home_area_pills("new", areas)
        made = _created_map()
        new = sorted(by_area(live, a), key=lambda r: made.get(str(r["entry_id"]), ""), reverse=True)[:12]
        with st.container(horizontal=True, key="home_row_new"):
            for r in new:
                _home_card("n", r)

        # 이번 주에 끝나는 팝업: 월~일 주간 캘린더 (11/18 요청). 그날 끝나는 팝업을 그 요일 칸에, 오늘 칸은 강조
        _home_head("이번 주에 끝나는 팝업", "hourglass_bottom", more_sort="종료 임박순", key="week")
        _home_week(df)

        # 사전예약 팝업 (태그·특전·소개에 '사전 예약')
        # 아직 열기 전(오픈 예정)인 팝업만 — 이미 진행 중인 건 뺀다 (11/18 요청). 빨리 여는 순
        res = sorted([r for r in live if _is_reserve(r) and _status(r)[2] == 1], key=lambda r: str(r.get("start_date")))
        _home_head("사전예약 팝업", "event_available", more_sort="오픈 임박순", key="res", reserve=True)
        if res:
            with st.container(horizontal=True, key="home_row_res"):
                for r in res:
                    sd = pd.to_datetime(r["start_date"]).date()
                    _home_card("p", r, badge=f"사전예약 D-{(sd - TODAY).days}")
        else:
            st.markdown('<div class="home-empty">곧 열리는 팝업 중 사전예약을 받는 곳이 없어요.</div>', unsafe_allow_html=True)

        # 꿀팁 가득! 실시간 후기 모음 (11/18 요청)
        _home_head("꿀팁 가득! 실시간 후기 모음", "rate_review", key="rv")
        _home_reviews(df)


HOME_CSS = """
<style>
.st-key-home { gap: 6px; }
[class*="st-key-hh_"] { margin-top: 22px; margin-bottom: 6px; min-height: 34px; justify-content: space-between !important; }

.home-h { font-size: 1.2rem; font-weight: 800; display: flex; align-items: center; gap: 6px; }
.home-h .mi { color: var(--accent); font-size: 1.35rem; }
[class*="st-key-hmore_"] button p { color: #7B8784 !important; font-size: .85rem !important; }
[class*="st-key-hp_"] { margin-bottom: 2px; }
.st-key-res_only_chip button { border-radius: 999px; background: #EEEBFD; border: 1px solid #6C5CE7; color: #4B3CC4;
  min-height: 0; padding: 3px 12px; }
.st-key-res_only_chip button p { font-size: .8rem !important; font-weight: 700; }
.home-empty { color: #7B8784; font-size: .85rem; padding: 10px 2px 4px; }
/* 랭킹 배너: 한 장씩 넘기는 줄 (scroll-snap) + ‹ › (_DRAG_JS) */
.st-key-home_banner { flex-wrap: nowrap !important; overflow-x: auto; overflow-y: hidden; gap: 0 !important;
  scroll-snap-type: x mandatory; scroll-behavior: smooth; scrollbar-width: none; border-radius: 18px; }
.st-key-home_banner::-webkit-scrollbar { display: none; }
.st-key-home [data-testid="stHorizontalBlock"]:has(.st-key-home_banner) { margin-top: 12px; }
.st-key-home_banner > div { flex: 0 0 100% !important; width: 100% !important; min-width: 100% !important; scroll-snap-align: start; }
.st-key-home_banner { height: 340px !important; min-height: 340px; }
.st-key-home_banner [class*="st-key-card_hb_"] { height: 340px; }
.st-key-home_banner [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.hb { position: relative; height: 340px; border-radius: 18px; overflow: hidden; background: #1E2523; }
.hb .hbbg { position: absolute; inset: -20px; background-size: cover; background-position: center; filter: blur(18px) brightness(.55); }
.hb .hbpic { position: absolute; right: 28px; top: 24px; bottom: 24px; aspect-ratio: 3/4; border-radius: 12px;
  background-size: cover; background-position: center; box-shadow: 0 10px 30px rgba(0,0,0,.4); }
.hb .hbtxt { position: absolute; left: 56px; bottom: 32px; right: 300px; color: #fff; }
.hb .hbrank { font-size: 4rem; font-weight: 900; font-style: italic; line-height: 1; letter-spacing: -2px; }
.hb .hbrank small { font-size: 1.2rem; font-style: normal; margin-left: 4px; }
/* 배너 제목 (11/18 요청): 왼쪽 위 작은 어두운 알약 (불꽃 아이콘 + 글씨) */
.hb .hbtitle { position: absolute; left: 46px; top: 24px; display: flex; align-items: center; gap: 5px; padding: 5px 12px 5px 9px;
  border-radius: 10px; background: rgba(20,24,23,.62); color: #fff; font-size: .9rem; font-weight: 800; backdrop-filter: blur(4px); }
.hb .hbtitle .mi { color: #8F7BFF; font-size: 1.1rem; font-variation-settings: 'FILL' 1; }
.hb .hbt { font-size: 1.9rem; font-weight: 900; line-height: 1.2; margin-top: 12px; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden; }
.hb .hbd { font-size: .9rem; opacity: .9; margin-top: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hb .hbchips { display: flex; gap: 6px; margin-top: 12px; }
.hb .hbchips span { font-size: .75rem; font-weight: 700; padding: 3px 10px; border-radius: 8px; background: rgba(255,255,255,.18); }
/* 배너 오른쪽 아래 점: 누르면 그 장으로 (_DRAG_JS) */
.aw-dots { position: absolute; right: 22px; z-index: 8; display: flex; gap: 6px; padding: 5px 9px; border-radius: 999px;
  background: rgba(0,0,0,.32); }
.aw-dots button { width: 8px; height: 8px; padding: 0; border: 0; border-radius: 999px; background: rgba(255,255,255,.55);
  cursor: pointer; transition: width .2s ease, background .2s ease; }
.aw-dots button.on { width: 20px; background: #fff; }
[data-testid="stColumn"]:has(.st-key-home_banner) .aw-arrow { width: 36px; height: 36px; font-size: 22px; line-height: 32px;
  background: rgba(255,255,255,.85); }
[data-testid="stColumn"]:has(.st-key-home_banner) .aw-arrow.l { left: 10px; }
[data-testid="stColumn"]:has(.st-key-home_banner) .aw-arrow.r { right: 10px; }
/* 오른쪽 1~5위 목록 */
.st-key-home_ranklist { background: #F6F8F7; border-radius: 18px; padding: 10px 12px; height: 340px; box-sizing: border-box;
  gap: 0 !important; justify-content: center; }
.st-key-home_ranklist [data-testid="stMarkdownContainer"], .st-key-home_ranklist [data-testid="stMarkdown"] { margin: 0 !important; }
.hls-wrap { display: flex; flex-direction: column; gap: 4px; height: 100%; justify-content: space-between; }
.hl { display: flex; align-items: center; gap: 12px; padding: 9px 10px; border-radius: 12px; cursor: pointer;
  transition: background .15s ease; }
.hl:hover { background: #fff; }
.hl.on { background: #fff; box-shadow: 0 2px 10px rgba(0,0,0,.06); }
.hl.on .hlt { color: var(--accent-deep); }
.hl .hln { font-size: 1.5rem; font-weight: 900; font-style: italic; color: var(--accent-deep); width: 22px; text-align: center; }
.hl .hlb { flex: 1; min-width: 0; }
.hl .hlt { font-weight: 800; font-size: .92rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hl .hls { font-size: .76rem; color: #7B8784; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hl .hlst { font-size: .72rem; font-weight: 800; color: var(--accent-deep); white-space: nowrap; }
.hl .hlst.blue { color: #2C5BC5; } .hl .hlst.red { color: #D93A4A; }

/* 옆으로 넘기는 줄 */
[class*="st-key-home_row_"] { flex-wrap: nowrap !important; overflow-x: auto; overflow-y: hidden; gap: 14px !important; align-items: flex-start !important;
  padding-bottom: 4px; cursor: grab; scroll-behavior: smooth; scrollbar-width: thin; }
[class*="st-key-home_row_"] > div { flex: 0 0 210px !important; width: 210px !important; min-width: 210px !important; }
.hc { padding-bottom: 18px; }
.hc .hcp { position: relative; aspect-ratio: 4/3; border-radius: 12px; background-size: cover; background-position: center;
  background-color: #EEF3F1; transition: transform .18s ease; }
[class*="st-key-card_h"]:hover .hcp { transform: scale(.97); }
.hc .hcrank { position: absolute; left: -2px; bottom: -14px; font-size: 3.4rem; font-weight: 900; line-height: 1; color: #fff;
  font-style: italic; text-shadow: 0 2px 10px rgba(0,0,0,.35); letter-spacing: -2px; }
.hc .hcbadge { position: absolute; left: 0; top: 0; padding: 4px 10px; border-radius: 12px 0 12px 0; background: #F2A33A;
  color: #fff; font-size: .74rem; font-weight: 800; }
.hc .hcbadge.res { background: #6C5CE7; }       /* 사전예약은 보라 (종료 임박 주황과 다르게, 11/18 요청) */
.hc .hct { margin-top: 10px; font-weight: 800; font-size: .95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hc .hcd { margin-top: 2px; font-size: .8rem; color: #5B6663; }
.hc .hcchips { margin-top: 6px; display: flex; gap: 4px; flex-wrap: wrap; }
.hc .hcchips span { font-size: .7rem; padding: 2px 7px; border-radius: 6px; background: #F1F4F3; color: #5B6663; font-weight: 600; }
.hc .hcchips span.st.green { color: var(--accent-deep); background: var(--accent-soft); }
.hc .hcchips span.st.blue { color: #2C5BC5; background: #EAF0FC; }
.hc .hcchips span.st.red { color: #D93A4A; background: #FDECEE; }
[class*="st-key-card_h"] [class*="st-key-fav_"] { top: 8px; right: 8px; }
/* 이번 주 캘린더: 월~일 일곱 칸 */
.st-key-home_week { flex-wrap: nowrap !important; gap: 0 !important; overflow-x: auto; overflow-y: hidden;
  border-top: 1px solid #E3E9E7; align-items: stretch !important; }
.st-key-home_week > div { flex: 1 0 0 !important; min-width: 150px !important; }
[class*="st-key-wk_"] { padding: 12px 10px 4px; border-right: 1px solid #EEF2F1; gap: 10px !important; height: 100%; }
.st-key-home_week > div:last-child [class*="st-key-wk_"] { border-right: 0; }
[class*="st-key-wk_"]:has(.wkh.today) { background: #EAF8F5; }
.wkh { display: flex; align-items: center; gap: 6px; font-size: 1rem; margin-bottom: 18px; }   /* 머리와 첫 카드 사이 여백 (11/18 요청) */
.wkh b { font-weight: 800; } .wkh .wkd { font-size: .75rem; color: #9AA5A1; }
.wkh .wkn { margin-left: auto; font-weight: 800; color: #9AA5A1; font-size: .9rem; }
.wkh.today b, .wkh.today .wkn { color: var(--accent-deep); }
.wkh.past { opacity: .5; }
[class*="st-key-wk_"]:has(.wkh.past) .hc { opacity: .55; }
.wk-empty { font-size: .75rem; color: #B3BCB9; padding: 8px 0; }
[class*="st-key-wk_more_"] button { width: 100%; min-height: 0; padding: 4px 6px; border-radius: 10px; background: #F1F4F3; border: 0; }
[class*="st-key-wk_more_"] button p { font-size: .78rem !important; color: #5B6663 !important; font-weight: 700; }
.hc.tall .hcp { aspect-ratio: 1/1; }     /* 포스터 높이 줄임 (11/18 요청) */
.hc.tall .hcbadge { border-radius: 12px 0 10px 0; background: #26302D; }
.hc.tall .hcd, .hc.tall .hcchips { display: none; }
.hc.tall { padding-bottom: 12px; }
.hc.tall .hct { margin-top: 5px; white-space: normal; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; font-size: .88rem; }
/* 후기 모음 카드 */
[class*="st-key-home_row_rv"] > div { flex: 0 0 260px !important; width: 260px !important; min-width: 260px !important; }   /* 좁게 (11/18 요청) */
.rvc { border: 1px solid #E6ECEA; border-radius: 16px; padding: 14px; box-shadow: 0 2px 10px rgba(0,0,0,.04); margin-bottom: 18px;
  background: #fff; }
.rvtop { display: flex; gap: 10px; align-items: center; }
.rvth { width: 48px; height: 48px; border-radius: 10px; background-size: cover; background-position: center; flex: none;
  border: 1px solid #EEF2F1; }
.rvtt { min-width: 0; }
.rvw { font-weight: 800; font-size: .95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rvchips { display: flex; gap: 4px; margin-top: 4px; }
.rvchips span { font-size: .68rem; padding: 1px 7px; border-radius: 6px; background: #F1F4F3; color: #5B6663; font-weight: 600; }
.rvchips span.st.green { color: var(--accent-deep); background: var(--accent-soft); }
.rvchips span.st.blue { color: #2C5BC5; background: #EAF0FC; } .rvchips span.st.red { color: #D93A4A; background: #FDECEE; }
.rvbox { margin-top: 12px; background: #F7F9F8; border-radius: 12px; padding: 12px; min-height: 120px; }
.rvme { display: flex; gap: 8px; align-items: center; }
.rvwho { min-width: 0; flex: 1; } .rvwho b { font-size: .85rem; }
.rvs { color: #F4B63F; font-size: .72rem; letter-spacing: 0; white-space: nowrap; } .rvs .off { color: #DDE3E1; }
.rvs b { color: #26302D; margin-left: 4px; letter-spacing: 0; } .rvs .of { color: #9AA5A1; letter-spacing: 0; }
.rvdate { font-size: .72rem; color: #9AA5A1; align-self: flex-start; }
.rvkind { display: inline-block; margin-top: 10px; font-size: .68rem; font-weight: 800; padding: 2px 8px; border-radius: 999px; }
.rvkind.visit { color: var(--accent-deep); background: var(--accent-soft); }
.rvkind.hope { color: #2C5BC5; background: #EAF0FC; }
.rvkind.etc { color: #5B6663; background: #EEF0EF; }
.rvbody { margin-top: 6px; font-size: .85rem; line-height: 1.5; color: #3A4542; display: -webkit-box; -webkit-line-clamp: 3;
  -webkit-box-orient: vertical; overflow: hidden; word-break: break-all; }
.rvpics { display: flex; gap: 6px; margin-top: 10px; }
.rvpics .rvp { flex: 1; aspect-ratio: 4/3; border-radius: 8px; background-size: cover; background-position: center; }
@media (max-width: 640px) {
  .hb { height: 240px; } .hb .hbpic { right: 14px; top: 16px; bottom: 16px; }
  .hb .hbtxt { left: 18px; right: 150px; bottom: 18px; }
  .hb .hbtitle { left: 18px; top: 16px; font-size: .78rem; padding: 4px 10px 4px 7px; }   /* 모바일: 아래 글자와 같은 시작점 (11/18) */ .hb .hbrank { font-size: 2.6rem; } .hb .hbt { font-size: 1.15rem; }
  .st-key-home_ranklist { height: auto; }
  .st-key-home_banner, .st-key-home_banner [class*="st-key-card_hb_"] { height: 240px !important; min-height: 240px; }
  [class*="st-key-home_row_"] > div { flex-basis: 150px !important; width: 150px !important; min-width: 150px !important; }
  .hc .hcrank { font-size: 2.6rem; }
  /* 모바일 이번 주: 월~일을 위에서 아래로 한 줄씩, 카드는 작은 그림 + 옆 글자 (11/18 요청) */
  .st-key-home_week { flex-direction: column !important; overflow-x: visible; border-top: 1px solid #E3E9E7; }
  .st-key-home_week > div { flex: none !important; width: 100% !important; min-width: 0 !important; }
  [class*="st-key-wk_"] { border-right: 0; border-bottom: 1px solid #EEF2F1; padding: 8px 8px; gap: 8px !important; }
  /* 머리 줄: 요일·수는 작게 (오늘만 그대로), 줄 가운데 정렬 (11/18 요청) */
  .wkh { margin-bottom: 0; font-size: .8rem; min-height: 22px; align-items: center; }
  .wkh .wkd { font-size: .68rem; } .wkh .wkn { font-size: .72rem; }
  .wkh.today { font-size: 1rem; } .wkh.today .wkd { font-size: .75rem; } .wkh.today .wkn { font-size: .9rem; }
  [class*="st-key-wk_"] [data-testid="stElementContainer"]:has(.wkh) { margin-bottom: 0 !important; }
  [class*="st-key-wk_"] [data-testid="stMarkdownContainer"]:has(.wkh) { margin-bottom: 0 !important; }
  .hc.tall { display: flex; align-items: center; gap: 10px; padding-bottom: 10px; }
  .hc.tall .hcp { width: 64px; flex: none; aspect-ratio: 1/1; border-radius: 10px; }
  .hc.tall .hcbadge { font-size: .58rem; padding: 2px 5px; border-radius: 10px 0 8px 0; }
  .hc.tall .hct { margin-top: 0; font-size: .85rem; -webkit-line-clamp: 2; }
  [class*="st-key-wk_"] [class*="st-key-fav_"] { display: none; }
  [class*="st-key-home_row_rv"] > div { flex-basis: 230px !important; width: 230px !important; min-width: 230px !important; }
  .hc .hct { font-size: .85rem; }
  .home-h { font-size: 1.05rem; }
}
</style>
"""


# ================================================================ 스토리 줄 (11/18 요청)
def _live_rows(df: pd.DataFrame) -> list[dict]:
    """진행 중·오픈 예정 팝업만 (끝난 건 뺌)."""
    return [r for r in df.to_dict("records") if _status(r)[2] < 2]


def _work_posters(rows: list[dict]) -> dict[str, str]:
    """작품별 대표 포스터: 진행 중인 팝업의 포스터가 먼저, 없으면 예정 팝업 것."""
    out: dict[str, str] = {}
    for r in sorted(rows, key=lambda r: _status(r)[2]):
        w = str(r.get("work") or "").strip()
        if w and w not in out and images.poster(r.get("images")):
            out[w] = _poster_url(r.get("images"))
    return out


def _story_pick(work: str) -> None:
    """스토리를 누르면 그 작품만 보이게 (작품 필터). 같은 걸 다시 누르면 풀린다."""
    ss = st.session_state
    ss["f_work"] = "전체" if ss.get("f_work") == work else work
    ss["selected"] = None
    if ss.get("home_view"):          # 홈에서 누르면 그 작품만 걸러진 리스트 보기로 (11/18)
        ss.update(home_view=False, list_only=True, f_work=work, scroll_top=True)


def _story_add() -> None:
    if not _member():
        _need_login("북마크는 로그인하면 쓸 수 있어요.")
        return
    st.session_state["_bm_open"] = True


def _story_open(eid: str) -> None:
    """동그라미를 누르면 그 북마크한 팝업 상세로 (11/18 요청)."""
    st.session_state.update(selected=eid, scroll_top=True)


def _guest_stories(rows: list[dict], limit: int = 12) -> None:
    """로그인 전 홈: '요즘 일정 많은 작품' — 진행 중·예정 팝업이 많은 작품 순. 숫자 = 그 작품 팝업 수.
    누르면 그 작품만 걸러진 리스트 보기로."""
    count: dict[str, int] = {}
    for r in rows:
        w = str(r.get("work") or "").strip()
        if w:
            count[w] = count.get(w, 0) + 1
    works = sorted(count, key=lambda w: (-count[w], w))[:limit]
    posters = _work_posters(rows)
    with st.container(key="stories"):
        st.markdown('<div class="story-head">요즘 일정 많은 작품</div>', unsafe_allow_html=True,
                    help="지금 진행 중이거나 곧 열리는 팝업이 많은 작품이에요. 숫자는 그 작품의 팝업 수예요. "
                         "로그인하고 팝업을 북마크하면 여기가 내 '북마크 팝업' 으로 바뀌어요.")
        with st.container(horizontal=True, key="story_row"):
            # (로그인 전에는 '최애 추가하기' 칸을 두지 않는다, 11/18 요청)
            for i, w in enumerate(works):
                with st.container(key=f"card_story_{i}"):
                    st.markdown(
                        f'<div class="story hot"><div class="ring"><div class="pic" style="background-image:url(&quot;{posters.get(w, images.DEFAULT_POSTER_URL)}&quot;)"></div>'
                        f'<span class="cnt">{count[w]}</span></div><div class="nm">{escape(w)}</div></div>', unsafe_allow_html=True)
                    st.button("보기", key=f"open_story_{i}", on_click=_story_pick, args=(w,))


def render_stories(df: pd.DataFrame) -> None:
    """홈 '북마크 팝업' (11/18 요청): 인스타 스토리처럼 동그란 포스터 줄. 내가 북마크한 (진행 중·예정) 팝업 하나에 동그라미 하나,
    위에는 지역, 아래는 작품 이름. 누르면 그 팝업 상세. 맨 앞 '최애 추가하기' 로 팝업을 골라 한 번에 북마크한다."""
    rows = _live_rows(df)
    if not _member():
        _guest_stories(rows)       # 로그인 전: '요즘 일정 많은 작품' (11/18 요청)
        return
    _, mine, _ = _fav_state()
    marked = sorted([r for r in rows if str(r.get("entry_id")) in mine], key=lambda r: (_status(r)[2], str(r.get("end_date"))))
    with st.container(key="stories"):
        st.markdown('<div class="story-head">북마크 팝업</div>', unsafe_allow_html=True,
                    help="내가 북마크한 팝업(진행 중 · 오픈 예정)이 여기에 모여요. 동그라미를 누르면 그 팝업으로 가고, "
                         "'최애 추가하기' 로 팝업을 골라 한 번에 북마크할 수 있어요.")
        with st.container(horizontal=True, key="story_row"):
            # 맨 앞에 두어 줄이 길어도 늘 보이게 (인스타 '내 스토리' 자리)
            with st.container(key="card_story_add"):
                st.markdown(f'<div class="story add"><div class="ring">{_mi("add")}</div><div class="nm">최애 추가하기</div></div>',
                            unsafe_allow_html=True)
                st.button("최애 추가하기", key="open_story_add", on_click=_story_add)
            if not marked:
                st.markdown('<div class="story-empty">팝업을 북마크하면 여기에 모여요.</div>', unsafe_allow_html=True)
            for i, r in enumerate(marked):
                eid = str(r["entry_id"])
                rg = geo.area_name(str(r.get("address") or ""))
                with st.container(key=f"card_story_{i}"):
                    st.markdown(
                        '<div class="story mark"><div class="ring">' + (f'<span class="rg">{escape(rg)}</span>' if rg else "")
                        + f'<div class="pic" style="background-image:url(&quot;{_poster_url(r.get("images"))}&quot;)"></div>'
                        + f'</div><div class="nm">{escape(str(r.get("work") or ""))}</div></div>', unsafe_allow_html=True)
                    st.button("보기", key=f"open_story_{i}", on_click=_story_open, args=(eid,))
    if st.session_state.pop("_bm_open", False):
        bookmark_pick_dialog(df)


@st.dialog("최애 추가하기", width="large")
def bookmark_pick_dialog(df: pd.DataFrame) -> None:
    """dueple 온보딩처럼: 검색칸 + 포스터 격자에서 팝업을 눌러 고르고, 저장하면 북마크된다 (내 캘린더 · 알림 · 스토리 줄에 반영)."""
    ss = st.session_state
    me, mine, _ = _fav_state()
    if "_bm_pick" not in ss:
        ss["_bm_pick"] = sorted(mine)
    pick: list[str] = ss["_bm_pick"]
    rows = _live_rows(df)
    st.markdown('<div class="fw-title">놓치고 싶지 않은 팝업을 골라 주세요</div>'
                '<div class="fw-sub">북마크한 팝업은 내 캘린더와 알림으로 챙겨 드리고, 그 작품이 \'내가 관심있는 작품\' 맨 앞에 보여요.</div>'
                f'<div class="fw-count"><b>{len(pick)}</b>개 선택</div>', unsafe_allow_html=True)
    q = st.text_input("팝업 검색", key="bm_q", placeholder="작품 · 카페 이름으로 검색", label_visibility="collapsed",
                      icon=":material/search:")
    key = _work_key(q)
    rows.sort(key=lambda r: (str(r["entry_id"]) not in pick, _status(r)[2], str(r.get("start_date") or "")))
    if key:
        rows = [r for r in rows if key in _work_key(f'{r.get("work")}{r.get("cafe_name")}{r.get("characters")}')]
    if not rows:
        st.markdown('<div class="ntf-empty" style="padding:18px 2px">찾는 팝업이 없어요. 다른 이름으로 검색해 보세요.</div>',
                    unsafe_allow_html=True)

    def toggle(eid: str) -> None:
        cur = ss["_bm_pick"]
        cur.remove(eid) if eid in cur else cur.append(eid)

    with st.container(horizontal=True, key="fw_grid"):
        for r in rows[:60]:
            eid = str(r["entry_id"])
            on = eid in pick
            label, color, _ = _status(r)
            with st.container(key=f"card_fw_{eid}"):
                st.markdown(
                    f'<div class="fwc{" on" if on else ""}"><div class="fwp" style="background-image:url(\'{_poster_url(r.get("images"))}\')">'
                    + (f'<span class="fwchk">{_mi("check")}</span>' if on else "")
                    + f'</div><div class="fwn">{escape(str(r.get("work") or ""))}</div>'
                    f'<div class="fwm">{escape(str(r.get("cafe_name") or ""))}</div>'
                    f'<div class="fwm">{escape(_period(r, lambda d: f"{d:%m.%d}", show_raw=False))}</div></div>',
                    unsafe_allow_html=True)
                st.button("고르기", key=f"open_fw_{eid}", on_click=toggle, args=(eid,))
    with st.container(horizontal=True, key="fw_foot"):
        if st.button("다음에 할게요", key="fw_skip", type="tertiary"):
            ss.pop("_bm_pick", None)
            st.rerun()
        if st.button("저장하기", key="fw_save", type="primary", icon=":material/check_circle:"):
            try:
                for eid in [e for e in pick if e not in mine]:
                    favorite.toggle(favs, eid, me, True)
                for eid in [e for e in mine if e not in pick]:
                    favorite.toggle(favs, eid, me, False)
            except StorageWriteError:
                st.error("저장하지 못했어요. 잠시 뒤 다시 눌러 주세요.", icon=":material/error:")
                return
            ss.pop("_bm_pick", None)
            ss.pop("_fav_cache", None)
            ss["flash"] = (f"북마크 {len(pick)}개를 저장했어요. 내 캘린더에서 볼 수 있어요.", ":material/bookmark_added:")
            st.rerun()


STORY_CSS = """
<style>
.st-key-stories { margin: 0 0 8px; gap: 6px !important; }   /* 제목과 동그라미 사이 반으로 (20px → 10px, 11/18 요청) */
.story-head { font-size: .95rem; font-weight: 800; margin-bottom: 2px; color: var(--accent-deep); }
.st-key-stories [data-testid="stMarkdown"]:has(.story-head) { width: fit-content !important; }
.st-key-stories [data-testid="stMarkdown"]:has(.story-head) > div { justify-content: flex-start !important; gap: 6px;
  align-items: center !important; }
/* 제목 옆 ? 를 글자와 같은 크기 · 같은 줄 가운데로 (11/18 요청) */
.st-key-stories [data-testid="stMarkdown"]:has(.story-head) [data-testid="stTooltipIcon"],
.st-key-stories [data-testid="stMarkdown"]:has(.story-head) [data-testid="stTooltipHoverTarget"] { display: flex; align-items: center;
  margin: 0 !important; height: .95rem; }
.st-key-stories [data-testid="stMarkdown"]:has(.story-head) [data-testid="stTooltipIcon"] svg { width: .95rem; height: .95rem; }
.st-key-stories .story-head { line-height: 1; margin: 0 !important; }
.st-key-stories [data-testid="stMarkdown"]:has(.story-head) [data-testid="stMarkdownContainer"] { margin: 0 !important; padding: 0 !important; }
.st-key-stories [data-testid="stMarkdown"]:has(.story-head) [data-testid="stMarkdownContainer"] > div { margin: 0 !important; }
.st-key-story_row { flex-wrap: nowrap !important; overflow-x: auto; overflow-y: hidden; gap: 8px !important; padding: 4px 2px 2px;
  scrollbar-width: none; }
.st-key-story_row::-webkit-scrollbar { display: none; }
/* 절반 크기 (11/18 요청) */
.st-key-story_row > div { flex: 0 0 84px !important; width: 84px !important; min-width: 84px !important; }
.story { display: flex; flex-direction: column; align-items: center; padding-bottom: 16px; }
.story .ring { position: relative; width: 72px; height: 72px; border-radius: 50%; padding: 3px; box-sizing: border-box;
  background: conic-gradient(from 210deg, #14b8a6, #7FE0CF, #FFD66B, #14b8a6); transition: transform .18s ease; }
.story .rg { position: absolute; left: 50%; bottom: -7px; transform: translateX(-50%); z-index: 2; white-space: nowrap;
  font-size: .62rem; font-weight: 800; color: #fff; background: var(--accent-deep); padding: 1px 7px; border-radius: 999px;
  border: 1.5px solid #fff; }
.st-key-story_row { padding-top: 10px !important; }
.story.hot .ring { background: conic-gradient(from 210deg, var(--accent-deep), var(--accent), #ffd66b, var(--accent-deep)); }
.story .cnt { position: absolute; right: -2px; bottom: -2px; min-width: 24px; height: 24px; padding: 0 5px; box-sizing: border-box;
  border-radius: 999px; background: var(--accent-deep); color: #fff; font-size: .75rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center; border: 2px solid #fff; }
.story.mark .ring { background: conic-gradient(from 210deg, #14b8a6, #7FE0CF, #FFD66B, #14b8a6); }   /* 북마크 동그라미: 민트→노랑 (11/18 요청) */
.story .pic { width: 100%; height: 100%; border-radius: 50%; border: 3px solid #fff; box-sizing: border-box;
  background-size: cover; background-position: center; background-color: #EEF3F1; }
.story .cnt { position: absolute; right: -4px; bottom: -3px; min-width: 17px; height: 17px; padding: 0 3px; box-sizing: border-box;
  border-radius: 999px; background: var(--accent-deep); color: #fff; font-size: .6rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center; border: 1.5px solid #fff; }
.story .nm { margin-top: 10px; width: 84px; text-align: center; font-size: .78rem; font-weight: 700; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.story.on .nm { color: var(--accent-deep); }
.story.on .ring { box-shadow: 0 0 0 2px var(--accent-soft); }
[class*="st-key-card_story_"]:hover .ring { transform: scale(.95); }
.story.add .ring { background: none; border: 2px dashed #D3DAD8; display: flex; align-items: center; justify-content: center; }
.story.add .ring .mi { font-size: 32px; color: var(--accent-deep); }
.story.add .nm { white-space: normal; line-height: 1.2; word-break: keep-all; }
.st-key-story_row > div:has(.story-empty) { flex: 0 1 auto !important; width: auto !important; min-width: 0 !important; }
.story-empty { font-size: .85rem; color: #7B8784; padding-top: 26px; white-space: nowrap; }
/* 옆으로 넘기기: 끌어서(드래그) 넘기고, 넘길 게 있으면 양옆 ‹ › 버튼 (_DRAG_JS 가 붙인다, 11/18 요청) */
.st-key-story_row, [class*="st-key-sim_row_"] { cursor: grab; scroll-behavior: smooth; }
.aw-dragging { cursor: grabbing !important; scroll-behavior: auto !important; user-select: none; }
.aw-arrow { position: absolute; z-index: 8; width: 28px; height: 28px; border-radius: 50%; border: 1px solid #DDE5E3;
  background: rgba(255,255,255,.95); box-shadow: 0 2px 8px rgba(0,0,0,.12); color: #26302D; font-size: 18px; line-height: 24px;
  text-align: center; cursor: pointer; padding: 0; display: none; }
.aw-arrow:hover { border-color: var(--accent); color: var(--accent-deep); }
.aw-arrow.l { left: -6px; } .aw-arrow.r { right: -6px; }
.aw-arrow.show { display: block; }
/* 최애 고르기 창 */
.fw-title { font-size: 1.25rem; font-weight: 800; text-align: center; }
.fw-sub { text-align: center; color: #7B8784; font-size: .88rem; margin-top: 4px; }
.fw-count { margin: 10px auto 2px; width: fit-content; padding: 4px 14px; border: 1px solid #DDE5E3; border-radius: 10px;
  font-size: .85rem; color: #7B8784; }
.fw-count b { color: var(--accent-deep); font-size: 1rem; margin-right: 2px; }
.st-key-fw_grid { flex-wrap: wrap !important; gap: 12px !important; max-height: 52vh; overflow-y: auto; padding: 2px; }
.st-key-fw_grid > div { flex: 0 0 calc((100% - 48px) / 5) !important; width: calc((100% - 48px) / 5) !important; min-width: 0 !important; }
.fwc { padding-bottom: 16px; }
.fwc .fwp { position: relative; aspect-ratio: 3/4; border-radius: 10px; background-size: cover; background-position: center;
  background-color: #EEF3F1; border: 3px solid transparent; box-sizing: border-box; }
.fwc.on .fwp { border-color: var(--accent); }
.fwc.on .fwp::after { content: ""; position: absolute; inset: 0; background: rgba(20,184,166,.18); border-radius: 7px; }
.fwc .fwchk { position: absolute; right: 6px; top: 6px; z-index: 1; width: 24px; height: 24px; border-radius: 50%;
  background: var(--accent); display: flex; align-items: center; justify-content: center; }
.fwc .fwchk .mi { color: #fff; font-size: 17px; }
.fwc .fwn { margin-top: 6px; font-size: .85rem; font-weight: 800; line-height: 1.25; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden; }
.fwc .fwm { font-size: .74rem; color: #7B8784; margin-top: 2px; }
.st-key-fw_foot { justify-content: space-between !important; margin-top: 6px; }
.st-key-fw_foot button[kind="primary"] { padding: 0 22px; }
@media (max-width: 640px) {
  .st-key-fw_grid > div { flex-basis: calc((100% - 24px) / 3) !important; width: calc((100% - 24px) / 3) !important; }
}
</style>
"""


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
            # 속도 (11/18): 카드를 한꺼번에 100장 넘게 그리면 클릭마다 화면 조각 400여 개·150KB 를 다시 보낸다 →
            # 처음엔 LIST_PAGE 장만, 아래 '더 보기' 로 더. 조건(검색·지역·정렬)이 바뀌면 다시 처음 장수로
            sig = hash(tuple(view["entry_id"]))
            if st.session_state.get("_list_sig") != sig:
                st.session_state.update(_list_sig=sig, list_n=LIST_PAGE)
            n_show = int(st.session_state.get("list_n", LIST_PAGE))
            grid = st.columns(4, gap="small")
            for i, (_, r) in enumerate(view.head(n_show).iterrows()):
                with grid[i % 4], st.container(key=f"card_w_{r['entry_id']}"):
                    st.markdown(_poster_card(r, *_status(r)[:2]), unsafe_allow_html=True)
                    open_button(r)
                    _heart(r["entry_id"], "w")
            if len(view) > n_show:
                with st.container(horizontal=True, horizontal_alignment="center", key="list_more"):
                    st.button(f"{len(view) - n_show}건 더보기", icon=":material/expand_more:", key="list_more_btn",
                              on_click=lambda: st.session_state.update(list_n=n_show + LIST_PAGE, _more_from=n_show))
            # 방금 '더보기' 로 불러왔으면 새로 나온 첫 카드가 화면 위쪽에 오게 내린다 (11/18 요청)
            first = st.session_state.pop("_more_from", None)
            if first is not None and first < len(view):
                eid = str(view.iloc[first]["entry_id"])
                components.html(
                    "<script>(function(){const d=window.parent.document;let n=0;const go=()=>{"
                    f"const el=d.querySelector('.st-key-card_w_{eid}');"
                    "const box=d.querySelector('[data-testid=stMain]');"
                    "if(el&&box){const top=el.getBoundingClientRect().top-box.getBoundingClientRect().top+box.scrollTop-110;"
                    "box.scrollTo({top:top,behavior:n?'auto':'smooth'});return true;}return false;};"
                    "const iv=setInterval(()=>{if(go()&&++n>2)clearInterval(iv);if(++n>20)clearInterval(iv);},250);})();</script>",
                    height=0)
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
/* 상세 아래 추천 줄 (11/18): 비슷한 팝업 · 많이 본 팝업 · 이 근처. 옆으로 넘겨 본다 */
.st-key-similar {{ margin-top:28px; border-top:1px solid #E6ECEA; padding-top:20px; }}
[class*="st-key-simsec_"] {{ margin-bottom:10px; }}
/* 제목 옆 ? 를 제목 바로 오른쪽에 (줄 끝으로 밀리지 않게) */
[class*="st-key-simsec_"] [data-testid="stMarkdown"]:has(.sim-head) {{ width:fit-content !important; }}
[class*="st-key-simsec_"] [data-testid="stMarkdown"]:has(.sim-head) > div {{ justify-content:flex-start !important; gap:6px; }}
.sim-head {{ font-size:1.05rem; font-weight:800; margin-bottom:4px; display:flex; align-items:center; gap:6px; }}
.sim-head .mi {{ color:var(--accent); font-size:1.35rem; }}
[class*="st-key-sim_row_"] {{ flex-wrap:nowrap !important; overflow-x:auto; overflow-y:hidden; gap:12px !important; align-items:flex-start !important;
  padding-bottom:4px; scrollbar-width:thin; }}
[class*="st-key-sim_row_"] > div {{ flex:0 0 136px !important; width:136px !important; min-width:136px !important; }}
.simc {{ padding-bottom:18px; }}   /* 마크다운 칸의 아래 음수 여백(-1rem)에 글 줄이 잘리지 않게 */
.simc .simp {{ position:relative; aspect-ratio:3/4; border-radius:10px; background-size:cover; background-position:center;
  background-color:#EEF3F1; transition:transform .18s ease; }}
[class*="st-key-card_sim_"]:hover .simp {{ transform:scale(.965); }}
.simc .sims {{ position:absolute; top:6px; left:6px; font-size:.64rem; font-weight:800; padding:1px 7px; border-radius:999px;
  background:#fff; color:var(--accent-deep); }}
.simc .simr {{ position:absolute; top:6px; right:6px; }}   /* 오른쪽 위 지역 배지 (11/18 요청) */
.simc .simr .area {{ display:inline-block; font-size:.64rem; font-weight:800; padding:1px 7px; border-radius:999px; }}
.simc .sims.blue {{ color:#2C5BC5; }} .simc .sims.red {{ color:#D93A4A; }}
.simc .simt {{ margin-top:6px; font-weight:800; font-size:.84rem; line-height:1.3; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; }}
.simc .simm {{ margin-top:1px; font-size:.72rem; color:#7B8784; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
@media (max-width: 640px) {{
  [class*="st-key-sim_row_"] {{ gap:10px !important; }}
  [class*="st-key-sim_row_"] > div {{ flex-basis:108px !important; width:108px !important; min-width:108px !important; }}
  .simc .simt {{ font-size:.78rem; }} .simc .simm {{ font-size:.68rem; }}
  .simc .sims, .simc .simr .area {{ font-size:.6rem; padding:1px 6px; }}
}}
/* 카드 작품 이름 오른쪽의 진행 상태 배지 */
.cstate {{ display:inline-block; vertical-align:middle; margin-left:6px; font-size:.78rem; font-weight:700;
          line-height:1.4; padding:.1rem .45rem; border-radius:.5rem; white-space:nowrap; }}
.cstate.green {{ background:#E3F6EA; color:#1F7A44; }}
.cstate.blue {{ background:#E5EEFC; color:#2C5BC5; }} .cstate.red {{ background:#FDE8EC; color:#D93A4A; }}
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
/* 아직 북마크 안 한 카드: 흰 바탕을 70% 투명하게 (포스터가 비쳐 보이게, 11/18 요청). 북마크한 카드는 그대로 */
[class*="st-key-card_"] [class*="st-key-fav_off_"] button {{ background:rgba(255,255,255,.3) !important; }}
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
.pcard .area, .pcard .state {{ z-index:2; }}
/* 상태 배지 글자색: 예정(D-n) 파랑, 마감임박 빨강 (11/18 요청) */
.pcard .state.blue {{ color:#2C5BC5 !important; }}
.pcard .state.red {{ color:#D93A4A !important; }}   /* 펼친 막 위에서도 지역·상태 배지가 보이게 */
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
[class*="st-key-card_w_"]:hover .pcard .t {{ white-space:normal; font-size:15px; }}
[class*="st-key-card_w_"]:hover .pcard .s {{ font-size:12px; }}
[class*="st-key-card_w_"]:hover .pcard .d {{ font-size:12px; }}
.pcard .more .m {{ font-size:11.5px; line-height:1.45; margin:0 0 6px; }}   /* 커서를 올리면 나오는 정보: 작게 (11/18) */
.pcard .more .m b {{ display:block; color:#9fe3d1; font-size:10.5px; margin-bottom:1px; }}
.pcard .more .chip {{ font-size:10.5px; padding:2px 8px; }}
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
  .st-key-wide_grid .pcard .info {{ height: 90px; padding: 8px 9px 9px 11px; }}   /* 아래 여백 줄임 (11/18) */
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
  /* 모바일도 이벤트·굿즈 칩을 한 줄로 작게 (11/18 요청: PC 처럼 보이게) */
  .st-key-wide_grid .pcard .chips {{ display: flex; height: 19px; gap: 3px; margin: 3px 0 0; }}
  .st-key-wide_grid .pcard .chips .chip {{ font-size: 9.5px; padding: 1px 6px; line-height: 1.5; }}
  .st-key-wide_grid .pcard .info {{ height: 108px; }}
  .st-key-wide_grid .pcard .area {{ top: 6px; left: 6px; font-size: 10.5px; padding: 2px 6px; }}
  .st-key-wide_grid .pcard .state {{ top: 6px; right: 6px; font-size: 10.5px; padding: 2px 7px; }}
  .st-key-wide_grid [class*="st-key-fav_"] {{ top: auto !important; bottom: -6px !important; right: 10px !important; }}   /* 기간 줄과 같은 높이로 (11/18) */
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
.chips .chip {{ max-width:100%; min-width:0; flex-shrink:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.chips .chip.tag, .chips .chip.warn {{ flex-shrink:0; }}   /* 이벤트 칩(짧음)은 그대로, 긴 굿즈 칩만 줄어든다 */
.chip {{ font-size:12.5px; font-weight:600; padding:3px 10px; border-radius:999px; background:{MINT_SOFT};
        color:{MINT_DEEP}; border:1px solid {MINT}; white-space:nowrap; }}
.chip.tag {{ background:{MINT}; color:#fff; border-color:{MINT}; }}
.upd {{ color:#8A9592; font-size:.7rem; margin:-4px 0 6px; display:flex; align-items:center; gap:4px; }}
.upd .mi {{ font-size:.95rem; }}

@media (min-width: 641px) {{ .st-key-map_row {{ margin-top:5px; }}   /* 지도 칸 위 선 = 물어보기 창 위 선 */
  [data-testid="stElementContainer"]:has(.upd) {{ margin-bottom:8px; }}
  .st-key-listtools {{ margin-bottom:10px; }} }}   /* 리스트 보기: 마지막 업데이트 · 팝업 카페 N곳 · 카드 사이 여백 (11/18 요청) */   /* 지도 보기: 마지막 업데이트와 지도 칸 사이 (11/18) */
.upd.warn {{ color:#C2560C; background:#FFF4EA; border-radius:10px; padding:6px 10px; margin:0 0 8px; }}
@media (max-width: 640px) {{ .upd {{ font-size:.64rem; margin:-8px 0 0; }}
  [data-testid="stMarkdownContainer"]:has(.upd) {{ margin-bottom:0 !important; }}
  [data-testid="stElementContainer"]:has(.upd) {{ margin-bottom:8px !important; }} }}   /* 모바일: 아래 칸과 붙지 않게 (11/18) */
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
.dbtn {{ flex:0 0 auto; align-self:flex-start; margin-left:auto; padding:.18rem .65rem; border:1px solid #DDE2E0;
        border-radius:999px; background:#fff; color:#26302D !important; text-decoration:none !important;
        font-size:.78rem; font-weight:700; white-space:nowrap; }}   /* 작게 (11/18 요청) */
.dbtn:hover {{ border-color:{MINT}; color:{MINT_DEEP} !important; }}
/* 모바일: 지도에서 확인하기는 주소 바로 아래, 주소와 같은 왼쪽 선에 (11/18 요청) */
@media (max-width: 640px) {{
  .dval {{ flex-basis: calc(100% - 90px); }}
  .dbtn {{ margin-left: 90px; }}
}}
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
/* 블로그 후기 카드: 제목(굵게) · 요약 2줄 · 블로거 · 날짜, 누르면 새 탭 */
.dblog {{ display:block; background:{GRAY_SOFT}; border-radius:14px; padding:12px 16px; margin-bottom:8px;
          text-decoration:none !important; color:#26302D !important; transition:background .15s; }}
.dblog:hover {{ background:{MINT_SOFT}; }}
.dblog-t {{ font-weight:800; font-size:.95rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.dblog-d {{ color:#6B7672; font-size:.82rem; line-height:1.45; margin-top:3px; display:-webkit-box; -webkit-line-clamp:2;
            -webkit-box-orient:vertical; overflow:hidden; }}
.dblog-m {{ color:#9AA5A1; font-size:.76rem; margin-top:4px; display:flex; align-items:center; gap:3px; }}
.dsec-src {{ font-size:.72rem; font-weight:600; color:#9AA5A1; margin-left:6px; }}
/* 리뷰 탭 안 '리뷰 후기 / 블로그 후기' (11/18 요청) */
.st-key-rv_subtabs {{ gap:0 !important; margin:14px 0 12px; border-bottom:1.5px solid #E3E8E6; }}
.st-key-rv_subtabs > div {{ flex:1 1 0 !important; }}
.st-key-rv_subtabs button {{ width:100% !important; background:#F6F8F7 !important; border:0 !important; border-radius:0 !important;
  box-shadow:none !important; padding:12px 0 10px !important; border-bottom:3px solid transparent !important; margin-bottom:-1.5px; }}
.st-key-rv_subtabs button p {{ font-size:1rem !important; font-weight:700 !important; color:#9AA5A1 !important; }}
.st-key-rv_subtabs [class*="st-key-rvsub_on_"] button {{ background:#fff !important; border-bottom-color:#26302D !important; }}
.st-key-rv_subtabs [class*="st-key-rvsub_on_"] button p {{ color:#26302D !important; font-weight:800 !important; }}
.blog-note {{ border:0; border-radius:12px; padding:5px 14px; text-align:center; font-size:.76rem; font-weight:600;   /* 글자 작게·위아래 여백 반 (11/18 요청) */
  color:#fff; background:{MINT}; margin-bottom:12px; display:flex; align-items:center; justify-content:center; gap:6px; }}
.blog-note .mi {{ color:#fff; }}
.blog-empty {{ color:#8A9592; font-size:.88rem; text-align:center; padding:28px 0; }}
.bcard {{ display:flex; gap:16px; align-items:stretch; border:1.5px solid #E3E8E6; border-radius:14px; padding:16px 18px;
  background:#fff; margin-bottom:10px; text-decoration:none !important; color:#26302D !important;
  transition:border-color .15s, box-shadow .15s; }}
.bcard:hover {{ border-color:{MINT}; box-shadow:0 4px 14px rgba(20,184,166,.12); }}
.bcard-txt {{ flex:1 1 auto; min-width:0; display:flex; flex-direction:column; gap:6px; }}
.bcard-t {{ font-weight:800; font-size:1.02rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.bcard-d {{ color:#5F6B67; font-size:.84rem; line-height:1.5; display:-webkit-box; -webkit-line-clamp:2;
  -webkit-box-orient:vertical; overflow:hidden; }}
.bcard-m {{ margin-top:auto; display:flex; justify-content:space-between; color:#8A9592; font-size:.76rem; }}
.bcard-img {{ width:96px; height:96px; flex:0 0 96px; object-fit:cover; border-radius:10px; background:#F4F6F5; }}
@media (max-width: 640px) {{ .bcard-img {{ width:72px; height:72px; flex-basis:72px; }} .bcard {{ padding:12px; gap:10px; }} }}
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
/* 이벤트·굿즈 칩이 없으면 그 자리를 비워 두지 않고 글자를 카드 아래쪽에 붙인다 (11/18 요청) */
.pcard .info {{ display:flex; flex-direction:column; justify-content:flex-end; }}
.pcard .chips.short:empty {{ display:none; }}
[class*="st-key-card_w_"]:hover .pcard .info {{ justify-content:flex-start; }}

.pcard .t {{ font-family:"Jua", sans-serif; font-size:17px; line-height:1.25; margin-bottom:2px;
             overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.pcard .s {{ font-size:12.5px; opacity:.92; font-weight:600; overflow:hidden; text-overflow:ellipsis;
             white-space:nowrap; }}
.pcard .d {{ font-size:13.5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:700; opacity:1; margin:3px 0 7px; }}
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


def _season_fx(on: bool) -> str:
    """계절 배경 스크립트 (11/18 요청: 내 캘린더에서만). 봄 꽃잎 · 여름 잎사귀 · 가을 단풍 · 겨울 눈.
    그림은 common/season.py 의 작은 SVG.
    한 번만 붙고 다시 그려도 새로 만들지 않는다. on 이 아니면(다른 화면) 떼어 낸다. 클릭을 막지 않고, '동작 줄이기' 면 끈다."""
    import json as _json

    if not on:
        return "<script>(function(){const o = window.parent.document.getElementById('aw-season'); if (o) o.remove();})();</script>"
    name = season.season_of(TODAY.month)
    return (
        "<script>(function(){const d = window.parent.document, w = window.parent;"
        f"const season = '{name}', urls = {_json.dumps(season.urls(name))};"
        "const old = d.getElementById('aw-season'); if (old && old.dataset.s === season) return; if (old) old.remove();"
        "if (w.matchMedia('(prefers-reduced-motion: reduce)').matches) return;"
        "if (!d.getElementById('aw-season-css')) { const st = d.createElement('style'); st.id = 'aw-season-css';"
        " st.textContent = '#aw-season{position:fixed;inset:0;pointer-events:none;z-index:999;overflow:hidden}'"
        " + '#aw-season i{position:absolute;top:-40px;display:block;background-size:contain;background-repeat:no-repeat;"
        "animation-name:awFall,awSway;animation-timing-function:linear,ease-in-out;animation-iteration-count:infinite,infinite;"
        "animation-direction:normal,alternate}'"
        " + '@keyframes awFall{from{transform:translateY(0) rotate(0deg)}to{transform:translateY(calc(100vh + 80px)) rotate(var(--r))}}'"
        " + '@keyframes awSway{from{margin-left:-24px}to{margin-left:24px}}'; d.head.appendChild(st); }"
        "const box = d.createElement('div'); box.id = 'aw-season'; box.dataset.s = season; box.setAttribute('aria-hidden', 'true');"
        "const n = w.innerWidth <= 640 ? 7 : 14;"
        "for (let k = 0; k < n; k++) { const e = d.createElement('i');"
        " const size = (season === 'winter' ? 9 : 22) + Math.random() * (season === 'winter' ? 9 : 14);"
        " const fall = 12 + Math.random() * 12;"
        " e.style.cssText = 'left:' + (Math.random() * 100) + '%;width:' + size + 'px;height:' + size + 'px;'"
        "  + 'background-image:url(' + urls[k % urls.length] + ');opacity:' + (.55 + Math.random() * .35) + ';'"
        "  + 'animation-duration:' + fall + 's,' + (3 + Math.random() * 3) + 's;'"
        "  + 'animation-delay:-' + (Math.random() * fall) + 's,0s;--r:' + (Math.random() > .5 ? '' : '-') + (180 + Math.random() * 360) + 'deg';"
        " box.appendChild(e); }"
        "d.body.appendChild(box); })();</script>"
    )


def _no_translate(season_on: bool = False) -> None:
    """페이지를 한국어로 표시해 크롬 자동 번역이 'ANI:WHERE' 를 '아니:어디에' 로 바꾸지 않게 한다.
    모든 화면이 부르는 곳이라 계절 배경도 여기서 붙이고 뗀다 (내 캘린더에서만 season_on=True)."""
    components.html(
        "<script>const d = window.parent.document;"
        "d.documentElement.lang = 'ko'; d.documentElement.setAttribute('translate', 'no');"
        "if (!d.querySelector('meta[name=google]')) { const m = d.createElement('meta');"
        "m.name = 'google'; m.content = 'notranslate'; d.head.appendChild(m); }</script>" + _season_fx(season_on),
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
    components.html(f"<script>window.parent.eval({json.dumps(_PIN_ICON_JS)});"
                    f"window.parent.eval({json.dumps(_DRAG_JS)});</script>", height=0)


# 옆으로 넘기는 줄(스토리 · 상세 아래 추천): 마우스로 끌어서 넘기고, 넘길 게 있으면 양옆에 ‹ › (11/18 요청).
# 화면을 다시 그려도 줄마다 한 번만 붙인다 (dataset.awDrag). 끌다가 놓으면 그 클릭은 카드 열기로 넘기지 않는다
_DRAG_JS = """
(function () {
  if (window.__awDrag) return; window.__awDrag = true;
  const SEL = '.st-key-story_row, [class*="st-key-sim_row_"], [class*="st-key-home_row_"], .st-key-home_banner, .st-key-home_week, .g-slides';
  function arrows(row) {
    const box = row.parentElement; if (!box) return;
    if (getComputedStyle(box).position === 'static') box.style.position = 'relative';
    let l = box.querySelector(':scope > .aw-arrow.l'), r = box.querySelector(':scope > .aw-arrow.r');
    if (!l) {
      l = document.createElement('button'); l.className = 'aw-arrow l'; l.type = 'button'; l.textContent = '‹'; l.setAttribute('aria-label', '이전');
      r = document.createElement('button'); r.className = 'aw-arrow r'; r.type = 'button'; r.textContent = '›'; r.setAttribute('aria-label', '다음');
      box.appendChild(l); box.appendChild(r);
    }
    const step = row.classList.contains('st-key-home_banner') ? 1 : .8;     // 배너는 한 장씩
    l.onclick = () => { row.__awTouched = Date.now(); row.scrollBy({left: -row.clientWidth * step}); };
    r.onclick = () => { row.__awTouched = Date.now(); row.scrollBy({left: row.clientWidth * step}); };
    if (step === 1) bannerUi(row, box);
    if (step === 1 && !row.__awAuto) {        // 배너: 5초마다 다음 장 (누른 뒤 8초는 멈춤), 끝이면 처음으로
      row.__awAuto = setInterval(() => {
        if (!row.isConnected) { clearInterval(row.__awAuto); return; }
        if (Date.now() - (row.__awTouched || 0) < 8000) return;
        const end = row.scrollLeft + row.clientWidth >= row.scrollWidth - 4;
        row.scrollTo({left: end ? 0 : row.scrollLeft + row.clientWidth});
      }, 5000);
    }
    if (row.__awPlace) { row.__awPlace(); return; }
    const place = row.__awPlace = () => {
      const l = box.querySelector(':scope > .aw-arrow.l'), r = box.querySelector(':scope > .aw-arrow.r');
      if (!l || !r) return;
      const mid = row.classList.contains('st-key-home_banner') ? row.clientHeight / 2
        : row.classList.contains('g-slides') ? 140 : Math.min(row.clientHeight / 2, 60);
      // 화면 위치 차이로 잰다 (offsetTop 은 감싼 칸에 따라 기준이 달라져 화살표가 엉뚱한 곳에 갔다)
      const top = row.getBoundingClientRect().top - box.getBoundingClientRect().top + mid - (l.offsetHeight || 28) / 2;
      l.style.top = r.style.top = top + 'px';
      l.classList.toggle('show', row.scrollLeft > 4);
      r.classList.toggle('show', row.scrollLeft + row.clientWidth < row.scrollWidth - 4);
      if (row.classList.contains('st-key-home_banner')) bannerUi(row, box);   // 넘길 때마다 점·목록 표시도 맞춘다
    };
    row.addEventListener('scroll', place, {passive: true}); place(); setTimeout(place, 400);
  }
  function wire(row) {
    if (row.dataset.awDrag) { arrows(row); return; }
    row.dataset.awDrag = '1';
    let down = false, x0 = 0, s0 = 0, moved = 0;
    row.addEventListener('mousedown', e => { if (e.button !== 0) return; down = true; moved = 0; x0 = e.pageX; s0 = row.scrollLeft; row.__awTouched = Date.now(); });
    window.addEventListener('mousemove', e => {
      if (!down) return; const dx = e.pageX - x0; moved = Math.max(moved, Math.abs(dx));
      if (moved > 5) { row.classList.add('aw-dragging'); row.scrollLeft = s0 - dx; e.preventDefault(); }
    });
    window.addEventListener('mouseup', () => { down = false; setTimeout(() => row.classList.remove('aw-dragging'), 0); });
    row.addEventListener('click', e => { if (moved > 5) { e.preventDefault(); e.stopPropagation(); moved = 0; } }, true);
    row.addEventListener('dragstart', e => e.preventDefault());
    arrows(row);
  }
  // '내가 관심있는 작품' 줄은 오른쪽 물어보기 창 옆까지만 늘어난다 (11/18 요청). 창이 없거나 아래에 있으면(모바일) 전체 폭
  function fitStories() {
    const st = document.querySelector('.st-key-stories'), ask = document.querySelector('.st-key-ask_panel');
    if (!st) return;
    const a = ask && ask.getBoundingClientRect(), r = st.getBoundingClientRect();
    const w = a && a.width && a.left > r.left + 200 && a.top > r.top - 2000 ? a.left - r.left - 16 : 0;
    st.style.maxWidth = w > 0 ? w + 'px' : '';
  }
  // 랭킹 배너: 오른쪽 아래 점(…) · 지금 장 표시 · 오른쪽 목록 줄을 누르면 그 장으로 (11/18 요청)
  function bannerGo(row, i) { row.__awTouched = Date.now(); row.scrollTo({left: row.clientWidth * i}); }
  function bannerUi(row, box) {
    const n = row.children.length;
    let dots = box.querySelector(':scope > .aw-dots');
    if (!dots || dots.children.length !== n) {
      if (dots) dots.remove();
      dots = document.createElement('div'); dots.className = 'aw-dots';
      for (let i = 0; i < n; i++) {
        const b = document.createElement('button'); b.type = 'button'; b.setAttribute('aria-label', (i + 1) + '위');
        b.onclick = (e) => { e.stopPropagation(); bannerGo(row, i); }; dots.appendChild(b);
      }
      box.appendChild(dots);
    }
    dots.style.top = (row.getBoundingClientRect().top - box.getBoundingClientRect().top + row.clientHeight - 34) + 'px';
    const cur = Math.round(row.scrollLeft / Math.max(row.clientWidth, 1));
    [...dots.children].forEach((b, i) => b.classList.toggle('on', i === cur));
    document.querySelectorAll('.hls-wrap .hl').forEach((h) => h.classList.toggle('on', +h.dataset.i === cur));
  }
  document.addEventListener('click', (e) => {
    const h = e.target.closest && e.target.closest('.hls-wrap .hl');
    const row = document.querySelector('.st-key-home_banner');
    if (h && row) bannerGo(row, +h.dataset.i);
  });
  let queued = false;
  const scan = () => { if (queued) return; queued = true;
    requestAnimationFrame(() => { queued = false; fitStories(); document.querySelectorAll(SEL).forEach(wire); }); };
  new MutationObserver(scan).observe(document.body, {childList: true, subtree: true});
  window.addEventListener('resize', scan); scan();
})();
"""


_PIN_ICON_JS = """
(function () {
  if (window.__aniPinIcon) return;
  window.__aniPinIcon = true;
  // PC 물어보기 창: 지도·리스트 보기 똑같은 규칙 — 메뉴바 아래에 붙어 따라오고, 아래는 화면 아래에서 19px 위까지 (11/18 요청)
  const fitAsk = () => {
    const pn = document.querySelector('.st-key-ask_panel');
    if (!pn || window.innerWidth <= 640) return;
    if (!pn.offsetParent) return;
    // 붙는 선(메뉴바 아래)보다 위로 밀려 올라가도 높이는 그대로 (위로 밀릴수록 커지던 문제)
    const stick = parseFloat(getComputedStyle(pn.closest('[data-testid="stColumn"]') || pn).top) || 96;
    const t = Math.max(pn.getBoundingClientRect().top, stick);
    const h = Math.max(520, Math.round(window.innerHeight - t - 19)) + 'px';
    if (pn.style.height !== h) pn.style.setProperty('height', h, 'important');
  };
  const update = () => {
    fitAsk();
    const btn = document.querySelector('.st-key-view_tools');      // 필터·보기 전환 아이콘 묶음
    const box = btn && btn.parentElement;                          // 원래 자리 (높이를 남겨 둔다)
    if (!btn && document.querySelector('.st-key-mycal_mnav')) {
      // 내 캘린더(아이콘 묶음이 없는 화면): 조금이라도 내려가면 글자 탭 대신 위에 붙는 아이콘 줄 (11/18 요청)
      const m = document.querySelector('[data-testid="stMain"]') || document.scrollingElement;
      document.documentElement.classList.toggle('aw-scrolled', (m ? m.scrollTop : 0) > 60);
      return;
    }
    if (!btn || !box) return;
    const r = box.getBoundingClientRect();
    if (!r.width) return;                       // 상세 화면처럼 숨어 있으면 그대로
    const mobile = window.innerWidth <= 640;
    const bar = document.querySelector('.st-key-topbar');
    // 원래 자리가 위에 붙은 상단 묶음(PC) / 화면 맨 위(모바일) 밑으로 들어가기 시작하면 붙이고, 붙일 때는 조금 띄운다
    const edge = mobile ? 0 : (bar ? Math.max(bar.getBoundingClientRect().bottom, 0) : 0);
    const limit = edge + 10;
    // 모바일: 아이콘 자리가 화면 위로 올라가면(스크롤함) 아이콘 줄, 아니면 메뉴바의 글자 탭 (11/18 요청)
    document.documentElement.classList.toggle('aw-scrolled', r.top < edge);
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


# 모바일 '맨 위로' 버튼 (11/18 요청): 어느 화면이든(리스트·지도·내 캘린더·관리자…) 아래로 스크롤하면 화면 아래 가운데에
# 위쪽 화살표 아이콘, 누르면 맨 위로. 메뉴바(_gnb)가 모든 화면에 있어서 거기서 한 번 붙인다
_TOP_BTN_JS = """
(function () {
  if (window.__aniTopBtn) return;
  window.__aniTopBtn = true;
  let scroller = null;
  const pos = () => Math.max(scroller ? scroller.scrollTop : 0, document.scrollingElement ? document.scrollingElement.scrollTop : 0);
  const sync = () => document.documentElement.classList.toggle('aw-top-on', pos() > 240);
  const make = () => {
    if (document.getElementById('aw-top')) return;
    const top = document.createElement('button');
    top.id = 'aw-top'; top.type = 'button'; top.setAttribute('aria-label', '맨 위로');
    top.innerHTML = '<span class="material-symbols-rounded">keyboard_arrow_up</span>';
    top.onclick = () => {
      [scroller, document.scrollingElement, document.querySelector('[data-testid="stMain"]'), document.querySelector('.stMain')]
        .forEach((el) => { if (el && el.scrollTo) el.scrollTo({ top: 0, behavior: 'smooth' }); });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    };
    document.body.appendChild(top);
  };
  make();
  document.addEventListener('scroll', (e) => {
    const t = e.target === document ? document.scrollingElement : e.target;
    if (t && t.scrollHeight > t.clientHeight + 20) scroller = t;
    sync();
  }, true);
  new MutationObserver(() => { make(); requestAnimationFrame(sync); }).observe(document.body, { childList: true });
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
    """목록 위 '마지막 업데이트 ○월 ○일 HH:MM' (작은 회색 글씨, 왼쪽 정렬).
    11/18 요청: 수집이 실패했거나 오래돼도 색·안내 문구 없이 날짜만 보여 준다 (기존 데이터는 그대로 보여 줌)."""
    last = notion_sync.last_update(store.all_rows())
    if last is None:
        return
    kst = last.astimezone(timezone(timedelta(hours=9)))
    st.markdown(f'<div class="upd">{_mi("update")} 마지막 업데이트 {kst.month}월 {kst.day}일 {kst:%H:%M}</div>',
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
    if f.get("reserve"):          # 홈 '사전예약 팝업' 더보기 (11/18): 사전예약 + 아직 열기 전인 팝업만
        view = view[view["start_date"] > TODAY]
        view = view[view.apply(lambda r: _is_reserve(r), axis=1)] if not view.empty else view
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
    st.session_state.update({"f_query": "", "f_work": "전체", "f_span": "진행중 + 예정", "res_only": False})
    st.session_state.pop("ask_only", None)
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
  color: #4B5260 !important; font-size: .88rem !important; letter-spacing: -.01em; }
.st-key-gnb_tabs button p { font-family: "NanumSquareRound", sans-serif !important; }
/* 메뉴바 묶음 안의 보이지 않는 칸(스타일·높이 0 iframe·위치 받기)이 간격만 차지하지 않게 */
.st-key-topbar { gap: 0 !important; }
.st-key-topbar > [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] style:only-child),
.st-key-topbar [data-testid="stElementContainer"]:has(iframe[height="0"]) { display: none !important; }
.st-key-topbar .st-key-filters { margin-top: 10px; }
/* PC: 검색 아이콘을 누르면 펼쳐지는 검색 줄 = 말풍선 (둥근 민트 테두리 + 검색 아이콘 쪽을 가리키는 꼬리, 11/18 요청) */
@media (min-width: 641px) {
  .st-key-topbar .st-key-filters { position: relative; overflow: visible !important; margin-top: 16px;
    border: 1.5px solid var(--accent); border-radius: 20px; background: #fff; padding: 12px 18px 14px !important;
    box-shadow: 0 6px 18px rgba(20,184,166,.10); }
  .st-key-topbar .st-key-filters::before, .st-key-topbar .st-key-filters::after { content: ""; position: absolute;
    right: var(--bubble-tail, 85px); width: 0; height: 0; border-style: solid; }
  .st-key-topbar .st-key-filters::before { top: -11px; border-width: 0 10px 11px 10px;
    border-color: transparent transparent var(--accent) transparent; }
  .st-key-topbar .st-key-filters::after { top: -8.5px; right: calc(var(--bubble-tail, 85px) + 1.5px);
    border-width: 0 8.5px 9.5px 8.5px; border-color: transparent transparent #fff transparent; }
}
.st-key-gnb_loc_box { display: none !important; }
/* 탭은 메뉴바 정가운데 (로고·오른쪽 아이콘 폭과 상관없이) */
.st-key-gnb_tabs { gap: 28px !important; width: auto !important; flex: 0 0 auto; position: absolute !important;
  left: 50%; top: 50%; transform: translate(-50%, -50%); z-index: 2; }
.st-key-gnb_tabs button { background: transparent !important; border: 0 !important; border-radius: 0 !important;
  box-shadow: none !important; padding: 10px 16px 3px !important; border-bottom: 3px solid transparent !important;
  min-height: 0 !important; }   /* 글자와 밑줄 사이 반으로 (12px → 6px, 11/18 요청) */
.st-key-gnb_tabs button p { font-size: .92rem !important; font-weight: 600 !important; color: #8A9592 !important; }
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
.st-key-gnb_right .st-key-login_btn button p { font-size: .88rem !important; }   /* 로그인·닉네임 글자 작게 (11/18 요청) */
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
/* 내 캘린더 '알림 받은 내역': 종 알림과 같은 모양 + 왼쪽 포스터. 빨간 점은 굵은 종류 글자 앞, '새 알림' 은 오른쪽 위 */
.ntf-item.has-pst { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; position: relative; }
.ntf-item.has-pst::before { display: none; }
.ntf-item .ntf-pst { width: 42px; height: 56px; flex: 0 0 42px; object-fit: cover; border-radius: 6px; }
.ntf-body { min-width: 0; flex: 1 1 auto; }
.ntf-body .ntf-cafe { color: #6B7672; font-size: .82rem; }
.ntf-item.has-pst .ntf-body { padding-right: 52px; }
.ntf-item.has-pst .ntf-st { position: absolute; top: 10px; right: 12px; float: none; }
.ntf-item.has-pst .ntf-body > b:first-of-type::before { content: ""; display: inline-block; width: 7px; height: 7px;
  border-radius: 50%; background: #FF6B6B; margin-right: 6px; vertical-align: 2px; }
.ntf-item.has-pst.read .ntf-body > b:first-of-type::before { background: #D5DBD9; }
.ntf-why { display: flex; align-items: center; gap: 3px; font-size: .74rem; color: #8A9592; margin-top: 2px; line-height: 1.35; }
.ntf-why .material-symbols-rounded, .ntf-why span { font-size: .82rem; }
[class*="ntfc_"] { position: relative; margin-bottom: 4px; }
[class*="ntfb_"] { position: absolute !important; inset: 0; z-index: 2; width: 100% !important; height: 100% !important; }
[class*="ntfb_"] > div, [class*="ntfb_"] .stButton { width: 100% !important; height: 100% !important; }
[class*="ntfb_"] button { width: 100% !important; height: 100% !important; opacity: 0 !important; cursor: pointer; }
[class*="ntfc_"]:hover .ntf-item { outline: 1.5px solid var(--accent); }
.ntf-item.plain { margin-bottom: 4px; cursor: default; }
.ntf-empty { color: #8A9592; font-size: .88rem; padding: 6px 2px; }
.st-key-gnb_loc_box { height: 0 !important; overflow: hidden !important; margin: 0 !important; }
#aw-top { display: none; position: fixed; left: 50%; bottom: 18px; transform: translateX(-50%); z-index: 1003; width: 42px; height: 42px;
  border-radius: 50%; border: 1.5px solid var(--accent); background: #fff; color: var(--accent-deep); align-items: center;
  justify-content: center; box-shadow: 0 4px 14px rgba(0,0,0,.16); cursor: pointer; padding: 0; }
#aw-top .material-symbols-rounded { font-size: 28px; line-height: 1; }
/* PC 에서도 스크롤하면 화면 아래 가운데에 '맨 위로' (11/18 요청) */
@media (min-width: 641px) { html.aw-top-on body #aw-top { display: flex; } }
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
  /* 스크롤하지 않았을 때(맨 위): PC 처럼 메뉴바에 글자 탭, 아이콘 줄은 자리만 남기고 숨김.
     스크롤해서 아이콘 자리가 화면 위로 올라가면(html.aw-scrolled): 글자 탭 대신 위에 붙는 아이콘 줄 (11/18 요청) */
  html:not(.aw-scrolled) body .st-key-gnb > *:has(.st-key-gnb_tabs) { display: flex !important; order: 3; flex: 1 1 100% !important;
    width: 100% !important; }
  html:not(.aw-scrolled) body .st-key-gnb .st-key-gnb_tabs { display: flex !important; position: static !important; transform: none !important;
    order: 3; flex: 1 1 100% !important; width: 100% !important; justify-content: center !important; gap: 14px !important; margin-top: 2px; }
  html:not(.aw-scrolled) body .st-key-gnb .st-key-gnb_tabs button { padding: 6px 4px 3px !important; }
  html:not(.aw-scrolled) body .st-key-gnb .st-key-gnb_tabs button p { font-size: .84rem !important; white-space: nowrap; }
  /* 맨 위에서는 지도·캘린더 아이콘을 숨기고(글자 탭이 대신) 필터 버튼만 둔다 (11/18 요청: 필터는 늘 보이게) */
  html:not(.aw-scrolled) body .st-key-view_tools .st-key-map_icon,
  html:not(.aw-scrolled) body .st-key-view_tools .st-key-m_cal_btn,
  html:not(.aw-scrolled) body .st-key-view_tools > *:has(.st-key-map_icon),
  html:not(.aw-scrolled) body .st-key-view_tools > *:has(.st-key-m_cal_btn) { display: none !important; }
  /* 모바일 지도: 화면 높이에 맞춰 크게 */
  .st-key-map_frame iframe { height: calc(100vh - 210px) !important; min-height: 420px; }
  html.aw-top-on body #aw-top { display: flex; }
  /* 아이콘을 버튼 가운데에 (아이콘 오른쪽에 붙는 빈 글자 칸 여백 제거) */
  html body .st-key-view_tools button { display: flex !important; align-items: center !important; justify-content: center !important; }
  html body .st-key-view_tools button > div, html body .st-key-view_tools button [data-testid="stMarkdownContainer"] {
    margin: 0 !important; justify-content: center !important; }
  html body .st-key-view_tools button span[data-testid="stIconMaterial"] { margin: 0 !important; }
  html body .st-key-view_tools button > div { gap: 0 !important; width: 100%; justify-content: center !important; }
  html body .st-key-view_tools .st-key-map_icon button [data-testid="stMarkdownContainer"],
  html body .st-key-view_tools .st-key-m_cal_btn button [data-testid="stMarkdownContainer"] { display: none !important; }
  html body .st-key-view_tools button p:empty, html body .st-key-view_tools button [data-testid="stMarkdownContainer"]:empty { display: none !important; }
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
  .st-key-gnb_right .st-key-login_btn button p { font-size: .78rem !important; }
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
    padding: 0 !important; background: #9EDDCC !important; border: 2px solid #0D9488 !important; box-shadow: 0 6px 16px rgba(46,156,130,.35) !important;   /* mint-line + 진한 테두리 (11/18 요청) */
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
    st.session_state["home_view"] = view == "home"      # 홈 (11/18 요청)
    st.session_state["res_only"] = False                # 홈 '사전예약 더보기' 로 건 조건은 탭을 옮기면 푼다
    st.session_state.pop("ask_only", None)              # 물어보기 '더보기' 로 건 조건도
    if view not in ("cal", "box", "home"):
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
        bool(ss.get("regions")), bool(ss.get("fav_only")), bool(ss.get("res_only")),
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


def _ntf_cookie() -> str:
    """읽은 알림 쿠키 이름: 회원마다 따로 (11/18 — 한 브라우저에서 계정을 바꾸면 읽음 표시가 섞이던 문제)."""
    key = str(st.session_state.get("member_key") or "guest")
    return f"{NTF_COOKIE}_{hashlib.sha1(key.encode()).hexdigest()[:8]}"


def _ntf_read() -> set[str]:
    """읽은 알림 번호들 (브라우저 쿠키에 남겨 다시 열어도 읽음으로 보인다). 회원마다 따로."""
    if "_ntf_read" not in st.session_state:
        raw = str(st.context.cookies.get(_ntf_cookie()) or "")
        st.session_state["_ntf_read"] = {x for x in raw.split(".") if len(x) == 8}
    return st.session_state["_ntf_read"]


def _ntf_mark(ids: list[str]) -> None:
    _ntf_read().update(ids)
    st.session_state["_ntf_cookie"] = True


def _ntf_click(nid: str, cafe_id: str | None) -> None:
    """알림 칸을 누름 → 읽음 처리, 팝업이면 그 팝업 상세로 (다른 화면이면 메인으로 옮겨서)."""
    _ntf_mark([nid])
    if cafe_id:
        st.session_state.update(cal_view=False, box_view=False, home_view=False, _gnb_to_map=True)
        _gnb_open(cafe_id)


def _ntf_cell(nid: str, html: str, cafe_id: str | None, poster: str | None = None, kp: str = "",
              past: bool = False) -> None:
    """알림 한 칸. poster 가 있으면 왼쪽에 포스터 (내 캘린더 '알림 받은 내역'). past = 지난 날 알림 (읽음 표시 대신 '지난 알림')."""
    read = past or nid in _ntf_read()
    state = "지난 알림" if past else ("읽음" if read else "새 알림")
    pic = f'<img class="ntf-pst" src="{escape(poster)}" alt="">' if poster else ""
    item = (f'<div class="ntf-item{" read" if read else ""}{" has-pst" if poster else ""}">{pic}<div class="ntf-body">'
            f'<span class="ntf-st">{state}</span>{html}</div></div>')
    if not cafe_id:          # 삭제 요청 승인/거부·공지처럼 갈 팝업이 없는 알림은 글만 (누를 수 없음, '모두 읽음'으로 읽음 처리)
        st.markdown(item.replace('class="ntf-item', 'class="ntf-item plain'), unsafe_allow_html=True)
        return
    with st.container(key=f"{kp}ntfc_{nid}"):
        st.markdown(item, unsafe_allow_html=True)
        st.button("열기", key=f"{kp}ntfb_{nid}", on_click=_ntf_click, args=(nid, cafe_id))


def _gnb(current: dict | None, on_map: bool = True) -> None:
    if st.session_state.pop("_cookie_clear", None):     # 방금 로그아웃·탈퇴 → 로그인 쿠키를 지운다
        _set_cookie("", 0)
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
    components.html(f"<script>window.parent.eval({json.dumps(_TOP_BTN_JS)});</script>", height=0)   # 모바일 '맨 위로'
    wide = bool(st.session_state.get("list_only"))
    with st.container(horizontal=True, key="gnb"):
        _logo_swap()
        if current:
            st.markdown(f'<style>html body .st-key-home_brand button {{ background-image: url("app/static/{FIXED_LOGO}")'
                        ' !important; }</style>', unsafe_allow_html=True)
        if st.button("ANI:WHERE", key="home_brand", type="tertiary"):
            # 로고 → 홈 (11/18 요청). 다른 화면(로그인·내 계정·등록하기 등)에서도 메인의 홈으로
            st.session_state.update(selected=None, scroll_top=True, home_view=True, cal_view=False, box_view=False)
            if not on_map:
                go("map")
            st.rerun()
        with st.container(horizontal=True, key="gnb_tabs"):
            cal = bool(st.session_state.get("cal_view"))
            box = bool(st.session_state.get("box_view"))
            if not on_map:
                current = {"_": "다른 화면"}       # 탭 밑줄을 모두 끈다
            home = bool(st.session_state.get("home_view"))
            on_home = home and not current and not cal and not box
            tab_map = not wide and not current and not cal and not box and not home      # (on_map 과 이름을 나눔 — 겹쳐서 +·물어보기 버튼이 사라졌다)
            on_list = wide and not current and not cal and not box and not home
            on_cal = cal and not current
            on_box = box and not current
            st.button("홈", key=f"gnbtab_{'on_' if on_home else ''}home", on_click=_gnb_go, args=("home",))   # 11/18 요청
            st.button("지도로 보기", key=f"gnbtab_{'on_' if tab_map else ''}map", on_click=_gnb_go, args=("map",))
            st.button("리스트로 보기", key=f"gnbtab_{'on_' if on_list else ''}list", on_click=_gnb_go, args=("list",))
            if _member():                       # 내 캘린더(알림·찜·다녀온)는 로그인한 사람만
                st.button("내 캘린더", key=f"gnbtab_{'on_' if on_cal else ''}cal", on_click=_gnb_go, args=("cal",))
        if not _member():   # 알림은 로그인한 사람만: 손님이면 알림 칸(과 그것을 감싼 칸)을 숨긴다
            st.markdown("<style>.st-key-bell_guest, .st-key-gnb_right > *:has(.st-key-bell_guest) "
                        "{ display: none !important; }</style>", unsafe_allow_html=True)
        # 검색 아이콘은 '지도로 보기' · '리스트로 보기' 탭에서만 (PC·모바일, 11/18 요청).
        # 홈 · 내 캘린더 · 상세 · 등록 · 로그인 · 마이페이지 · 회원가입 등에서는 그리지 않는다
        ss_ = st.session_state
        show_search = on_map and not current and not ss_.get("home_view") and not ss_.get("cal_view") and not ss_.get("box_view")
        with st.container(horizontal=True, key="gnb_right"):
            # 검색 아이콘: 누르면 아래 검색 필터 줄(검색·작품·캐릭터·진행여부·날짜)을 펼치고 접는다.
            # 걸어 둔 조건이 있으면 아이콘 옆에 그 수. 모바일에서는 필터 시트를 연다
            if show_search:
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
                js = (f"window.parent.document.cookie = {json.dumps(_ntf_cookie() + '=' + '.'.join(sorted(_ntf_read())[-200:]))}"
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
.st-key-ntf_box .mc-title { font-family: inherit; text-align: center; color: var(--accent-deep, #0d9488); font-size: .82rem;
  font-weight: 800; margin: 0 auto 4px; display: table; border: 0; border-radius: 999px;
  padding: 3px 12px; background: var(--accent-soft, #E6F7F4); }   /* 테두리 대신 연한 포인트 색 배경 (11/18 요청) */
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
/* 내 캘린더 칸: 날짜 숫자·요일·막대 글씨를 작게 (11/18 요청) */
.st-key-mycal_box .cal-dow div { font-size: .74rem; padding: 6px 0; }
.st-key-mycal_box .cal-day { font-size: .76rem; padding: 4px 6px; }
.st-key-mycal_box .cal-day.today span { padding: 0 5px; }
.st-key-mycal_box .cal-bar { font-size: .64rem; height: 18px; line-height: 18px; padding: 0 5px; border-radius: 5px; }
.st-key-mycal_box .up-name { font-size: .86rem; }
.st-key-mycal_box .up-when { font-size: .78rem; }
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


def _notice_history(days_back: int = 2) -> list[tuple[date, str, str, dict]]:
    """알림 받은 내역: 북마크한 팝업마다 '오픈 D-3 ~ 당일', '종료 D-3 ~ 당일' 알림이 생긴 날을 거꾸로 계산한다.
    (저장하지 않아도 북마크·기간만으로 같은 내역이 다시 나온다) → (알림 날, 종류, 글자, 행)"""
    _, mine, _ = _fav_state()
    rules = _rules()
    out: list[tuple[date, str, str, dict]] = []
    for r in mycal.latest_rows(store.all_rows()):
        if str(r.get("entry_id")) not in mine:
            continue
        s_, e_ = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        if e_ and e_ < TODAY:
            continue                         # 끝난 팝업의 알림 내역은 보이지 않게 (11/18 요청)
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
    # (모바일 리스트·지도 아이콘 줄은 11/18 요청으로 뺐다 — 메뉴바 탭으로 옮긴다)
    # 순서 (11/18 요청): 왼쪽 = 내 캘린더(가장 넓게) · 가운데 = 찜·다녀온·최근 본(조금 작게) · 오른쪽 = 알림 받은 내역
    # 캘린더는 지도 보기 오른쪽 캘린더와 같은 크기, 알림은 데일리 팝업 노트와 같은 폭·모양
    left, mid, right = st.columns([1.55, 2.3, 1.5], gap="medium")      # 찜 줄이고 알림 내역 키움 (11/18)
    with right, st.container(key="ntf_box"):
        # 긴 설명은 제목 옆 ? 에 (11/18 요청: 문구가 길어 줄이 어색했음)
        r_ = _rules()
        st.markdown('<div class="mc-title">알림 받은 내역 <span class="nh-help" tabindex="0">?<span class="nh-tip">'
                    f'북마크한 팝업의 <b>오픈 {r_["open"]["days"]}일 전</b>, <b>종료 {r_["end"]["days"]}일 전</b>부터 당일까지 '
                    '알려 드려요. 최근 3일 알림만 보여요.<br>관리자 공지와 삭제 요청 결과도 여기에 와요.</span></span></div>',
                    unsafe_allow_html=True)
        _render_notice_history()
    with left, st.container(key="mycal_box"):
        render_calendar()
    with mid, st.container(key="keep_box"):
        tab = st.session_state.get("box_tab", "fav")
        if tab not in ("fav", "visited", "recent"):
            tab = "fav"
        with st.container(horizontal=True, key="box_tabs"):
            for t, label in (("fav", "북마크"), ("visited", "다녀온 팝업"), ("recent", "최근 본 팝업")):
                st.button(label, key=f"boxtab_{'on_' if tab == t else ''}{t}", on_click=_box_tab, args=(t,))
        render_box_view(tab)


def _render_notice_history() -> None:
    """종 알림과 같은 모양(새 알림/읽음 · 굵은 종류 · 왜 왔는지 한 줄 · 칸 전체가 버튼) + 왼쪽 포스터 (11/18 요청).
    오늘 알림은 종과 같은 번호를 써서 한쪽에서 읽으면 다른 쪽도 '읽음'."""
    me = _member()
    rules = _rules()
    inbox = _inbox(str(me["entry_id"])) if me else []
    # 최근 3일 알림만 (그 전 내역은 보이지 않음, 11/18 요청)
    inbox = [r for r in inbox if (admin._day(r.get("updated_at")) or TODAY) >= TODAY - timedelta(days=2)]
    if inbox:
        st.markdown('<div class="nh-day">받은 알림</div>', unsafe_allow_html=True)
    for r in inbox[:20]:                    # 공지 · 삭제 요청 처리 결과 (관리자가 보냄)
        _ntf_cell(_ntf_id("i" + str(r.get("row_id"))),
                  f'<b>{escape(str(r.get("title") or ""))}</b><br>{escape(str(r.get("body") or ""))}'
                  + _why_html(admin.KIND_RULE.get(str(r.get("kind")), "notice")), None, kp="h")
    hist = _notice_history()
    if not hist:
        st.markdown('<div class="ntf-empty">아직 받은 알림이 없어요. 리스트에서 팝업을 북마크하면 오픈·종료가 가까울 때 '
                    '여기에 쌓여요.</div>', unsafe_allow_html=True)
    last_day = None
    for day, kind, label, r in hist[:40]:
        if day != last_day:
            st.markdown(f'<div class="nh-day">{"오늘" if day == TODAY else f"{day.month}월 {day.day}일"}</div>',
                        unsafe_allow_html=True)
            last_day = day
        eid = str(r.get("entry_id"))
        name = escape(f'{r.get("work") or ""} · {r.get("cafe_name") or ""}'.strip(" ·"))
        bell = f"<b>{label}</b> · {name}" + _why_html(kind)      # 종 알림(_notices)과 같은 글 → 같은 번호(읽음 공유)
        nid = _ntf_id(f"m{TODAY}{eid}{bell}") if day == TODAY else _ntf_id(f"h{day}{eid}{label}")
        # 화면에는 종류 / 작품 / 매장을 줄바꿈으로 (11/18 요청)
        text = (f"<b>{label}</b><br>{escape(str(r.get('work') or ''))}<br>"
                f"<span class='ntf-cafe'>{escape(str(r.get('cafe_name') or ''))}</span>" + _why_html(kind))
        _ntf_cell(nid, text, eid, poster=_poster_url(r.get("images")), kp="h", past=day != TODAY)
    _render_near_picks()


NEAR_KM = 20          # '내 주변' 으로 볼 거리


def _render_near_picks() -> None:
    """알림 받은 내역 아래 '내 주변 추천' 최대 3곳 (11/18 요청).
    대상: 지금 진행 중이거나 3일 안에 여는 팝업 중 내 위치에서 NEAR_KM 안 (북마크한 곳은 위 알림에 있으니 뺌).
    순서: 별점 높은 순 → 다녀온 후기 많은 순 → 가까운 순."""
    st.markdown('<div class="nh-day">내 주변 추천 <span class="nh-help" tabindex="0">?<span class="nh-tip">'
                f'내 위치에서 {NEAR_KM}km 안에 있는 팝업 중 <b>지금 진행 중</b>이거나 <b>3일 안에 여는</b> 곳을 골라요.<br>'
                '순서: 별점 높은 순 → 다녀온 후기 많은 순 → 가까운 순, 최대 3곳.<br>'
                '이미 북마크한 팝업은 위 알림에 있어서 빼요. 위치를 허용해야 보여요.</span></span></div>',
                unsafe_allow_html=True)
    loc = _my_loc()
    if not loc:
        st.markdown('<div class="ntf-empty">위치를 허용하면 내 주변에서 별점 좋은 팝업을 추천해 드려요. '
                    '브라우저 주소창의 위치 권한을 허용해 주세요.</div>', unsafe_allow_html=True)
        return
    me = (float(loc["lat"]), float(loc["lng"]))
    _, mine, _ = _fav_state()
    ratings = _ask_ctx().get("ratings") or {}
    cand = []
    for r in mycal.latest_rows(store.all_rows()):
        if r.get("status") == "deleted" or str(r.get("entry_id")) in mine:
            continue
        s_, e_ = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
        if not (s_ and e_) or e_ < TODAY or (s_ - TODAY).days > 3:
            continue                       # 진행 중 또는 D-3 안에 여는 것만
        try:
            km = my_place._km(me, (float(r.get("lat")), float(r.get("lng"))))
        except (TypeError, ValueError):
            continue
        if km > NEAR_KM:
            continue
        avg, n = ratings.get(str(r.get("entry_id")), (0.0, 0))
        cand.append((-avg, -n, km, r, avg, n))
    cand.sort(key=lambda t: t[:3])
    if not cand:
        st.markdown(f'<div class="ntf-empty">내 위치에서 {NEAR_KM}km 안에 지금 열려 있거나 곧 여는 팝업이 없어요.</div>',
                    unsafe_allow_html=True)
        return
    for _, _, km, r, avg, n in cand[:3]:
        eid = str(r.get("entry_id"))
        dist = f"{km * 1000:.0f}m" if km < 1 else f"{km:.1f}km"
        # 거리 / 작품 / 매장 줄바꿈 (별점·상태 줄은 뺐다, 기준은 제목 옆 ? 에) — 11/18 요청
        text = (f"<b>내 주변 {dist}</b><br>{escape(str(r.get('work') or ''))}<br>"
                f"<span class='ntf-cafe'>{escape(str(r.get('cafe_name') or ''))}</span>")
        _ntf_cell(_ntf_id(f"r{TODAY}{eid}"), text, eid, poster=_poster_url(r.get("images")), kp="h")


# ------------------------------------------------------------ '보관함' 탭: 찜 · 다녀온(내가 쓴 다녀온 후기) · 최근 본
BOX_CSS = """
<style>
.bx-title { font-family: "Jua", sans-serif; font-size: 1.7rem; color: #26302D; margin: 6px 0 4px; }
.st-key-box_tabs { gap: 0 !important; border-bottom: 1.5px solid #E3E8E6; margin-bottom: 0; }   /* 아래 안내와 간격 반으로 (11/18) */
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
[class*="st-key-bx_"] { position: relative; margin-bottom: 10px; }
/* 찜·다녀온·최근 본 카드: 커서를 올리면 명암 (11/18 요청) */
.bxc { transition: background .15s, border-color .15s, box-shadow .15s; }
[class*="st-key-bx_"]:hover .bxc { background: #F1FAF7; border-color: var(--accent); box-shadow: 0 4px 14px rgba(20,184,166,.14); }
/* 다녀온 후기 상자가 칸 아래 테두리에 겹치지 않게 아래 여백 (11/18) */
.st-key-keep_box, .st-key-ntf_box { padding-bottom: 22px !important; }
/* '내 주변 추천' 옆 회색 ? : 커서를 올리면 추천 기준 안내 */
.nh-help { position: relative; display: inline-flex; align-items: center; justify-content: center; width: 15px; height: 15px;
  border-radius: 50%; background: #E3E8E6; color: #6B7672; font-size: .66rem; font-weight: 900; cursor: help; margin-left: 4px;
  vertical-align: 1px; }
.nh-tip { display: none; position: absolute; top: calc(100% + 6px); right: -8px; z-index: 60; width: 230px; background: #26302D;
  color: #fff; font-size: .74rem; font-weight: 500; line-height: 1.55; padding: 9px 11px; border-radius: 10px; text-align: left;
  box-shadow: 0 6px 18px rgba(0,0,0,.18); }
.nh-tip b { color: #7BE3CF; }
.nh-help:hover .nh-tip, .nh-help:focus .nh-tip { display: block; }
.st-key-ntf_box [class*="ntfc_"], .st-key-ntf_box .ntf-item.plain { margin-bottom: 8px; }
/* 알림 받은 내역: 흰 카드 + 테두리 (안 읽은 알림은 민트 테두리) — 11/18 요청 */
.st-key-ntf_box .ntf-item { background: #fff; border: 1.5px solid #E3E8E6; border-radius: 14px; }
.st-key-ntf_box .ntf-item:not(.read) { border-color: var(--accent); }
.st-key-ntf_box [class*="ntfc_"]:hover .ntf-item { outline: none; border-color: var(--accent-deep); box-shadow: 0 4px 14px rgba(20,184,166,.14); }
.st-key-keep_box [data-testid="stMarkdownContainer"]:has(.bxr) { margin-bottom: 4px !important; }
.bxc { display: flex; gap: 12px; background: #fff; border: 1.5px solid #E3E8E6; border-radius: 16px; padding: 10px; }
.bxc img.pst { width: 82px; height: 110px; object-fit: cover; border-radius: 10px; flex: 0 0 82px; }
.bxc .t { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.bxc .w { font-family: "Jua", sans-serif; font-size: 1.15rem; color: #2E9C82; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bxc .c { font-weight: 800; font-size: .92rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bxc .d { color: #2E9C82; font-weight: 800; font-size: .85rem; }
.bxc .st { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: .72rem; font-weight: 800; background: #E6F6F0;
  color: #2E9C82; width: fit-content; }
.bxc .st.end { background: #EEF1F0; color: #8A9592; }
/* 예정: 배지·작품 이름·기간을 파란색으로 (11/18 요청, 캘린더의 '예정' 표와 같은 파랑) */
.bxc.soon .st { background: #E5EEFC; color: #2C5BC5; }
.bxc.soon .w, .bxc.soon .d { color: #2C5BC5; }
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


RECENT_MAX = 10        # 최근 본 팝업 최대 개수 (11/18 요청: 20 → 10)


def _remember_recent(cafe_id: str) -> None:
    """최근 본 팝업 (이 브라우저 세션 안에서, 최신 RECENT_MAX 개)."""
    rec = [x for x in st.session_state.get("recent_seen", []) if x != cafe_id]
    st.session_state["recent_seen"] = ([cafe_id] + rec)[:RECENT_MAX]


def _box_tab(t: str) -> None:
    st.session_state["box_tab"] = t


def _box_card(r: dict, key: str, review_html: str = "") -> None:
    eid = str(r.get("entry_id"))
    s_, e_ = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
    md = lambda d: f"{d.month}.{d.day}" if d else ""          # noqa: E731
    state = ("종료" if e_ and e_ < TODAY else "예정" if s_ and s_ > TODAY else "진행 중") if s_ else ""
    with st.container(key=f"bx_{key}_{eid}"):
        st.markdown(
            f'<div class="bxc{" soon" if state == "예정" else ""}"><img class="pst" src="{escape(_poster_url(r.get("images")))}" alt="">'
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
    # 끝난 팝업은 어디에도 보이지 않게 (11/18 요청): 북마크·다녀온·최근 본 모두 종료일이 오늘 이후인 것만
    latest = {str(r.get("entry_id")): r for r in mycal.latest_rows(store.all_rows())
              if r.get("status") != "deleted" or r.get("source") == "기간 종료"}
    latest = {k: r for k, r in latest.items() if (mycal._day(r.get("end_date")) or TODAY) >= TODAY}

    if tab == "fav":
        st.markdown(f'<div class="bx-tip">{_mi("notifications")} 북마크한 팝업은 오픈·종료 3일 전부터 알림으로 알려 드려요.</div>',
                    unsafe_allow_html=True)
        _, mine, _ = _fav_state()
        rows = sorted((latest[i] for i in mine if i in latest),
                      key=lambda r: (str(r.get("end_date") or "") < TODAY.isoformat(), str(r.get("start_date") or "")))
        if not rows:
            _box_empty("아직 북마크한 팝업이 없어요", "리스트나 상세에서 북마크 아이콘을 누르면 여기에 모여요.", "bookmark_add")
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
        ids = [i for i in st.session_state.get("recent_seen", []) if i in latest][:RECENT_MAX]
        st.markdown(f'<div class="bx-tip">{_mi("history")} 이 브라우저에서 최근에 연 팝업 상세예요 (최대 {RECENT_MAX}개).</div>',
                    unsafe_allow_html=True)
        if not ids:
            _box_empty("최근 본 팝업이 없어요", "리스트나 지도에서 팝업을 눌러 상세를 열면 여기에 남아요.", "history")
            return
        _box_grid([(latest[i], "") for i in ids], "recent")


def page_map() -> None:
    st.markdown(GLOBAL_CSS + LIST_CSS + STORY_CSS + HOME_CSS, unsafe_allow_html=True)
    ss = st.session_state
    _no_translate(season_on=bool(ss.get("cal_view") and not ss.get("selected") and _member()))   # 계절 배경은 내 캘린더에서만
    _history_guard(on_main=True)
    _clear_buttons()    # 상단 검색칸 오른쪽 × 로 검색어 한 번에 지우기
    _keep_scroll()
    _pin_view_icon()
    try:
        _warm_blog_counts(stats.popups(store.all_rows()))     # 블로그 후기 건수 미리 세기 (서버마다 하루 한 번, 뒤에서)
    except Exception:
        pass
    _live_send()
    # 처음 들어오면 기본은 리스트 전체보기 (지도보기는 버튼으로)
    st.session_state.setdefault("list_only", True)
    st.session_state.setdefault("home_view", True)     # 새로 열거나 새로고침하면 첫 화면은 늘 홈 (11/18 요청)
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
    if st.session_state.get("home_view") and not current:
        render_home(df)
        return
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
        bool(ss.get("regions")), bool(ss.get("fav_only")), bool(ss.get("res_only")),
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
    if ss.get("pc_filters"):
        # 말풍선 꼬리를 검색 아이콘 바로 밑에 (오른쪽 아이콘 수가 손님·회원·관리자마다 달라서 실제 위치로 잰다)
        components.html("<script>(function(){const d=window.parent.document;let t=0;const f=()=>{"
                        "const ic=d.querySelector('.st-key-gnb_search_on'),box=d.querySelector('.st-key-topbar .st-key-filters');"
                        "if(ic&&box){const a=ic.getBoundingClientRect(),b=box.getBoundingClientRect();"
                        "box.style.setProperty('--bubble-tail',Math.max(12,b.right-(a.left+a.width/2)-10)+'px');}};"
                        "const iv=setInterval(()=>{f();if(++t>10)clearInterval(iv);},200);"
                        "window.parent.addEventListener('resize',f);})();</script>", height=0)
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
        st.multiselect("지역", areas, key="regions_m", placeholder="지역 고르기 (여러 곳 가능)", select_all=False,
                       on_change=lambda: ss.update(regions=ss["regions_m"]))

    # 띄어쓰기는 보지 않는다 · '아냐' 는 '아냐 포저' 로도 찾힌다 (_filter_view)
    # 팔로우한 곳만·지역·정렬은 리스트 전체보기에서만 보이고 걸린다 (지도보기에서는 숨기기만 해서 고른 값은 남는다)
    wide = bool(st.session_state.get("list_only")) and not current
    fcond = {"query": query, "work": pick_work, "chars": pick_chars, "span": span, "day": pick_day,
             "regions": st.session_state.get("regions", []) if wide else [],
             "fav": bool(st.session_state.get("fav_only")) if wide else False,
             "reserve": bool(st.session_state.get("res_only")) if wide else False}
    view = _filter_view(df, fcond)
    ask_only = st.session_state.get("ask_only") if wide else None
    if ask_only:          # 물어보기 '더보기': 그 답에서 찾은 팝업 전부 (검색 조건 대신)
        view = df[df["entry_id"].astype(str).isin(set(ask_only["ids"]))]
    if wide:
        view = _sort_view(view, st.session_state.get("sort", SORTS[0]))
    else:
        # 칸을 위젯으로 집어서 숨긴다 (':not(:first-child)' 로 잡으면 '팝업 카페 N곳' 칸 안의 리스트 전체보기 버튼 칸까지 숨는다)
        # 정렬 칸은 남기고(보기 전환 아이콘이 그 위에 있다) 정렬 고르기만 숨긴다
        st.markdown("<style>.st-key-listtools [data-testid='stColumn']:has([class*='st-key-folsw_'], .st-key-regions),"
                    " .st-key-listtools .st-key-sort, .st-key-m_only { display: none !important; }"
                    # 지도보기 PC: 목록 위 도구 줄은 비어 있어서 숨긴다 → 메뉴바와 지도 사이 간격이 반으로 (11/18 요청)
                    " @media (min-width: 641px) { .st-key-listtools { display: none !important; } }</style>",
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
    # 리스트로 보기 (PC): 왼쪽 칸에 마지막 업데이트 · 관심 작품 · 도구 줄 · 목록, 오른쪽 물어보기는 마지막 업데이트 줄부터 길게
    # (11/18 요청: 북마크·지역·정렬 줄은 물어보기 창 앞까지만). 모바일은 물어보기 칸을 숨기고 위 '물어보기' 버튼으로
    if wide:
        lst, chat = st.columns([3.3, 1.165], gap="medium")   # 물어보기 폭 = 지도보기와 같게
        left = lst
    elif not current:
        # 지도로 보기도 같게 (11/18 요청): 왼쪽 큰 칸(마지막 업데이트 · 관심 작품 · 데일리 노트 · 지도), 오른쪽 물어보기
        map_left, map_right = st.columns([0.9 + 3.4, 1.55], gap="medium")
        left = map_left
    else:
        left = contextlib.nullcontext()
    with left:
        if ask_only:     # 물어보기 '더보기' 로 왔다는 표시 + 풀기
            with st.container(horizontal=True, key="ask_only_bar", vertical_alignment="center"):
                st.markdown(f'<div class="ask-only">{_mi("forum")} 물어보기 결과 · <b>{escape(ask_only["label"])}</b> '
                            f'<span>{len(view)}건</span></div>', unsafe_allow_html=True)
                st.button("전체 팝업 보기", icon=":material/close:", key="ask_only_clear", type="tertiary",
                          on_click=lambda: st.session_state.pop("ask_only", None))
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
                           placeholder="지역 고르기 (여러 곳 가능)", select_all=False)   # 기본이 전체라 '전체 선택' 은 뺌 (11/18)
        with sort:
            _view_icon_button(wide, active, m_open)
            st.selectbox("정렬", SORTS, key="sort", label_visibility="collapsed")

        # ('마지막 업데이트' 줄은 11/18 요청으로 모든 화면에서 뺐다 — _update_note 는 남겨 둠)
        if wide:
            if st.session_state.get("res_only"):
                st.button("사전예약 팝업만 보는 중", icon=":material/close:", key="res_only_chip",
                          on_click=lambda: st.session_state.update(res_only=False))
            render_list(view, wide=True, df_all=df, fcond=fcond)
    if wide:
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
        render_similar(current, df)      # 같은 작품의 다른 지역·다른 팝업 (11/18 요청)
    else:
        # 지도보기: 왼쪽 데일리 팝업 노트, 가운데 지도, 오른쪽 내 캘린더 (팝업 리스트는 두지 않는다)
        st.markdown(CAL_CSS, unsafe_allow_html=True)
        with map_left, st.container(key="map_row"):
            col_day, col_map = st.columns([0.9, 3.4], gap="medium")
        with col_day, st.container(key="map_daily"):
            render_daily(df)
        with col_map, st.container(key="map_frame"):
            draw_map()
        # PC 지도: 화면 높이에 맞춰 늘린다 (메뉴바·여백만 빼고, 페이지 스크롤이 생기지 않을 만큼, 11/18 요청)
        st.markdown("<style>@media (min-width: 641px) { .st-key-map_frame iframe { height: calc(100vh - 140px) !important;"
                    " min-height: 520px; }"
                    # 옆 물어보기 창도 지도와 같은 위·아래 선으로 (11/18 요청)
                    # 옆 물어보기 창은 '마지막 업데이트' 줄부터 화면 아래까지 길게 (11/18 요청, 리스트 보기와 같게)
                    " .st-key-ask_panel { height: calc(100vh - 115px) !important; min-height: 520px; max-height: none !important; }"
                    # 위에 '내가 관심있는 작품' 줄이 있으면 지도는 그만큼 줄여 물어보기 창과 아래 선을 맞춘다 (11/18)
                    # 지도는 물어보기 창과 아래 선을 맞춘다 (위에 '마지막 업데이트' 줄만큼 짧게, 11/18)
                    " .st-key-map_frame iframe { height: calc(100vh - 115px) !important; } }</style>",
                    unsafe_allow_html=True)
        with map_right, st.container(key="ask_panel"):   # 내 캘린더 자리 → 물어보기 (캘린더는 '내 캘린더' 탭으로)
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
        try:
            saved = [images.save(name, data) for name, data in files]
        except ValueError as err:
            st.error(str(err), icon=":material/error:")
            return
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
        try:
            saved = [images.save(name, data) for name, data in files]
        except ValueError as err:
            st.session_state["wiz_err"] = str(err)
            return False
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
    _no_translate(season_on=True)      # 계절 배경 (내 캘린더에서만, 11/18)
    if _brand(home=True, fixed=True):
        st.session_state.update(home_view=True, cal_view=False, box_view=False, selected=None)   # 로고 → 홈 (11/18)
        go("map")
    render_calendar()


def render_calendar(compact: bool = False) -> None:
    """내 캘린더 묶음 (월 머리글·이전/다음 달·달력·곧 있는 팝업). compact 면 지도 옆 좁은 칸용으로 칸 높이를 줄인다."""
    _, mine, _ = _fav_state()
    # 기간이 끝나 지도에서 내려간 팔로우도 지난 달력에 남도록, 내린 기록까지 포함한 최신 행에서 고른다
    events = mycal.fav_events(mycal.latest_rows(store.all_rows()), mine, TODAY)
    events = [e for e in events if e.end >= TODAY]          # 끝난 팝업은 달력에서도 뺀다 (11/18 요청)

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
.auth-foot { color: #9AA5A1; font-size: .7rem; line-height: 1.6; text-align: center; margin: 22px auto 0; padding-top: 12px;
  border-top: 1px solid #EEF1F0; max-width: 100%; }
.auth-foot b { color: #6B7672; }
/* 로그인·가입 화면: 입력칸 이름 옆 ? 를 오른쪽 끝이 아니라 이름 바로 옆에 (11/18 요청) */
.st-key-auth_wrap [data-testid="stWidgetLabel"], [data-testid="stForm"] [data-testid="stWidgetLabel"] {
  justify-content: flex-start !important; gap: 4px !important; }
.st-key-auth_wrap [data-testid="stWidgetLabel"] > div, [data-testid="stForm"] [data-testid="stWidgetLabel"] > div {
  flex: 0 0 auto !important; width: auto !important; margin-left: 0 !important; }
/* 회원가입 안내: 작은 글씨 · 연한 회색 바탕 · 테두리 (11/18 요청) */
.auth-sub.auth-guide { font-size: .7rem; line-height: 1.6; color: #5F6B67; background: #F4F6F5; border: 1px solid #E3E8E6;
  border-radius: 12px; padding: 10px 14px; text-align: left !important; }
.auth-or { display: flex; align-items: center; gap: .6rem; max-width: 380px; color: #9AA5A1; font-size: .8rem;
  margin: 1rem 0 .3rem; }
.me-av { margin-bottom: 8px; }
.auth-card.me-card { display: flex; align-items: center; gap: 16px; }
.me-card .me-av { margin: 0; flex: 0 0 auto; }
.me-card .me-info { min-width: 0; text-align: left; }
.me-card .me-info b { font-size: 1.05rem; }
/* 약관 전체 동의: 굵게, 아래 항목들과 얇은 선으로 나눈다 */
/* 간편 가입 버튼: 가운데 (11/18 요청) */
.st-key-soc_join { display: flex !important; justify-content: center !important; width: 100% !important; }
.st-key-soc_join .stButton { width: auto !important; }
.st-key-soc_allbox { border-bottom: 1px solid #E3E8E6; padding-bottom: 6px; margin-bottom: 2px; }
.st-key-soc_allbox label p { font-weight: 800 !important; }
/* 마이페이지 저장 · 로그아웃: 모바일에서도 한 줄에 반반 */
[data-testid="stForm"]:has(input[aria-label="닉네임 바꾸기"]) [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; }
[data-testid="stForm"]:has(input[aria-label="닉네임 바꾸기"]) [data-testid="stColumn"] { flex: 1 1 0 !important; min-width: 0 !important; width: auto !important; }
.st-key-withdraw_box { margin-top: 10px; }
.st-key-withdraw_box button { border: 0 !important; background: transparent !important; box-shadow: none !important;
  padding: 0 !important; min-height: 0 !important; width: auto !important; }
.st-key-withdraw_box button p { font-size: .76rem !important; color: #9AA5A1 !important; text-decoration: underline; }
.st-key-withdraw_box button [data-testid="stIconMaterial"], .st-key-withdraw_box button svg { display: none !important; }
.consent-box { background: #F4F8F6; border-radius: 12px; padding: 10px 12px; margin: 6px 0 8px; font-size: .82rem; color: #3A4542; }
.consent-box table { width: 100%; border-collapse: collapse; margin: 6px 0; }
.consent-box th { width: 44px; text-align: left; color: #2E9C82; font-weight: 800; padding: 3px 6px 3px 0; vertical-align: top; border: 0; }
.consent-box td { padding: 3px 0; border: 0; line-height: 1.5; }
.consent-box span { color: #7A8582; font-size: .76rem; }
.consent-link { font-size: .76rem; color: #8A9592; margin: 2px 0 8px; }
.consent-link a { color: #2E9C82 !important; font-weight: 700; }
/* 가입 화면의 전문 보기·만 14세 안내: 가운데 정렬 + 얇은 테두리 상자 (11/18 요청) */
.consent-note { text-align: center; border: 1px solid #E3E8E6; border-radius: 10px; padding: 8px 12px; margin: 6px 0 10px; line-height: 1.6; }
.st-key-privacy_wrap { max-width: 860px; margin: 0 auto; }
.st-key-privacy_wrap a[id] { display: block; scroll-margin-top: 96px; }   /* 사용법 안내 #칸 바로가기: 메뉴바 밑으로 */
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
.auth-card { border: 1.5px solid #9EDDCC; border-radius: 14px; padding: 1rem 1.1rem; max-width: 460px; background: #fff;
  margin-bottom: 14px; }   /* 아래 '프로필 사진 바꾸기' 칸과 붙지 않게 (11/18) */
</style>
"""


# 로그인이 끝났을 때 (앱 창 = 부품 iframe 의 parent 에서 실행).
# ① 다른 창에 '로그인 끝' 신호(localStorage aw_login_done) → 원래 창이 새로고침 (LOGIN_WATCH_JS)
# ② 이 창이 간편 로그인 작은 창이면 스스로 닫는다. 창 이름(aw_login)은 카카오 · 네이버를 거치면 크롬이 지워서(11/18 배포에서
#    창이 안 닫힘), 열 때 sessionStorage 에 남긴 표시(aw_popup — 새 창은 연 창의 sessionStorage 를 물려받음)와 opener 도 본다
# ③ 브라우저가 닫기를 막으면 '닫아도 돼요' 안내를 덮어 보여 준다
LOGIN_DONE_JS = """setTimeout(function(){
try{localStorage.setItem('aw_login_done',String(Date.now()));}catch(e){}
var pop=false;
try{pop=sessionStorage.getItem('aw_popup')==='1';}catch(e){}
try{pop=pop||!!window.top.opener;}catch(e){}
try{pop=pop||window.top.name==='aw_login';}catch(e){}
if(!pop)return;
try{sessionStorage.removeItem('aw_popup');}catch(e){}
try{window.top.close();}catch(e){}
setTimeout(function(){var d=document;if(!d.body||d.getElementById('aw-done'))return;var o=d.createElement('div');o.id='aw-done';
o.style.cssText='position:fixed;inset:0;z-index:999999;background:rgba(255,255,255,.97);display:flex;align-items:center;justify-content:center;text-align:center;padding:24px;font:700 18px/1.6 sans-serif;color:#0d9488';
o.textContent='로그인됐어요. 이 창은 닫고 원래 창으로 돌아가 주세요.';d.body.appendChild(o);},900);
},700);"""

# 원래 창: 간편 로그인 작은 창에서 로그인이 끝났다는 신호를 받으면 작은 창을 닫고 새로고침(로그인 화면이면 홈으로).
# 앱 창에 직접 붙여서(parent.eval) Streamlit 이 화면을 다시 그려도 남는다 (부품 iframe 은 다시 그리면 사라짐)
LOGIN_WATCH_JS = r"""if(!window.__awWatch){window.__awWatch=1;
var ck=function(){return (document.cookie.match(/(?:^|; )__COOKIE__=([^;]*)/)||[])[1]||'';};
var first=ck(),done=false;
var go=function(){if(done)return;done=true;try{window.__awPop&&window.__awPop.close();}catch(_){}
var p=location.pathname;if(/\/(login|auth)\/?$/.test(p)){location.replace(p.replace(/\/(login|auth)\/?$/,'/')+location.search);}
else{location.reload();}};
window.addEventListener('storage',function(e){if(e.key==='aw_login_done'&&e.newValue)go();});
var chk=function(){if(!window.__awPop)return;var v=ck();if(v&&v!==first)go();};
window.addEventListener('focus',chk);document.addEventListener('visibilitychange',chk);setInterval(chk,1500);}""".replace(
    "__COOKIE__", auth.COOKIE)
# ↑ 신호(storage)를 못 받는 브라우저 대비: 이 창이 작은 창을 열었으면(__awPop) 로그인 쿠키가 바뀌었을 때 ·
#   작은 창이 닫혀 이 창에 다시 초점이 올 때도 새로고침 (11/18 배포: 작은 창은 닫혔는데 원래 창이 그대로)


def _set_cookie(value: str, days: int) -> None:
    """로그인 쿠키를 브라우저에 심는다 (다음에 열어도 로그인 유지). 서버는 st.context.cookies 로 읽는다."""
    secure = "; Secure" if auth.base_url().startswith("https") else ""
    js = (f"window.parent.document.cookie = {json.dumps(auth.COOKIE + '=' + value)} + "
          f"'; path=/; max-age={days * 86400}; SameSite=Lax{secure}"
          + ("; expires=Thu, 01 Jan 1970 00:00:00 GMT" if days <= 0 else "") + "';")
    if value and days > 0:
        # 간편 로그인 창(로그인 화면이 window.open 으로 연 'aw_login' 창)에서 로그인이 끝났으면 쿠키를 심은 뒤 그 창을 닫는다.
        # 원래 창은 쿠키가 생긴 걸 알아채고 새로고침해 로그인된 화면이 된다 (11/18 요청). 보통 창이면 아무 일도 없다
        # 타이머는 바깥 창(parent.eval)에 건다 — 로그인 뒤 화면을 다시 그리면 이 부품 iframe 이 사라져 타이머도 같이 사라졌다
        js += f"window.parent.eval({json.dumps(LOGIN_DONE_JS)});"
    components.html(f"<script>{js}</script>", height=0)


_USER_STATE = ("_ntf_read", "_ntf_cookie", "recent_seen", "box_tab", "_fav_cache", "_member_cache", "_avatar_cache",
               cookie_bridge.KEY)


def _clear_user_state() -> None:
    """계정이 바뀌면 이전 사람의 알림 읽음·최근 본·북마크 기억을 버린다 (11/18: 네이버 → 카카오로 바꿨더니 섞임)."""
    for k in _USER_STATE:
        st.session_state.pop(k, None)


def _login_done(row: dict, msg: str) -> None:
    _clear_user_state()
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


GUIDE_FILE = Path(__file__).resolve().parent / "docs" / "guide.md"
GUIDE_CSS_FILE = Path(__file__).resolve().parent / "static" / "guide" / "guide.css"   # 튜토리얼 꾸밈 (11/18)
CONTACT_EMAIL = "tjtek888@gmail.com"      # docs/privacy-policy.md 10절 연락처와 같게


def _footer() -> None:
    """페이지 맨 아래 바닥글 (11/18 요청): © 연도 ANI:WHERE · 운영 · 개인정보 문의 + 개인정보처리방침 · 사용법 링크."""
    # 꾸밈을 바닥글과 함께 넣어 어느 화면(홈·리스트·상세·사용자 튜토리얼·개인정보처리방침)에서도 같게: 가운데 · 작은 회색 글씨 (11/18 요청)
    st.markdown(
        '<style>.aw-foot { margin-top: 48px; padding: 22px 0 8px; border-top: 1px solid #E6ECEA; color: #9AA5A1 !important;'
        ' font-size: .75rem !important; line-height: 1.8; text-align: center; }'
        ' .aw-foot div { font-size: .75rem !important; color: #9AA5A1 !important; }'
        ' .aw-foot a { color: #7B8784 !important; text-decoration: none; font-size: .75rem !important; }'
        ' .aw-foot a:hover { text-decoration: underline; }'
        ' .aw-foot .aw-foot-links { display: flex; gap: 14px; margin-top: 2px; justify-content: center; flex-wrap: wrap; }</style>',
        unsafe_allow_html=True)
    # (꾸밈 <style> 칸은 화면에서 접히게 되어 있어서, 바닥글 글은 따로 그린다)
    st.markdown(
        f'<div class="aw-foot"><div>© {TODAY.year} ANI:WHERE</div>'
        f'<div>운영: ANI:WHERE · 문의: <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></div>'
        '<div class="aw-foot-links"><a href="./privacy" target="_self">개인정보처리방침 · 이용약관</a>'
        '<a href="./guide" target="_self">사용자 튜토리얼</a><a href="./design" target="_self">디자인 시스템</a></div></div>', unsafe_allow_html=True)


DESIGN_DIR = Path(__file__).resolve().parent / "docs" / "design"
DESIGN_COMPONENTS = [("Badge", "배지"), ("Button", "버튼"), ("PosterCard", "포스터 카드"), ("StoryCircle", "북마크 팝업 동그라미"),
                     ("Chip", "칩")]
DESIGN_CSS = """
<style>
.st-key-design_wrap { max-width: 1040px; margin: 0 auto; }
.ds-cover { width: 100%; max-width: 960px; overflow: hidden; border-radius: 18px; border: 1px solid #E3E9E7; margin: 6px 0 10px; }
.ds-cover .cv { transform-origin: 0 0; }
@media (max-width: 1040px) { .ds-cover { height: 270px; } .ds-cover .cv { transform: scale(0.9); } }
@media (max-width: 900px) { .ds-cover { height: 225px; } .ds-cover .cv { transform: scale(0.75); } }
@media (max-width: 760px) { .ds-cover { height: 186px; } .ds-cover .cv { transform: scale(0.62); } }
@media (max-width: 640px) { .ds-cover { height: 156px; } .ds-cover .cv { transform: scale(0.52); } }
@media (max-width: 520px) { .ds-cover { height: 126px; } .ds-cover .cv { transform: scale(0.42); } }
@media (max-width: 430px) { .ds-cover { height: 108px; } .ds-cover .cv { transform: scale(0.36); } }
@media (max-width: 380px) { .ds-cover { height: 96px; } .ds-cover .cv { transform: scale(0.32); } }
.ds-h2 { font-size: 1.4rem; font-weight: 900; margin: 34px 0 6px; padding-top: 22px; border-top: 1px solid #E6ECEA; }
.ds-sub { color: #7B8784; font-size: .88rem; margin: 0 0 12px; }
.ds-sw { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px; margin: 8px 0 14px; }
.ds-sw > div { border: 1px solid #E3E9E7; border-radius: 12px; overflow: hidden; background: #fff; }
.ds-sw .chip { height: 64px; border-bottom: 1px solid #EEF2F1; }
.ds-sw .nm { padding: 8px 10px 0; font-weight: 800; font-size: .85rem; }
.ds-sw .vl { padding: 0 10px; font-size: .75rem; color: #7B8784; font-variant-numeric: tabular-nums; }
.ds-sw .us { padding: 4px 10px 10px; font-size: .74rem; color: #4B5653; line-height: 1.5; }
.ds-grp { font-weight: 800; color: #0d9488; margin: 14px 0 2px; font-size: .95rem; }
.ds-type > div { display: flex; gap: 16px; align-items: baseline; padding: 10px 0; border-bottom: 1px solid #EEF2F1; }
.ds-type .meta { width: 190px; flex: none; font-size: .75rem; color: #7B8784; }
.ds-type .meta b { display: block; color: #26302D; font-size: .85rem; }
.ds-scale { display: flex; flex-wrap: wrap; gap: 18px; align-items: flex-end; margin: 6px 0 12px; }
.ds-scale > div { text-align: center; font-size: .75rem; color: #7B8784; }
.ds-scale .bar { background: var(--accent); border-radius: 3px; margin: 0 auto 6px; }
.ds-scale .box { width: 72px; height: 72px; background: #e6fbf7; border: 2px solid #14b8a6; margin: 0 auto 6px; }
.ds-scale .shd { width: 110px; height: 64px; background: #fff; border-radius: 12px; margin: 0 auto 10px; }
.ds-comp { border: 1px solid #E3E9E7; border-radius: 16px; margin: 12px 0 18px; overflow: hidden; }
.ds-comp .stage { background: #F6F8F7; padding: 6px; overflow-x: auto; }
.ds-comp .doc { padding: 4px 18px 10px; font-size: .9rem; line-height: 1.7; }
.ds-logos { display: flex; flex-wrap: wrap; gap: 14px; }
.ds-logos figure { margin: 0; width: 220px; text-align: center; font-size: .78rem; color: #7B8784; }
.ds-logos img { width: 100%; height: 110px; object-fit: contain; background: #fff; border: 1px solid #E3E9E7; border-radius: 12px; padding: 10px; box-sizing: border-box; }
@media (max-width: 640px) { .ds-type > div { flex-direction: column; gap: 4px; } .ds-type .meta { width: auto; } }
</style>
"""


def _design_vars(tok: dict) -> str:
    """tokens.json → CSS 변수 (컴포넌트 모습 · 색 칸이 같은 값을 쓰게). 별칭 {mint} 은 var(--mint)."""
    out = []
    for t in tok["color"]["tokens"]:
        v = t["value"] if isinstance(t["value"], str) else next(iter(t["value"].values()))
        out.append(f'--{t["name"]}: ' + (f'var(--{v[1:-1]})' if v.startswith("{") else v) + ";")
    for fam in ("spacing", "radius", "shadow"):
        out += [f'--{t["name"]}: {t["value"]};' for t in tok.get(fam, {}).get("tokens", [])]
    out += [f'--font-{k}: {v};' for k, v in tok["type"]["families"].items()]
    return "<style>.st-key-design_wrap { " + " ".join(out) + " }</style>"


def page_design() -> None:
    """ANI:WHERE 디자인 시스템 (/design, 누구나 열람, 11/18 요청). Claude Design 의 디자인 시스템과 같은 내용을
    docs/design/ (tokens.json · README.md · components/) 에서 읽어 그린다 — 값은 이 파일들 한 곳에서만 고친다."""
    import json as _json

    try:
        tok = _json.loads((DESIGN_DIR / "tokens.json").read_text(encoding="utf-8"))
        book = (DESIGN_DIR / "README.md").read_text(encoding="utf-8")
        comp_css = (Path(__file__).resolve().parent / "static" / "design" / "components.css").read_text(encoding="utf-8")
        comp_css += (Path(__file__).resolve().parent / "static" / "design" / "cover.css").read_text(encoding="utf-8")
    except (OSError, ValueError):
        st.warning("디자인 시스템을 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.", icon=":material/error:")
        return
    st.markdown(GLOBAL_CSS + AUTH_CSS + DESIGN_CSS + "<style>" + comp_css + "</style>", unsafe_allow_html=True)
    st.markdown(_design_vars(tok), unsafe_allow_html=True)
    _no_translate()
    with st.container(key="topbar"):
        _gnb(None, on_map=False)
    with st.container(key="design_wrap"):
        # 표지 (Claude Design 표지와 같은 그림). 960px 로 그리고 화면이 좁으면 줄여 보인다
        cover = (DESIGN_DIR / "components" / "Cover.html").read_text(encoding="utf-8")
        st.markdown(f'<div class="ds-cover">{cover}</div>', unsafe_allow_html=True)
        st.markdown('<div class="ds-sub">ANI:WHERE 앱 코드(<code>app_cafemap.py</code>)에서 값을 그대로 옮긴 디자인 시스템이에요. '
                    'Claude Design 에 같은 내용이 있고, 이 페이지는 누구나 볼 수 있게 앱 안에 둔 것이에요.</div>', unsafe_allow_html=True)

        # 1) 브랜드 안내서 (말투 · 색 쓰임 · 글꼴 · 모양 · 배지 뜻 · 아이콘 · 로고 · 옮기지 않은 것)
        st.markdown(book.split("\n", 1)[1] if book.startswith("# ") else book)

        # 2) 색 토큰
        st.markdown('<div class="ds-h2">색 토큰</div><div class="ds-sub">이름 · 값 · 언제 쓰는지. 칸의 색은 실제 값이에요.</div>',
                    unsafe_allow_html=True)
        groups = [("포인트 · 브랜드", ("accent", "mint", "gnb")), ("글자 · 바탕 · 선", ("ink", "muted", "subtle", "line", "surface", "gray")),
                  ("강조 · 상태", ("coral", "blue", "red", "purple", "orange", "star", "today", "gantt")), ("지역", ("city",))]
        for title, pre in groups:
            cells = []
            for t in tok["color"]["tokens"]:
                if not t["name"].startswith(pre):
                    continue
                v = t["value"] if isinstance(t["value"], str) else next(iter(t["value"].values()))
                cells.append(f'<div><div class="chip" style="background:var(--{t["name"]})"></div><div class="nm">{escape(t["name"])}</div>'
                             f'<div class="vl">{escape(v)}</div><div class="us">{escape(t.get("usage", ""))}</div></div>')
            st.markdown(f'<div class="ds-grp">{escape(title)}</div><div class="ds-sw">{"".join(cells)}</div>', unsafe_allow_html=True)

        # 3) 글꼴
        st.markdown('<div class="ds-h2">글꼴</div><div class="ds-sub">제목은 Jua, 본문은 나눔스퀘어라운드 → Pretendard, 아이콘은 Material Symbols Rounded.</div>',
                    unsafe_allow_html=True)
        rows = []
        for g in tok["type"]["groups"]:
            fam = f'var(--font-{g["family"]})'
            for sty in g["styles"]:
                rows.append(f'<div><div class="meta"><b>{escape(sty["name"])}</b>{escape(g["name"])} · {sty["fontSize"]} / {sty["lineHeight"]} · {sty["fontWeight"]}'
                            f'<br>{escape(sty.get("usage", ""))}</div><div style="font-family:{fam};font-size:{sty["fontSize"]};line-height:{sty["lineHeight"]};'
                            f'font-weight:{sty["fontWeight"]}">{escape(sty.get("sample", ""))}</div></div>')
        st.markdown(f'<div class="ds-type">{"".join(rows)}</div>', unsafe_allow_html=True)

        # 4) 간격 · 모서리 · 그림자
        st.markdown('<div class="ds-h2">간격 · 모서리 · 그림자</div>', unsafe_allow_html=True)
        sp = "".join(f'<div><div class="bar" style="width:{t["value"]};height:40px"></div><b>{t["name"]}</b><br>{t["value"]}</div>' for t in tok["spacing"]["tokens"])
        rd = "".join(f'<div><div class="box" style="border-radius:{t["value"]}"></div><b>{t["name"]}</b><br>{t["value"]}</div>' for t in tok["radius"]["tokens"])
        sh = "".join(f'<div><div class="shd" style="box-shadow:{t["value"]}"></div><b>{t["name"]}</b></div>' for t in tok["shadow"]["tokens"])
        st.markdown(f'<div class="ds-grp">간격</div><div class="ds-scale">{sp}</div><div class="ds-grp">모서리</div><div class="ds-scale">{rd}</div>'
                    f'<div class="ds-grp">그림자</div><div class="ds-scale">{sh}</div>', unsafe_allow_html=True)

        # 5) 컴포넌트 (앱 CSS 를 옮긴 모습 + 쓰는 규칙)
        st.markdown('<div class="ds-h2">컴포넌트</div><div class="ds-sub">앱 화면의 CSS 를 보고 옮긴 모습이에요 (누르는 동작은 없어요).</div>',
                    unsafe_allow_html=True)
        for key, label in DESIGN_COMPONENTS:
            try:
                html = (DESIGN_DIR / "components" / f"{key}.html").read_text(encoding="utf-8")
                doc = (DESIGN_DIR / "components" / f"{key}.md").read_text(encoding="utf-8")
            except OSError:
                continue
            doc = doc.split("\n", 1)[1] if doc.startswith("# ") else doc
            st.markdown(f'<div class="ds-grp">{escape(label)} <span style="color:#9AA5A1;font-weight:600">{key}</span></div>'
                        f'<div class="ds-comp"><div class="stage">{html}</div></div>', unsafe_allow_html=True)
            st.markdown(doc)

        # 6) 로고 · 그림
        st.markdown('<div class="ds-h2">로고 · 그림</div><div class="ds-sub">저장소 static/ 의 파일 그대로. 다시 그리거나 색을 바꾸지 않아요.</div>'
                    '<div class="ds-logos">'
                    + "".join(f'<figure><img src="app/static/{f}" alt="{a}"><figcaption>{f} · {a}</figcaption></figure>'
                              for f, a in (("logo.png", "기본 로고"), ("logo_mint.png", "민트 로고"), ("logo2.png", "보조 로고"),
                                           ("ask_avatar.png", "물어보기 도우미"), ("default_poster.png", "기본 포스터")))
                    + '</div>', unsafe_allow_html=True)


def page_guide() -> None:
    """사용자 튜토리얼 (/guide). 물어보기에서 '사용법 알려줘' 하면 이 페이지로 안내한다 (11/18). 칸마다 #map #list … 바로가기.
    내용은 docs/guide.md, 꾸밈은 static/guide/guide.css, 그림은 static/guide/*.png (임시 데이터로 찍은 화면)."""
    try:
        guide_css = "<style>" + GUIDE_CSS_FILE.read_text(encoding="utf-8") + "</style>"
    except OSError:
        guide_css = ""
    st.markdown(GLOBAL_CSS + AUTH_CSS + guide_css, unsafe_allow_html=True)
    _no_translate()
    with st.container(key="topbar"):
        _gnb(None, on_map=False)
    with st.container(key="privacy_wrap"):
        try:
            st.markdown(GUIDE_FILE.read_text(encoding="utf-8"), unsafe_allow_html=True)
        except OSError:
            st.warning("사용자 튜토리얼을 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.", icon=":material/error:")
    # 처음 3단계 배너: 끌어서 넘기기 + 양옆 ‹ › (11/18 요청, 리스트·홈 줄과 같은 _DRAG_JS)
    components.html(f"<script>window.parent.eval({json.dumps(_DRAG_JS)});</script>", height=0)
    # 주소 끝 #add 같은 칸으로 바로 내려간다 (화면이 다 그려진 뒤라 브라우저 기본 이동이 안 먹어서 몇 번 다시 시도)
    components.html("<script>(function(){const P=window.parent,D=P.document;"
                    # 위 바로가기(#home 등)를 누르면 그 칸으로 부드럽게 (Streamlit 은 스크롤 칸이 따로라 직접 옮긴다)
                    "if(!P.__awGuideNav){P.__awGuideNav=1;D.addEventListener('click',e=>{const a=e.target.closest&&e.target.closest('.g-nav a');"
                    "if(!a)return;const t=D.getElementById(a.getAttribute('href').slice(1));if(t){e.preventDefault();"
                    "t.scrollIntoView({behavior:'smooth',block:'start'});P.history.replaceState(null,'',a.getAttribute('href'));}});}"
                    "const id=decodeURIComponent((P.location.hash||'').slice(1));"
                    "if(!id)return;let n=0;const t=setInterval(()=>{const e=P.document.getElementById(id);"
                    "if(e){e.scrollIntoView({block:'start'});clearInterval(t);}if(++n>40)clearInterval(t);},150);})();</script>",
                    height=0)


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
    st.session_state.pop("_auth_err", None)     # 로그인 화면에 오면 지난 간편 로그인 오류는 지운다
    row = _member()
    if row:
        _my_account(row)
        return
    with st.container(key="auth_tabs"):        # 탭을 가운데에 두려고 따로 묶는다
        mode = st.segmented_control("로그인 또는 회원가입", ["로그인", "회원가입"], default="로그인",
                                    label_visibility="collapsed", key="auth_mode") or "로그인"
    if mode == "로그인":
        st.markdown('<div class="auth-title">환영합니다</div>'
                    '<div class="auth-sub">아이디로 가입했다면 아래에, 카카오·네이버로 가입했다면 간편 로그인 가능해요.</div>',
                    unsafe_allow_html=True)
        _password_login_form()
        st.markdown('<div class="auth-or">또는 간편 로그인</div>', unsafe_allow_html=True)
        verb = "로그인"
    else:
        st.markdown('<div class="auth-title">3초 만에 회원가입</div>'
                    '<div class="auth-sub auth-guide"><b>아이디·비밀번호·닉네임</b>만 있으면 가입돼요. 이메일·전화번호는 받지 않아요.<br>'
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
            # 11/18 요청: 같은 페이지에서 넘어가게. iframe 밖(내 컴퓨터, 앱 주소를 바로 연 경우)이면 아래 스크립트가
            # target 을 _self 로 바꾼다. 배포 사이트처럼 iframe 안이면 바깥 창 이동이 막혀 있어 새 탭 그대로
            st.markdown(f'<a class="auth-btn {prov}" href="{escape(auth.authorize_url(prov))}" target="_blank" rel="noopener">'
                        f'{label}로 {verb}</a>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="auth-btn off">{label} {verb} 준비 중</span>', unsafe_allow_html=True)

    # iframe 밖이면 간편 로그인 버튼을 같은 페이지에서 열고, 새 탭 안내 문구를 숨긴다 (11/18 요청)
    # iframe 안(배포 사이트)이면 새 탭 대신 작은 로그인 창(window.open, 이름 aw_login)으로 연다 →
    # 로그인이 끝나면 그 창이 스스로 닫히고(_set_cookie), 이 창은 쿠키를 보고 새로고침된다 (11/18 요청)
    components.html(
        "<script>(function(){const w=window.parent,d=w.document;let n=0;const f=()=>{"
        "if(w.top!==w){d.querySelectorAll('a.auth-btn').forEach(a=>{if(a.dataset.awPop)return;a.dataset.awPop='1';"
        "a.addEventListener('click',e=>{const x=Math.max(0,(w.screen.width-480)/2),y=Math.max(0,(w.screen.height-720)/2);"
        # 새 창은 연 창의 sessionStorage 를 물려받는다 → 작은 창 표시(aw_popup)를 남겼다가 4초 뒤 이 창에서는 지운다
        "try{w.sessionStorage.setItem('aw_popup','1');}catch(_){}"
        "const pop=w.open(a.href,'aw_login','popup=yes,width=480,height=720,left='+x+',top='+y);"
        "w.eval(\"setTimeout(function(){try{sessionStorage.removeItem('aw_popup');}catch(e){}},4000)\");"
        "if(pop){w.__awPop=pop;e.preventDefault();pop.focus();}});});return;}"   # 창이 막히면(팝업 차단) 원래대로 새 탭
        "d.querySelectorAll('a.auth-btn').forEach(a=>{a.target='_self';a.removeAttribute('rel');});"
        "d.documentElement.classList.add('aw-top');};f();const iv=setInterval(()=>{f();if(++n>10)clearInterval(iv);},400);"
        f"w.eval({json.dumps(LOGIN_WATCH_JS)});"
        "})();</script>",
        height=0)
    # 새 탭에서 간편 로그인이 끝나면(로그인 쿠키가 생기면) 이 탭도 메인으로 옮긴다 (11/18: 원래 탭이 로그인 화면에 남던 문제)
    components.html(
        "<script>(function(){const w=window.parent;const val=()=>((w.document.cookie.match(/(?:^|; )" + auth.COOKIE
        + "=([^;]*)/)||[])[1]||'');const first=val();"
        # 처음 값과 달라진 '빈 값이 아닌' 로그인 쿠키가 생기면 (예전 쿠키가 남아 있어도 새 로그인을 알아챈다)
        "const iv=setInterval(()=>{const v=val();if(v&&v!==first){clearInterval(iv);"
        # 부품 iframe 은 바깥 화면을 직접 옮길 권한이 없어서, 바깥 화면 쪽에서 실행되도록 parent.eval 로 넘긴다
        r"w.eval(`location.replace(location.pathname.replace(/\\/(login|auth)\\/?$/,'/')+location.search)`);}},1500);"
        "setTimeout(()=>clearInterval(iv),600000);})();</script>", height=0)
    # 안내는 맨 아래에 작게 한 묶음으로 (11/18 요청)
    st.markdown('<style>html.aw-top .auth-newtab { display: none; }</style>', unsafe_allow_html=True)
    st.markdown('<div class="auth-foot"><span class="auth-newtab">카카오·네이버 로그인은 <b>작은 새 창</b>에서 열려요. 로그인을 마치면 그 창은 저절로 닫히고 '
                '이 화면이 로그인된 메인으로 바뀌어요.<br></span>로그인하지 않아도 팝업은 둘러볼 수 있어요.<br>'
                '받는 정보: <b>별명(닉네임)</b>과 계정 고유 번호뿐이에요. 고유 번호는 알아볼 수 없게 바꿔서(해시) 저장하고, '
                '이메일·전화번호·실명은 받지도 저장하지도 않아요.</div>', unsafe_allow_html=True)
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
    _login_done(row, f"{row['nickname']}님, 환영합니다!")
    go("map")                                # 로그인하면 메인으로 (11/18)


PRIVACY_TABLE = {
    "local": "아이디 · 일방향 암호화한 비밀번호 · 닉네임 · 동의 시각",
    "social": "로그인 수단 · 계정 번호를 되돌릴 수 없게 바꾼 값 · 닉네임 · 동의 시각",
}


def _consent_keys(key: str, photo: bool) -> list[str]:
    return [f"{key}_age", f"{key}_terms", f"{key}_priv"] + ([f"{key}_photo"] if photo else [])


def _consent_all(key: str, photo: bool) -> None:
    """'약관 전체 동의' 를 누르면 아래 항목(선택 포함)을 모두 같은 값으로."""
    on = bool(st.session_state.get(f"{key}_all"))
    for k in _consent_keys(key, photo):
        st.session_state[k] = on


def _consent_sync(key: str, photo: bool) -> None:
    """항목을 하나씩 바꾸면 '전체 동의' 표시도 맞춘다 (모두 켜졌을 때만 켜짐)."""
    st.session_state[f"{key}_all"] = all(st.session_state.get(k) for k in _consent_keys(key, photo))


def _consent_boxes(kind: str, key: str, photo_label: str | None = None, all_toggle: bool = False) -> dict:
    """가입 동의: 필수(만 14세 이상 · 이용약관 · 개인정보 수집·이용)와 선택(프로필 사진)을 따로 받는다.
    무엇을·왜·얼마나 보관하는지 바로 보이게 표로 고지한다 (11/18 개인정보 설계)."""
    st.markdown(
        '<div class="consent-box"><b>개인정보 수집·이용 안내</b>'
        '<table><tr><th>항목</th><td>' + PRIVACY_TABLE[kind] + '</td></tr>'
        '<tr><th>목적</th><td>회원 식별·로그인, 리뷰 작성자 표시, 북마크·알림</td></tr>'
        '<tr><th>보관</th><td><b>탈퇴할 때까지</b> (탈퇴하면 지난 기록까지 바로 지워요)</td></tr></table>'
        '<span>이메일·전화번호·실명은 받지 않아요. 동의하지 않으면 가입할 수 없지만, 로그인 없이도 둘러볼 수 있어요.</span></div>',
        unsafe_allow_html=True)
    # 폼 밖에서만(all_toggle) '약관 전체 동의' — 폼 안의 칸은 서로를 바꿀 수 없다 (11/18 요청: 안내 상자 바로 아래)
    kw = {}
    if all_toggle:
        args = (key, bool(photo_label))
        with st.container(key=f"{key}_allbox"):
            st.checkbox("약관 전체 동의" + (" (선택 항목 포함)" if photo_label else ""), key=f"{key}_all",
                        on_change=_consent_all, args=args)
        kw = {"on_change": _consent_sync, "args": args}
    out = {
        "age": st.checkbox("[필수] 만 14세 이상이에요", key=f"{key}_age", **kw),
        "terms": st.checkbox("[필수] 이용약관에 동의해요", key=f"{key}_terms", **kw),
        "privacy": st.checkbox("[필수] 위 개인정보 수집·이용에 동의해요", key=f"{key}_priv", **kw),
        "photo": st.checkbox(photo_label, key=f"{key}_photo", **kw) if photo_label else False,
    }
    st.markdown(f'<div class="consent-link consent-note">전문 보기: <a href="{PRIVACY_URL}" target="_blank">개인정보처리방침 · 이용약관</a>'
                ' · 만 14세 미만은 가입할 수 없어요 (법정대리인 동의 절차를 갖추지 않았어요)</div>', unsafe_allow_html=True)
    return out


def _consent_error(c: dict) -> str:
    if not c["age"]:
        return "만 14세 이상만 가입할 수 있어요."
    if not (c["terms"] and c["privacy"]):
        return "필수 항목(이용약관 · 개인정보 수집·이용)에 동의해야 가입할 수 있어요."
    return ""


def _password_signup_form() -> None:
    """일반 회원가입: 필수 정보(아이디·비밀번호·닉네임·동의)만 받는다.
    폼으로 묶지 않는다: '약관 전체 동의' 가 아래 항목을 바로 바꿔야 해서 (간편 가입과 같게, 11/18 요청)."""
    with st.container(key="pw_signup"):
        lid = st.text_input("아이디 (필수)", max_chars=20, placeholder="영어 소문자·숫자·_ 4~20자",
                            autocomplete="username")
        pw = st.text_input("비밀번호 (필수)", type="password", max_chars=auth.PW_MAX,
                           placeholder="영문+숫자 8자 이상", autocomplete="new-password")
        pw2 = st.text_input("비밀번호 확인 (필수)", type="password", max_chars=auth.PW_MAX, autocomplete="new-password")
        nick = st.text_input("닉네임 (선택)", max_chars=auth.MAX_NICK, placeholder=_suggest_nick(), help=NICK_HELP)
        consent = _consent_boxes("local", "pwc", all_toggle=True)
        st.markdown('<div class="auth-sub auth-guide">이메일·전화번호를 받지 않아서 <b>비밀번호를 잊으면 찾을 수 없어요.</b> '
                    '꼭 기억해 두세요. 프로필 사진(선택)은 가입한 뒤 마이페이지에서 올릴 수 있어요.</div>',
                    unsafe_allow_html=True)
        done = st.button("가입하기", type="primary", icon=":material/person_add:", width="stretch", key="pw_join")
    if not done:
        return
    err = _consent_error(consent)
    if err:
        st.warning(err, icon=":material/error:")
        return
    try:
        if not " ".join(str(nick or "").split()):      # 닉네임을 비워 두면 '꾸밈말 + 캐릭터' 로 자동 (11/18)
            nick = _suggest_nick(final=True)
        row = auth.register_password(members, lid, pw, pw2, nick)
    except auth.AuthError as e:
        st.warning(str(e), icon=":material/error:")
        return
    # 손님 북마크는 옮기지 않는다: 손님 북마크는 IP 로 묶여 있어 같은 와이파이·같은 컴퓨터의 다른 사람 것까지
    # 새 계정에 들어갔다 (11/18). 북마크는 이제 회원만 할 수 있다
    _login_done(row, "가입했어요!")
    go("map")


def _logout() -> None:
    # 여기서 바로 쿠키 지우는 스크립트를 그리면 뒤따르는 st.rerun() 에 묻혀 브라우저에 닿지 않는다 →
    # 새로고침하면 남은 쿠키로 다시 로그인됐다 (11/18). 다시 그린 화면의 메뉴바(_gnb)에서 지운다
    st.session_state["_cookie_clear"] = True
    st.session_state.pop("_cookie_pending", None)
    _clear_user_state()
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
    # 프로필 사진 옆에 닉네임 · 로그인 수단 · 가입일 · 회원 번호 (11/18 요청)
    st.markdown(f'<div class="auth-title">내 계정</div><div class="auth-card me-card">'
                f'<div class="me-av">{_avatar_img(row.get("avatar"), 72, "me-avimg")}</div><div class="me-info">'
                f'<b>{escape(_nick_only(auth.display_name(row)))}</b><br><span class="auth-note">{escape(prov)} 계정으로 로그인 중 · '
                f'가입 {escape(str(row.get("agreed_at", ""))[:10])}<br>회원 번호 <code>{escape(str(row["entry_id"]))}</code>'
                f'{" · 관리자" if _is_admin() else ""}</span></div></div>', unsafe_allow_html=True)
    with st.expander("프로필 사진 바꾸기"):
        st.caption("리뷰 옆에 동그랗게 보여요. 선택이에요 — 없으면 기본 그림이 보여요. 사람 얼굴·개인정보가 든 사진은 피해 주세요.")
        n = st.session_state.get("_av_n", 0)
        up = st.file_uploader("사진 올리기 (png·jpg·webp, 5MB까지)", type=["png", "jpg", "jpeg", "webp"], key=f"av_up_{n}")
        if up is not None:     # 고른 사진을 바로 보여 준다 (저장 전 미리보기, 11/18 요청: 기다리는 게 보이게)
            st.markdown(f'<div class="av-preview"><img src="data:{up.type or "image/png"};base64,'
                        f'{base64.b64encode(up.getvalue()).decode()}" alt=""><span>이 사진으로 바뀌어요 — 가운데를 동그랗게 잘라요</span></div>',
                        unsafe_allow_html=True)
        ok_photo = st.checkbox("[선택] 프로필 사진 수집·이용에 동의해요 — 리뷰 옆 표시용, '기본 사진 설정'을 누르면 바로 지워요",
                               key=f"av_agree_{n}")
        c1, c2 = st.columns(2)
        if c1.button("이 사진으로 저장", type="primary", width="stretch", disabled=up is None or not ok_photo, key="av_save"):
            data = up.getvalue()
            if images.too_big(data, 5):
                st.warning("5MB 이하 사진만 올릴 수 있어요.", icon=":material/error:")
            else:
                try:
                    with st.spinner("사진을 줄여서 저장하는 중…"):
                        auth.set_avatar(members, row, images.save_avatar(up.name, data))
                    _avatar_saved("프로필 사진을 바꿨어요.")
                except ValueError as err:
                    st.warning(str(err), icon=":material/error:")
        if c2.button("기본 사진 설정", width="stretch", key="av_default"):
            auth.set_avatar(members, row, "none")
            _avatar_saved("기본 사진으로 바꿨어요.")
        if row.get("provider") in ("kakao", "naver"):
            st.caption(f'{auth.PROVIDER_LABEL[row["provider"]]} 프로필 사진은 가입할 때 [선택] 항목에 동의하면 불러와요.')
    with st.form("rename", border=False):
        cur_nick = str(row.get("nickname", "") or "")
        if len(cur_nick) > auth.MAX_NICK:      # 예전(16자까지) 닉네임: 칸에는 10자까지만 들어간다 (11/18 10자 제한)
            st.caption(f"지금 닉네임이 {auth.MAX_NICK}자를 넘어요. 저장하면 {auth.MAX_NICK}자 안으로 바뀌어요.")
        nick = st.text_input("닉네임 바꾸기", value=cur_nick[:auth.MAX_NICK], max_chars=auth.MAX_NICK,
                             placeholder=_suggest_nick(),
                             help="칸을 비워 두고 저장하면 흐리게 보이는 랜덤 닉네임으로 바꿔요 (가입할 때와 같게)")
        # 저장 · 로그아웃을 한 줄에 반반 (11/18 요청). 폼 안에는 제출 버튼만 둘 수 있어서 로그아웃도 제출 버튼으로
        b1, b2 = st.columns(2)
        saved = b1.form_submit_button("저장", icon=":material/check:", type="primary", width="stretch")
        if b2.form_submit_button("로그아웃", icon=":material/logout:", width="stretch"):
            _logout()
            st.session_state["flash"] = ("로그아웃했어요.", ":material/logout:")
            st.rerun()
        if saved:
            # 비워 두고 저장 → 랜덤 닉네임 (11/18 요청). 그사이 누가 먼저 썼으면 _suggest_nick 이 새로 짓는다
            nick = (nick or "").strip() or _suggest_nick(final=True)
            try:
                auth.rename(members, row, nick)
                st.session_state.pop("_member_cache", None)
                st.session_state["flash"] = (f"닉네임을 '{nick}'(으)로 바꿨어요.", ":material/check_circle:")
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
    # 탈퇴하기: 맨 아래 작은 회색 글씨(버튼이지만 글자처럼) — 11/18 요청
    with st.container(key="withdraw_box"), st.popover("탈퇴하기"):
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
        # 돌아오자마자 화면이 한 번 더 그려진다(쿠키 읽기). 그때 주소의 code 가 이미 지워져 있어도
        # 결과를 잃지 않게, code 와 교환 결과·오류를 세션에 먼저 담는다 (11/18 배포 오류)
        st.session_state["_auth_cs"] = (qp["code"], qp["state"])
        st.session_state.pop("_auth_err", None)
        st.query_params.clear()        # code 는 한 번만 쓸 수 있다. 새로고침해도 다시 쓰지 않게 주소에서 지운다
    cs = st.session_state.get("_auth_cs")
    if cs:
        try:
            got = auth.exchange(*cs)
        except auth.AuthError as e:
            st.session_state["_auth_err"] = str(e)
        else:
            st.session_state["_pending_ident"] = got
        st.session_state.pop("_auth_cs", None)
    if st.session_state.get("_auth_err"):
        st.warning(st.session_state["_auth_err"], icon=":material/error:")
        st.page_link(PAGES["login"], label="다시 로그인하기", icon=":material/login:")
        return
    ident = st.session_state.get("_pending_ident")
    if ident:
        row = auth.find(members, ident.member_key)
        if row:
            st.session_state.pop("_pending_ident", None)
            _login_done(row, f"{row['nickname']}님, 환영합니다!")
            go("map")
            return
    if not ident and _member():
        # 이미 로그인됨: 로그인을 마친 뒤 이 화면이 한 번 더 그려지면 안내 대신 메인으로 (11/18)
        go("map")
        return
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
    # 폼으로 묶지 않는다: '약관 전체 동의' 가 아래 항목을 바로 바꿔야 해서 (11/18)
    with st.container(key="soc_signup"):
        nick = st.text_input("닉네임 (선택)", value=str(ident.nickname or "")[:auth.MAX_NICK], max_chars=auth.MAX_NICK,
                             placeholder=_suggest_nick(), help=NICK_HELP, key="soc_nick")
        consent = _consent_boxes("social", "soc", f"[선택] {label} 프로필 사진을 불러와 리뷰 옆에 보여 줘요 (사진 주소 저장, "
                                 "마이페이지에서 언제든 지울 수 있어요)" if ident.avatar else None, all_toggle=True)
        done = st.button("가입하고 시작하기", type="primary", icon=":material/check_circle:", key="soc_join")
    if done:
        err = _consent_error(consent)
        if err:
            st.warning(err, icon=":material/error:")
            return
        if not consent["photo"]:                 # 사진은 선택 동의한 경우에만 저장
            ident = dataclasses.replace(ident, avatar="none")
        try:
            if not " ".join(str(nick or "").split()):
                nick = _suggest_nick(final=True)
            row = auth.signup(members, ident, nick)
        except auth.AuthError as e:
            st.warning(str(e), icon=":material/error:")
            return
        st.session_state.pop("_pending_ident", None)
        _login_done(row, "가입했어요!")         # 손님 북마크는 옮기지 않는다 (위 아이디 가입과 같은 이유)
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
/* 숫자 카드가 담는 칸보다 커서 아래 줄과 겹쳤다 (모바일, 11/18) → 칸 높이를 카드에 맞춤 */
[class*="st-key-admk_"] { height: auto !important; }
[class*="st-key-admk_"] [data-testid="stMarkdownContainer"], [class*="st-key-admk_"] [data-testid="stMarkdown"] {
  margin-bottom: 0 !important; }
[class*="st-key-admk_"] [data-testid="stElementContainer"]:has(.adm-kpi) { margin-bottom: 0 !important; height: auto !important; }
@media (max-width: 640px) {
  .adm-title { font-size: 1.45rem; }
  .adm-sub { font-size: .76rem; margin-bottom: 8px; }
  .adm-eyebrow { font-size: .64rem; }
  .st-key-adm_kpis { gap: 8px !important; }
  .st-key-adm_kpis > * { flex: 1 1 140px !important; }
  .adm-kpi { padding: 9px 11px; }
  .adm-kpi span { font-size: .7rem; }
  .adm-kpi b { font-size: 1.25rem; }
  .adm-kpi b small { font-size: .78rem; }
  .st-key-adm_links a p, .st-key-adm_links button p { font-size: .72rem !important; }
}
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
.st-key-adm_links { gap: 8px !important; margin: 4px 0 -36px; position: relative; z-index: 2; }
.st-key-adm_links a { border-radius: 999px !important; border: 1.5px solid #CDEDE3 !important; background: #fff !important; }
.st-key-adm_links a p { font-size: .82rem !important; font-weight: 700 !important; color: #2E9C82 !important; }
@media (max-width: 900px) { .st-key-adm_links { margin: 4px 0 6px; } }
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
.gt-wk { position: absolute; top: -1px; bottom: -1px; background: rgba(255, 107, 107, .13); }
.gt-today { position: absolute; top: -1px; bottom: -1px; width: 2px; margin-left: -1px; background: #FF5A5A; z-index: 1; }
.gt-tick.now { color: #E5484D; font-weight: 800; }
.gt-head .gt-wk, .gt-head .gt-today { display: none; }
.gt-bar { position: absolute; top: 6px; height: 14px; border-radius: 4px; background: var(--c); }
.gt-head .gt-track { height: 20px; }
.gt-tick .gt-short { display: none; }
@media (max-width: 640px) { .gt-tick .gt-full { display: none; } .gt-tick .gt-short { display: inline; } }
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
ADMIN_TABS = [("board", "팝업 현황"), ("usage", "이용 지표"), ("survey", "사용자 테스트"), ("requests", "삭제 요청"),
              ("notices", "알림 관리"), ("members", "회원 정보"), ("raw", "원본 데이터")]
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


GANTT_COLOR = {"예정": "#3672BD", "진행": "#14B8A6", "종료": "#A9B3B0"}     # 진한 색으로 되돌림 (11/18 요청)
GANTT_PAGE = 20     # 이 주 일정: 처음 20곳, 더보기마다 20곳 더 (11/18 요청)
BOARD_PAGE = 10     # 고른 주 현황: 칸마다 처음 10곳, 더보기마다 10곳 더


def _admin_gantt(mon: date) -> None:
    """고른 주(월~일) 하루 단위 팝업 일정. 주 밖으로 이어지면 막대 끝을 ‹ › 로, 오늘 칸은 연한 민트."""
    start, end = mon, mon + timedelta(days=6)
    span = (end - start).days + 1
    every = admin.gantt_rows(store.all_rows(), start, end, limit=10_000)
    n_key = f"adm_gantt_n_{mon.isoformat()}"
    rows = every[:st.session_state.get(n_key, GANTT_PAGE)]

    def pct(d: date) -> float:
        return max(0.0, min(100.0, (d - start).days / span * 100))

    # 오늘 칸: 연한 빨강 배경 + 가운데 빨간 선 (11/18 요청: 더 눈에 띄게)
    wk = (f'<div class="gt-wk" style="left:{pct(TODAY):.2f}%;width:{100 / span:.2f}%"></div>'
          f'<div class="gt-today" style="left:{pct(TODAY) + 50 / span:.2f}%"></div>'
          if start <= TODAY <= end else "")
    grid = "".join(f'<div class="gt-grid" style="left:{pct(start + timedelta(days=i)):.2f}%"></div>' for i in range(1, span))
    wd = "월화수목금토일"
    ticks = "".join(f'<div class="gt-tick{" now" if start + timedelta(days=i) == TODAY else ""}" '
                    f'style="left:{(i + .5) / span * 100:.2f}%">'
                    f'<span class="gt-full">{"오늘 " if start + timedelta(days=i) == TODAY else ""}'
                    f'{(start + timedelta(days=i)).month}/{(start + timedelta(days=i)).day}({wd[i]})</span>'
                    # 모바일은 칸이 좁아 날짜가 겹친다 → 요일 한 글자만 (오늘은 '오늘'), 11/18 요청
                    f'<span class="gt-short">{"오늘" if start + timedelta(days=i) == TODAY else wd[i]}</span></div>'
                    for i in range(span))
    today = ""
    html = [f'<div class="gt"><div class="gt-row gt-head"><div class="gt-lab"><b>팝업 {len(every)}곳</b></div>'
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
                + '<span><i style="background:#FF5A5A"></i>오늘 (빨간 칸)</span><span>막대가 칸 끝에 붙어 있으면 이 주 앞뒤로 이어져요</span></div></div>')
    st.markdown("".join(html), unsafe_allow_html=True)
    if len(every) > len(rows):
        with st.container(horizontal=True, horizontal_alignment="center", key="adm_more_gantt"):
            st.button(f"{len(every) - len(rows)}건 더보기", icon=":material/expand_more:", key="adm_gantt_more_btn",
                      on_click=lambda: st.session_state.update({n_key: len(rows) + GANTT_PAGE}))


def _admin_board() -> None:
    mon = _week_nav("board")
    st.markdown('<div class="adm-panel-h">이 주 일정 (간트 차트 · 하루 단위)</div>', unsafe_allow_html=True)
    _admin_gantt(mon)
    st.markdown('<div class="adm-panel-h">고른 주 현황</div>', unsafe_allow_html=True)
    board = admin.popup_board(store.all_rows(), mon)
    colors = {"새로 생성": "#14B8A6", "예정": "#3672BD", "진행": "#23866A", "종료": "#8A9592"}
    cols = st.columns(4, gap="small")
    for i, (col, (name, rows)) in enumerate(zip(cols, board.items())):
        n_key = f"adm_board_n_{i}_{mon.isoformat()}"
        n_show = st.session_state.get(n_key, BOARD_PAGE)
        with col:
            cards = "".join(
                f'<a class="adm-card adm-link adm-pcard" href="{_adm_href(r)}" target="_self">'
                f'<img src="{escape(_poster_url(r.get("images")))}" alt="" loading="lazy"><div>'
                f'<b>{escape(str(r.get("work") or ""))}</b>'
                f'<span>{escape(str(r.get("cafe_name") or ""))}</span>'
                f'<em>{escape(str(r.get("start_date") or "")[5:])} ~ {escape(str(r.get("end_date") or "")[5:])}</em></div></a>'
                for r in rows[:n_show]) or '<div class="adm-empty">없어요</div>'
            st.markdown(f'<div class="adm-col" style="--c:{colors[name]}"><div class="adm-colhead">{name}'
                        f'<small>{len(rows)}곳</small></div>{cards}</div>', unsafe_allow_html=True)
            if len(rows) > n_show:
                with st.container(horizontal=True, horizontal_alignment="center", key=f"adm_more_board_{i}"):
                    st.button(f"{len(rows) - n_show}건 더보기", icon=":material/expand_more:", key=f"adm_board_more_btn_{i}",
                              on_click=lambda k=n_key, n=n_show: st.session_state.update({k: n + BOARD_PAGE}))
    st.caption("새로 생성 = 그 주에 처음 등록 · 예정 = 그 주가 끝난 뒤 4주 안에 시작 · 진행 = 그 주에 열려 있고 다음 주에도 이어짐 · 종료 = 그 주에 끝남")


# 사용자 테스트 바로가기 (11/18 요청). .env / Secrets 로 바꿀 수 있고, 없으면 지금 쓰는 폼 주소
SURVEY_FORMS = {   # 버전: (참여자에게 보낼 주소, 폼 고치기). 1차 = 로그인 · 물어보기 없던 첫 버전, 2차 = 지금 (11/18 요청)
    "1차": ("https://docs.google.com/forms/d/e/1FAIpQLSe8ZKxd1bcF4jgTYwHgFdmXGsX5Y2PcGe9KTZTDLl6V_gzHpA/viewform",
            "https://docs.google.com/forms/d/1E53ZHq-zHC0qy4jfwwekTV-KrbsfU8PakrsJH77A8m8/edit"),
    "2차": ("https://docs.google.com/forms/d/e/1FAIpQLScp02W0zqeqYRwdMPW4D9Az-2hJny5sFDFkg0gRlnqvnF71mA/viewform",
            "https://docs.google.com/forms/d/1P1TZjlF-YR-80fa4s2-ABUFRJfiSU0b4aQo_raosceg/edit"),
}
N8N_URL = "http://localhost:5678"     # n8n 은 운영자 컴퓨터에서 돈다 (그 컴퓨터에서만 열림)


def _survey_links(sheet_id: str) -> None:
    """1차 · 2차 설문 폼(참여자에게 보낼 주소 · 폼 고치기) · 응답 시트 · n8n 바로가기 버튼."""
    for ver, (form, edit) in SURVEY_FORMS.items():
        with st.container(horizontal=True, key=f"adm_survey_links_{ver}", vertical_alignment="center"):
            st.link_button(f"{ver} 설문 폼 (참여자에게 보낼 주소)", form, icon=":material/assignment:",
                           type="primary" if ver == "2차" else "secondary")
            st.link_button(f"{ver} 폼 고치기", edit, icon=":material/edit_note:")
    with st.container(horizontal=True, key="adm_survey_links"):
        if sheet_id:
            st.link_button("응답 시트 (1차 · 2차 같이)", f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
                           icon=":material/table_view:")
        st.link_button("n8n 워크플로", os.getenv("N8N_URL") or N8N_URL, icon=":material/account_tree:")
    st.caption("n8n 은 운영자 컴퓨터(http://localhost:5678)에서 돌아서, 그 컴퓨터에서만 열려요. 테스트 날에는 n8n 을 켜 두세요.")


@st.cache_data(ttl=60, show_spinner=False)
def _survey_rows(sheet_id: str) -> tuple[list[dict], str]:
    """n8n 이 쌓은 구글 시트 '정리' 탭을 CSV 로 읽는다 (1분 기억). (줄들, 오류 글)."""
    import io
    import requests

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
    try:
        res = requests.get(url, params={"tqx": "out:csv", "sheet": "정리"}, timeout=10)
        if res.status_code != 200 or "text/csv" not in res.headers.get("content-type", ""):
            return [], "시트를 읽지 못했어요 (공유 설정이 '링크가 있는 모든 사용자 · 보기' 인지 확인해 주세요)."
        df = pd.read_csv(io.StringIO(res.content.decode("utf-8")), dtype=str).fillna("")
        return df.to_dict("records"), ""
    except Exception as exc:  # 네트워크 · 형식 오류 — 관리자 화면이 멈추지 않게 안내만
        return [], f"시트를 읽지 못했어요 ({type(exc).__name__}). 잠시 뒤 다시 열어 주세요."


def _admin_survey() -> None:
    """사용자 테스트 (11/18 요청): n8n 이 구글 폼 응답을 정리해 쌓은 '정리' 탭 → A(평소 방법)/B(ANI:WHERE) 비교 ·
    과제별 성공률 · 문제 정의(불편한 점 · 정보 출처) · 만족도 그래프 + 원본 표.
    시트 주소(번호)는 .env / Secrets 의 SURVEY_SHEET_ID. 숫자는 stats.survey_summary (n8n 메일과 같은 규칙)."""
    sheet_id = (os.getenv("SURVEY_SHEET_ID") or "").strip()
    _survey_links(sheet_id)
    if not sheet_id:
        st.info("설문 시트가 아직 연결되지 않았어요. `.env`(배포는 Streamlit Secrets)에 `SURVEY_SHEET_ID` 를 넣어 주세요 "
                "(구글 시트 주소의 /d/ 와 /edit 사이 글자). 만드는 법: automation/n8n/README.md", icon=":material/link_off:")
        return
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    c1.markdown('<div class="adm-panel-h">사용자 테스트 (n8n 설문)</div>', unsafe_allow_html=True)
    if c2.button("새로고침", icon=":material/refresh:", key="adm_survey_reload", width="stretch"):
        _survey_rows.clear()
    rows, err = _survey_rows(sheet_id)
    if err:
        st.warning(err, icon=":material/error:")
        return
    if not rows:
        st.info("아직 들어온 응답이 없어요. 참여자가 설문 폼을 내면 n8n 이 1분 안에 여기로 쌓아요.",
                icon=":material/hourglass_empty:")
        return
    view = st.segmented_control("보기", ["1차 → 2차 개선", "2차 자세히", "1차 자세히"], default="1차 → 2차 개선",
                                key="adm_survey_view", label_visibility="collapsed") or "1차 → 2차 개선"
    if view == "1차 → 2차 개선":
        _survey_improve(rows)
    else:
        ver = view[:2]
        sub = [r for r in rows if stats.survey_version(r) == ver]
        if not sub:
            st.info(f"{ver} 폼 응답이 아직 없어요.", icon=":material/hourglass_empty:")
        else:
            _survey_detail(sub)
    st.caption("구글 폼(1차 · 2차) → n8n(내 컴퓨터) → 구글 시트 '정리' 탭(버전 칸) → 여기. 이메일 · 이름 · 연락처는 받지 않고, "
               "자유 답변의 전화번호 · 이메일은 n8n 이 지워요.")


SV_COLORS = ["#A9B3B0", "#14B8A6"]     # 1차 회색 · 2차 포인트 민트


SV_GROUP_CSS = """<style>
[class*="st-key-svg_"] { background: #FAFDFC; }
[class*="st-key-svg_"] .sv-gh { font-size: .82rem; font-weight: 800; color: var(--accent-deep); margin-bottom: -6px; }
[class*="st-key-svg_"] [data-testid="stMetricValue"] { font-size: 1.55rem !important; }
[class*="st-key-svg_"] [data-testid="stMetricLabel"] p { font-size: .8rem !important; color: #5F6B67 !important; }
</style>"""


def _sv_groups(groups: list[tuple[str, list[tuple]]], key: str) -> None:
    """숫자 카드를 항목별 상자로 묶어 보여 준다 (11/18 요청: 한 줄에 다섯 개가 붙어 있어 보기 힘듦).
    groups = [(상자 제목, [(이름, 값, 변화 또는 None, 'normal'|'inverse'), ...]), ...] — 상자 폭은 카드 수에 비례."""
    st.markdown(SV_GROUP_CSS, unsafe_allow_html=True)
    cols = st.columns([max(1, len(items)) for _, items in groups], gap="small")
    for i, (col, (title, items)) in enumerate(zip(cols, groups)):
        with col, st.container(border=True, key=f"svg_{key}_{i}"):
            st.markdown(f'<div class="sv-gh">{escape(title)}</div>', unsafe_allow_html=True)
            for c, (label, value, delta, color) in zip(st.columns(len(items)), items):
                c.metric(label, value, delta, delta_color=color)


def _sv_fmt(v, unit: str = "") -> str:
    return "-" if v is None else f"{v:g}{unit}"


def _survey_improve(rows: list[dict]) -> None:
    """1차(로그인 · 물어보기 없던 첫 버전) → 2차(지금): 무엇이 나아지고 편해졌나 (11/18 요청). 숫자는 stats.survey_compare."""
    c = stats.survey_compare(rows)
    a, b, tgt = c["1차"], c["2차"], stats.SURVEY_TARGET
    if not a["응답자"] or not b["응답자"]:
        st.info(f"1차 응답 {a['응답자']}명 · 2차 응답 {b['응답자']}명이에요. 두 폼 모두 응답이 들어오면 여기서 1차 → 2차 를 비교해요. "
                "(지금은 '2차 자세히' · '1차 자세히' 에서 볼 수 있어요)", icon=":material/compare_arrows:")
        return

    def delta(x, y, unit):
        return None if x is None or y is None else f"{round(y - x, 1):+g}{unit}"

    # 1) 숫자 카드: 2차 값 + 1차 대비 변화
    _sv_groups([
        ("참여", [("1차", f"{a['응답자']}명", None, "normal"), ("2차", f"{b['응답자']}명", None, "normal")]),
        ("과제 성공률", [("1차", _sv_fmt(a["성공률"], "%"), None, "normal"),
                      ("2차", _sv_fmt(b["성공률"], "%"), delta(a["성공률"], b["성공률"], "%p"), "normal")]),
        ("질문 1 평균 시간", [("1차", _sv_fmt(a["질문1초"], "초"), None, "normal"),
                         ("2차", _sv_fmt(b["질문1초"], "초"), delta(a["질문1초"], b["질문1초"], "초"), "inverse")]),
        ("만족 · 의향 (2차, 1차 대비)", [("만족도 (5점)", _sv_fmt(b["만족도"]), delta(a["만족도"], b["만족도"], "점"), "normal"),
                                   ("다시 쓸 의향", _sv_fmt(b["다시쓸의향"], "%"),
                                    delta(a["다시쓸의향"], b["다시쓸의향"], "%p"), "normal")]),
    ], key="improve")
    ok_s = b["성공률"] is not None and b["성공률"] >= tgt["success"]
    ok_t = b["질문1초"] is not None and b["질문1초"] <= tgt["q1"]
    st.caption(f"초록 · 빨강 작은 숫자 = 1차 대비 변화. 2차 목표: 과제 성공률 {tgt['success']:g}% 이상 {'O' if ok_s else 'X'} · "
               f"질문 1 평균 {tgt['q1']:g}초 이하 {'O' if ok_t else 'X'}. 시간은 응답자가 고른 구간의 가운데 값(대략값)"
               + ("  ·  응답자가 적어 참고용이에요" if min(a["응답자"], b["응답자"]) < 10 else ""))

    # 2) 그래프
    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<div class="adm-panel-h">팝업 하나 찾는 시간 (초) · 평소 방법 → 1차 → 2차</div>', unsafe_allow_html=True)
        base = stats._avg([x for x in (a["평소초"], b["평소초"]) if x is not None])
        st.bar_chart(pd.DataFrame({"방법": ["① 평소 방법", "② 1차", "③ 2차"],
                                   "초": [base or 0, a["질문1초"] or 0, b["질문1초"] or 0]}),
                     x="방법", y="초", color="#14B8A6", horizontal=True, height=190, x_label="", y_label="", sort=False)
        st.markdown('<div class="adm-panel-h">과제별 성공률 (%) · 1차 vs 2차</div>', unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame([{"과제": f"{t} · {n}", **{v: c[v]["과제별"][t]["성공률"] or 0 for v in ("1차", "2차")}}
                                   for t, n in stats.SURVEY_TASKS.items()]),
                     x="과제", y=["1차", "2차"], color=SV_COLORS, stack=False, horizontal=True, height=280,
                     x_label="", y_label="", sort=False)
    with g2:
        st.markdown('<div class="adm-panel-h">과제별 평균 시간 (초, 해낸 사람) · 1차 vs 2차</div>', unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame([{"과제": f"{t} · {n}", **{v: c[v]["과제별"][t]["평균초"] or 0 for v in ("1차", "2차")}}
                                   for t, n in stats.SURVEY_TASKS.items()]),
                     x="과제", y=["1차", "2차"], color=SV_COLORS, stack=False, horizontal=True, height=280,
                     x_label="", y_label="", sort=False)
        st.markdown('<div class="adm-panel-h">만족도 분포 (명) · 1차 vs 2차</div>', unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame([{"점수": f"{i}점", **{v: c[v]["만족도분포"].get(str(i), 0) for v in ("1차", "2차")}}
                                   for i in range(1, 6)]),
                     x="점수", y=["1차", "2차"], color=SV_COLORS, stack=False, height=190, x_label="", y_label="", sort=False)

    # 3) 지표 표 (나아짐 / 그대로 / 나빠짐)
    st.markdown('<div class="adm-panel-h">무엇이 나아졌나 (1차 → 2차)</div>', unsafe_allow_html=True)
    table = []
    for name, x, y, unit, up, goal in c["지표"]:
        if x is None or y is None:
            verdict = "-"
        elif abs(y - x) < 1e-9:
            verdict = "그대로"
        else:
            verdict = "나아짐" if (y > x) == up else "나빠짐"
        table.append({"지표": name, "1차": _sv_fmt(x, unit), "2차": _sv_fmt(y, unit),
                      "변화": "-" if x is None or y is None else f"{round(y - x, 1):+g}{'%p' if unit == '%' else unit}",
                      "판정": verdict,
                      "목표": "-" if goal is None else (f"{goal:g}{unit} 이상" if up else f"{goal:g}{unit} 이하")})
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch", height=35 * (len(table) + 1) + 3)

    # 4) 같은 사람 (닉네임으로 묶인 1차 · 2차)
    same = c["같은 사람"]
    st.markdown('<div class="adm-panel-h">같은 사람이 1차 · 2차 둘 다 해 봤을 때 (닉네임으로 묶음)</div>', unsafe_allow_html=True)
    if not same["명"]:
        st.caption("1차 · 2차 모두 낸 사람이 아직 없어요 (1차 폼에는 2차 로그인 닉네임을 적게 안내해요).")
    else:
        k = st.columns(4)
        k[0].metric("두 번 다 한 사람", f"{same['명']}명")
        k[1].metric("질문 1 이 빨라진 사람", f"{same['빨라진 사람']} / {same['시간 잰 사람']}명")
        k[2].metric("평균 줄어든 시간", _sv_fmt(same["평균 줄어든 초"], "초"))
        k[3].metric("해낸 과제가 늘어난 사람", f"{same['더 해낸 사람']}명")
        with st.expander(f"사람별 ({same['명']}명)"):
            st.dataframe(pd.DataFrame(c["짝"]), hide_index=True, width="stretch")

    # 5) 막힌 곳 1차 · 2차 나란히 + 평소 불편한 점
    c1, c2 = st.columns(2)
    for col, v in ((c1, "1차"), (c2, "2차")):
        with col:
            st.markdown(f'<div class="adm-panel-h">{v} · 자주 막힌 곳</div>', unsafe_allow_html=True)
            st.markdown("\n".join(f"- {escape(bk)} — {n}번" for bk, n in c[v]["막힌곳"]) or "없어요.", unsafe_allow_html=True)
    pains: dict = {}
    for v in ("1차", "2차"):
        for p_, n in c[v]["불편한점"]:
            pains[p_] = pains.get(p_, 0) + n
    if pains:
        st.markdown('<div class="adm-panel-h">평소 불편한 점 (문제 정의 · 1차 · 2차 응답 합계)</div>', unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame(sorted(pains.items(), key=lambda kv: -kv[1]), columns=["불편한 점", "명"]),
                     x="불편한 점", y="명", color="#F2A33A", horizontal=True, height=240, x_label="", y_label="", sort="-명")


def _survey_detail(rows: list[dict]) -> None:
    """한 버전(1차 또는 2차)의 자세한 결과."""
    s = stats.survey_summary(rows)
    tgt = stats.SURVEY_TARGET
    fmt = _sv_fmt

    # 1) 숫자 카드 (A/B · 목표)
    _sv_groups([
        ("참여", [("응답자", f"{s['응답자']}명", None, "normal")]),
        ("팝업 하나 찾는 시간 (A/B)", [
            ("A · 평소 방법", fmt(s["평소초"], "초"), None, "normal"),
            ("B · ANI:WHERE", fmt(s["질문1초"], "초"),
             None if s["평소초"] is None or s["질문1초"] is None else f"{round(s['질문1초'] - s['평소초'], 1):+g}초", "inverse")]),
        ("과제", [("성공률 (목표 80% 이상)", fmt(s["성공률"], "%"), None, "normal")]),
        ("만족 · 의향", [("만족도 (5점)", fmt(s["만족도"]), None, "normal"),
                       ("평소보다 편함 (5점)", fmt(s["비교"]), None, "normal"),
                       ("다시 쓸 의향", fmt(s["다시쓸의향"], "%"), None, "normal")]),
    ], key="detail")
    ok_s = s["성공률"] is not None and s["성공률"] >= tgt["success"]
    ok_t = s["질문1초"] is not None and s["질문1초"] <= tgt["q1"]
    st.caption(f"목표 달성: 과제 성공률 {'O' if ok_s else 'X'} · 질문 1 평균 {tgt['q1']:g}초 이하 {'O' if ok_t else 'X'}"
               "  ·  A = 평소 방법(SNS · 커뮤니티 · 검색)으로 걸리던 시간(응답자가 고른 구간), B = ANI:WHERE 로 직접 해 본 시간"
               + ("  ·  응답자가 적어 참고용이에요" if s["응답자"] < 10 else ""))

    # 2) 그래프
    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<div class="adm-panel-h">A/B · 팝업 하나 찾는 시간 (초)</div>', unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame({"방법": ["평소 방법", "ANI:WHERE"], "초": [s["평소초"] or 0, s["질문1초"] or 0]}),
                     x="방법", y="초", color="#56C2A7", horizontal=True, height=180, x_label="", y_label="")
        st.markdown('<div class="adm-panel-h">과제별 성공률 (%)</div>', unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame({"과제": [f"{t} · {n}" for t, n in stats.SURVEY_TASKS.items()],
                                   "성공률": [s["과제별"][t]["성공률"] or 0 for t in stats.SURVEY_TASKS]}),
                     x="과제", y="성공률", color="#14B8A6", horizontal=True, height=220, x_label="", y_label="", sort=False)
    with g2:
        st.markdown('<div class="adm-panel-h">평소 불편한 점 (문제 정의 · 명)</div>', unsafe_allow_html=True)
        if s["불편한점"]:
            st.bar_chart(pd.DataFrame(s["불편한점"], columns=["불편한 점", "명"]), x="불편한 점", y="명", color="#F2A33A",
                         horizontal=True, height=240, x_label="", y_label="", sort="-명")
        st.markdown('<div class="adm-panel-h">평소 정보를 찾는 곳 (명)</div>', unsafe_allow_html=True)
        if s["정보출처"]:
            st.bar_chart(pd.DataFrame(s["정보출처"], columns=["출처", "명"]), x="출처", y="명", color="#A9C3EA",
                         horizontal=True, height=200, x_label="", y_label="", sort="-명")
    g3, g4 = st.columns(2)
    with g3:
        st.markdown('<div class="adm-panel-h">만족도 분포 (명)</div>', unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame({"점수": [f"{i}점" for i in range(1, 6)], "명": [s["만족도분포"].get(str(i), 0) for i in range(1, 6)]}),
                     x="점수", y="명", color="#9EDDCC", height=180, x_label="", y_label="", sort=False)
    with g4:
        st.markdown('<div class="adm-panel-h">팝업 방문 빈도 (명)</div>', unsafe_allow_html=True)
        if s["방문빈도"]:
            st.bar_chart(pd.DataFrame(s["방문빈도"], columns=["빈도", "명"]), x="빈도", y="명", color="#56C2A7",
                         height=180, x_label="", y_label="", sort=False)

    # 3) 표 · 글
    st.markdown('<div class="adm-panel-h">과제별</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"과제": f"{t} · {n}", "응답": s["과제별"][t]["명"], "성공률": fmt(s["과제별"][t]["성공률"], "%"),
                                "평균 시간(성공)": fmt(s["과제별"][t]["평균초"], "초"),
                                "해냈어요 / 어렵게 / 못 했어요": " / ".join(str(s["과제별"][t]["결과"].get(k, 0))
                                                                     for k in ("해냈어요", "어렵게 해냈어요", "못 했어요"))}
                               for t, n in stats.SURVEY_TASKS.items()]), hide_index=True, width="stretch")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="adm-panel-h">자주 막힌 곳</div>', unsafe_allow_html=True)
        st.markdown("\n".join(f"- {b} — {n}번" for b, n in s["막힌곳"]) or "아직 없어요.")
    with c2:
        st.markdown('<div class="adm-panel-h">바라는 점</div>', unsafe_allow_html=True)
        st.markdown("\n".join(f"- {escape(w)}" for w in s["바라는점"][:10]) or "아직 없어요.", unsafe_allow_html=True)
    with st.expander(f"원본 응답 ({len(rows)}줄 · 한 사람 = 질문 1~4 네 줄)"):
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


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


# 관리자 바로가기. 예약 작업 주소는 계정마다 달라서 .env / Streamlit Secrets 의 ADMIN_ROUTINE_URL (없으면 예약 작업 목록)
ADMIN_ROUTINE_URL = os.getenv("ADMIN_ROUTINE_URL") or "https://claude.ai/code/routines"
def _supabase_dashboard_url() -> str:
    """Supabase 데이터(표 편집기) 바로가기. 프로젝트 번호는 SUPABASE_URL(https://<번호>.supabase.co)에서 읽는다 (11/18 요청:
    Notion 트래커 대신 실제 앱 데이터가 있는 Supabase 를 바로 열기). 설정이 없으면 대시보드 첫 화면."""
    host = urlparse(os.getenv("SUPABASE_URL", "")).hostname or ""
    ref = host.split(".")[0] if host.endswith(".supabase.co") else ""
    return f"https://supabase.com/dashboard/project/{ref}/editor" if ref else "https://supabase.com/dashboard/projects"
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
    # 바로가기: 매일 수집을 돌리는 Claude 예약 작업 · 앱 데이터가 있는 Supabase 표 (11/18 요청: Notion 트래커 → Supabase)
    with st.container(horizontal=True, horizontal_alignment="right", key="adm_links"):
        st.link_button("Claude 예약 작업 (매일 08:00 수집)", ADMIN_ROUTINE_URL, icon=":material/schedule:")
        st.link_button("Supabase 데이터 보기", _supabase_dashboard_url(), icon=":material/database:")
        # 앱은 Supabase 를 처음에 한 번 불러와 기억한다 (매일 08:45 · 앱에서 저장할 때 자동 갱신).
        # Supabase 화면에서 직접 고쳤을 때만 이 버튼으로 바로 새로 불러온다
        if st.button("데이터 새로 불러오기", icon=":material/refresh:", key="adm_refresh"):
            storage_mod.refresh_all()
            st.session_state["flash"] = ("Supabase 에서 새로 불러왔어요.", ":material/check_circle:")
            st.rerun()
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
    elif tab == "survey":
        _admin_survey()
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
  height: calc(100vh - var(--apn-top, 172px) - 112px) !important; max-height: calc(100vh - var(--apn-top, 172px) - 16px);
  flex: 0 0 auto !important; }   /* Streamlit 기본 flex:1 1 0% 이면 높이가 무시돼 대화창이 내용만큼 줄어든다 */
.st-key-ask_panel > * { flex: 0 0 auto; }
.apn-num { color: var(--accent); font-weight: 800; }
.apn-links { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.apn-link { display: inline-flex; align-items: center; gap: 4px; width: fit-content; font-size: .8rem; font-weight: 700;
  color: var(--accent-deep) !important; background: #fff; border: 1px solid var(--accent); border-radius: 999px;
  padding: 2px 10px; text-decoration: none !important; }
.apn-link .mi { font-size: .95rem; color: var(--accent-deep); }
/* 답변 속 굵은 글자(작품·지역·날짜, 닉네임, 건수 등)는 모두 포인트 민트로 (11/18 요청) */
.apn-bot b, .apn-bot strong { color: var(--accent); font-weight: 800; }
/* 페이지 맨 아래까지 내려도 물어보기 창이 같은 자리에 붙어 있게: 창이 든 줄이 페이지 끝까지 닿도록 아래 기본 여백(96px)을 줄인다 (11/18 요청) */
@media (min-width: 641px) { [data-testid="stMainBlockContainer"]:has(.st-key-ask_panel) { padding-bottom: 19px !important; } }
.st-key-ask_panel > *:has(.st-key-apn_log), .st-key-ask_panel > .st-key-apn_log {
  flex: 1 1 auto !important; min-height: 0 !important; display: flex; flex-direction: column; }
/* 대화창을 따로 다시 그리는 칸(fragment)으로 바꾸며 감싸는 상자가 한 겹 늘었다 (11/18):
   대화 기록까지 이어지는 상자를 모두 세로 flex 로 → 대화 기록이 남는 높이만 쓰고, 추천 칩·입력칸은 늘 보인다 */
.st-key-ask_panel :has(.st-key-apn_log):not(.st-key-apn_log) { display: flex !important; flex-direction: column !important;
  flex: 1 1 auto !important; min-height: 0 !important; height: auto !important; }
.st-key-ask_panel :has(.st-key-apn_log):not(.st-key-apn_log) > :not(:has(.st-key-apn_log)):not(.st-key-apn_log) {
  flex: 0 0 auto !important; }
.st-key-apn_log { flex: 1 1 auto !important; height: auto !important; max-height: none !important;
  min-height: 90px !important; overflow-y: auto !important; }
.st-key-ask_panel { border: 1.5px solid #E3E8E6; border-radius: 16px; background: #fff;
  padding: 0 !important; gap: 0 !important; overflow: hidden; box-shadow: 0 4px 18px rgba(38,48,45,.06); }
.st-key-ask_panel > div { padding-left: 14px; padding-right: 14px; }
.apn-head { display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  padding: 12px 0 10px; }
/* 제목 줄: 포인트 색, 위아래 적당한 여백. 스크롤한 대화가 제목 밑으로 비쳐 겹치지 않게 흰 바탕을 깔고 위로 올린다 */
.st-key-ask_panel > div:has(.apn-head), .st-key-ask_panel [data-testid="stElementContainer"]:has(.apn-head) {
  position: relative; z-index: 2; background: #fff; margin-bottom: 0 !important; }
.st-key-ask_panel [data-testid="stMarkdownContainer"]:has(.apn-head) { margin-bottom: 0 !important; }
.apn-title { font-family: "Jua", sans-serif; font-size: 1.25rem; color: var(--accent-deep, #0d9488); }
.apn-sub { color: #9AA5A1; font-size: .78rem; white-space: nowrap; }
.apn-who { color: #6B7672; font-size: .78rem; margin: 10px 0 4px; }
.apn-row { display: flex; align-items: flex-start; gap: 8px; margin: 12px 0 4px; }
.apn-ava { width: 38px; height: 38px; flex: 0 0 38px; border-radius: 50%; border: 1.5px solid #CDEDE3; background: #EAF8F3; }
.apn-col { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.apn-name { color: #6B7672; font-size: .74rem; font-weight: 700; }
.apn-exbox { margin-top: 8px; border: 1.5px solid var(--accent, #14b8a6); background: #E6FBF7; border-radius: 12px;
  padding: 8px 10px; display: flex; flex-wrap: wrap; gap: 5px; }
.apn-exbox b { width: 100%; font-size: .74rem; color: var(--accent-deep, #0d9488); margin-bottom: 1px; }
.apn-ex { font-size: .74rem; line-height: 1.35; color: #0F5E57; background: #fff; border: 1px solid #A7E6D8;
  border-radius: 999px; padding: 2px 9px; }
.apn-bot { background: #EEF1F0; border: 0; border-radius: 4px 18px 18px 18px; padding: 10px 14px;
  color: #26302D; font-size: .9rem; line-height: 1.6; word-break: keep-all; align-self: flex-start; }
/* 찾은 팝업 카드는 말풍선과 같은 줄에서 시작 (캐릭터 폭만큼 들여쓰기) */
[class*="st-key-apn_card_"], [class*="st-key-apd_card_"] { margin-left: 46px !important; width: calc(100% - 46px) !important;
  max-width: calc(100% - 46px) !important; min-width: 0 !important; }
.apn-me { display: flex; justify-content: flex-end; margin: 10px 0 2px; }
.apn-me span { background: var(--accent, #56C2A7); color: #fff; border-radius: 12px 12px 2px 12px; padding: 8px 12px;
  font-size: .9rem; max-width: 85%; word-break: keep-all; }
.apn-badge { display: inline-block; margin-top: 6px; padding: 1px 8px; border-radius: 999px; font-size: .7rem;
  font-weight: 700; border: 1px solid #9EDDCC; color: #2E9C82; background: #fff; }
.apn-badge.fb { border-color: #C9D1CE; color: #6B7672; }
/* 찾은 팝업 카드: 왼쪽 포스터 · 오른쪽 작품(민트) · 매장(굵게) · 주소(회색) · 기간(민트 굵게) */
[class*="st-key-apn_card_"], [class*="st-key-apd_card_"] { position: relative; gap: 0 !important; margin: 6px 0; }
.apc { display: flex; gap: 10px; align-items: center; background: #E9F7F2; border-radius: 14px; padding: 8px;
  min-width: 0; max-width: 100%; box-sizing: border-box; overflow: hidden;
  transition: background .12s; }
[class*="st-key-apn_card_"]:hover .apc, [class*="st-key-apd_card_"]:hover .apc { background: #DCF2EA; }
.apc img { width: 54px; height: 72px; flex: 0 0 54px; object-fit: cover; border-radius: 7px; background: #fff; }
.apc-txt { min-width: 0; display: flex; flex-direction: column; justify-content: center; gap: 2px; }
.apc-work { font-family: "Jua", sans-serif; font-size: 1rem; line-height: 1.25; color: #2E9C82;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.apc-cafe { font-weight: 800; font-size: .82rem; color: #26302D; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.apc-addr { color: #7A8582; font-size: .74rem; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 1;
  -webkit-box-orient: vertical; overflow: hidden; }
.apc-date { color: #2E9C82; font-weight: 800; font-size: .78rem; margin-top: 1px; }
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
/* 추천 질문 칩 글자를 한 단계 작게 (11/18 요청) — 버튼 안 p 가 자기 글자 크기를 따로 가져서 p 에 준다 */
.st-key-apn_chips button p, .st-key-apd_chips button p { font-size: .78rem !important; line-height: 1.3; display: block; }
/* 글자를 담는 칸도 같은 글자 크기·줄 높이로 → 칩 안에서 위아래 가운데 */
.st-key-apn_chips button [data-testid="stMarkdownContainer"], .st-key-apd_chips button [data-testid="stMarkdownContainer"] {
  font-size: .78rem !important; line-height: 1.3 !important; }
.st-key-apn_chips button, .st-key-apd_chips button { padding: 3px 10px !important; }
.st-key-apn_form [data-testid="stForm"], .st-key-apd_form [data-testid="stForm"] { padding: 10px 0 14px; }
/* 추천 칩 ↔ 입력칸 간격을 반으로 (28px → 14px, 11/18 요청) */
.st-key-apn_form [data-testid="stForm"], .st-key-apd_form [data-testid="stForm"] { padding-top: 0 !important; }
.st-key-apn_form, .st-key-apd_form { margin-top: -4px !important; }
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
            chat.append({"role": "bot", "text": text, "ids": [], "badge": "규칙 기반 대체",
                         "guide": res.query.intent == "unknown", "links": list(res.links)})
        else:
            limit = min(len(res.hits), ask.RANK_MAX) if res.query.intent in ("blog_rank", "review_rank", "rating_rank") else 5
            used = [i for i in res.used_ids] or [str(h.row.get("entry_id")) for h in res.hits[:limit]]
            rows = {str(h.row.get("entry_id")): h.row for h in res.hits}
            cards = [_ask_card(i, rows[i], res.distances.get(i)) for i in used[:limit] if i in rows]
            # 검색 질문은 '네, N건 있어요' 를 말풍선으로 (규칙(의도) 질문은 그 안내 문장)
            say = res.summary if not res.query.intent else (res.text or "")
            all_ids = [str(h.row.get("entry_id")) for h in res.hits]
            more = {"ids": all_ids, "label": q[:40]} if len(all_ids) > len(cards) else None
            chat.append({"role": "bot", "text": res.text, "badge": res.badge, "ids": cards, "say": say, "links": list(res.links),
                         "more": more,
                         "head": "" if not res.query.intent else (res.summary or _ASK_HEADS.get(res.query.intent, ""))
                         # 내 주변: '· 내 위치에서 가까운 순 N건 팝업이에요' 처럼 몇 건인지 붙인다 (11/18 요청)
                         + (f" {len(res.hits)}건 팝업이에요" if res.query.intent == "near" and not res.summary else "")})
            _ask_log(q)
    del chat[:-20]                 # 너무 길어지지 않게 최근 20개만


_ASK_HEADS = {"blog_rank": "블로그 후기 수 순", "review_rank": "리뷰 수 순", "rating_rank": "별점 순",
              "near": "내 위치에서 가까운 순", "recommend": "추천 (별점 → 리뷰 많은 순)", "ending": "곧 끝나는 순",
              "upcoming": "곧 열리는 순", "popular": "북마크 많은 순", "reviewed": "후기 많은 순"}
_ASK_LOG = Path(__file__).resolve().parent / "logs" / "ask_questions.jsonl"
ASK_DEFAULT_CHIPS = ["내 주변 가까운 팝업", "팝업 추천해줘", "지금 진행 중인 서울 팝업", "곧 끝나는 팝업", "이번 주말 성수 팝업"]


@st.cache_data(ttl=3600, show_spinner=False)
def _region_of(lat: float, lng: float) -> str:
    """좌표 → '서울 마포구 서교동' (카카오 로컬). 못 받으면 빈 문자열 → 물어보기 규칙이 가까운 팝업 지역으로 어림."""
    return geo.region_of(round(lat, 4), round(lng, 4))


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
    me = _member()
    return {"loc": _my_loc(), "ratings": ratings, "favs": favorite.counts(favs.current_rows()),
            # 나에 대한 질문 (11/18): '내 닉네임 뭐야?' · '내 북마크' · '지금 내 위치 어디야?'
            "nick": _nick_only(auth.display_name(me)) if me else "",
            "my_favs": sorted(favorite.mine(favs.current_rows(), _fav_user())) if me else None,
            "region_of": _region_of,
            "review_counts": review.counts(reviews.current_rows()),      # 리뷰 많은·적은 순 (11/18)
            "blog_totals": _blog_totals_for}                              # 블로그 후기 많은·적은 순 (부를 때만 셈)


@st.cache_data(ttl=86400, show_spinner=False)
def _blog_totals(keys: tuple) -> dict:
    """팝업별 네이버 블로그 글 수 (하루 동안 기억). keys = ((entry_id, work, cafe_name, address), …). 한도 안에서만 부른다."""
    from concurrent.futures import ThreadPoolExecutor
    def one(k):
        return k[0], blog.total({"work": k[1], "cafe_name": k[2], "address": k[3]}, usage=api_usage)
    with ThreadPoolExecutor(max_workers=6) as ex:
        return {eid: n for eid, n in ex.map(one, keys) if n is not None}


def _blog_totals_for(rows: list[dict]) -> dict:
    if not blog.enabled():
        return {}
    keys = tuple(sorted((str(r.get("entry_id")), str(r.get("work") or ""), str(r.get("cafe_name") or ""),
                         str(r.get("address") or "")) for r in rows))
    try:
        return _blog_totals(keys)
    except Exception:
        return {}


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


def _ask_show_all(more: dict) -> None:
    """물어보기 답의 팝업 전부를 리스트로 보기에 (다른 검색 조건은 풀고, 위에 '물어보기 결과' 표시 · 해제 버튼)."""
    _reset_filters()
    _gnb_go("list")
    st.session_state["ask_only"] = {"ids": list(more.get("ids") or []), "label": str(more.get("label") or "")}
    st.session_state["list_n"] = LIST_PAGE


def _ask_panel_open(cafe_id: str) -> None:
    st.session_state["selected"] = str(cafe_id)
    st.session_state["scroll_top"] = True


ASK_AVATAR = "app/static/ask_avatar.png"      # 로고의 토끼를 동그랗게 자른 그림


_ASK_SPLIT = re.compile(r"(<[^>]+>|&[#\w]+;)")       # 태그·글자 참조(&#x27; 등)는 건드리지 않는다
_ASK_NUM = re.compile(r"\d[\d,./:]*\d|\d")   # 1,234 · 12/04 · 11:39 는 한 덩어리


def _ask_nums(html: str) -> str:
    """답변 속 숫자만 굵은 포인트 민트로 (11/18 요청). 태그 안·글자 참조 안의 숫자는 그대로."""
    return "".join(part if _ASK_SPLIT.fullmatch(part) else _ASK_NUM.sub(r'<b class="apn-num">\g<0></b>', part)
                   for part in _ASK_SPLIT.split(html))


def _ask_links(links) -> str:
    """답 아래 바로가기 (사용법 안내 페이지 등). 새 탭으로 열어 대화는 그대로 둔다."""
    out = "".join(f'<a class="apn-link" href="{escape(str(u))}" target="_blank">{_mi("open_in_new")}{escape(str(t))}</a>'
                  for t, u in (links or []))
    return f'<div class="apn-links">{out}</div>' if out else ""


def _guide_head() -> str:
    """못 알아들음 안내: '작품 이름 · 장소 · 날짜' 를 굵은 포인트 색으로 (11/18 요청, .apn-bot b)."""
    key = "작품 이름 · 장소 · 날짜"
    return escape(ask.GUIDE_HEAD).replace(key, f"<b>{key}</b>", 1)


def _ask_bot(html: str) -> str:
    """ANI:WHERE 말풍선: 왼쪽에 동그란 로고 캐릭터, 오른쪽에 둥근 회색 말풍선 (11/18 요청)."""
    html = _ask_nums(html)
    return (f'<div class="apn-row"><img class="apn-ava" src="{ASK_AVATAR}" alt="ANI:WHERE">'
            f'<div class="apn-col"><div class="apn-name">ANI:WHERE</div><div class="apn-bot">{html}</div></div></div>')


def _ask_chat_body(prefix: str, log_height: int, in_dialog: bool = False) -> None:
    """대화 기록 · 예시 칩 · 입력칸. PC 옆 대화창(apn)과 모바일 팝업(apd)이 같은 기록(ask_chat)을 쓴다."""
    with st.container(height=log_height, border=False, key=f"{prefix}_log"):
        # 첫 인사: 회원이면 닉네임을 불러 준다 (손님은 이름 없이, 11/18 요청)
        me = _member()
        # 닉네임 속 숫자는 '답변 숫자 민트' 에 걸리지 않게 글자 참조(&#57;)로 바꿔 둔다
        nick = "".join(f"&#{ord(c)};" if c.isdigit() else c for c in escape(str((me or {}).get("nickname") or "")))
        who = f' <b>{nick}</b>님' if nick else ""
        st.markdown(_ask_bot(f'안녕하세요{who} 궁금하신 팝업에서 찾아 드릴게요!<br><b>작품 · 지역 · 날짜</b>로 물어보면 '
                             '더 정확하게 찾을 수 있어요!'), unsafe_allow_html=True)
        for n, m in enumerate(st.session_state.get("ask_chat", [])):
            if m["role"] == "me":
                st.markdown(f'<div class="apn-me"><span>{escape(m["text"])}</span></div>', unsafe_allow_html=True)
                continue
            # 대화창에서는 'AI 산출 / 규칙 기반 대체' 배지를 보이지 않는다 (사용자 요청 11/18). /ask 화면에는 남아 있다
            # 찾은 팝업이 있으면 요약 문장(회색 상자)은 아래 버튼과 겹쳐서 숨기고 'N곳' 만 (사용자 요청 11/18)
            if m.get("ids"):
                head = f' · {escape(m["head"])}' if m.get("head") else ""
                body = escape(m["say"]) + head if m.get("say") else f'찾은 팝업 <b>{len(m["ids"])}곳</b>{head}'
                st.markdown(_ask_bot(body), unsafe_allow_html=True)
            else:
                if m.get("guide"):           # 못 알아들음: 안내 한 줄 + 예시는 작은 민트 테두리 상자 (11/18 요청)
                    ex = "".join(f'<span class="apn-ex">{escape(x)}</span>' for x in ask.GUIDE_EXAMPLES)
                    st.markdown(_ask_bot(f'{_guide_head()}<div class="apn-exbox"><b>이렇게 물어보세요</b>{ex}</div>'),
                                unsafe_allow_html=True)
                else:
                    st.markdown(_ask_bot(escape(m["text"]).replace(chr(10), "<br>") + _ask_links(m.get("links"))),
                                unsafe_allow_html=True)
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
                        # 대화창은 따로 다시 그려지는 칸(fragment)이라, 상세로 갈 때만 화면 전체를 다시 그린다
                        if st.button(f"{card['work']} 상세 보기", key=key):
                            _ask_panel_open(cid)
                            st.rerun(scope="app")
            more = m.get("more")
            if more and m.get("ids"):
                # 카드는 5건까지만 → 나머지는 리스트로 보기에서 다 (11/18 요청)
                with st.container(key=f"{prefix}_more_{n}"):
                    # 조건 바꾸기는 콜백에서 (입력칸이 그려지기 전에 돌아야 값을 바꿀 수 있다), 그다음 앱 전체를 다시 그린다
                    if st.button(f"{len(more['ids']) - len(m['ids'])}건 더보기 · 리스트로 보기", icon=":material/add:",
                                 key=f"{prefix}_morebtn_{n}", width="stretch", on_click=_ask_show_all, args=(more,)):
                        st.rerun() if in_dialog else st.rerun(scope="app")
    # 새 답이 생기면 대화창을 마지막 대화의 처음(방금 한 질문)이 맨 위에 오게 내린다 (11/18 요청). 대화 수가 바뀔 때만
    n_chat = len(st.session_state.get("ask_chat", []))
    # 지도 ↔ 리스트로 옮겨 대화창을 새로 그릴 때도 마지막 대화로 (11/18 요청). 같은 화면에서 대화 수가 그대로면
    # 같은 내용의 스크립트라 다시 실행되지 않아, 읽던 자리가 튀지 않는다
    if True:
        components.html(
            "<script>(function(){const d=window.parent.document;let t=0;"
            "const go=()=>{const box=d.querySelector('.st-key-" + prefix + "_log');if(!box)return;"
            "const mark=[...box.querySelectorAll('.apn-me')].pop()||[...box.querySelectorAll('.apn-row')].pop();"
            "[box,...box.querySelectorAll('*')].forEach(e=>{const o=getComputedStyle(e).overflowY;"
            "if((o==='auto'||o==='scroll')&&e.scrollHeight>e.clientHeight+4){"
            "e.scrollTop=mark?e.scrollTop+mark.getBoundingClientRect().top-e.getBoundingClientRect().top-6:e.scrollHeight;}});};"
            "const iv=setInterval(()=>{go();if(++t>12)clearInterval(iv);},150);})();</script>"
            f"<!-- {prefix} {n_chat} -->", height=0)          # 내용이 같으면 다시 실행되지 않아서 번호를 붙인다
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
    _ask_panel_live()


@st.fragment
def _ask_panel_live() -> None:
    """질문을 보내면 대화창만 다시 그린다 (11/18: 화면 전체가 다시 그려져 느렸음). 카드의 '상세 보기'만 전체를 다시 그림."""
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
    "guide": st.Page(page_guide, title="사용자 튜토리얼 · ANI:WHERE", icon=":material/help:", url_path="guide"),
    "design": st.Page(page_design, title="디자인 시스템 · ANI:WHERE", icon=":material/palette:", url_path="design"),
}
# 손님이면(방금 로그아웃한 경우는 빼고) 브라우저의 로그인 쿠키를 읽어 서버로 넘겨주는 부품을 둔다 (11/18 배포 로그인 유지)
if not st.session_state.get("member_key") and not st.session_state.get("_logged_out"):
    cookie_bridge.mount(auth.COOKIE)
try:
    st.navigation(list(PAGES.values()), position="hidden").run()
    _footer()          # 바닥글은 모든 페이지 맨 아래에 (11/18 요청)
except StorageWriteError as exc:
    # Supabase 가 쓰기를 거절함 (RLS: 남의 리뷰 수정·민감정보·동시 수정 충돌, 또는 연결 끊김). 화면이 멈추지 않게 안내만
    st.error("저장하지 못했어요. 잠시 뒤 다시 시도해 주세요. 내가 쓴 글이 아니거나 개인정보가 들어 있으면 저장되지 않아요.",
             icon=":material/error:")
    st.caption(f"자세한 이유: {str(exc)[:200]}")
