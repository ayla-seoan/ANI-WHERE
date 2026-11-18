"""e2e_member.py 에 더한 점검 (Playwright) — 토스트 · 사진 올리기 · 종 알림 · 최애 추가하기 · 관리자 리뷰 삭제 알림.
실제 Supabase 는 건드리지 않는다. e2e_member.py 와 같은 시험 서버(WEB_STORAGE=local)에, 관리자 번호를 하나 더 넣어 띄운다:
    ADMIN_MEMBER_KEYS=e9b3081fcb7d7356   (아이디 e2e_admin 의 회원 번호)

    python -X utf8 web/scripts/e2e_extra.py http://localhost:3100 <WEB_DATA_DIR> [스크린샷 폴더] [시험 사진 폴더]

시험 사진 폴더에는 a.png 와 위치 정보(EXIF GPS)가 든 gps.jpg 를 둔다 (없으면 여기서 만든다).
"""
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3100"
DATA = Path(sys.argv[2]) if len(sys.argv) > 2 else None
SHOTS = Path(sys.argv[3]) if len(sys.argv) > 3 else None
IMG = Path(sys.argv[4]) if len(sys.argv) > 4 else Path(__file__).resolve().parent / ".e2e-img"
PW = "abcd1234"
ADMIN_ID = "e2e_admin"
ADMIN_KEY = hashlib.sha256(f"popup-cafe-map:member:local:{ADMIN_ID}".encode()).hexdigest()[:16]
TODAY = (datetime.now(timezone.utc) + timedelta(hours=9)).date()


def sha1_8(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def make_images():
    IMG.mkdir(parents=True, exist_ok=True)
    if not (IMG / "a.png").exists():
        Image.new("RGB", (640, 480), (20, 184, 166)).save(IMG / "a.png")
    if not (IMG / "gps.jpg").exists():
        ex = Image.Exif()
        ex[0x010F] = "TestCam"
        ex[0x8825] = {1: "N", 2: (37.0, 33.0, 10.0), 3: "E", 4: (126.0, 58.0, 20.0)}
        Image.new("RGB", (800, 600), (240, 120, 80)).save(IMG / "gps.jpg", exif=ex.tobytes())


def shot(page, name, full=True):
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)


def wait_path(page, path):
    page.wait_for_function("p => location.pathname === p", arg=path, timeout=20000)


def toast(page, text, name=None):
    """가운데 토스트: 글자가 그대로(깨지지 않게) 보이고, 아이콘이 있고, 화면 안에 있고, 다른 것보다 위에 있는지"""
    t = page.locator(".ani-toast")
    expect(t).to_contain_text(text, timeout=10000)
    expect(t).to_have_class("ani-toast show", timeout=3000)
    if name and SHOTS:  # 2.8초 뒤 사라지므로 사진부터 (나타나는 0.18초 움직임이 끝난 뒤)
        page.wait_for_timeout(250)
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{name}.png"), animations="disabled")
    tx = t.locator(".tx").inner_text()
    assert "%" not in tx and "�" not in tx, f"토스트 글자가 깨짐: {tx!r}"
    assert t.locator("svg").count() == 1, "토스트 아이콘이 없음"
    box = t.bounding_box()
    vw = page.viewport_size["width"]
    assert box and box["x"] >= 0 and box["x"] + box["width"] <= vw + 1, f"토스트가 화면 밖: {box}"
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    top = page.evaluate("([x, y]) => { const e = document.elementFromPoint(x, y); return !!e && !!e.closest('.ani-toast'); }", [cx, cy])
    # pointer-events:none 이라 elementFromPoint 로는 아래 것이 잡힌다 → z-index 로 대신 확인
    z = int(page.evaluate("getComputedStyle(document.querySelector('.ani-toast')).zIndex"))
    assert z >= 3000, f"토스트 z-index {z}"
    return tx


def signup(page, lid, nick=""):
    page.goto(f"{BASE}/login")
    page.get_by_role("tab", name="회원가입").click()
    page.fill("input[name=login_id]", lid)
    page.fill("input[name=password]", PW)
    page.fill("input[name=password2]", PW)
    if nick:
        page.fill("input[name=nickname]", nick)
    page.get_by_label("약관 전체 동의").check()
    page.get_by_role("button", name="가입하기").click()
    try:
        wait_path(page, "/")
    except Exception as e:
        raise RuntimeError(f"가입 실패: {page.locator('.auth-warn').all_inner_texts()}") from e


