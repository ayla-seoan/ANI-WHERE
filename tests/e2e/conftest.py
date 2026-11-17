"""E2E 테스트 준비: 실제 data/ 를 임시 폴더로 복사하고, 그 복사본을 쓰는 Streamlit 을 띄운다.

- 앱은 ANIWHERE_DATA_DIR 이 가리키는 폴더에만 쓴다 → 진짜 data/*.json 은 건드리지 않는다.
- API 키(OpenAI·Notion·Kakao)는 비워서 띄운다. 키가 없어도 앱은 동작해야 한다.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PORT = int(os.getenv("E2E_PORT", "8599"))
BASE_URL = f"http://localhost:{PORT}"


def _healthy() -> bool:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/_stcore/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def data_dir(tmp_path_factory) -> Path:
    """data/ 의 임시 복사본. 테스트가 북마크·리뷰를 쌓아도 여기에만 남는다."""
    dst = tmp_path_factory.mktemp("aniwhere") / "data"
    shutil.copytree(ROOT / "data", dst)
    return dst


@pytest.fixture(scope="session")
def app_url(data_dir) -> str:
    if _healthy():
        pytest.exit(f"포트 {PORT} 에 이미 다른 서버가 떠 있습니다. 끄고 다시 실행하거나 E2E_PORT 를 바꿔 주세요.")
    env = os.environ.copy()
    env.update({
        "STORAGE_MODE": "local",
        "ANIWHERE_DATA_DIR": str(data_dir),
        # 빈 값으로 넣어 두면 load_dotenv() 가 .env 값으로 덮어쓰지 않는다
        "OPENAI_API_KEY": "", "NOTION_TOKEN": "",
        "PYTHONIOENCODING": "utf-8",
        "ANIWHERE_LINKCHECK": "0",      # 참고 웹사이트 확인(외부 요청)은 테스트에서 끈다
    })
    log = open(data_dir.parent / "streamlit.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app_cafemap.py",
         "--server.port", str(PORT), "--server.headless", "true",
         "--browser.gatherUsageStats", "false", "--server.fileWatcherType", "none"],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.time() + 90
        while not _healthy():
            if proc.poll() is not None or time.time() > deadline:
                raise RuntimeError(f"Streamlit 이 뜨지 않았습니다. 로그: {log.name}")
            time.sleep(0.5)
        yield BASE_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=os.getenv("E2E_HEADED") != "1")
        yield b
        b.close()


@pytest.fixture
def page(browser, app_url):
    """테스트마다 새 브라우저 창(새 세션). PC 폭 1400px."""
    ctx = browser.new_context(viewport={"width": 1400, "height": 900}, locale="ko-KR")
    pg = ctx.new_page()
    pg.set_default_timeout(20_000)
    yield pg
    ctx.close()


@pytest.fixture
def mobile_page(browser, app_url):
    """휴대폰 폭 390px 창."""
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="ko-KR",
                              is_mobile=True, has_touch=True, device_scale_factor=3)
    pg = ctx.new_page()
    pg.set_default_timeout(20_000)
    yield pg
    ctx.close()
