"""팝업 등록하기 · 수정하기 끝까지 점검 (Playwright). 실제 Supabase 는 건드리지 않는다 — 시험용 local 저장소로 띄운 서버에만 돈다.

먼저 서버를 시험 모드로 띄운다 (web/ 에서):
    WEB_STORAGE=local WEB_DATA_DIR=<빈 임시 폴더> WEB_OAUTH_MOCK=1 AUTH_SECRET=test-secret-1234567890 \
    SITE_URL=http://localhost:3202 ADMIN_MEMBER_KEYS=e9b3081fcb7d7356 npx next dev -p 3202
그다음:
    python -X utf8 web/scripts/e2e_popup.py http://localhost:3202 <WEB_DATA_DIR> [스크린샷 폴더]

흐름: 아이디 가입 → 상세 '수정하기' 탭: 카페명·특전 바꿔 저장 → 화면에 바로 반영 + local cafes.json 에 새 revision(editor=내 닉네임)
→ 전화번호 넣으면 막힘(화면 · 서버) → 수정 이력에서 이전 버전으로 되돌리기 → 반영 → 포스터 사진 바꾸기(png) + 추가 이미지(EXIF 든 jpg,
저장된 파일에 EXIF 없음) → 관리자(e2e_admin)로 '지도에서 내리기' → 상세 404 · 목록에서 사라짐 → /add 공지로 간편등록(규칙 기반 대체 표시)
→ 등록 → 새 상세가 열림 → 모바일(390)에서 단계별 등록 → 상세. 마지막에 local 파일이 append-only 인지(앞 행 그대로, revision 1씩) 확인.
"""
import json
import re
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3202"
DATA = Path(sys.argv[2]) if len(sys.argv) > 2 else None
SHOTS = Path(sys.argv[3]) if len(sys.argv) > 3 else None
RUN = int(time.time()) % 100000
LID = f"e2e_pop{RUN}"
PW = "abcd1234"
ADMIN_ID = "e2e_admin"
TODAY = (date.today()).isoformat()
TMP = (SHOTS or Path(".")) / "_files"


def shot(page, name, full=True):
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)


def wait_path(page, path):
    page.wait_for_function("p => location.pathname === p", arg=path, timeout=20000)


def toast_has(page, text):
    expect(page.locator(".ani-toast")).to_contain_text(text, timeout=15000)


def cafes_local():
    p = DATA / "cafes.json" if DATA else None
    return json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else []


def make_files():
    TMP.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (60, 80), (20, 184, 166)).save(TMP / "poster.png")
    img = Image.new("RGB", (64, 48), (240, 120, 80))
    exif = Image.Exif()
    exif[0x010F] = "E2E Camera Maker"      # Make
    exif[0x0110] = "E2E Model"             # Model
    exif[0x8825] = {1: "N", 2: (37.0, 33.0, 0.0), 3: "E", 4: (126.0, 58.0, 0.0)}   # GPS
    img.save(TMP / "exif.jpg", "JPEG", exif=exif.tobytes())
    assert Image.open(TMP / "exif.jpg").getexif(), "시험용 jpg 에 EXIF 가 들어가야 한다"


def pick_popup():
    """지금 지도에 있는 서울 팝업 중 끝나지 않은 것 하나 (수정 저장 검사에 걸리지 않게)"""
    raw = json.load(urllib.request.urlopen(
        "https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main/data/cafes.json", timeout=20))
    latest = {}
    for r in raw + cafes_local():
        p = latest.get(r["entry_id"])
        if not p or int(r["revision"]) >= int(p["revision"]):
            latest[r["entry_id"]] = r
    for r in latest.values():
        if (r["status"] == "active" and str(r.get("address", "")).startswith("서울")
                and str(r["end_date"])[:10] >= TODAY and "기간 확인 필요" not in str(r.get("tags"))):
            return r
    raise SystemExit("수정해 볼 팝업이 없다")


def signup(page, lid, tag):
    page.goto(f"{BASE}/login")
    page.get_by_role("tab", name="회원가입").click()
    page.fill("input[name=login_id]", lid)
    page.fill("input[name=password]", PW)
    page.fill("input[name=password2]", PW)
    page.get_by_label("약관 전체 동의").check()
    page.get_by_role("button", name="가입하기").click()
    try:
        wait_path(page, "/")
    except Exception:
        # 이미 있는 아이디(같은 폴더로 다시 돌렸을 때) → 로그인
        page.get_by_role("tab", name="로그인").click()
        page.fill("input[name=login_id]", lid)
        page.fill("input[name=password]", PW)
        page.get_by_role("button", name="로그인", exact=True).click()
        wait_path(page, "/")
    expect(page.locator(".gnb-me")).to_be_visible()
    print(tag, "로그인 OK:", lid)