def login(page, lid):
    page.goto(f"{BASE}/login")
    if page.locator(".gnb-me").count():
        page.get_by_role("button", name="로그아웃").click()
        expect(page.locator(".gnb-login")).to_be_visible(timeout=15000)
    page.fill("input[name=login_id]", lid)
    page.fill("input[name=password]", PW)
    page.get_by_role("button", name="로그인", exact=True).click()
    wait_path(page, "/")


def logout(page):
    page.goto(f"{BASE}/login")
    page.get_by_role("button", name="로그아웃").click()
    wait_path(page, "/login")
    expect(page.locator(".gnb-login")).to_be_visible(timeout=15000)  # 같은 주소라 경로만으로는 끝난 걸 모른다


def cafes():
    """시험 서버가 보는 팝업 = GitHub 공개 data/cafes.json (최신 revision, 지운 것 빼고)"""
    raw = json.loads(urllib.request.urlopen(
        "https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main/data/cafes.json", timeout=20).read())
    best = {}
    for r in raw:
        k = str(r["entry_id"])
        if k not in best or int(r["revision"]) >= int(best[k]["revision"]):
            best[k] = r
    return [r for r in best.values() if r.get("status") != "deleted"]


def day(v):
    try:
        return datetime.fromisoformat(str(v)[:10]).date()
    except ValueError:
        return None


