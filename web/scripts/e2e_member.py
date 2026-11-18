"""회원 기능 끝까지 점검 (Playwright). 실제 Supabase 는 건드리지 않는다 — 시험용 local 저장소로 띄운 서버에만 돈다.

먼저 서버를 시험 모드로 띄운다 (web/ 에서, 빌드한 뒤):
    WEB_STORAGE=local WEB_DATA_DIR=<빈 임시 폴더> WEB_OAUTH_MOCK=1 AUTH_SECRET=test-secret-1234567890 \
    SITE_URL=http://localhost:3100 npx next start -p 3100
그다음:
    python -X utf8 web/scripts/e2e_member.py http://localhost:3100 <WEB_DATA_DIR> [스크린샷 폴더]

흐름: 아이디 가입 → 로그아웃 → 틀린 비밀번호 → 로그인 → 북마크 → 내 캘린더에 보임 → 전화번호 든 리뷰 거절(화면·서버 둘 다)
→ 다녀온 후기(별점) 등록 → 수정 → 답글 → 삭제 → 닉네임 바꾸기 → 로그아웃 → 카카오(가짜) 처음 가입 → 다시 로그인 → 로그아웃.
마지막에 local 파일이 append-only 로 쌓였는지(지운 행 없음, revision 이 1씩 늘어남) 확인한다.

이어서 볼 것 (같은 서버, ADMIN_MEMBER_KEYS=e9b3081fcb7d7356 로 띄웠을 때):
    e2e_extra.py  — 토스트(글자·아이콘·위치·z-index) · 리뷰/프로필 사진 올리기(EXIF 지움, 256px webp) · 종 알림(앱과 같은 번호·읽음 쿠키,
                    내 주변 추천) · 최애 추가하기 · 관리자 리뷰 삭제 → 받은 알림
    e2e_admin.py  — 관리자 대시보드 /data (삭제 요청 승인·거부 → 알림, 공지·알림 규칙)
    e2e_popup.py  — 상세 수정하기 · 수정 이력 · 되돌리기 · 포스터 올리기 · 지도에서 내리기 · /add 등록하기
    e2e_pages.py  — /privacy · /guide · /design · /ask · 블로그 후기 · 공유 버튼
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"
DATA = Path(sys.argv[2]) if len(sys.argv) > 2 else None
SHOTS = Path(sys.argv[3]) if len(sys.argv) > 3 else None
LID = f"e2e_{int(time.time()) % 100000}"
PW = "abcd1234"


def shot(page, name):
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)


def wait_path(page, path):
    # Next 의 화면 이동(pushState)은 page.url 이 늦게 바뀌어서 location 으로 직접 기다린다
    page.wait_for_function("p => location.pathname === p", arg=path, timeout=15000)


def toast_has(page, text):
    expect(page.locator(".ani-toast")).to_contain_text(text, timeout=8000)


def run(page, tag):
    # ---- 아이디 가입 ----
    page.goto(f"{BASE}/login")
    shot(page, f"web_{tag}_login")
    page.get_by_role("tab", name="회원가입").click()
    lid = f"{LID}{tag}"
    page.fill("input[name=login_id]", lid)
    page.fill("input[name=password]", PW)
    page.fill("input[name=password2]", PW)
    nick_ph = page.get_attribute("input[name=nickname]", "placeholder")
    shot(page, f"web_{tag}_signup")
    # 동의 없이 → 막힘
    page.get_by_role("button", name="가입하기").click()
    expect(page.locator(".auth-warn")).to_contain_text("만 14세")
    page.get_by_label("약관 전체 동의").check()
    page.get_by_role("button", name="가입하기").click()
    wait_path(page, "/")
    expect(page.locator(".gnb-me")).to_be_visible()
    print(tag, "가입 OK, 자동 닉네임:", nick_ph)

    # ---- 로그아웃 → 틀린 비밀번호 → 로그인 ----
    page.goto(f"{BASE}/login")
    page.get_by_role("button", name="로그아웃").click()
    wait_path(page, "/login")
    expect(page.locator(".gnb-login")).to_be_visible()
    page.fill("input[name=login_id]", lid)
    page.fill("input[name=password]", "wrong1234")
    page.get_by_role("button", name="로그인", exact=True).click()
    expect(page.locator(".auth-warn")).to_contain_text("아이디나 비밀번호가 맞지 않아요")
    page.fill("input[name=password]", PW)
    page.get_by_role("button", name="로그인", exact=True).click()
    wait_path(page, "/")
    expect(page.locator(".gnb-me")).to_be_visible()
    print(tag, "로그인 OK")

    # ---- 북마크 → 내 캘린더 ----
    page.goto(f"{BASE}/list")
    card = page.locator(".pcard-wrap").first
    work = card.locator(".t").inner_text()
    href = card.locator("a").first.get_attribute("href")
    card.locator(".bm").click()
    toast_has(page, "북마크했어요")
    page.goto(f"{BASE}/calendar")
    expect(page.locator(".up-item").first).to_contain_text(work)
    shot(page, f"web_{tag}_calendar")
    print(tag, "북마크 → 내 캘린더 OK:", work)

    # ---- 리뷰 ----
    page.goto(f"{BASE}{href}")
    box = page.locator(".rvbox")
    box.get_by_role("radio", name="4점").click()
    box.locator("textarea").fill("연락은 010-1234-5678 로 주세요")
    expect(box.locator(".auth-warn")).to_contain_text("민감한 개인정보(전화번호)")
    expect(box.get_by_role("button", name="리뷰 등록")).to_be_disabled()
    # 화면 검사를 건너뛰고 보내도 서버가 거절해야 한다
    box.get_by_role("button", name="리뷰 등록").evaluate("b => { b.disabled = false; b.form.requestSubmit(b); }")
    expect(box.locator(".auth-warn").last).to_contain_text("입력할 수 없습니다", timeout=8000)
    print(tag, "전화번호 리뷰 거절 OK (화면 + 서버)")
    box.locator("textarea").fill("굿즈가 많고 대기 20분 정도였어요")
    box.get_by_role("button", name="리뷰 등록").click()
    toast_has(page, "리뷰를 남겼습니다")
    th = page.locator(".rv-thread").first
    expect(th).to_contain_text("굿즈가 많고")
    expect(th.locator(".rv-stars")).to_have_text("★★★★☆")
    # 수정
    th.get_by_role("button", name="내 글 수정·삭제").click()
    th.get_by_role("button", name="수정", exact=True).click()
    th.locator("form.edit textarea").fill("굿즈가 많고 대기 30분이었어요 (수정)")
    th.get_by_role("button", name="저장", exact=True).click()
    toast_has(page, "수정했습니다")
    expect(page.locator(".rv-thread").first).to_contain_text("(수정됨)")
    # 답글
    th = page.locator(".rv-thread").first
    th.locator("form.reply textarea").click()
    th.locator("form.reply textarea").fill("정보 고마워요")
    th.get_by_role("button", name="답글 등록").click()
    toast_has(page, "답글을 남겼습니다")
    expect(page.locator(".rv-thread").first.locator(".is-reply")).to_contain_text("정보 고마워요")
    shot(page, f"web_{tag}_detail_reviews")
    # 원글 삭제 (답글도 함께 안 보임)
    th = page.locator(".rv-thread").first
    th.locator(".rv-card").first.get_by_role("button", name="내 글 수정·삭제").click()
    th.get_by_role("button", name="삭제", exact=True).click()
    page.locator(".dlg").get_by_role("button", name="삭제", exact=True).click()
    toast_has(page, "삭제했어요")
    expect(page.locator(".rv-thread", has_text="대기 30분")).to_have_count(0)
    print(tag, "리뷰 등록·수정·답글·삭제 OK")

    # ---- 마이페이지: 닉네임 바꾸기 ----
    page.goto(f"{BASE}/login")
    newnick = f"테스트{tag}닉"
    page.fill("input[name=nickname]", newnick)
    page.get_by_role("button", name="저장", exact=True).click()
    toast_has(page, newnick)  # 앱처럼 가운데 토스트로 알린다
    shot(page, f"web_{tag}_mypage")
    page.goto(f"{BASE}/")
    shot(page, f"web_{tag}_home_member")
    page.goto(f"{BASE}/login")
    page.get_by_role("button", name="로그아웃").click()
    wait_path(page, "/login")
    print(tag, "닉네임 바꾸기 · 로그아웃 OK")


def social(page):
    page.goto(f"{BASE}/login")
    page.get_by_role("link", name="카카오로 로그인").click()
    wait_path(page, "/auth/join")
    expect(page.locator(".auth-title")).to_have_text("거의 다 됐어요")
    page.fill("input[name=nickname]", "")
    page.get_by_label("약관 전체 동의").check()
    page.get_by_role("button", name="가입하고 시작하기").click()
    wait_path(page, "/")
    expect(page.locator(".gnb-me")).to_be_visible()
    page.goto(f"{BASE}/login")
    expect(page.locator(".auth-note")).to_contain_text("카카오 계정으로 로그인 중")
    page.get_by_role("button", name="로그아웃").click()
    wait_path(page, "/login")
    # 두 번째: 이미 가입한 계정 → 바로 로그인
    page.get_by_role("link", name="카카오로 로그인").click()
    wait_path(page, "/")
    expect(page.locator(".gnb-me")).to_be_visible()
    page.goto(f"{BASE}/login")
    page.get_by_role("button", name="로그아웃").click()
    wait_path(page, "/login")
    expect(page.locator(".gnb-login")).to_be_visible()
    print("카카오(가짜) 처음 가입 → 다시 로그인 → 로그아웃 OK")


def check_append_only():
    if not DATA:
        return
    for name in ("members", "favorites", "reviews", "visits"):
        rows = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
        by = {}
        for r in rows:
            by.setdefault(r["entry_id"], []).append(int(r["revision"]))
        for eid, revs in by.items():
            assert revs == list(range(1, len(revs) + 1)), (name, eid, revs)
        print(f"append-only OK: {name} {len(rows)}행 · 글 {len(by)}개")
    reviews = json.loads((DATA / "reviews.json").read_text(encoding="utf-8"))
    assert not any("010-1234-5678" in r["body"] for r in reviews), "전화번호가 저장되면 안 된다"
    assert any(r["status"] == "deleted" for r in reviews), "삭제도 새 행으로 쌓여야 한다"
    print("민감정보 저장 없음 · 삭제는 새 행 OK")


with sync_playwright() as p:
    b = p.chromium.launch()
    for tag, vp in (("pc", {"width": 1440, "height": 900}), ("m", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp, service_workers="block")
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        try:
            run(page, tag)
        except Exception:
            print("실패한 화면:", page.evaluate("location.href"), page.locator(".auth-warn").all_inner_texts(), errs)
            shot(page, f"fail_{tag}")
            raise
        if tag == "pc":
            social(page)
        sw = page.evaluate("document.documentElement.scrollWidth")
        print(tag, "scrollWidth", sw, "errors:", errs)
        assert not errs
        ctx.close()
    b.close()
check_append_only()
print("\n모든 회원 기능 점검 통과")