def logout(page):
    page.goto(f"{BASE}/login")
    page.get_by_role("button", name="로그아웃").click()
    wait_path(page, "/login")
    expect(page.locator(".gnb-login")).to_be_visible(timeout=15000)


def open_edit(page, cid):
    page.goto(f"{BASE}/popup/{cid}")
    page.get_by_role("tab", name="수정하기").click()
    expect(page.locator(".ed-panel")).to_be_visible()
    return page.locator(".ed-panel")


def field(panel, label):
    lab = panel.page.locator(".ed-label", has_text=re.compile(f"^{label}"))
    return panel.locator("label.ed-field").filter(has=lab).locator("input").first


def edit_flow(page):
    target = pick_popup()
    cid = target["entry_id"]
    base_rev = int(target["revision"])
    print("수정해 볼 팝업:", cid, target["work"], "·", target["cafe_name"], "rev", base_rev)
    before = len(cafes_local())

    # 손님은 로그인 안내만
    page.goto(f"{BASE}/popup/{cid}")
    page.get_by_role("tab", name="수정하기").click()
    expect(page.locator(".ed-gate")).to_contain_text("팝업 정보 수정은 로그인하면 할 수 있어요.")
    shot(page, "pc_edit_guest")
    signup(page, LID, "pc")

    panel = open_edit(page, cid)
    shot(page, "pc_edit_tab")
    expect(page).to_have_url(f"{BASE}/popup/{cid}?tab=edit")
    name_in = field(panel, "카페명")
    perks_in = field(panel, "특전")
    old_name = name_in.input_value()
    new_name = f"{old_name} E2E{RUN}"
    name_in.fill(new_name)
    old_perks = perks_in.input_value()
    perks_in.fill((old_perks + ", " if old_perks else "") + f"테스트 특전 {RUN}")
    panel.get_by_role("button", name="수정 저장").click()
    toast_has(page, "수정했습니다.")
    expect(page.locator(".dcafe")).to_have_text(new_name, timeout=15000)
    expect(page.locator(".dbox").first).to_contain_text(f"테스트 특전 {RUN}")
    rows = cafes_local()
    last = rows[-1]
    assert last["entry_id"] == cid and int(last["revision"]) == base_rev + 1, last
    assert last["source"] == "직접 수정" and last["cafe_name"] == new_name, last
    assert last["editor"].endswith("#m" + json.loads((DATA / "members.json").read_text(encoding="utf-8"))[-1]["entry_id"][:4]), last["editor"]
    assert "| notion:" not in target.get("note", "") or "| notion:" in last["note"], "notion 표시는 남아야 한다"
    print("수정 저장 OK → 화면 반영 + 새 revision", last["revision"], "editor", last["editor"], "note", last["note"][:40])

    # 전화번호 → 화면에서 막고, 화면 검사를 건너뛰어도 서버가 거절
    panel = page.locator(".ed-panel")
    field(panel, "특전").fill("문의 010-1234-5678")
    expect(panel.locator(".ed-err").first).to_contain_text("민감한 개인정보(전화번호)")
    save = panel.get_by_role("button", name="수정 저장")
    expect(save).to_be_disabled()
    shot(page, "pc_edit_sensitive")
    save.evaluate("b => { b.disabled = false; b.click(); }")
    expect(panel.locator(".ed-err").last).to_contain_text("입력할 수 없습니다", timeout=15000)
    assert len(cafes_local()) == len(rows), "전화번호가 든 수정은 저장되면 안 된다"
    print("전화번호 수정 거절 OK (화면 + 서버)")

    # 수정 이력 → 이전 버전으로 되돌리기
    page.goto(f"{BASE}/popup/{cid}?tab=edit")
    page.locator(".hx-exp summary").click()
    expect(page.locator(".hx-item.now")).to_contain_text(f"{base_rev + 1}번째")
    expect(page.locator(".hx-item.now")).to_contain_text("직접 수정")
    shot(page, "pc_history")
    page.locator(".hx-item", has_text=f"{base_rev}번째").get_by_role("button", name="이 버전으로 돌아가기").click()
    toast_has(page, f"{base_rev}번째 버전으로 되돌렸어요.")
    expect(page.locator(".dcafe")).to_have_text(old_name, timeout=15000)
    last = cafes_local()[-1]
    assert last["source"] == f"{base_rev}번째로 되돌리기" and int(last["revision"]) == base_rev + 2, last
    assert last["cafe_name"] == target["cafe_name"] and last["perks"] == target["perks"], last
    print("되돌리기 OK → rev", last["revision"], last["source"])

    # 포스터 바꾸기(png) + 이미지 추가(EXIF jpg)
    panel = open_edit(page, cid)
    had = len([x for x in str(target.get("images") or "").split(",") if x.strip()])
    panel.locator(".ed-drop input[aria-label='포스터 바꾸기']").set_input_files(str(TMP / "poster.png"))
    if had:
        dlg = page.locator(".dlg", has_text="포스터 변경")
        expect(dlg).to_contain_text("변경하시겠습니까?")
        shot(page, "pc_edit_poster_confirm", full=False)
        dlg.get_by_role("button", name="변경").click()
    expect(panel.locator(".ed-newposter")).to_contain_text("새 포스터로 변경돼요")
    panel.locator(".ed-drop input[aria-label='이미지 추가']").set_input_files(str(TMP / "exif.jpg"))
    expect(panel.locator(".ed-files li")).to_have_count(1)
    shot(page, "pc_edit_images")
    panel.get_by_role("button", name="수정 저장").click()
    toast_has(page, "수정했습니다.")
    last = cafes_local()[-1]
    imgs = [x.strip() for x in last["images"].split(",") if x.strip()]
    assert imgs[0].startswith("/uploads/") and imgs[0].endswith(".png"), imgs
    jpg = [x for x in imgs if x.endswith(".jpg")]
    assert jpg, imgs
    saved = DATA / "uploads" / Path(jpg[-1]).name
    assert saved.exists(), saved
    assert not Image.open(saved).getexif(), "저장된 사진에 EXIF 가 남으면 안 된다"
    old_imgs = [x.strip() for x in str(target.get("images") or "").split(",") if x.strip()]
    assert imgs[1:len(old_imgs)] == old_imgs[1:], (imgs, old_imgs)
    print("포스터 바꾸기 + 추가 이미지 OK, EXIF 지워짐:", imgs[0], jpg[-1])
    expect(page.locator(".gallery img").first).to_have_attribute("src", imgs[0], timeout=15000)

    # 이력 카드에 '포스터 변경' · '이미지 1장 추가'
    page.goto(f"{BASE}/popup/{cid}?tab=edit")
    page.locator(".hx-exp summary").click()
    now = page.locator(".hx-item.now")
    expect(now).to_contain_text("포스터 변경" if had else "포스터 추가")
    expect(now).to_contain_text("이미지 1장 추가")
    shot(page, "pc_history_images")
    logout(page)
    return cid, before


