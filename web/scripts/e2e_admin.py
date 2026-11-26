"""관리자 대시보드(/data) · 지표(/stats) · 삭제 요청 끝까지 점검 (Playwright). 실제 Supabase 는 건드리지 않는다 —
시험용 local 저장소로 띄운 서버에만 돈다.

먼저 서버를 시험 모드로 띄운다 (web/ 에서). 관리자 = 아이디 e2e_admin 의 회원 번호:
    NEXT_DIST_DIR=.next-a WEB_STORAGE=local WEB_DATA_DIR=<빈 임시 폴더> WEB_OAUTH_MOCK=1 \
    AUTH_SECRET=test-secret-1234567890 SITE_URL=http://localhost:3201 ADMIN_MEMBER_KEYS=e9b3081fcb7d7356 \
    npx next dev -p 3201
그다음:
    python -X utf8 web/scripts/e2e_admin.py http://localhost:3201 <WEB_DATA_DIR> [스크린샷 폴더]

흐름: 관리자 가입(e2e_admin) → /data 사이드바 8페이지 (A안 11/26, PC 1440 · 모바일 390 스크린샷, 가로 스크롤 없음) →
일반 회원 가입 → /data 는 '관리자 전용' · 관리자 서버 액션(CSV 포함)을 직접 불러도 거절(기록 안 늘어남) → 일반 회원 삭제 요청
(상세 '삭제 요청' 버튼이 있으면 화면으로, 없으면 같은 서버 액션을 직접 부른다) → 짧은 이유 · 중복 요청 거절 →
관리자 승인 → 대상 팝업 '삭제됨' 새 행 + 요청자 알림 → 알림 규칙: 오픈 일수 저장 · '삭제 요청 거부' 끄기 →
거부(사유 없음 거절 → 사유 적고 거부) → 꺼진 규칙이라 알림 없이 기록만 → 규칙 다시 켜기 →
공지 추가 · 수정 · 삭제 (개인정보 든 공지 거절) → /stats (PC · 모바일).
마지막에 local 파일이 append-only 로 쌓였는지(revision 이 1씩 늘어남) 확인한다.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3201"
DATA = Path(sys.argv[2]) if len(sys.argv) > 2 else None
SHOTS = Path(sys.argv[3]) if len(sys.argv) > 3 else None
WEB = Path(__file__).resolve().parent.parent
NEXT_DIR = WEB / os.environ.get("NEXT_DIST_DIR", ".next-a")
ADMIN_ID, ADMIN_KEY, PW = "e2e_admin", "e9b3081fcb7d7356", "abcd1234"
USER_ID = f"e2e_req{int(time.time()) % 100000}"
TABS = [("home", "한눈에 보기"), ("board", "팝업 현황"), ("usage", "이용 지표"), ("requests", "삭제 요청"),
        ("notices", "알림 관리"), ("members", "회원 정보"), ("raw", "원본 데이터"), ("survey", "사용자 테스트")]


def shot(page, name):
    if SHOTS:
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)


def wait_path(page, path):
    page.wait_for_function("p => location.pathname === p", arg=path, timeout=20000)


def toast_has(page, text):
    expect(page.locator(".ani-toast")).to_contain_text(text, timeout=15000)


def table(name):
    f = DATA / f"{name}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def latest(rows):
    out = {}
    for r in rows:
        if r["entry_id"] not in out or int(r["revision"]) >= int(out[r["entry_id"]]["revision"]):
            out[r["entry_id"]] = r
    return out


def no_hscroll(page, label):
    sw = page.evaluate("document.documentElement.scrollWidth")
    vw = page.evaluate("window.innerWidth")
    assert sw <= vw, f"{label}: 가로 스크롤이 생김 (scrollWidth {sw} > {vw})"


def login_or_signup(page, lid):
    page.goto(f"{BASE}/login")
    if page.locator(".gnb-me").count():
        page.get_by_role("button", name="로그아웃").click()
        wait_path(page, "/login")
    page.fill("input[name=login_id]", lid)
    page.fill("input[name=password]", PW)
    page.get_by_role("button", name="로그인", exact=True).click()
    try:
        wait_path(page, "/")
        return
    except Exception:
        pass
    page.goto(f"{BASE}/login")
    page.get_by_role("tab", name="회원가입").click()
    page.fill("input[name=login_id]", lid)
    page.fill("input[name=password]", PW)
    page.fill("input[name=password2]", PW)
    page.get_by_label("약관 전체 동의").check()
    page.get_by_role("button", name="가입하기").click()
    wait_path(page, "/")
    expect(page.locator(".gnb-me")).to_be_visible()


def action_ids():
    """서버 액션 번호 (dev 서버가 만든 server-reference-manifest). 관리자 화면을 한 번 연 뒤에 읽는다."""
    f = NEXT_DIR / "server" / "server-reference-manifest.json"
    man = json.loads(f.read_text(encoding="utf-8"))
    out = {}
    for aid, info in man.get("node", {}).items():
        name = info.get("exportedName") or ""
        if not name:
            # 예전 형식: workers 안의 모듈 이름으로만 알 수 있다 → 아래에서 직접 찾는다
            continue
        out[name] = aid
    return out


def call_action(ctx, aid, fields, path="/data"):
    """브라우저 폼과 같은 모양(React encodeReply: [이전 상태, FormData])으로 서버 액션을 직접 부른다."""
    multipart = {f"_1_{k}": v for k, v in fields.items()}
    multipart["0"] = '[null,"$K1"]'
    res = ctx.request.post(f"{BASE}{path}", headers={"Next-Action": aid, "Accept": "text/x-component"},
                           multipart=multipart)
    return res.status, res.text()


def call_args(ctx, aid, args, path="/data"):
    """인자를 그대로 받는 서버 액션 (예: rawCsvAction(table, onlyNow, q)) 을 직접 부른다."""
    res = ctx.request.post(f"{BASE}{path}", headers={"Next-Action": aid, "Accept": "text/x-component",
                                                      "Content-Type": "text/plain;charset=UTF-8"},
                           data=json.dumps(args))
    return res.status, res.text()


def pick_popups():
    """시험에 쓸 팝업 두 곳 (local 모드 팝업 표 = GitHub 공개 cafes.json + 이 폴더 기록)"""
    raw = json.loads(urllib.request.urlopen(
        "https://raw.githubusercontent.com/ayla-seoan/ANI-WHERE/main/data/cafes.json", timeout=20).read())
    own = table("cafes")
    cur = latest(raw + own)
    ok = [r for r in cur.values() if r["status"] == "active" and r.get("work") and r.get("cafe_name")]
    ok.sort(key=lambda r: r["entry_id"])
    return ok[0], ok[1]


def admin_tabs(page, tag):
    page.goto(f"{BASE}/data")
    expect(page.locator(".ax-h1")).to_contain_text("오늘 처리할 일")
    expect(page.locator(".ax-menu a.on")).to_contain_text("한눈에 보기")
    expect(page.locator(".ax-kpi")).to_have_count(5)
    expect(page.locator(".gnb-wrap")).to_be_hidden()   # 관리자 화면은 서비스 메뉴바 대신 사이드바
    for key, label in TABS:
        page.locator(".ax-menu").get_by_role("link", name=re.compile("^" + label)).click()
        page.wait_for_function("k => (new URLSearchParams(location.search).get('tab') || 'home') === k", arg=key,
                               timeout=20000)
        expect(page.locator(".ax-menu a.on")).to_contain_text(label)
        page.wait_for_load_state("networkidle")
        no_hscroll(page, f"{tag} {key}")
        shot(page, f"data_{tag}_{key}")
    # 사용자 테스트: 설문 자료가 있으면(SURVEY_SHEET_ID, 시험은 local 의 SURVEY_CSV_FILE) 세 보기 모두
    page.goto(f"{BASE}/data?tab=survey")
    if page.locator(".st-seg").count():
        for sv, label in (("2", "2차 자세히"), ("1", "1차 자세히"), ("improve", "1차 → 2차 개선")):
            page.locator(".st-seg").get_by_role("tab", name=label).click()
            expect(page.locator(".st-seg a.on")).to_contain_text(label)
            page.wait_for_load_state("networkidle")
            no_hscroll(page, f"{tag} survey {sv}")
            shot(page, f"data_{tag}_survey_{sv}")
        print(tag, "사용자 테스트 세 보기 OK")
    # 숫자 카드 → 목록 펼치기 · 닫기
    page.goto(f"{BASE}/data")
    page.locator(".ax-kpi").nth(1).click()
    expect(page.locator(".ax-kpilist")).to_be_visible()
    no_hscroll(page, f"{tag} kpi")
    shot(page, f"data_{tag}_kpi_live")
    page.get_by_role("link", name="목록 닫기").click()
    expect(page.locator(".ax-kpilist")).to_have_count(0)
    # 주 이동 (다음 주 → 이번 주)
    page.get_by_role("link", name="다음 주").click()
    expect(page.get_by_role("link", name="이번 주", exact=True)).to_be_visible()
    page.get_by_role("link", name="이번 주", exact=True).click()
    expect(page.locator(".ax-wk-label")).to_contain_text("이번 주")
    # 예전 주소(?tab=board)도 그대로 열린다
    page.goto(f"{BASE}/data?tab=board")
    expect(page.locator(".ax-menu a.on")).to_contain_text("팝업 현황")
    print(tag, "관리자 페이지 8개 · 숫자 카드 · 주 이동 · 예전 주소 OK")


def stats_pages(page, tag):
    page.goto(f"{BASE}/stats")
    expect(page.locator(".stats-title")).to_have_text("ANI:WHERE 지표")
    expect(page.locator(".mt").first).to_be_visible()
    page.wait_for_load_state("networkidle")
    no_hscroll(page, f"{tag} stats")
    shot(page, f"stats_{tag}")
    print(tag, "/stats OK")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        errs = []

        def new(vp):
            ctx = b.new_context(viewport=vp, service_workers="block")
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errs.append(str(e)))
            return ctx, pg

        # ---- 1) 관리자: 가입 → 탭 · 스크린샷 (PC) ----
        actx, ap = new({"width": 1440, "height": 900})
        login_or_signup(ap, ADMIN_ID)
        assert ADMIN_KEY in latest(table("members")), "e2e_admin 회원 번호가 ADMIN_MEMBER_KEYS 와 다르다 (REVIEW_NICK_SALT?)"
        admin_tabs(ap, "pc")
        ids = action_ids()
        for need in ("requestDeleteAction", "decideAction", "noticeSaveAction", "ruleSaveAction", "rawCsvAction"):
            assert need in ids, f"서버 액션 번호를 찾지 못함: {need} ({sorted(ids)})"

        # ---- 2) 일반 회원: /data 못 봄 + 관리자 액션 직접 불러도 거절 ----
        uctx, up = new({"width": 1440, "height": 900})
        login_or_signup(up, USER_ID)
        mem = latest(table("members"))
        user_key = max((r for r in mem.values() if r["entry_id"] != ADMIN_KEY), key=lambda r: r["updated_at"])["entry_id"]
        up.goto(f"{BASE}/data")
        expect(up.locator(".stats-title")).to_have_text("관리자 전용")
        expect(up.get_by_role("link", name="로그인하기")).to_be_visible()
        expect(up.locator(".ax-kpi")).to_have_count(0)
        expect(up.locator(".ax-side")).to_have_count(0)
        shot(up, "data_user_denied")
        before = {n: len(table(n)) for n in ("notices", "alert_rules", "del_requests", "cafes")}
        st, body = call_action(uctx, ids["noticeSaveAction"], {"entry_id": "", "title": "해킹 공지", "body": "보이면 안 됨"})
        assert "관리자만" in body, (st, body[:300])
        st, body = call_action(uctx, ids["ruleSaveAction"], {"rule": "open", "enabled": "0", "days": "3", "max_items": "8"})
        assert "관리자만" in body, (st, body[:300])
        st, body = call_action(uctx, ids["decideAction"], {"entry_id": "x", "approve": "1", "admin_reason": ""})
        assert "관리자만" in body, (st, body[:300])
        st, body = call_args(uctx, ids["rawCsvAction"], ["members", False, ""])
        assert "관리자만" in body and "e9b3081" not in body, (st, body[:300])
        after = {n: len(table(n)) for n in before}
        assert before == after, ("관리자 아닌 사람의 요청으로 기록이 늘면 안 된다", before, after)
        # 손님(로그인 안 함)도 거절
        gctx, gp = new({"width": 1440, "height": 900})
        gp.goto(f"{BASE}/data")
        expect(gp.locator(".stats-title")).to_have_text("관리자 전용")
        st, body = call_action(gctx, ids["noticeSaveAction"], {"entry_id": "", "title": "손님 공지", "body": "x"})
        assert "관리자만" in body, (st, body[:300])
        st, body = call_args(gctx, ids["rawCsvAction"], ["members", False, ""])
        assert "관리자만" in body, (st, body[:300])
        st, body = call_action(gctx, ids["requestDeleteAction"],
                               {"target_type": "cafe", "target_id": "abc", "title": "t", "reason": "손님은 못 보내요"})
        assert "로그인한 회원만" in body, (st, body[:300])
        gctx.close()
        print("일반 회원 · 손님: /data 안내 + 관리자 서버 액션 거절 OK (기록 그대로)")

        # ---- 3) 일반 회원: 삭제 요청 (두 팝업) ----
        pa, pb = pick_popups()
        via_ui = False
        up.goto(f"{BASE}/popup/{pa['entry_id']}")
        tab = up.get_by_role("tab", name="수정하기")
        if tab.count():
            tab.first.click()
        btn = up.get_by_role("button", name="삭제 요청", exact=True)
        if btn.count():
            via_ui = True
            btn.first.click()
            dlg = up.locator(".dr-dlg")
            expect(dlg).to_be_visible()
            shot(up, "delete_request_dialog_pc")
            dlg.locator("textarea").fill("짧음")
            dlg.get_by_role("button", name="요청 보내기").click()
            expect(dlg.locator(".dr-warn")).to_contain_text("5자 이상")
            dlg.locator("textarea").fill("이미 끝난 행사예요. 지도에서 내려 주세요")
            dlg.get_by_role("button", name="요청 보내기").click()
            toast_has(up, "삭제 요청을 보냈어요")
            print("상세 '삭제 요청' 버튼으로 요청 OK")
        else:
            title = f"{pa['work']} · {pa['cafe_name']}"
            st, body = call_action(uctx, ids["requestDeleteAction"],
                                   {"target_type": "cafe", "target_id": pa["entry_id"], "title": title, "reason": "짧음"},
                                   path=f"/popup/{pa['entry_id']}")
            assert "5자 이상" in body, body[:300]
            st, body = call_action(uctx, ids["requestDeleteAction"],
                                   {"target_type": "cafe", "target_id": pa["entry_id"], "title": title,
                                    "reason": "이미 끝난 행사예요. 지도에서 내려 주세요"}, path=f"/popup/{pa['entry_id']}")
            assert "삭제 요청을 보냈어요" in body, body[:300]
            print("상세에 '삭제 요청' 버튼이 아직 없어 같은 서버 액션을 직접 불러 요청 OK")
        # 같은 글에 또 → 거절
        st, body = call_action(uctx, ids["requestDeleteAction"],
                               {"target_type": "cafe", "target_id": pa["entry_id"], "title": "x",
                                "reason": "한 번 더 보내 봐요 거절돼야 해요"})
        assert "아직 처리 중" in body, body[:300]
        # 전화번호 든 이유 → 거절
        st, body = call_action(uctx, ids["requestDeleteAction"],
                               {"target_type": "cafe", "target_id": pb["entry_id"], "title": "x",
                                "reason": "연락은 010-1234-5678 로 주세요"})
        assert "개인정보" in body, body[:300]
        st, body = call_action(uctx, ids["requestDeleteAction"],
                               {"target_type": "cafe", "target_id": pb["entry_id"],
                                "title": f"{pb['work']} · {pb['cafe_name']}", "reason": "같은 행사가 두 번 올라왔어요"})
        assert "삭제 요청을 보냈어요" in body, body[:300]
        reqs = latest(table("del_requests"))
        mine = [r for r in reqs.values() if r["requester"] == user_key and r["decision"] == "pending"]
        assert len(mine) == 2, mine
        assert all(r["requester_nick"].endswith(f"#m{user_key[:4]}") for r in mine), mine
        print("짧은 이유 · 중복 요청 · 전화번호 거절, 대기 요청 2건 OK")

        # ---- 4) 관리자: 승인 ----
        ap.goto(f"{BASE}/data?tab=requests")
        n_pend = sum(1 for r in latest(table("del_requests")).values() if r["decision"] == "pending")
        expect(ap.locator(".ax-menu a.on")).to_contain_text("삭제 요청")
        expect(ap.locator(".ax-menu a.on .ax-badge")).to_have_text(str(n_pend))
        expect(ap.locator(".ax-tabs2 a.on")).to_have_text(f"대기 {n_pend}")
        shot(ap, "data_pc_requests_pending")
        # 한눈에 보기 '처리할 일'에도 대기 요청이 모두 보인다
        ap.goto(f"{BASE}/data")
        expect(ap.locator(".ax-todo-i", has_text="삭제 요청")).to_have_count(n_pend)
        ap.goto(f"{BASE}/data?tab=requests")
        if pa["cafe_name"] not in ap.locator(".ax-req-open").inner_text():
            ap.locator(".ax-req-mini", has_text=pa["cafe_name"]).get_by_role("link", name="열어서 처리").click()
            expect(ap.locator(".ax-req-open")).to_contain_text(pa["cafe_name"])
        ap.locator(".ax-req-open").get_by_role("button", name="승인하고 내리기").click()
        toast_has(ap, "승인했어요")
        cafes = latest(table("cafes"))
        assert cafes[pa["entry_id"]]["status"] == "deleted", cafes.get(pa["entry_id"])
        assert cafes[pa["entry_id"]]["source"] == "삭제 요청 승인"
        assert cafes[pa["entry_id"]]["cafe_name"] == pa["cafe_name"], "삭제 행은 내용을 그대로 옮겨 쌓는다"
        ok_notice = [r for r in table("notices") if r["target"] == user_key and r["kind"] == "삭제 승인"]
        assert len(ok_notice) == 1 and pa["cafe_name"] in ok_notice[0]["body"], ok_notice
        print("승인 → 팝업 '삭제됨' 새 행 + 요청자 알림 OK")

        # ---- 5) 알림 규칙: 오픈 일수 5 · '삭제 요청 거부' 끄기 ----
        ap.goto(f"{BASE}/data?tab=notices")
        row = ap.locator("tr[data-rule=open]")
        row.locator("input[name=days]").fill("5")
        row.get_by_role("button", name="저장", exact=True).click()
        toast_has(ap, "'북마크한 팝업 오픈' 규칙을 저장했어요")
        expect(ap.locator("tr[data-rule=open]")).to_contain_text("오픈 5일 전부터")
        expect(ap.locator("tr[data-rule=open] input[name=days]")).to_have_value("5")
        ap.locator("tr[data-rule=del_no]").get_by_role("switch").click()
        toast_has(ap, "'삭제 요청 거부' 규칙을 껐어요")
        expect(ap.locator("tr[data-rule=del_no]")).to_contain_text("꺼짐")
        expect(ap.locator("tr[data-rule=del_no]").get_by_role("switch")).to_have_attribute("aria-checked", "false")
        # 랭크 승급(제안)은 꺼진 채 표시만 (누를 수 없음)
        expect(ap.get_by_role("switch", name=re.compile("랭크 승급"))).to_be_disabled()
        shot(ap, "data_pc_notices_rules")
        print("알림 규칙 저장 · 끄기 OK")

        # ---- 6) 거부: 사유 없이 → 막힘, 사유 적고 → 기록만 (규칙이 꺼져 알림 없음) ----
        ap.goto(f"{BASE}/data?tab=requests")
        item = ap.locator(".ax-req-open")
        expect(item).to_contain_text(pb["cafe_name"])
        item.get_by_role("button", name="거부", exact=True).click()
        toast_has(ap, "거부 사유를 적어 주세요")
        item.locator("textarea[name=admin_reason]").fill("같은 행사가 아니에요")
        item.get_by_role("button", name="거부", exact=True).click()
        toast_has(ap, "거부했어요")
        reqs = latest(table("del_requests"))
        rej = [r for r in reqs.values() if r["target_id"] == pb["entry_id"]][0]
        assert rej["decision"] == "rejected" and rej["admin_reason"] == "같은 행사가 아니에요", rej
        assert not [r for r in table("notices") if r["target"] == user_key and r["kind"] == "삭제 거부"], \
            "꺼진 규칙이면 거부 알림이 가면 안 된다"
        assert latest(table("cafes")).get(pb["entry_id"], {}).get("status") != "deleted", "거부하면 팝업은 그대로"
        ap.locator(".ax-tabs2").get_by_role("tab", name=re.compile("처리 완료")).click()
        expect(ap.locator(".ax-tbl")).to_contain_text("같은 행사가 아니에요")
        expect(ap.locator(".ax-tbl")).to_contain_text("승인")
        shot(ap, "data_pc_requests_done")
        print("거부: 사유 필수 · 꺼진 규칙이라 알림 없이 기록만 OK")
        # 규칙 다시 켜기
        ap.goto(f"{BASE}/data?tab=notices")
        ap.locator("tr[data-rule=del_no]").get_by_role("switch").click()
        toast_has(ap, "'삭제 요청 거부' 규칙을 저장했어요")
        expect(ap.locator("tr[data-rule=del_no]")).to_contain_text("켜짐")

        # ---- 7) 공지: 개인정보 거절 → 추가 → 수정 → 삭제 ----
        ed = ap.locator(".ax-nform")
        ed.locator("input[name=title]").fill("e2e 공지")
        ed.locator("textarea[name=body]").fill("문의는 test@example.com")
        ed.get_by_role("button", name="공지 보내기").click()
        toast_has(ap, "개인정보는 넣을 수 없어요")
        ed.locator("textarea[name=body]").fill("이번 주말 점검이 있어요")
        ed.get_by_role("button", name="공지 보내기").click()
        toast_has(ap, "공지를 저장했어요")
        item = ap.locator(".ax-nitem", has_text="e2e 공지")
        expect(item).to_contain_text("수정 0회")
        expect(item).to_contain_text("보이는 중")
        item.get_by_role("button", name="수정").click()
        expect(ap.locator(".ax-nform-h")).to_have_text("공지 수정")
        ap.locator(".ax-nform textarea[name=body]").fill("이번 주말 점검이 있어요 (시간 변경)")
        ap.locator(".ax-nform").get_by_role("button", name="수정 저장").click()
        toast_has(ap, "공지를 저장했어요")
        item = ap.locator(".ax-nitem", has_text="e2e 공지")
        expect(item).to_contain_text("수정 1회")
        shot(ap, "data_pc_notices_saved")
        # 회원 종 알림에도 보인다
        up.goto(f"{BASE}/")
        nt = [r for r in table("notices") if r["target"] == "all" and r["title"] == "e2e 공지"]
        assert len(nt) == 2 and {int(r["revision"]) for r in nt} == {1, 2}, nt
        item.get_by_role("button", name="삭제").click()
        toast_has(ap, "공지를 삭제했어요")
        expect(ap.locator(".ax-nitem", has_text="e2e 공지")).to_have_count(0)
        assert latest(table("notices"))[nt[0]["entry_id"]]["status"] == "deleted"
        print("공지 개인정보 거절 · 추가 · 수정(revision 2) · 삭제(새 행) OK")

        # ---- 8) 원본 데이터: 표 바꾸기 · 찾기 · 최신만 ----
        ap.goto(f"{BASE}/data?tab=raw")
        ap.locator(".ax-tabsel").get_by_role("tab", name=re.compile("삭제 요청")).click()
        expect(ap.locator(".ax-rawt")).to_contain_text("approved")
        ap.locator("input[name=q]").fill(pb["entry_id"])
        ap.locator("input[name=q]").press("Enter")
        expect(ap.locator(".ax-rawcount")).to_contain_text("2행")
        ap.get_by_role("radio", name="지금 내용만").click()
        expect(ap.locator(".ax-rawcount")).to_contain_text("1행")
        ap.wait_for_load_state("networkidle")
        # CSV 내려받기: 화면과 같은 조건(찾기 · 지금 내용만)
        with ap.expect_download() as dl:
            ap.get_by_role("button", name="CSV 내려받기").click()
        lines = [ln for ln in Path(dl.value.path()).read_text(encoding="utf-8-sig").splitlines() if ln]
        assert lines[0].startswith("row_id,entry_id,revision") and len(lines) == 2 and pb["entry_id"] in lines[1], lines
        # 북마크 표의 회원 칸(user)은 CSV 에도 없다
        ap.goto(f"{BASE}/data?tab=raw&t=favorites")
        ap.wait_for_load_state("networkidle")   # 버튼이 살아난 뒤에 누른다
        with ap.expect_download() as dl:
            ap.get_by_role("button", name="CSV 내려받기").click()
        head = Path(dl.value.path()).read_text(encoding="utf-8-sig").splitlines()[0]
        assert "user" not in head.split(","), head
        print("원본 데이터 표 · 찾기 · 지금 내용만 · CSV OK")

        # ---- 9) /stats (PC) · 모바일 관리자 탭 · /stats (모바일) ----
        stats_pages(ap, "pc")
        mctx, mp = new({"width": 390, "height": 844})
        login_or_signup(mp, ADMIN_ID)
        admin_tabs(mp, "m")
        stats_pages(mp, "m")
        # 모바일 삭제 요청 대화상자 (상세 버튼이 있을 때만)
        if via_ui:
            mu, mup = new({"width": 390, "height": 844})
            login_or_signup(mup, USER_ID)
            mup.goto(f"{BASE}/popup/{pb['entry_id']}")
            if mup.get_by_role("tab", name="수정하기").count():
                mup.get_by_role("tab", name="수정하기").first.click()
            mup.get_by_role("button", name="삭제 요청", exact=True).first.click()
            box = mup.locator(".dr-dlg").bounding_box()
            assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390, box
            shot(mup, "delete_request_dialog_m")
            mu.close()
        for c in (actx, uctx, mctx):
            c.close()
        b.close()
        assert not errs, errs


def check_append_only():
    if not DATA:
        return
    for name in ("members", "del_requests", "notices", "alert_rules", "cafes", "visits"):
        rows = table(name)
        by = {}
        for r in rows:
            by.setdefault(r["entry_id"], []).append(int(r["revision"]))
        for eid, revs in by.items():
            if name == "cafes":   # local 팝업 표는 GitHub 기록 다음 번호부터 이어 쌓는다
                assert revs == list(range(revs[0], revs[0] + len(revs))), (name, eid, revs)
            else:
                assert revs == list(range(1, len(revs) + 1)), (name, eid, revs)
        print(f"append-only OK: {name} {len(rows)}행 · 글 {len(by)}개")
    assert not any("010-1234-5678" in r["reason"] for r in table("del_requests")), "전화번호가 저장되면 안 된다"
    assert not any("test@example.com" in r["body"] for r in table("notices")), "이메일이 저장되면 안 된다"
    print("민감정보 저장 없음 OK")


main()
check_append_only()
print("\n관리자 · 지표 · 삭제 요청 점검 통과")
