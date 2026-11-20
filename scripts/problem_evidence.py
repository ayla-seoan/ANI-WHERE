"""문제 정의 근거를 '모은 팝업 데이터'에서 직접 센다 (PRD 1절 '왜 불편한가').

  python -X utf8 scripts/problem_evidence.py          # 화면에 표
  python -X utf8 scripts/problem_evidence.py --save   # docs/problem-evidence.md

왜 (1차 강사 코멘트, 11/20): 문제 정의에 근거를 보태라. 사용자 설문 · 인터뷰(docs/user-test/)와 함께,
"정보가 흩어져 있다" · "팝업은 짧다" 를 우리가 모은 실제 공지 링크 · 기간으로 보여 준다.
- 데이터: data/cafes.json (GitHub 공개 백업, append-only) 의 팝업마다 마지막 기록. 삭제된 팝업은 뺀다.
- 흩어짐: 참고 웹사이트 링크의 도메인 수. recal.kr(우리가 참고하는 모음 사이트)은 따로 센다 —
  '모음 사이트 하나만 보면 되지 않나?' 에 답하려고 모음 사이트를 뺀 공식 출처 수도 같이 본다.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "cafes.json"
OUT = ROOT / "docs" / "problem-evidence.md"
AGG = ("recal.kr",)
SNS = {"x.com", "instagram.com"}
ALIAS = {"twitter.com": "x.com", "m.instagram.com": "instagram.com"}
ALWAYS = "2099-12-31"


def current() -> list[dict]:
    rows = json.loads(DATA.read_text(encoding="utf-8"))
    cur: dict[str, dict] = {}
    for r in rows:
        e = r.get("entry_id")
        if e not in cur or int(r.get("revision") or 0) >= int(cur[e].get("revision") or 0):
            cur[e] = r
    return [r for r in cur.values() if r.get("status") != "deleted"]


def domains(r: dict) -> set[str]:
    out = set()
    for u in re.findall(r"https?://[^\s,]+", str(r.get("links") or "")):
        d = re.sub(r"^www\.", "", u.split("/")[2].lower())
        out.add(ALIAS.get(d, d))
    return out


def _d(s) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def build() -> str:
    rows = current()
    ds = [domains(r) for r in rows]
    linked = [d for d in ds if d]
    official = [d - set(AGG) for d in linked]
    multi = sum(len(d) >= 2 for d in linked)
    multi_off = sum(len(d) >= 2 for d in official)
    has_sns = sum(bool(d & SNS) for d in linked)
    no_official = sum(not d for d in official)
    top = Counter(x for d in linked for x in d).most_common(8)

    spans = []
    for r in rows:
        s, e = _d(r.get("start_date")), _d(r.get("end_date"))
        if s and e and str(r.get("end_date"))[:10] != ALWAYS and e >= s:
            spans.append((e - s).days + 1)
    seoul = sum(str(r.get("address") or "").startswith("서울") for r in rows)

    def pct(a: int, b: int) -> str:
        return f"{a}/{b} ({round(a / b * 100)}%)" if b else "-"

    lines = [
        f"기준: `data/cafes.json` 의 팝업 {len(rows)}곳 (삭제 제외, 팝업마다 마지막 기록) · {datetime.now():%Y-%m-%d} 생성",
        "",
        "## 1. 정보가 흩어져 있다",
        "",
        "| 지표 | 값 |",
        "| --- | --- |",
        f"| 참고 웹사이트 링크가 있는 팝업 | {pct(len(linked), len(rows))} |",
        f"| 정보가 **2곳 이상의 사이트**에 나뉘어 있음 | {pct(multi, len(linked))} · 팝업 하나당 평균 {statistics.mean(len(d) for d in linked):.1f}곳 |",
        f"| 모음 사이트(recal.kr)를 빼도 공식 출처가 2곳 이상 | {pct(multi_off, len(linked))} |",
        f"| 공식 공지가 X · 인스타그램에 있음 (SNS 를 봐야 함) | {pct(has_sns, len(linked))} |",
        f"| 모음 사이트에만 있고 공식 출처 링크가 없음 | {pct(no_official, len(linked))} |",
        "",
        "많이 나온 출처: " + " · ".join(f"{d} {n}" for d, n in top),
        "",
        "## 2. 팝업은 짧고 몰려 있다",
        "",
        "| 지표 | 값 |",
        "| --- | --- |",
        f"| 진행 기간 중앙값 | {statistics.median(spans):.0f}일 (기간이 있는 {len(spans)}곳, '상시' 제외) |",
        f"| 30일 이하 | {pct(sum(x <= 30 for x in spans), len(spans))} |",
        f"| 14일 이하 | {pct(sum(x <= 14 for x in spans), len(spans))} |",
        f"| 서울 | {pct(seoul, len(rows))} |",
        "",
        "## 해석과 한계",
        "",
        "- 팝업 하나의 정보가 평균 2곳 넘는 사이트(모음 사이트 포함)에 나뉘어 있고, 공식 공지는 대부분 X · 인스타그램에 있다 → 한 화면에 모으는 서비스의 근거.",
        "- 이 숫자는 **우리가 모은 팝업 기준**이다 (모으는 방식 · 출처에 치우침이 있을 수 있음). 사용자가 실제로 불편한지는 "
        "설문 · 인터뷰(`docs/user-test/report.md`, `docs/user-test/interviews.md`)로 따로 확인한다.",
        "- 끝난 팝업은 주간 정리로 DB 에서 지워져서(`supabase/migrations/012`) 오래된 팝업은 이 숫자에 덜 들어간다.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    text = build()
    print(text)
    if args.save:
        OUT.write_text("# 문제 정의 근거 — 모은 팝업 데이터에서 센 것\n\n"
                       "`python -X utf8 scripts/problem_evidence.py --save` 가 만든다.\n\n" + text, encoding="utf-8")
        print(f"→ {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
