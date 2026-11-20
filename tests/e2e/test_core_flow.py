"""ANI:WHERE 핵심 흐름 E2E 테스트 (Playwright).

목록 → 검색/필터 → 상세 → 북마크·캘린더 → 민감정보 차단 → 모바일 폭.
앱은 conftest 가 data/ 임시 복사본으로 띄운다. 진짜 data/*.json 은 바뀌지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path
import os
import re
from datetime import date

from playwright.sync_api import Page, expect

CARD = '[class*="st-key-card_w_"]'          # 리스트 전체보기 카드 (st.container key=card_w_<id>)
LONG = 30_000                               # 첫 화면은 지도·포스터를 그리느라 느리다


# ------------------------------------------------------------------ 도움 함수
def open_list(page: Page, url: str) -> int:
    """첫 화면(홈)을 열고 '리스트로 보기' 탭으로 가서, 카드가 다 그려질 때까지 기다린 뒤 카드 수를 돌려준다.
    (11/18: 새로 열면 첫 화면은 늘 홈)"""
    page.goto(url + "/")
    expect(page.locator(".st-key-home")).to_be_visible(timeout=LONG)
    wait_idle(page)
    page.locator('[class*="st-key-gnbtab_"][class*="list"] button').click()
    expect(page.locator(CARD).first).to_be_visible(timeout=LONG)
    wait_idle(page)
    return page.locator(CARD).count()


def sign_up(page: Page, url: str) -> None:
    """아이디로 새로 가입해 로그인한다 (북마크·리뷰는 회원만, 11/18). 임시 데이터에만 쌓인다."""
    import uuid
    page.goto(url + "/login")
    wait_idle(page)
    page.get_by_text("회원가입", exact=True).first.click()
    wait_idle(page)
    f = page.locator(".st-key-pw_signup")      # 폼이 아니라 칸 묶음 ('약관 전체 동의' 가 아래 항목을 바로 바꾸게, 11/18)
    f.get_by_label("아이디 (필수)").fill("qa_" + uuid.uuid4().hex[:8])
    f.get_by_label("비밀번호 (필수)").fill("qatest1234")
    f.get_by_label("비밀번호 확인 (필수)").fill("qatest1234")
    f.get_by_role("textbox", name="닉네임 (선택)").fill("테스트봇" + uuid.uuid4().hex[:4])   # 중복 금지 · 칸 옆 ? 가 있어 역할로 찾음
    # '약관 전체 동의' 하나로 필수 3개(만 14세 이상 · 이용약관 · 개인정보 수집·이용)가 모두 켜진다 (11/18)
    f.locator(".st-key-pwc_allbox label").click()
    for i in range(1, 4):
        expect(f.locator('[data-testid="stCheckbox"] input').nth(i)).to_be_checked(timeout=LONG)
    f.get_by_role("button", name="가입하기").click()
    # 가입하면 메인으로 가고, 메뉴바의 '로그인' 자리에 닉네임이 보인다
    expect(page).to_have_url(re.compile(r"/$"), timeout=LONG)          # 메인으로 옮겨졌는지 먼저
    expect(page.locator(f"{CARD}, .st-key-home").first).to_be_visible(timeout=LONG)   # 첫 화면은 홈 (11/18)
    wait_idle(page)
    expect(page.locator(".st-key-login_btn button").last).to_contain_text("테스트봇", timeout=LONG)

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


def reveal(page: Page, eid: str) -> None:
    """리스트는 처음 24장만 그린다 (11/18 속도). 그 카드가 보일 때까지 '더 보기' 를 누른다."""
    for _ in range(20):
        if page.locator(f".st-key-card_w_{eid}").count():
            return
        more = page.locator(".st-key-list_more_btn button")
        if not more.count():
            return
        before = page.locator(CARD).count()
        more.click()
        expect(page.locator(CARD)).not_to_have_count(before, timeout=LONG)
        wait_idle(page)


def open_detail(page: Page, eid: str) -> None:
    """카드 전체를 덮는 '자세히 보기' 버튼을 눌러 상세를 연다."""
    reveal(page, eid)
    page.locator(f".st-key-open_{eid} button").click(force=True)
    expect(page.locator(".dtitle")).to_be_visible(timeout=LONG)
    wait_idle(page)


# ------------------------------------------------------------------ 1. 목록
def test_1_목록이_뜬다(page: Page, app_url):
    n = open_list(page, app_url)
    assert n > 0, "팝업 카드가 하나도 없습니다"
    # 머리글 '팝업 카페 N곳' 의 N 은 전체 수, 카드는 처음 24장까지만 그리고 나머지는 '더 보기' (11/18 속도)
    total = int(re.search(r"팝업 카페\s*(\d+)\s*곳", page.locator(".st-key-listbar").inner_text()).group(1))
    assert n == min(total, 24), f"처음 카드 수 {n} (전체 {total})"
    if total > 24:
        page.locator(".st-key-list_more_btn button").click()
        expect(page.locator(CARD)).to_have_count(min(total, 48), timeout=LONG)


# ------------------------------------------------------------------ 2. 검색/필터
def test_2_검색으로_좁혀지고_없으면_안내가_뜬다(page: Page, app_url, data_dir):
    total = open_list(page, app_url)
    target = pick_cafe(data_dir)
    word = str(target["work"])
    # 검색 필터 줄은 메뉴바의 검색 아이콘을 눌러야 펼쳐진다 (11/18 화면 변경)
    page.locator(".st-key-gnb_search_off button").click()
    wait_idle(page)
    box = page.get_by_role("textbox", name="검색")
    box.fill(word)
    box.press("Enter")
    wait_idle(page)
    expect(page.locator(f".st-key-card_w_{target['entry_id']}")).to_be_visible(timeout=LONG)
    # 다시 그리는 동안 예전 카드가 잠깐 같이 남아 있을 수 있다 → 수가 처음 장수 이하로 내려올 때까지 기다린다
    page.wait_for_function(f"document.querySelectorAll('{CARD}').length <= {total}", timeout=LONG)
    found = page.locator(CARD).count()
    assert 0 < found <= total
    assert found < total or total == 1, f"검색해도 카드 수가 그대로입니다 ({found}/{total})"

    box.fill("zzqx없는작품9876")
    box.press("Enter")
    wait_idle(page)
    expect(page.get_by_text("이 조건엔 행사가 없어요")).to_be_visible(timeout=LONG)
    expect(page.locator(CARD)).to_have_count(0, timeout=LONG)    # 예전 카드가 잠깐 남아 있을 수 있어 사라질 때까지 기다림
    # 빈 표(dataframe)가 아니라 안내 문구여야 한다
    assert page.locator('[data-testid="stDataFrame"], [data-testid="stTable"]').count() == 0
    # 조건 완화 버튼: '검색어 지우기 (N곳)' 을 누르면 다시 카드가 보인다 (11/18 안정성)
    relax = page.locator(".st-key-relax_query button")
    expect(relax).to_contain_text("검색어 지우기", timeout=LONG)
    relax.click()
    wait_idle(page)
    expect(page.locator(CARD).first).to_be_visible(timeout=LONG)


# ------------------------------------------------------------------ 3. 상세
def test_3_카드를_누르면_상세가_열리고_탭으로_돌아올_수_있다(page: Page, app_url, data_dir):
    open_list(page, app_url)
    target = pick_cafe(data_dir, with_links=True)
    open_detail(page, target["entry_id"])
    expect(page.locator(".dtitle")).to_have_text(str(target["work"]))
    expect(page.get_by_text("방문 전 확인", exact=True)).to_be_visible()
    expect(page.get_by_text("참고 웹사이트", exact=True).first).to_be_visible()

    # 상세에서 돌아가기는 메뉴바의 '리스트로 보기' 탭 ('리스트로 돌아가기' 버튼은 11/18 에 뺐다)
    page.locator(".st-key-gnb_tabs").get_by_role("button", name="리스트로 보기").click()
    wait_idle(page)
    expect(page.locator(CARD).first).to_be_visible(timeout=LONG)
    expect(page.locator(".dtitle")).to_have_count(0)


# ------------------------------------------------------------------ 4. 북마크 → 캘린더
def test_4_북마크하면_내_캘린더에_보인다(page: Page, app_url, data_dir):
    sign_up(page, app_url)
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
        # 계절 배경은 내 캘린더에서만 (11/18 요청). 동작 줄이기 설정이 아닌 브라우저 기준
        expect(page.locator("#aw-season")).to_be_attached(timeout=LONG)
    finally:
        # 상태 되돌리기: 북마크 해제
        open_list(page, app_url)
        expect(page.locator("#aw-season")).to_have_count(0)        # 리스트에서는 떨어지는 그림이 없다
        page.locator(f".st-key-fav_on_w_{eid} button").click()
        expect(page.locator(f".st-key-fav_off_w_{eid}")).to_be_visible(timeout=LONG)
        wait_idle(page)

    page.goto(app_url + "/calendar")
    expect(page.get_by_text("내 캘린더", exact=True).first).to_be_visible(timeout=LONG)
    wait_idle(page)
    expect(page.locator(".up-name", has_text=work)).to_have_count(0)


# ------------------------------------------------------------------ 5. 안정성 (민감정보 차단)
def test_5_리뷰에_전화번호를_넣으면_막힌다(page: Page, app_url, data_dir):
    sign_up(page, app_url)
    before = (data_dir / "reviews.json").read_text(encoding="utf-8")
    open_list(page, app_url)
    target = pick_cafe(data_dir)
    open_detail(page, target["entry_id"])

    warn = page.get_by_text(re.compile(r"민감한 개인정보\(.*전화번호.*\)는 입력할 수 없습니다"))
    # 상세가 막 열린 직후엔 입력칸이 다시 그려지며 넣은 글이 사라질 때가 있다 → 경고가 뜰 때까지 몇 번 다시 넣는다
    for _ in range(3):
        wait_idle(page)
        body = page.get_by_placeholder(re.compile("다녀온 후기나 기대하는 점")).first
        body.scroll_into_view_if_needed()
        body.fill("대기 줄 길어요. 문의는 010-1234-5678 로 주세요")
        body.press("Tab")                  # 칸을 벗어나야 값이 서버로 넘어간다
        wait_idle(page)
        try:
            expect(warn).to_be_visible(timeout=8000)
            break
        except AssertionError:
            continue
    expect(warn).to_be_visible(timeout=LONG)
    send = page.get_by_role("button", name="리뷰 등록")
    # 다시 그리는 동안 예전 탭의 버튼이 잠깐 같이 남아 있을 수 있다 → 하나만 남을 때까지 기다린다
    expect(send).to_have_count(1, timeout=LONG)
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


# ------------------------------------------------------------------ 7. 손님은 북마크 대신 로그인 화면으로
def test_7_손님이_북마크를_누르면_로그인_화면으로(page: Page, app_url, data_dir):
    open_list(page, app_url)
    page.locator('[class*="st-key-fav_off_w_"] button').first.click()
    expect(page.get_by_text("환영합니다", exact=True)).to_be_visible(timeout=LONG)
    assert page.url.rstrip("/").endswith("/login")


# ------------------------------------------------------------------ 8. 등록하기: 손님에겐 + 가 없고, 회원은 들어간다
def test_8_등록은_회원만(page: Page, app_url, data_dir):
    open_list(page, app_url)
    assert page.locator(".st-key-add_btn").count() == 0, "손님에게 등록(+) 버튼이 보입니다"
    page.goto(app_url + "/add")
    expect(page.get_by_text("환영합니다", exact=True)).to_be_visible(timeout=LONG)   # 로그인 화면으로
    sign_up(page, app_url)
    open_list(page, app_url)
    expect(page.locator(".st-key-add_btn button")).to_be_visible(timeout=LONG)
    page.locator(".st-key-add_btn button").click()
    expect(page.get_by_text("팝업 카페 등록하기")).to_be_visible(timeout=LONG)


# ------------------------------------------------------------------ 9. 로그아웃하면 새로고침해도 로그아웃 (11/18 버그)
def test_9_로그아웃하면_새로고침해도_로그인되지_않는다(page: Page, app_url, data_dir):
    sign_up(page, app_url)
    page.goto(app_url + "/login")
    wait_idle(page)
    page.get_by_role("button", name="로그아웃").click()
    wait_idle(page)
    for _ in range(20):                            # 쿠키는 화면 속 스크립트가 지운다 → 지워질 때까지 잠깐 기다림
        if not any(c["name"] == "aw_session" and c["value"] for c in page.context.cookies()):
            break
        page.wait_for_timeout(500)
    assert not any(c["name"] == "aw_session" and c["value"] for c in page.context.cookies()), "로그인 쿠키가 남아 있어요"
    open_list(page, app_url)                       # 새로 연 화면(=새로고침)
    expect(page.locator(".st-key-login_btn button").last).not_to_contain_text("테스트봇", timeout=LONG)


# ------------------------------------------------------------------ 10. 새 계정은 남의 북마크를 물려받지 않는다 (11/18 버그)
def test_10_새로_가입하면_북마크가_비어_있다(page: Page, app_url, data_dir):
    # 같은 컴퓨터(같은 IP)의 손님 북마크가 있어도 새 계정에 옮겨지지 않아야 한다
    from common import favorite
    import json
    guest = favorite.user_key(None)
    rows = json.loads((data_dir / "favorites.json").read_text(encoding="utf-8"))
    cafe = current_cafes(data_dir)[0]["entry_id"]
    rows.append({"row_id": "e2eguest01", "entry_id": f"{guest}:{cafe}", "revision": 1, "status": "active",
                 "updated_at": "2026-11-18T00:00:00+00:00", "cafe_id": cafe, "user": guest})
    (data_dir / "favorites.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    sign_up(page, app_url)
    open_list(page, app_url)
    expect(page.locator('[class*="st-key-fav_on_w_"]')).to_have_count(0)


# ------------------------------------------------------------------ 11. 스토리 줄 · 팝업 북마크 추가 (11/18)
def go_home(page: Page, url: str) -> None:
    """로고를 눌러 홈으로 ('내가 관심있는 작품' 줄은 홈에만, 11/18)."""
    open_list(page, url)
    page.locator(".st-key-home_brand button").click()
    expect(page.locator(".st-key-home")).to_be_visible(timeout=LONG)
    wait_idle(page)


def test_11_팝업_북마크_추가로_고르면_관심있는_작품_맨_앞에_온다(page: Page, app_url, data_dir):
    go_home(page, app_url)
    # 로그인 전에는 '특전 있는 작품들' 만 (최애 추가하기 · 북마크 동그라미 없음, 11/18)
    expect(page.locator(".st-key-stories .story.hot").first).to_be_visible(timeout=LONG)
    expect(page.locator(".st-key-stories .story.add")).to_have_count(0)
    expect(page.locator(".st-key-stories .story.mark")).to_have_count(0)

    sign_up(page, app_url)
    go_home(page, app_url)
    expect(page.locator(".st-key-stories .story-empty")).to_be_visible(timeout=LONG)     # 새 회원도 아직 없음
    page.locator(".st-key-open_story_add button").click()
    dlg = page.locator('[role="dialog"]')
    expect(dlg.get_by_text("놓치고 싶지 않은 팝업을 골라 주세요")).to_be_visible(timeout=LONG)
    # 팝업 하나 (마지막 카드)
    cards = dlg.locator('[class*="st-key-card_fw_"]')
    expect(dlg.locator(".fwn").first).to_be_visible(timeout=LONG)   # 카드가 다 뜬 뒤에 읽는다 (가끔 빈 목록을 읽음)
    names = dlg.locator(".fwn").all_inner_texts()
    idx = len(names) - 1
    pick = names[idx]
    eid = next(c.split("st-key-card_fw_")[1].split()[0] for c in [cards.nth(idx).get_attribute("class")])
    dlg.locator(f".st-key-open_fw_{eid} button").click()
    expect(dlg.locator(".fw-count b")).to_have_text("1", timeout=LONG)
    if os.getenv("E2E_SHOTS"):
        page.screenshot(path=os.path.join(os.getenv("E2E_SHOTS"), "fw_dialog.png"))
    dlg.get_by_role("button", name="저장하기").click()
    expect(dlg).to_have_count(0, timeout=LONG)
    wait_idle(page)
    expect(page.locator(".st-key-stories .story.mark .nm")).to_have_text([pick], timeout=LONG)   # 북마크한 팝업 하나 = 동그라미 하나
    if os.getenv("E2E_SHOTS"):
        page.locator(".st-key-stories").screenshot(path=os.path.join(os.getenv("E2E_SHOTS"), "stories.png"))
    # 동그라미를 누르면 그 팝업 상세로 (11/18), 상세의 북마크 버튼이 '켜짐'
    page.locator(".st-key-open_story_0 button").click()
    expect(page.locator(".dtitle")).to_have_text(pick, timeout=LONG)
    expect(page.locator(f".st-key-fav_on_d_{eid}")).to_be_attached(timeout=LONG)


# ------------------------------------------------------------------ 12. 홈 (11/18)
def test_12_로고를_누르면_홈이_열리고_랭킹_카드로_상세에_간다(page: Page, app_url):
    open_list(page, app_url)
    page.locator(".st-key-home_brand button").click()
    expect(page.locator(".st-key-home")).to_be_visible(timeout=LONG)
    expect(page.locator(".story-head")).to_have_text("특전 있는 작품들")   # 로그인 전 (11/18)
    expect(page.locator(".story.hot").first).to_be_visible()
    expect(page.locator(".hbtitle").first).to_contain_text("실시간 인기 급상승 랭킹")   # 배너 안 왼쪽 위
    for title in ("따끈따끈 신규 등록 팝업", "곧 끝나는 팝업", "사전예약 팝업", "꿀팁 가득! 실시간 후기 모음"):
        expect(page.locator(".home-h", has_text=title)).to_be_visible(timeout=LONG)
    expect(page.locator(".st-key-gnbtab_on_home")).to_be_visible()
    rank = page.locator(".hls-wrap .hl")
    expect(rank.first).to_be_visible(timeout=LONG)
    assert rank.count() <= 5
    if rank.count() > 1:
        # 목록 2위를 누르면 배너가 2위 장으로 (상세로 가지 않음)
        rank.nth(1).click()
        page.wait_for_function("(() => { const b = document.querySelector('.st-key-home_banner');"
                               " return Math.round(b.scrollLeft / b.clientWidth) === 1; })()", timeout=LONG)
        expect(page.locator(".aw-dots button.on")).to_have_count(1)
        expect(page.locator(".st-key-home")).to_be_visible()
    # 배너를 누르면 그 팝업 상세
    page.locator('[class*="st-key-card_hb_"]').nth(1 if rank.count() > 1 else 0).click(position={"x": 120, "y": 120})
    expect(page.locator(".dtitle")).to_be_visible(timeout=LONG)
    # 리스트로 보기 탭으로 가면 홈이 아니다
    page.locator('[class*="st-key-gnbtab_"][class*="list"] button').click()
    expect(page.locator(CARD).first).to_be_visible(timeout=LONG)
    expect(page.locator(".st-key-home")).to_have_count(0)


# ------------------------------------------------------------------ 13. 내 리뷰: 고칠 때 사진 추가 · 내가 삭제 (11/18)
def test_13_내_리뷰는_고칠때_사진을_붙이고_직접_지울_수_있다(page: Page, app_url, data_dir):
    sign_up(page, app_url)
    open_list(page, app_url)
    target = pick_cafe(data_dir)
    open_detail(page, target["entry_id"])
    text = "e2e 사진 추가 확인용 리뷰"
    send = page.get_by_role("button", name="리뷰 등록")
    # 상세가 막 열린 직후엔 입력칸이 다시 그려지며 넣은 글이 사라질 때가 있다 → 등록 버튼이 켜질 때까지 다시 넣는다
    for _ in range(3):
        wait_idle(page)
        body = page.get_by_placeholder(re.compile("다녀온 후기나 기대하는 점")).first
        body.fill(text)
        body.press("Tab")
        wait_idle(page)
        try:
            expect(send).to_have_count(1, timeout=8000)      # 다시 그리는 동안 예전 탭이 잠깐 남는다
            expect(send).to_be_enabled(timeout=8000)
            break
        except AssertionError:
            continue
    send.click()
    expect(page.get_by_text(text).first).to_be_visible(timeout=LONG)
    wait_idle(page)

    card = page.locator('[class*="st-key-rv_more_"]').first
    card.locator("button").first.click()
    page.get_by_role("button", name="수정").first.click()
    wait_idle(page)
    page.locator('[class*="st-key-rv_edit_img_"] input[type="file"]').set_input_files(
        str(Path(__file__).resolve().parents[2] / "static" / "default_poster.png"))
    wait_idle(page)
    page.get_by_role("button", name="저장").first.click()
    expect(page.locator(".rv-pics img").first).to_be_visible(timeout=LONG)
    wait_idle(page)

    # 내가 쓴 글은 내가 지울 수 있다 (관리자가 아니어도)
    page.locator('[class*="st-key-rv_more_"]').first.locator("button").first.click()
    page.get_by_role("button", name="삭제", exact=True).first.click()
    dlg = page.get_by_test_id("stDialog")           # ('⋯' 칸도 role=dialog 라서 확인 창만 집는다)
    expect(dlg).to_be_visible(timeout=LONG)
    page.wait_for_timeout(800)                       # 창이 뜨는 동안의 움직임(애니메이션)이 끝난 뒤 누른다 (부하가 크면 누름이 빗나갔음)
    dlg.get_by_role("button", name="삭제", exact=True).click(timeout=LONG)
    wait_idle(page)
    expect(page.get_by_text(text)).to_have_count(0, timeout=LONG)


# ------------------------------------------------------------------ 14. 디자인 시스템 공개 페이지 (11/18)
def test_14_디자인_시스템_페이지는_로그인_없이_열린다(page: Page, app_url):
    page.goto(app_url + "/design")
    expect(page.locator(".ds-cover svg")).to_be_visible(timeout=LONG)
    tokens = json.loads((Path(__file__).resolve().parents[2] / "docs" / "design" / "tokens.json").read_text(encoding="utf-8"))
    expect(page.locator(".ds-sw > div")).to_have_count(len(tokens["color"]["tokens"]), timeout=LONG)   # 색 토큰마다 한 칸
    expect(page.locator(".ds-comp")).to_have_count(5)
    assert page.evaluate("document.documentElement.scrollWidth") <= page.viewport_size["width"]
    expect(page.locator(".aw-foot a", has_text="디자인 시스템")).to_be_visible()