def admin_flow(page, cid):
    signup(page, ADMIN_ID, "admin")
    panel = open_edit(page, cid)
    expect(panel.get_by_role("button", name="삭제 요청")).to_have_count(0)
    panel.get_by_role("button", name="지도에서 내리기 (관리자)").click()
    dlg = page.locator(".dlg", has_text="정말로 지도에서 삭제하시겠습니까?")
    shot(page, "pc_admin_takedown", full=False)
    dlg.get_by_role("button", name="삭제", exact=True).click()
    wait_path(page, "/")
    toast_has(page, "지도에서 내렸습니다. 이력은 남아 있습니다.")
    last = cafes_local()[-1]
    assert last["entry_id"] == cid and last["status"] == "deleted" and last["source"] == "지도에서 내림", last
    r = page.goto(f"{BASE}/popup/{cid}")
    assert r.status == 404, r.status
    page.goto(f"{BASE}/list")
    expect(page.locator(f"a[href='/popup/{cid}']")).to_have_count(0)
    print("관리자 지도에서 내리기 OK → 상세 404 · 목록에서 사라짐")


QUICK = f"""소드 아트 온라인 콜라보 카페 오픈!
기간: {(date.today() + timedelta(days=3)):%Y.%m.%d} ~ {(date.today() + timedelta(days=40)):%Y.%m.%d}
장소: 카페 이투이{RUN} 홍대점
주소: 서울 마포구 양화로 188 AK&홍대 5층
음료 주문 시 랜덤 코스터 증정
아크릴 스탠드, 캔뱃지 판매
사전 예약제로 운영합니다"""