def run(page, tag):
    n = int(time.time()) % 100000
    lid = f"x{n}{tag}"
    nick = f"토{n}{tag}"
    # ---- 토스트: 가입 · 로그아웃 · 로그인(한글 닉네임) ----
    signup(page, lid, nick)
    toast(page, "가입했어요!", f"toast_{tag}_signup")
    logout(page)
    toast(page, "로그아웃했어요.", f"toast_{tag}_logout")
    login(page, lid)
    tx = toast(page, f"{nick}님, 환영합니다!", f"toast_{tag}_login")
    print(tag, "토스트 가입·로그아웃·로그인 OK:", tx)

    # ---- 토스트: 북마크 켜기·끄기 ----
    page.goto(f"{BASE}/list")
    card = page.locator(".pcard-wrap").nth(1)
    card.locator(".bm").click()
    toast(page, "북마크했어요. 내 캘린더에서 볼 수 있어요.", f"toast_{tag}_bookmark_on")
    page.wait_for_timeout(3300)
    card.locator(".bm").click()
    toast(page, "북마크를 해제했어요.", f"toast_{tag}_bookmark_off")
    print(tag, "토스트 북마크 OK")

    # ---- 손님이 누름 → 로그인 안내 토스트 ----
    # (아래 관리자 흐름에서 확인)

    # ---- 리뷰 사진 (별점 + 사진만으로 다녀온 후기) ----
    href = page.locator(".pcard-wrap").first.locator("a").first.get_attribute("href")
    page.goto(f"{BASE}{href}")
    box = page.locator(".rvbox")
    box.get_by_role("radio", name="5점").click()
    box.get_by_role("button", name="+ 사진 첨부").click()
    box.locator(".pic-drop input[type=file]").set_input_files([str(IMG / "a.png"), str(IMG / "gps.jpg")])
    expect(box.locator(".pic-one")).to_have_count(2)
    shot(page, f"web_{tag}_review_photo_pick", full=False)
    box.get_by_role("button", name="리뷰 등록").click()
    toast(page, "리뷰를 남겼습니다.", f"toast_{tag}_review_saved")
    th = page.locator(".rv-thread").first
    expect(th.locator(".rv-pics img")).to_have_count(2)
    srcs = th.locator(".rv-pics img").evaluate_all("xs => xs.map(x => x.getAttribute('src'))")
    assert all(s.startswith("/uploads/") for s in srcs), srcs
    if DATA:
        for s in srcs:
            f = DATA / "uploads" / s.rsplit("/", 1)[1]
            im = Image.open(f)
            assert not im.getexif().get_ifd(0x8825), f"위치 정보가 남음: {f}"
            assert not im.getexif().get(0x010F), f"기기 정보가 남음: {f}"
    print(tag, "리뷰 사진 2장 올리기 · 위치 정보 지움 OK", srcs)
    # 수정: 첫 사진은 빼고 한 장 더
    th.get_by_role("button", name="내 글 수정·삭제").click()
    th.get_by_role("button", name="수정", exact=True).click()
    th.locator(".rv-keep-one input[type=checkbox]").first.uncheck()
    th.locator("form.edit .pic-drop input[type=file]").set_input_files([str(IMG / "a.png")])
    th.get_by_role("button", name="저장", exact=True).click()
    toast(page, "수정했습니다.")
    expect(page.locator(".rv-thread").first.locator(".rv-pics img")).to_have_count(2)
    page.wait_for_timeout(500)
    shot(page, f"web_{tag}_review_photo_done")
    print(tag, "리뷰 사진 고치기 OK")

    # ---- 프로필 사진 ----
    page.goto(f"{BASE}/login")
    page.locator("summary", has_text="프로필 사진 바꾸기").click()
    page.locator("input[name=photo]").set_input_files(str(IMG / "gps.jpg"))
    expect(page.locator(".av-preview img")).to_be_visible()
    expect(page.get_by_role("button", name="이 사진으로 저장")).to_be_disabled()  # [선택] 동의 전
    page.locator("input[name=agree]").check()
    shot(page, f"web_{tag}_avatar_pick", full=False)
    page.get_by_role("button", name="이 사진으로 저장").click()
    toast(page, "프로필 사진이 수정되었어요.", f"toast_{tag}_avatar")
    expect(page.locator(".me-avimg")).to_have_attribute("src", __import__("re").compile(r"^/uploads/[0-9a-f]{12}\.webp$"))
    src = page.locator(".me-avimg").get_attribute("src")
    if DATA:
        im = Image.open(DATA / "uploads" / src.rsplit("/", 1)[1])
        assert im.size == (256, 256) and im.format == "WEBP", (im.size, im.format)
        assert not im.getexif().get_ifd(0x8825)
    print(tag, "프로필 사진 256px webp OK", src)
    # ---- 토스트: 닉네임 바꾸기 ----
    nn = f"새{n}{tag}"
    page.fill("input[name=nickname]", nn)
    page.get_by_role("button", name="저장", exact=True).click()
    toast(page, f"닉네임을 '{nn}'(으)로 바꿨어요.", f"toast_{tag}_nickname")
    page.get_by_role("button", name="기본 사진 설정").click()
    toast(page, "기본 사진으로 수정되었어요.")
    print(tag, "닉네임 · 기본 사진 토스트 OK")
    return lid, nn, href


