"""E2E 테스트(tests/e2e)를 돌리고 결과를 한국어 표로 보여 준 뒤 docs/qa-results.md 에 날짜별로 덧붙인다.

    python scripts/qa_report.py            # 모두 실행
    python scripts/qa_report.py -k 검색     # pytest 옵션은 그대로 넘긴다

통과율(%)은 발표용 지표다. 이전 기록은 지우지 않고 맨 아래에 새 구역을 붙인다.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "qa-results.md"
RESULT = {"passed": "통과", "failed": "실패", "error": "오류", "skipped": "건너뜀"}


def _label(name: str) -> str:
    """test_3_카드를_누르면_상세가_열리고 → 3. 카드를 누르면 상세가 열리고"""
    name = name.split("[")[0].removeprefix("test_")
    num, _, rest = name.partition("_")
    return f"{num}. {rest.replace('_', ' ')}" if num.isdigit() else name.replace("_", " ")


def _cases(xml_path: Path) -> list[dict]:
    out = []
    for tc in ET.parse(xml_path).getroot().iter("testcase"):
        state = "passed"
        for tag in ("failure", "error", "skipped"):
            el = tc.find(tag)
            if el is not None:
                state = "failed" if tag == "failure" else tag
                msg = (el.get("message") or "").splitlines()[0][:120] if el.get("message") else ""
                break
        else:
            msg = ""
        out.append({"name": _label(tc.get("name", "")), "state": state,
                    "time": float(tc.get("time") or 0), "msg": msg})
    return out


def _table(cases: list[dict]) -> str:
    lines = ["| 테스트 이름 | 결과 | 걸린 시간 |", "| --- | --- | ---: |"]
    for c in cases:
        res = RESULT[c["state"]] + (f" — {c['msg']}" if c["msg"] else "")
        lines.append(f"| {c['name']} | {res.replace('|', '/')} | {c['time']:.1f}초 |")
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        xml_path = Path(tmp) / "junit.xml"
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        cmd = [sys.executable, "-m", "pytest", "tests/e2e", "-q", "-p", "no:cacheprovider",
               f"--junitxml={xml_path}", *sys.argv[1:]]
        started = datetime.now()
        proc = subprocess.run(cmd, cwd=ROOT, env=env)
        if not xml_path.exists():
            print("pytest 결과 파일이 만들어지지 않았습니다. 위 출력을 확인해 주세요.")
            return proc.returncode or 1
        cases = _cases(xml_path)

    ran = [c for c in cases if c["state"] != "skipped"]
    passed = sum(c["state"] == "passed" for c in ran)
    rate = 100 * passed / len(ran) if ran else 0.0
    total = sum(c["time"] for c in cases)
    summary = (f"통과율 **{rate:.0f}%** ({passed}/{len(ran)}) · 총 {total:.1f}초"
               + (f" · 건너뜀 {len(cases) - len(ran)}개" if len(cases) != len(ran) else ""))
    table = _table(cases)

    print("\n" + table + "\n\n" + summary.replace("**", ""))

    DOC.parent.mkdir(parents=True, exist_ok=True)
    head = "" if DOC.exists() else (
        "# QA 결과 기록 — Playwright 핵심 흐름 자동 테스트\n\n"
        "`python scripts/qa_report.py` 를 돌릴 때마다 아래에 한 구역씩 쌓인다 (이전 기록은 지우지 않는다).\n"
        "테스트 설명은 `tests/e2e/README.md`.\n")
    section = (f"\n## {started:%Y-%m-%d %H:%M} 실행\n\n{summary}\n\n{table}\n")
    with DOC.open("a", encoding="utf-8") as f:
        f.write(head + section)
    print(f"\n기록을 덧붙였습니다: {DOC.relative_to(ROOT)}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
