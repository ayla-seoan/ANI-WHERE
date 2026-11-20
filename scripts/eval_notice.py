"""공지 → 등록 칸 채우기 정확도: 1차 규칙(common/cafe.rule_based) vs 2차 규칙(common/notice.parse_notice).

  python -X utf8 scripts/eval_notice.py          # 표 출력
  python -X utf8 scripts/eval_notice.py --save   # docs/notice-eval.md 에 저장
  python -X utf8 scripts/eval_notice.py --ai     # OPENAI_API_KEY 가 있으면 cafe 프롬프트 v1 · v2 도 같은 세트로

정답: samples/notice_eval.jsonl (입력은 1차 때 만든 samples/tweets_sample.txt 10건 + tweets_edge_cases.txt 4건을 그대로 쓴다.
2차 규칙을 만들기 전에 있던 파일이라 2차에 유리하게 고른 입력이 아니다). 정답은 원문을 읽고 사람이 적었다.
'오늘'은 샘플을 만든 시점에 맞춰 2026-11-01 로 고정한다.

칸별 채점
- 작품 · 카페명: 띄어쓰기 · 문장부호를 뺀 뒤 정답이 결과 안에 있으면 맞음
- 지역: 결과 주소에 정답 지역 낱말(예: 서울 · 강남) 중 하나가 있으면 맞음 (주소가 없으면 틀림)
- 기간: 시작일 · 종료일이 모두 같으면 맞음 (정답 기간이 없는 '날짜 역전'은 채점에서 뺀다)
- 캐릭터: 집합이 같으면 맞음
- 특전 · 굿즈: 항목 단위 정밀도 · 재현율 → F1 (정답 낱말이 결과 항목 안에 들어 있으면 같은 항목)
- 검토 신호: 정상 10건은 신호가 없어야(오경보), 까다로운 4건은 신호가 있어야(놓침) 맞음
  1차 = confidence 'low', 2차 = status 가 '자동등록' 이 아님
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import cafe, notice  # noqa: E402

GOLD = ROOT / "samples" / "notice_eval.jsonl"
TODAY = date(2026, 11, 1)
FIELDS = ["작품", "카페명", "지역", "기간", "캐릭터"]


def _norm(s: str) -> str:
    return re.sub(r"[\s!·.,'\"『』「」\[\]【】#]", "", str(s or "")).lower()


def _texts() -> dict[str, list[str]]:
    out = {}
    for name in ("tweets_sample.txt", "tweets_edge_cases.txt"):
        out[name] = [b.strip() for b in (ROOT / "samples" / name).read_text(encoding="utf-8").split("---")]
    return out


def run_v1(text: str) -> dict:
    res = cafe.rule_based(text, today=TODAY)
    if not res.entries:
        return {"flag": True}
    e = res.entries[0]
    return {"work": e.work, "cafe": e.cafe_name, "address": e.address, "start": e.start_date, "end": e.end_date,
            "characters": e.characters, "perks": e.perks, "goods": e.goods, "flag": e.confidence == "low"}


def run_v2(text: str) -> dict:
    g = notice.parse_notice(text, today=TODAY)
    return {"work": g.get("work"), "cafe": g.get("cafe_name"),
            "address": " ".join(x for x in (g.get("address"), g.get("area")) if x),
            "start": g.get("start_date"), "end": g.get("end_date"), "characters": g.get("characters") or [],
            "perks": g.get("perks") or [], "goods": g.get("goods") or [], "flag": g.get("status") != "자동등록",
            "reasons": g.get("reasons") or []}


def run_ai(version: str):
    from common import ai
    from common.schema import CafeExtraction

    def go(text: str) -> dict:
        res = ai.call_structured("cafe", f"오늘: {TODAY.isoformat()}\n\n{text}", CafeExtraction, version=version)
        if not res.ok or not res.data.entries:
            return {"flag": True, "error": res.error}
        e = res.data.entries[0]
        return {"work": e.work, "cafe": e.cafe_name, "address": e.address, "start": e.start_date, "end": e.end_date,
                "characters": e.characters, "perks": e.perks, "goods": e.goods, "flag": e.confidence == "low"}
    return go


def _items(gold: list[str], got: list[str]) -> tuple[int, int, int]:
    """(맞은 수, 정답 수, 결과 수)"""
    g, p = [_norm(x) for x in gold], [_norm(x) for x in got if _norm(x)]
    hit = sum(any(x in y or y in x for y in p) for x in g)
    return hit, len(g), len(p)


def score(gold: dict, got: dict) -> dict:
    s: dict = {}
    s["작품"] = bool(got.get("work")) and _norm(gold["work"]) in _norm(got.get("work"))
    s["카페명"] = bool(got.get("cafe")) and _norm(gold["cafe"]) in _norm(got.get("cafe"))
    s["지역"] = any(t in str(got.get("address") or "") for t in gold["region"])
    if gold["start"]:
        s["기간"] = str(got.get("start")) == gold["start"] and str(got.get("end")) == gold["end"]
    s["캐릭터"] = {_norm(x) for x in gold["characters"]} == {_norm(x) for x in got.get("characters") or []}
    s["특전"] = _items(gold["perks"], got.get("perks") or [])
    s["굿즈"] = _items(gold["goods"], got.get("goods") or [])
    s["신호"] = bool(got.get("flag")) == gold["flag"]
    return s


def summarize(rows: list[tuple[dict, dict]]) -> dict:
    out = {}
    for f in FIELDS:
        xs = [s[f] for _, s in rows if f in s]
        out[f] = (sum(xs), len(xs))
    for f in ("특전", "굿즈"):
        hit = sum(s[f][0] for _, s in rows)
        gold = sum(s[f][1] for _, s in rows)
        pred = sum(s[f][2] for _, s in rows)
        p = hit / pred if pred else 0.0
        r = hit / gold if gold else 0.0
        out[f] = (round(2 * p * r / (p + r) * 100) if p + r else 0, p, r)
    normal = [s["신호"] for g, s in rows if not g["flag"]]
    hard = [s["신호"] for g, s in rows if g["flag"]]
    out["오경보"] = (len(normal) - sum(normal), len(normal))
    out["놓침"] = (len(hard) - sum(hard), len(hard))
    core = [s[f] for _, s in rows for f in FIELDS if f in s]
    out["핵심 5칸"] = (sum(core), len(core))
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--ai", action="store_true")
    args = ap.parse_args()
    gold = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]
    texts = _texts()
    runners = {"1차 규칙 (cafe.rule_based)": run_v1, "2차 규칙 (notice.parse_notice)": run_v2}
    if args.ai:
        runners["AI cafe v1"] = run_ai("v1")
        runners["AI cafe v2"] = run_ai("v2")

    results = {}
    detail = []
    for name, fn in runners.items():
        rows = []
        for g in gold:
            got = fn(texts[g["file"]][g["index"]])
            s = score(g, got)
            rows.append((g, s))
            wrong = [f for f in FIELDS + ["신호"] if f in s and not s[f]]
            if wrong:
                detail.append(f"| {name.split(' (')[0]} | {g['id']} {g['kind']} | {', '.join(wrong)} | "
                              f"{str(got.get('address') or '-')[:24]} · {got.get('start')}~{got.get('end')}"
                              f"{' · ' + '; '.join(got.get('reasons', []))[:60] if got.get('reasons') else ''} |")
        results[name] = summarize(rows)

    def pct(a: int, b: int) -> str:
        return f"{a}/{b} ({round(a / b * 100)}%)" if b else "-"

    names = list(results)
    lines = [f"| 칸 | {' | '.join(names)} |", "| --- |" + " --- |" * len(names)]
    for f in ["핵심 5칸"] + FIELDS:
        lines.append(f"| {f} | " + " | ".join(pct(*results[n][f]) for n in names) + " |")
    for f in ("특전", "굿즈"):
        lines.append(f"| {f} F1 | " + " | ".join(f"{results[n][f][0]}%" for n in names) + " |")
    lines.append("| 검토 신호 오경보 (정상 10건 중, 낮을수록 좋음) | " + " | ".join(pct(*results[n]["오경보"]) for n in names) + " |")
    lines.append("| 검토 신호 놓침 (까다로운 4건 중, 낮을수록 좋음) | " + " | ".join(pct(*results[n]["놓침"]) for n in names) + " |")
    table = "\n".join(lines)
    miss = "\n".join(["| 방식 | 입력 | 틀린 칸 | 결과 (주소 · 기간 · 사유) |", "| --- | --- | --- | --- |"] + detail)
    print(table)
    print()
    print(miss)
    if args.save:
        out = ROOT / "docs" / "notice-eval.md"
        head = "" if out.exists() else (
            "# 공지 → 칸 채우기 정확도 (1차 규칙 vs 2차 규칙)\n\n"
            "`python -X utf8 scripts/eval_notice.py --save` 로 쌓인다. 채점 규칙은 스크립트 맨 위 설명, 정답은 `samples/notice_eval.jsonl`.\n"
            "입력 14건(정상 10 · 까다로운 4)은 1차 때 만든 샘플이라 2차 규칙에 맞춰 고른 것이 아니다. 대신 **건수가 적고 공지가 깔끔한 편**이라 실제 공지보다 점수가 높게 나올 수 있다.\n")
        with out.open("a", encoding="utf-8") as f:
            f.write(f"{head}\n## {datetime.now():%Y-%m-%d %H:%M}\n\n{table}\n\n틀린 것:\n\n{miss}\n")
        print(f"→ {out.relative_to(ROOT)} 에 저장")


if __name__ == "__main__":
    main()