def bell_and_picker(page, tag, lid):
    """종 알림: 북마크한 팝업(종료 D-n) · 모두 읽음 · 쿠키 이름/값이 앱과 같은지 · 내 주변 추천 · 내 캘린더 알림 내역"""
    rows = cafes()
    soon = [r for r in rows if day(r.get("start_date")) and day(r.get("end_date"))
            and day(r["start_date"]) <= TODAY <= day(r["end_date"]) <= TODAY + timedelta(days=3)]
    assert soon, "3일 안에 끝나는 팝업이 없어 시험할 수 없음"
    target = sorted(soon, key=lambda r: str(r["entry_id"]))[0]
    eid = str(target["entry_id"])
    # 최애 추가하기 (홈) 로 북마크
    page.goto(f"{BASE}/")
    page.get_by_role("button", name="최애 추가하기").click()
    dlg = page.locator(".fw-dlg")
    expect(dlg).to_be_visible()
    dlg.locator(".fw-search input").fill(str(target.get("cafe_name") or target.get("work")))
    dlg.locator(".fwc").first.click()
    expect(dlg.locator(".fw-count b")).to_have_text("1")
    shot(page, f"web_{tag}_picker", full=False)
    dlg.get_by_role("button", name="저장하기").click()
    toast(page, "북마크 1개를 저장했어요. 내 캘린더에서 볼 수 있어요.", f"toast_{tag}_picker")
    expect(page.locator(".story.mark")).to_have_count(1)
    print(tag, "최애 추가하기 → 북마크 1개 OK", eid)

    page.reload()
    bell = page.locator(".gnb-bell")
    expect(bell).to_have_class(__import__("re").compile(r"\bdot\b"))
    bell.click()
    pop = page.locator(".bell-pop")
    d = (day(target["end_date"]) - TODAY).days
    label = "오늘 종료" if d == 0 else f"종료 D-{d}"
    expect(pop.locator(".ntf-item", has_text=label)).to_have_count(1)
    shot(page, f"web_{tag}_bell_open", full=False)
    # 앱과 같은 알림 번호 · 쿠키 이름
    import html as _h
    name = _h.escape(f'{target.get("work") or ""} · {target.get("cafe_name") or ""}'.strip(" ·"))
    why = '<div class="ntf-why"><span class="mi " aria-hidden="true">info</span> ' + _h.escape(
        "북마크한 팝업이 곧 끝나요 (종료 3일 전부터 알려 드려요)") + "</div>"
    want_id = sha1_8(f"m{TODAY}{eid}<b>{label}</b> · {name}{why}")
    pop.get_by_role("button", name="모두 읽음").click()
    expect(bell).not_to_have_class(__import__("re").compile(r"\bdot\b"))
    key = hashlib.sha256(f"popup-cafe-map:member:local:{lid}".encode()).hexdigest()[:16]
    cname = f"aw_ntf_read_{hashlib.sha1(key.encode()).hexdigest()[:8]}"
    ck = {c["name"]: c for c in page.context.cookies()}
    assert cname in ck, (cname, list(ck))
    ids = ck[cname]["value"].split(".")
    assert want_id in ids, (want_id, ids)
    assert ck[cname]["sameSite"] == "Lax"
    page.reload()
    expect(page.locator(".gnb-bell")).not_to_have_class(__import__("re").compile(r"\bdot\b"))
    print(tag, "종: 빨간 점 → 모두 읽음 → 새로고침해도 읽음 OK, 쿠키", cname, "번호", want_id)
    # 내 캘린더 '알림 받은 내역' 에서도 같은 번호로 '읽음'
    page.goto(f"{BASE}/calendar")
    today_item = page.locator(".ntf-box .ntf-item", has_text=label).first
    expect(today_item.locator(".ntf-st")).to_have_text("읽음")
    shot(page, f"web_{tag}_calendar_ntf")
    print(tag, "내 캘린더 알림 내역 읽음 공유 OK")

    # 내 주변 추천: 위치를 허용하면 지금 열려 있는 가까운 곳 (북마크한 곳은 빠짐)
    near = [r for r in rows if r.get("lat") not in (None, "") and str(r["entry_id"]) != eid
            and day(r.get("start_date")) and day(r.get("end_date"))
            and day(r["start_date"]) <= TODAY <= day(r["end_date"])]
    if near:
        c = near[0]
        page.context.grant_permissions(["geolocation"], origin=BASE)
        page.context.set_geolocation({"latitude": float(c["lat"]), "longitude": float(c["lng"])})
        page.goto(f"{BASE}/")
        page.locator(".gnb-bell").click()
        expect(page.locator(".bell-pop .ntf-item", has_text="내 주변")).not_to_have_count(0, timeout=15000)
        nid = sha1_8(f"n{TODAY}{c['entry_id']}")
        shot(page, f"web_{tag}_bell_near", full=False)
        page.locator(".bell-pop .ntf-item", has_text="내 주변").first.click()
        page.wait_for_function("() => location.pathname.startsWith('/popup/')", timeout=20000)
        ck = {x["name"]: x for x in page.context.cookies()}
        print(tag, "내 주변 추천 OK (가까운 곳 번호", nid, "읽음 쿠키 수", len(ck[cname]["value"].split(".")), ")")
        page.goto(f"{BASE}/calendar")
        expect(page.locator(".ntf-box .ntf-item", has_text="내 주변")).not_to_have_count(0, timeout=15000)
        shot(page, f"web_{tag}_calendar_near")
        print(tag, "내 캘린더 내 주변 추천 OK")
    return eid


