"""홈 랭킹 규칙 (common/rank.py) — 웹 web/lib/rank.ts 도 같은 samples/rank_cases.json 으로 시험한다 (npm run test:rank)."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from common import rank

CASES = json.loads((Path(__file__).resolve().parent.parent / "samples" / "rank_cases.json").read_text("utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_rank_case(case):
    sc = rank.scores(case["favorites"], case["reviews"], now=datetime.fromisoformat(case["now"]))
    assert {k: list(v) for k, v in sc.items()} == case["scores"]
    live = [{"entry_id": p["id"], "start_date": p["start"]} for p in case["popups"]]
    assert [r["entry_id"] for r in rank.order(live, sc)] == case["expected"]
