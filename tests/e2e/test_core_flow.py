"""ANI:WHERE 핵심 흐름 E2E 테스트 (Playwright).

목록 → 검색/필터 → 상세 → 북마크·캘린더 → 민감정보 차단 → 모바일 폭.
앱은 conftest 가 data/ 임시 복사본으로 띄운다. 진짜 data/*.json 은 바뀌지 않는다.
"""
from __future__ import annotations

import json
import re
from datetime import date

from playwright.sync_api import Page, expect

CARD = '[class*="st-key-card_w_"]'          # 리스트 전체보기 카드 (st.container key=card_w_<id>)
LONG = 30_000                               # 첫 화면은 지도·포스터를 그리느라 느리다


# ------------------------------------------------------------------ 도움 함수
def open_list(page: Page, url: str) -> int:
    """첫 화면(리스트)을 열고 카드가 다 그려질 때까지 기다린 뒤 카드 수를 돌려준다."""
    page.goto(url + "/")
    expect(page.locator(CARD).first).to_be_visible(timeout=LONG)
    wait_idle(page)
    return page.locator(CARD).count()


def wait_idle(page: Page) -> None:
    """Streamlit 이 다시 그리기를 마칠 때까지 (오른쪽 위 '실행 중' 표시가 사라질 때까지)."""
    page.wait_for_timeout(300)
    expect(page.locator('[data-testid="stStatusWidget"]')).to_have_count(0, timeout=LONG)


def current_cafes(data_dir) -> list[dict]:
    """임시 data/ 의 카페 중 지금 목록에 나올 것(최신 기록, 삭제 안 됨, 아직 안 끝남)."""
    latest: dict[str, dict] = {}
    for r in json.loads((data_dir / "cafes.json").read_text(encoding="utf-8")):
        eid = str(r["entry_id"])
        if eid not in latest or int(r.get("revision", 0)) >= int(latest[eid].get("revision", 0)):
            latest[eid] = r
    today = date.today().isoformat()
    return [r for r in latest.values()
            if r.get("status") != "deleted" and str(r.get("end_date", ""))[:10] >= today]


def pick_cafe(data_dir, with_links: bool = False) -> dict:
    rows = [r for r in current_cafes(data_dir) if not with_links or str(r.get("links") or "").strip()]
    assert rows, "테스트에 쓸 카페가 임시 데이터에 없습니다"
    return rows[0]


def open_detail(page: Page, eid: str) -> None:
    """카드 전체를 덮는 '자세히 보기' 버튼을 눌러 상세를 연다."""
    page.locator(f".st-key-open_{eid} button").click(force=True)
    expect(page.get_by_role("button", name=re.compile("리스트로 돌아가기"))).to_be_visible(timeout=LONG)
    wait_idle(page)


# ------------------------------------------------------------------ 1. 목록
def test_1_목록이_뜬다(page: Page, app_url):
    n = open_list(page, app_url)
    assert n > 0, "팝업 카드가 하나도 없습니다"
    # 머리글 '팝업 카페 N곳' 의 숫자와 실제 카드 수가 같아야 한다
    expect(page.get_by_text(re.compile(rf"팝업 카페\s*{n}\s*곳"))).to_be_visible()


# ------------------------------------------------------------------ 2. 검색/필터
def test_2_검색으로_좁혀지고_없으면_안내가_뜬다(page: Page, app_url, data_dir):
    total = open_list(page, app_url)
    target = pick_cafe(data_dir)
    word = str(target["work"])
    box = page.get_by_role("textbox", name="검색")
    box.fill(word)
    box.press("Enter")
    wait_idle(page)
    expect(page.locator(f".st-key-card_w_{target['entry_id']}")).to_be_visible(timeout=LONG)
    found = page.locator(CARD).count()
    assert 0 < found <= total
    assert found < total or total == 1, f"검색해도 카드 수가 그대로입니다 ({found}/{total})"

    box.fill("zzqx없는작품9876")
    box.press("Enter")
    wait_idle(page)
    expect(page.get_by_text("조건에 맞는 카페가 없습니다")).to_be_visible(timeout=LONG)
    assert page.locator(CARD).count() == 0
    # 빈 표(dataframe)가 아니라 안내 문구여야 한다
    assert page.locator('[data-testid="stDataFrame"], [data-testid="stTable"]').count() == 0