def admin_flow(page, tag, writer_lid, cafe_href):
    """관리자: 남의 리뷰를 사유 없이 지우면 막힘(오류 토스트) → 사유 쓰고 삭제 → 쓴 회원 종에 '받은 알림'"""
    logout(page)
    try:
        signup(page, ADMIN_ID)          # 닉네임은 자동 ('관리자' 같은 이름은 닉네임 규칙에 막힌다)
    except Exception as e:
        print("  (관리자 가입 대신 로그인:", e, ")")
        login(page, ADMIN_ID)           # 앞의 화면 크기에서 이미 가입했으면 로그인
    expect(page.locator(".gnb-admin")).to_be_visible()
    assert page.locator(".gnb-admin").get_attribute("href") == "/data"
    page.goto(f"{BASE}{cafe_href}")
    th = page.locator(".rv-thread").first
    th.get_by_role("button", name="글 삭제 (관리자)").click()
    th.get_by_role("button", name="삭제 (관리자)", exact=True).click()
    page.locator(".dlg").get_by_role("button", name="삭제", exact=True).click()
    toast(page, "삭제 사유를 두 글자 이상", f"toast_{tag}_error")
    page.locator(".dlg textarea").fill("시험용 사유입니다")
    shot(page, f"web_{tag}_admin_review_delete", full=False)
    page.locator(".dlg").get_by_role("button", name="삭제", exact=True).click()
    toast(page, "쓴 사람에게 사유를 알림으로 보냈어요.")
    print(tag, "관리자 리뷰 삭제(사유) OK")
    logout(page)
    login(page, writer_lid)
    expect(page.locator(".gnb-bell")).to_have_class(__import__("re").compile(r"\bdot\b"))
    page.locator(".gnb-bell").click()
    item = page.locator(".bell-pop .ntf-item.plain", has_text="작성하신 리뷰가 삭제되었어요")
    expect(item).to_have_count(1)
    expect(item).to_contain_text("시험용 사유입니다")
    shot(page, f"web_{tag}_bell_inbox", full=False)
    page.goto(f"{BASE}/calendar")
    expect(page.locator(".ntf-box .ntf-item.plain", has_text="작성하신 리뷰가 삭제되었어요")).to_have_count(1)
    print(tag, "받은 알림(리뷰 삭제 사유) — 종 · 내 캘린더 OK")
    # 손님이 북마크를 누르면 로그인 화면 + 안내 토스트
    logout(page)
    page.goto(f"{BASE}/list")
    page.locator(".pcard-wrap").first.locator(".bm").click()
    wait_path(page, "/login")
    toast(page, "북마크는 로그인하면 쓸 수 있어요.", f"toast_{tag}_need_login")
    print(tag, "손님 → 로그인 안내 토스트 OK")


def check_append_only():
    if not DATA:
        return
    for name in ("members", "favorites", "reviews", "notices"):
        f = DATA / f"{name}.json"
        if not f.exists():
            continue
        rows = json.loads(f.read_text(encoding="utf-8"))
        by = {}
        for r in rows:
            by.setdefault(r["entry_id"], []).append(int(r["revision"]))
        for eid, revs in by.items():
            assert revs == list(range(1, len(revs) + 1)), (name, eid, revs)
        print(f"append-only OK: {name} {len(rows)}행")


make_images()
with sync_playwright() as p:
    b = p.chromium.launch()
    for tag, vp in (("pc", {"width": 1440, "height": 900}), ("m", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp, service_workers="block", locale="ko-KR")
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        try:
            lid, _, href = run(page, tag)
            bell_and_picker(page, tag, lid)
            admin_flow(page, tag, lid, href)
        except Exception:
            print("실패한 화면:", page.evaluate("location.href"), errs)
            shot(page, f"fail_extra_{tag}")
            raise
        sw = page.evaluate("document.documentElement.scrollWidth")
        assert sw <= vp["width"], f"가로 스크롤 {sw}"
        print(tag, "scrollWidth", sw, "errors:", errs)
        assert not errs, errs
        ctx.close()
    b.close()
check_append_only()
print("\n토스트 · 사진 · 종 알림 · 최애 추가하기 · 관리자 리뷰 삭제 점검 통과")
