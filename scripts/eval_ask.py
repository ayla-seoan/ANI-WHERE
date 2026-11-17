"""팝업 Q&A 검색 정확도 평가. samples/ask_eval.jsonl 의 질문마다 검색 결과가 조건을 지키는지 본다.

  python scripts/eval_ask.py            # 표 + 요약
  python scripts/eval_ask.py --save     # docs/metrics.md 에 붙일 결과를 docs/ask-eval.md 에 날짜별로 쌓기

채점 (질문 하나 = 1점):
  - empty: true  → 결과가 0건이어야 정답 (데이터에 없는 것을 지어내지 않는가)
  - 그 밖       → 결과가 1건 이상이고, 상위 결과 모두가 work / place / window 조건을 지켜야 정답
오늘 날짜는 2026-11-17 로, 데이터는 그날 전까지 쌓인 기록으로 고정한다 (DATA_ASOF).
저장소가 append-only 라서 매주 Notion 이 새 팝업을 넣어도 평가 기준 데이터는 그대로 되살릴 수 있다.
(실제로 11/17 동기화로 치이카와 팝업이 들어와 "치이카와 팝업 있어?" 의 정답이 바뀌었다 → 고정이 필요했다)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import ask, stats  # noqa: E402
from common.storage import Storage  # noqa: E402

TODAY = date(2026, 11, 17)
DATA_ASOF = "2026-11-17"      # 이 날짜 전까지 쌓인 기록만 평가에 쓴다


def grade(case: dict, query, hits) -> tuple[bool, str]:
    if case.get("empty"):
        return (not hits), ("0건 정상" if not hits else f"{len(hits)}건 나옴 (없어야 함)")
    if not hits:
        return False, "0건 (있어야 함)"
    for h in hits:
        r = h.row
        if case.get("work") and case["work"].replace(" ", "") not in str(r.get("work", "")).replace(" ", ""):
            return False, f"다른 작품 섞임: {r.get('work')}"
        if case.get("place") and not ask._place_match(case["place"], r):
            return False, f"다른 지역 섞임: {r.get('address')}"
        if case.get("window") and not (query.window and ask._overlaps(r, query.window)):
            return False, "날짜 조건 안 맞음"
        if case.get("ongoing") and not ask._ongoing(r, TODAY):
            return False, f"진행 중이 아닌 팝업 섞임: {r.get('work')}"
        if case.get("upcoming") and not (ask.mycal._day(r.get("start_date")) and ask.mycal._day(r.get("start_date")) > TODAY):
            return False, f"이미 시작한 팝업 섞임: {r.get('work')}"
    if case.get("intent") and query.intent != case["intent"]:
        return False, f"질문 종류를 {query.intent or '검색'}(으)로 읽음 (기대: {case['intent']})"
    return True, f"{len(hits)}건 모두 조건 일치"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    rows = stats.popups(Storage(worksheet="cafes").all_rows(), until=DATA_ASOF)
    cases = [json.loads(l) for l in (ROOT / "samples" / "ask_eval.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    lines = ["| # | 질문 | 읽은 조건 | 결과 | 판정 |", "| --- | --- | --- | --- | --- |"]
    ok = 0
    for i, case in enumerate(cases, 1):
        query, hits = ask.find(case["q"], rows, TODAY, case.get("ctx"))
        good, why = grade(case, query, hits)
        ok += good
        lines.append(f"| {i} | {case['q']} | {query.describe()} | {why} | {'O' if good else 'X'} |")
    rate = ok / len(cases) * 100
    summary = f"검색 정확도 {ok}/{len(cases)} = {rate:.0f}%  (오늘 {TODAY} 고정, {DATA_ASOF} 전 기록 팝업 {len(rows)}건)"
    print("\n".join(lines))
    print("\n" + summary)
    if args.save:
        out = ROOT / "docs" / "ask-eval.md"
        head = "" if out.exists() else "# 팝업 Q&A 검색 평가 기록\n\n`python scripts/eval_ask.py --save` 를 돌릴 때마다 아래에 쌓인다.\n"
        with out.open("a", encoding="utf-8") as f:
            f.write(f"{head}\n## {datetime.now():%Y-%m-%d %H:%M}\n\n{summary}\n\n" + "\n".join(lines) + "\n")
        print(f"→ {out.relative_to(ROOT)} 에 저장")


if __name__ == "__main__":
    main()
