"""앱(Streamlit)에만 있던 화면을 웹에서 끝까지 점검 (Playwright): /privacy · /guide · /design · /ask · 블로그 후기 · 공유 버튼.
실제 Supabase 는 건드리지 않는다 — 시험용 local 저장소로 띄운 서버에만 돈다.

먼저 서버를 시험 모드로 띄운다 (web/ 에서). 블로그·AI 키는 비워서 '빈 상태' · '규칙 기반 대체' 를 본다:
    NAVER_BLOG_CLIENT_ID= NAVER_BLOG_CLIENT_SECRET= OPENAI_API_KEY= \
    WEB_STORAGE=local WEB_DATA_DIR=<빈 임시 폴더> AUTH_SECRET=test-secret-1234567890 \
    SITE_URL=http://localhost:3203 npx next dev -p 3203
그다음:
    python -X utf8 web/scripts/e2e_pages.py http://localhost:3203 <WEB_DATA_DIR> [스크린샷 폴더]

흐름 (PC 1440 · 모바일 390 각각):
  /privacy · /guide · /design · /ask 열기 → 제목 확인 → 스크린샷 → 가로 스크롤 없음(scrollWidth <= innerWidth)
  /guide#add 로 그 칸이 열리는지, 처음 3단계 배너에 › 버튼이 생기는지
  /ask 질문 3개: 작품 검색(배지 'AI 산출' 또는 '규칙 기반 대체') · 곧 끝나는 팝업(자주 묻는 질문) · 못 알아듣는 질문(0건 안내)
       + 전화번호가 든 질문은 가리고 찾는다는 안내
  /api/blog/<id> 가 키 없을 때 빈 상태({enabled:false, posts:[]})를 돌려주는지
  상세(/popup/<id>)에 공유 버튼이 붙어 있으면: 펼치기 → 링크 복사 → 클립보드가 <BASE>/popup/<id> 인지
  상세에 '블로그 후기' 탭이 붙어 있으면: 눌러서 '네이버 검색을 연결한 뒤에 보여요' 안내가 보이는지
마지막에 local 파일이 append-only 로 쌓였는지(revision 이 1씩 늘어남) 확인한다.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3203").rstrip("/")
DATA = Path(sys.argv[2]) if len(sys.argv) > 2 else None
SHOTS = Path(sys.argv[3]) if len(sys.argv) > 3 else None


def shot(page, name):
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)


def no_hscroll(page, where):
    sw, iw = page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
    assert sw <= iw, f"{where}: 가로 스크롤 생김 (scrollWidth {sw} > innerWidth {iw})"
    return sw, iw


def pages(page, tag):
    # ---- 개인정보처리방침
    page.goto(f"{BASE}/privacy")
    expect(page.locator(".pg-doc h1").first).to_have_text("개인정보처리방침")
    expect(page.locator(".pg-doc")).to_contain_text("이용약관 (요약)")
    expect(page.locator(".pg-doc table").first).to_be_visible()
    shot(page, f"web_privacy_{tag}")
    print(tag, "/privacy OK", no_hscroll(page, "/privacy"))

    # ---- 사용자 튜토리얼
    page.goto(f"{BASE}/guide")
    expect(page.locator(".g-hero-t")).to_have_text("ANI:WHERE 사용자 튜토리얼")
    expect(page.locator(".pg-guide img").first).to_be_visible()
    # 그림이 실제로 열리는지 (깨진 그림 없음)
    page.wait_for_load_state("networkidle")
    broken = page.evaluate("[...document.querySelectorAll('.pg-guide img')].filter(i => i.complete && !i.naturalWidth).map(i => i.src)")
    assert not broken, f"깨진 그림: {broken}"
    if tag == "pc":
        expect(page.locator(".g-slides-wrap .aw-arrow.r.show")).to_be_visible()
    for key in ("home", "map", "list", "bookmark", "cal", "add", "edit", "delete", "login", "ask", "mobile"):
        assert page.locator(f"#{key}").count() == 1, f"/guide#{key} 칸이 없다"
    shot(page, f"web_guide_{tag}")
    print(tag, "/guide OK", no_hscroll(page, "/guide"))
    page.goto(f"{BASE}/guide#add")
    page.wait_for_timeout(900)
    top = page.evaluate("document.getElementById('add').getBoundingClientRect().top")
    assert -5 < top < 200, f"/guide#add 로 그 칸이 열려야 한다 (top={top})"
    print(tag, "/guide#add 바로가기 OK")

    # ---- 디자인 시스템
    page.goto(f"{BASE}/design")
    expect(page.locator(".ds-cover .cv .name")).to_have_text("ANI:WHERE")
    expect(page.locator(".ds-h2", has_text="색 토큰")).to_be_visible()
    assert page.locator(".ds-sw > div").count() > 10
    assert page.locator(".ds-comp").count() == 5
    shot(page, f"web_design_{tag}")
    print(tag, "/design OK", no_hscroll(page, "/design"))


def ask(page, tag):
    page.goto(f"{BASE}/ask")
    expect(page.locator(".ask-q")).to_have_text("팝업에게 물어보기")
    shot(page, f"web_ask_{tag}")
    # 예시 질문을 누르면 입력칸에 들어간다
    page.locator(".ask-exs button").nth(1).click()
    expect(page.locator(".ask-form input")).to_have_value("주술회전 팝업 어디서 해?")

    def q(text):
        page.fill(".ask-form input", text)
        page.get_by_role("button", name="물어보기").click()
        expect(page.locator(".ask-result")).to_be_visible(timeout=60000)

    # 1) 작품 검색 → 서버 AI 다듬기 (키 없으면 규칙 기반 대체)
    q("주술회전 팝업 어디서 해?")
    expect(page.locator(".ask-cond")).to_contain_text("질문에서 읽은 조건:")
    if page.locator(".ask-none").count():
        print(tag, "/ask 작품 검색: 0건 안내 (데이터에 없음)")
    else:
        badge = page.locator(".ask-badge").first.inner_text()
        assert badge in ("AI 산출", "규칙 기반 대체"), badge
        assert page.locator(".ask-hit").count() >= 1
        print(tag, "/ask 작품 검색 OK —", badge, "·", page.locator(".ask-hit").count(), "곳")
    shot(page, f"web_ask_{tag}_q1")
    # 2) 자주 묻는 질문 (규칙)
    q("곧 끝나는 팝업")
    if page.locator(".ask-none").count() == 0:
        expect(page.locator(".ask-badge").first).to_have_text("규칙 기반 대체")
    print(tag, "/ask 곧 끝나는 팝업 OK")
    # 3) 못 알아듣는 질문 → 0건 다음 할 일 안내
    q("오늘 날씨 어때?")
    expect(page.locator(".ask-none")).to_contain_text("조건에 맞는 팝업을 찾지 못했어요")
    print(tag, "/ask 0건 안내 OK")
    # 4) 개인정보가 든 질문 → 가리고 찾는다는 안내
    q("010-1234-5678 부산 팝업 알려줘")
    expect(page.locator(".ask-note.info")).to_contain_text("개인정보")
    # 5) 너무 짧은 질문 → 경고만
    page.fill(".ask-form input", "a")
    page.get_by_role("button", name="물어보기").click()
    expect(page.locator(".ask-note.warn")).to_contain_text("너무 짧아요")
    print(tag, "/ask 입력 검사 OK", no_hscroll(page, "/ask"))


def first_popup_id(page):
    page.goto(f"{BASE}/list")
    href = page.locator("a[href^='/popup/']").first.get_attribute("href")
    return href.split("/popup/")[1].split("?")[0]


def blog_and_share(page, tag, pid):
    if tag == "pc":
        with urllib.request.urlopen(f"{BASE}/api/blog/{pid}") as r:
            body = json.loads(r.read().decode("utf-8"))
        assert body["posts"] == [] and body["count"] == 0 and body["enabled"] is False, body
        print("blog route 키 없음 → 빈 상태 OK", body)
    page.goto(f"{BASE}/popup/{pid}")
    page.wait_for_load_state("networkidle")
    if page.locator(".shr-main").count():
        page.locator(".shr-main").click()
        expect(page.locator(".shr-panel button")).to_have_count(3)
        page.locator(".shr-copy").click()
        expect(page.locator(".shr-msg")).to_have_text("링크를 복사했어요")
        clip = page.evaluate("navigator.clipboard.readText()")
        assert clip == f"{BASE}/popup/{pid}", clip
        no_hscroll(page, "상세 공유 펼침")
        shot(page, f"web_share_{tag}")
        page.wait_for_timeout(3300)
        assert page.locator(".shr-msg").count() == 0, "안내는 3초 뒤 사라져야 한다"
        print(tag, "공유 버튼: 펼치기 · 링크 복사 OK", clip)
    else:
        print(tag, "공유 버튼: 상세에 아직 안 붙음 (SKIP)")
    tab = page.get_by_role("tab", name=re.compile("블로그 후기"))
    if tab.count():
        txt = tab.first.inner_text()
        tab.first.click()
        if page.locator(".blog-tab").count():
            expect(page.locator(".blog-tab .blog-empty")).to_have_text("블로그 후기는 네이버 검색을 연결한 뒤에 보여요.")
            expect(page.locator(".blog-tab .blog-note")).to_contain_text("네이버 블로그 검색 결과예요")
            assert re.search(r"블로그 후기( 0)?$", tab.first.inner_text().strip()), (txt, tab.first.inner_text())
            shot(page, f"web_blog_{tag}")
            print(tag, "블로그 후기 탭: 빈 상태 OK —", tab.first.inner_text())
        else:
            print(tag, "블로그 후기 탭: BlogTab 이 아직 안 붙음 (SKIP)")


def check_append_only():
    if not DATA or not DATA.exists():
        return
    for f in sorted(DATA.glob("*.json")):
        rows = json.loads(f.read_text(encoding="utf-8"))
        by = {}
        for r in rows:
            by.setdefault(r["entry_id"], []).append(int(r["revision"]))
        for eid, revs in by.items():
            assert revs == list(range(1, len(revs) + 1)), (f.name, eid, revs)
        print(f"append-only OK: {f.stem} {len(rows)}행")


with sync_playwright() as p:
    b = p.chromium.launch()
    pid = None
    for tag, vp in (("pc", {"width": 1440, "height": 900}), ("m", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp, service_workers="block", permissions=["clipboard-read", "clipboard-write"])
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        try:
            pages(page, tag)
            ask(page, tag)
            pid = pid or first_popup_id(page)
            blog_and_share(page, tag, pid)
        except Exception:
            print("실패한 화면:", page.evaluate("location.href"), errs)
            shot(page, f"fail_{tag}")
            raise
        print(tag, "errors:", errs)
        assert not errs
        ctx.close()
    b.close()
check_append_only()
print("\n앱에만 있던 화면(개인정보처리방침 · 튜토리얼 · 디자인 시스템 · 물어보기 · 블로그 후기 · 공유) 점검 통과")