def quick_flow(page):
    page.goto(f"{BASE}/add")
    expect(page.locator(".add-title")).to_have_text("팝업 카페 등록하기")
    shot(page, "pc_add_step0")
    page.get_by_role("button", name="공지로 간편등록").click()
    expect(page.locator(".wiz-title")).to_have_text("공지로 간편등록")
    read = page.get_by_role("button", name="읽어오기")
    expect(read).to_be_disabled()
    shot(page, "pc_quick_empty")
    page.get_by_label("공지", exact=True).fill(QUICK)
    read.click()
    expect(page.locator(".ai-badge")).to_contain_text("규칙 기반 대체", timeout=20000)
    expect(page.locator(".quick-src")).to_contain_text("규칙 기반으로 읽었어요 (AI 아님)")
    body = page.locator(".quick-body")
    expect(body.get_by_role("combobox", name="작품")).to_have_value("소드 아트 온라인")
    expect(field(body, "카페명")).to_have_value(f"카페 이투이{RUN} 홍대점")
    expect(body.locator("#ed-addr")).to_have_value("서울 마포구 양화로 188 AK&홍대 5층")
    expect(field(body, "특전")).to_have_value("음료 주문 시 랜덤 코스터 증정")
    expect(field(body, "굿즈")).to_have_value("아크릴 스탠드, 캔뱃지")
    expect(body.get_by_role("button", name="사전 예약")).to_have_attribute("aria-pressed", "true")
    shot(page, "pc_quick_read")
    before = len(cafes_local())
    body.get_by_role("button", name="등록하기").click()
    page.wait_for_function("() => location.pathname.startsWith('/popup/')", timeout=30000)
    toast_has(page, "1곳을 지도에 올렸습니다.")
    rows = cafes_local()
    new = rows[-1]
    assert len(rows) == before + 1 and new["source"] == "간편 등록" and int(new["revision"]) == 1, new
    assert page.evaluate("location.pathname") == f"/popup/{new['entry_id']}"
    expect(page.locator(".dcafe")).to_have_text(f"카페 이투이{RUN} 홍대점")
    assert new["intro"].startswith("소드 아트 온라인 콜라보 카페 오픈!"), new["intro"][:30]
    print("간편등록(규칙 기반 대체) → 등록 → 상세 OK:", new["entry_id"], new["note"])
    shot(page, "pc_after_add")


def wizard_flow(page, tag):
    """단계별 등록 (모바일 390)"""
    page.goto(f"{BASE}/add")
    s = lambda n: shot(page, f"{tag}_add_step{n}")
    s(0)
    page.get_by_role("combobox", name="작품").click()
    page.get_by_role("combobox", name="작품").fill("귀멸의 칼날")
    page.keyboard.press("Enter")
    page.get_by_role("combobox", name="캐릭터").click()
    page.locator(".ed-menu li").first.click()
    page.keyboard.press("Escape")
    expect(page.locator(".ed-chip")).to_have_count(1)
    page.get_by_role("button", name="다음").click()
    s(1)
    page.get_by_placeholder("(카페명)을 입력해주세요").fill(f"단계 카페{RUN}")
    page.locator("#ed-addr").fill("서울 성동구 연무장길 33")
    page.get_by_role("button", name="다음").click()
    expect(page.locator(".wiz-title")).to_have_text("이미지")
    expect(page.locator(".wiz-card")).to_contain_text("대략 위치")
    page.locator(".ed-drop input").first.set_input_files(str(TMP / "poster.png"))
    expect(page.locator(".wiz-poster")).to_be_visible()
    s(2)
    page.get_by_role("button", name="다음").click()
    page.locator("input[type=date]").first.fill((date.today() + timedelta(days=1)).isoformat())
    page.get_by_label("종료일 없음 (상시)").check()
    s(3)
    page.get_by_role("button", name="다음").click()
    page.get_by_placeholder("(특전)을 입력해주세요 (예: 랜덤 코스터, 포토카드)").fill("입장 특전 엽서")
    page.get_by_label("포토부스").check()
    page.locator("textarea").first.fill("https://example.com/notice")
    s(4)
    page.get_by_role("button", name="다음").click()
    page.locator("textarea").first.fill("단계별 등록 시험 소개 글")
    s(5)
    page.get_by_role("button", name="다음").click()
    expect(page.locator(".wiz-sum")).to_contain_text(f"단계 카페{RUN}")
    expect(page.locator(".wiz-sum")).to_contain_text("2099.12.31")
    s(6)
    before = len(cafes_local())
    page.get_by_role("button", name="등록하기").click()
    page.wait_for_function("() => location.pathname.startsWith('/popup/')", timeout=30000)
    toast_has(page, "1곳을 지도에 올렸습니다.")
    new = cafes_local()[-1]
    assert len(cafes_local()) == before + 1 and new["source"] == "직접 등록", new
    assert new["end_date"] == "2099-12-31" and "상시" in new["tags"] and "포토부스" in new["tags"], new
    assert new["images"].startswith("/uploads/"), new["images"]
    print(tag, "단계별 등록 OK:", new["entry_id"], new["tags"], new["note"])
    # 모바일 상세 수정하기 탭 · 이력
    page.get_by_role("tab", name="수정하기").click()
    shot(page, f"{tag}_edit_tab")
    page.locator(".hx-exp summary").click()
    shot(page, f"{tag}_history")


