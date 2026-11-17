"""지표 한 장 요약: 앱 데이터 · 검색 평가 · 사용자 테스트 · 훅 기록을 모아 docs/metrics-log.md 에 날짜별로 쌓는다.

  python scripts/metrics_snapshot.py          # 출력만
  python scripts/metrics_snapshot.py --save   # docs/metrics-log.md 에 추가 (지우지 않고 쌓기)

/stats 화면과 같은 함수(common/stats.py)를 써서 화면 숫자와 문서 숫자가 어긋나지 않는다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import stats  # noqa: E402
from common.storage import Storage  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    all_rows = Storage(worksheet="cafes").all_rows()
    rows = stats.popups(all_rows)
    before = stats.completeness(stats.popups(all_rows, until=stats.NOTION_CUTOFF))
    now = stats.completeness(rows)
    status = stats.status_counts(rows, date.today())
    lines = [
        "### 1. 북극성 지표: 방문 전 정보 완결률",
        f"- 이전({stats.NOTION_CUTOFF} 전, {before['n']}건): **{before['complete']}%**",
        f"- 지금({now['n']}건): **{now['complete']}%**  (변화 {now['complete'] - before['complete']:+.1f}%p)",
        "- 칸별: " + ", ".join(f"{k} {before['fields'].get(k, 0)}→{v}%" for k, v in now["fields"].items()),
        f"- 진행 중 {status['진행 중']} · 예정 {status['예정']} · 종료 {status['종료']}",
        "",
        "### 2. 팝업 Q&A 검색 정확도",
    ]
    ev = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts" / "eval_ask.py")],
                        capture_output=True, text=True, encoding="utf-8")
    lines.append("- " + (ev.stdout.strip().splitlines()[-1] if ev.stdout.strip() else f"실행 실패: {ev.stderr[-200:]}"))
    lines += ["", "### 3. 사용자 테스트"]
    ut = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "scripts" / "user_test_report.py")],
                        capture_output=True, text=True, encoding="utf-8")
    lines.append(ut.stdout.strip() or ut.stderr[-200:])
    lines += ["", "### 4. 훅이 막은 횟수 (logs/hooks.jsonl)"]
    hook_log = ROOT / "logs" / "hooks.jsonl"
    recs = [json.loads(l) for l in hook_log.read_text(encoding="utf-8").splitlines() if l.strip()] if hook_log.exists() else []
    blocked = [r for r in recs if r.get("blocked")]
    lines.append(f"- 막은 횟수 {len(blocked)}회" + (f" (커밋 검사 {sum(r['hook'] == 'precommit_guard' for r in blocked)}, "
                                                 f"프롬프트 덮어쓰기 {sum(r['hook'] == 'edit_rules' for r in blocked)})" if blocked else ""))
    text = "\n".join(lines)
    print(text)
    if args.save:
        out = ROOT / "docs" / "metrics-log.md"
        head = "" if out.exists() else ("# 지표 기록\n\n`python scripts/metrics_snapshot.py --save` 를 돌릴 때마다 아래에 쌓인다. "
                                         "지표 정의는 PRD.md 의 '성공 지표'.\n")
        with out.open("a", encoding="utf-8") as f:
            f.write(f"{head}\n## {datetime.now():%Y-%m-%d %H:%M}\n\n{text}\n")
        print(f"\n→ {out.relative_to(ROOT)} 에 저장")


if __name__ == "__main__":
    main()