# ------------------------------------------------------------------ 3. 상세
def test_3_카드를_누르면_상세가_열리고_돌아올_수_있다(page: Page, app_url, data_dir):
    open_list(page, app_url)
    target = pick_cafe(data_dir, with_links=True)
    open_detail(page, target["entry_id"])
    expect(page.locator(".dtitle")).to_have_text(str(target["work"]))
    expect(page.get_by_text("방문 전 확인", exact=True)).to_be_visible()
    expect(page.get_by_text("참고 웹사이트", exact=True).first).to_be_visible()

    page.get_by_role("button", name=re.compile("리스트로 돌아가기")).click()
    wait_idle(page)
    expect(page.locator(CARD).first).to_be_visible(timeout=LONG)
    expect(page.locator(".dtitle")).to_have_count(0)


# ------------------------------------------------------------------ 4. 북마크 → 캘린더
def test_4_북마크하면_내_캘린더에_보인다(page: Page, app_url, data_dir):
    open_list(page, app_url)
    # 아직 북마크하지 않은 카드 하나
    target = next((r for r in current_cafes(data_dir)
                   if page.locator(f".st-key-fav_off_w_{r['entry_id']}").count()), None)
    assert target, "북마크하지 않은 카드가 없습니다"
    eid, work = target["entry_id"], str(target["work"])

    page.locator(f".st-key-fav_off_w_{eid} button").click()
    expect(page.locator(f".st-key-fav_on_w_{eid}")).to_be_visible(timeout=LONG)
    wait_idle(page)

    try:
        page.goto(app_url + "/calendar")
        expect(page.get_by_text("내 캘린더", exact=True).first).to_be_visible(timeout=LONG)
        wait_idle(page)
        # 곧 있는 팝업 목록(또는 달력 막대)에 이 팝업이 들어 있어야 한다
        expect(page.locator(".up-name", has_text=work).first).to_be_attached(timeout=LONG)
        expect(page.locator(".cal-bar", has_text=work).first).to_be_attached()
    finally:
        # 상태 되돌리기: 북마크 해제
        open_list(page, app_url)
        page.locator(f".st-key-fav_on_w_{eid} button").click()
        expect(page.locator(f".st-key-fav_off_w_{eid}")).to_be_visible(timeout=LONG)
        wait_idle(page)

    page.goto(app_url + "/calendar")
    expect(page.get_by_text("내 캘린더", exact=True).first).to_be_visible(timeout=LONG)
    wait_idle(page)
    expect(page.locator(".up-name", has_text=work)).to_have_count(0)


# ------------------------------------------------------------------ 5. 안정성 (민감정보 차단)
def test_5_리뷰에_전화번호를_넣으면_막힌다(page: Page, app_url, data_dir):
    before = (data_dir / "reviews.json").read_text(encoding="utf-8")
    open_list(page, app_url)
    target = pick_cafe(data_dir)
    open_detail(page, target["entry_id"])

    body = page.get_by_placeholder(re.compile("다녀온 후기나 기대하는 점")).first
    body.scroll_into_view_if_needed()
    body.fill("대기 줄 길어요. 문의는 010-1234-5678 로 주세요")
    body.press("Tab")                  # 칸을 벗어나야 값이 서버로 넘어간다
    wait_idle(page)

    expect(page.get_by_text(re.compile(r"민감한 개인정보\(.*전화번호.*\)는 입력할 수 없습니다"))).to_be_visible(timeout=LONG)
    send = page.get_by_role("button", name="리뷰 등록")
    expect(send).to_be_disabled()
    send.click(force=True)             # 눌러도 저장되지 않아야 한다
    wait_idle(page)
    assert (data_dir / "reviews.json").read_text(encoding="utf-8") == before, "리뷰 저장소가 바뀌었습니다"


# ------------------------------------------------------------------ 6. 모바일 폭
def test_6_모바일_390px에서_가로_스크롤이_없다(mobile_page: Page, app_url):
    n = open_list(mobile_page, app_url)
    assert n > 0
    mobile_page.wait_for_timeout(1000)
    sw, cw = mobile_page.evaluate(
        "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    assert sw <= cw + 1, f"가로 스크롤이 생깁니다 (내용 폭 {sw}px > 화면 {cw}px)"
    # 첫 카드가 화면 폭 안에 들어와야 한다
    box = mobile_page.locator(CARD).first.bounding_box()
    assert box and box["x"] >= 0 and box["x"] + box["width"] <= cw + 1