def check_append_only(snapshot):
    rows = cafes_local()
    # local 저장소는 파일을 다시 쓸 때 숫자 칸(lat·lng)을 글자로 적는다 → 값만 비교
    norm = lambda rs: [{k: str(v) for k, v in r.items()} for r in rs]
    assert norm(rows[: len(snapshot)]) == norm(snapshot), "앞서 쌓인 행이 바뀌면 안 된다 (append-only)"
    by = {}
    for r in rows:
        by.setdefault(r["entry_id"], []).append(int(r["revision"]))
    for eid, revs in by.items():
        assert revs == list(range(revs[0], revs[0] + len(revs))), (eid, revs)
    assert not any("010-1234-5678" in json.dumps(r, ensure_ascii=False) for r in rows), "전화번호가 저장되면 안 된다"
    print(f"append-only OK: cafes {len(rows)}행 (이번에 {len(rows) - len(snapshot)}행 추가) · 글 {len(by)}개 · 민감정보 없음")


make_files()
snapshot = cafes_local()
with sync_playwright() as p:
    b = p.chromium.launch()
    errs = []
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, service_workers="block")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    cons = []
    page.on("console", lambda m: cons.append(f"{page.url} {m.text[:300] if 'hydrated' not in m.text else m.text[-1500:]}") if m.type == "error" else None)
    try:
        cid, _ = edit_flow(page)
        admin_flow(page, cid)
        quick_flow(page)
        sw = page.evaluate("document.documentElement.scrollWidth")
        print("pc scrollWidth", sw)
        print("pc 콘솔 오류:", cons)
    except Exception:
        print("실패한 화면:", page.evaluate("location.href"), page.locator(".ed-err, .auth-warn").all_inner_texts(), errs)
        shot(page, "fail_pc")
        raise
    ctx.close()

    ctx = b.new_context(viewport={"width": 390, "height": 844}, service_workers="block", is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("console", lambda m: cons.append(f"{page.url} {m.text[:300] if 'hydrated' not in m.text else m.text[-1500:]}") if m.type == "error" else None)
    try:
        signup(page, LID, "m")
        wizard_flow(page, "m")
        for path in ("/add", page.evaluate("location.pathname") + "?tab=edit"):
            page.goto(f"{BASE}{path}")
            page.wait_for_timeout(500)
            sw = page.evaluate("document.documentElement.scrollWidth")
            print("m", path, "scrollWidth", sw)
            assert sw <= 390, f"모바일 가로 스크롤 {sw}"
        page.goto(f"{BASE}/add")
        page.get_by_role("button", name="공지로 간편등록").click()
        page.get_by_label("공지", exact=True).fill(QUICK.replace(str(RUN), f"{RUN}m"))
        page.get_by_role("button", name="읽어오기").click()
        expect(page.locator(".ai-badge")).to_contain_text("규칙 기반 대체", timeout=20000)
        shot(page, "m_quick_read")
        sw = page.evaluate("document.documentElement.scrollWidth")
        assert sw <= 390, f"모바일 가로 스크롤 {sw}"
    except Exception:
        print("실패한 화면:", page.evaluate("location.href"), page.locator(".ed-err, .auth-warn").all_inner_texts(), errs)
        shot(page, "fail_m")
        raise
    ctx.close()
    b.close()
print("페이지 오류:", errs)
print("콘솔 오류:", cons)
assert not errs
check_append_only(snapshot)
print("\n팝업 등록 · 수정하기 점검 통과")
