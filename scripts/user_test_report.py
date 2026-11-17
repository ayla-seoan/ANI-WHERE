"""사용자 테스트 결과(docs/user-test/results.csv) → 과업 성공률 · 소요 시간 표.

  python scripts/user_test_report.py          # 표 출력
  python scripts/user_test_report.py --save   # docs/user-test/report.md 에 날짜별로 쌓기

CSV 칸: 참가자(P1, P2… 이름 대신 번호), 버전(1차 / 2차), 과업(T1~T4), 성공(Y/N), 소요초, 막힌 지점, 메모
성공 = 도움 없이 과업을 끝냄. 3분(180초)을 넘기면 실패로 센다 (docs/user-test/plan.md).
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "docs" / "user-test" / "results.csv"
LIMIT = 180
TARGET_SUCCESS = 80        # PRD 에서 미리 정한 성공 기준 (%)


def build() -> tuple[str, pd.DataFrame]:
    df = pd.read_csv(CSV, encoding="utf-8-sig", dtype=str).fillna("")
    if df.empty:
        return ("아직 기록이 없어요. docs/user-test/plan.md 순서대로 3~5명 테스트를 하고 "
                "results.csv 에 한 줄씩 적은 뒤 다시 돌려 주세요."), df
    df["소요초"] = pd.to_numeric(df["소요초"], errors="coerce")
    df["성공여부"] = (df["성공"].str.upper().str.strip() == "Y") & (df["소요초"].fillna(LIMIT + 1) <= LIMIT)
    table = (df.groupby(["과업", "버전"])
               .agg(참가자=("참가자", "nunique"), 성공률=("성공여부", lambda s: round(s.mean() * 100)),
                    평균초=("소요초", lambda s: round(s.mean(), 1)))
               .reset_index())
    total = df.groupby("버전")["성공여부"].mean().mul(100).round().astype(int)
    lines = ["| 과업 | 버전 | 참가자 | 성공률(%) | 평균 소요(초) |", "| --- | --- | --- | --- | --- |"]
    lines += [f"| {r.과업} | {r.버전} | {r.참가자} | {r.성공률} | {r.평균초} |" for r in table.itertuples()]
    lines.append("")
    for ver, rate in total.items():
        mark = "달성" if rate >= TARGET_SUCCESS else "미달"
        lines.append(f"- {ver} 전체 과업 성공률 **{rate}%** (목표 {TARGET_SUCCESS}% {mark})")
    stuck = df.loc[df["막힌 지점"].str.strip() != "", ["버전", "과업", "막힌 지점"]]
    if not stuck.empty:
        lines += ["", "막힌 지점:"] + [f"- [{r.버전} {r.과업}] {r._3}" for r in stuck.itertuples()]
    return "\n".join(lines), df


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    text, df = build()
    print(text)
    if args.save and not df.empty:
        out = CSV.parent / "report.md"
        head = "" if out.exists() else "# 사용자 테스트 결과\n\n`python scripts/user_test_report.py --save` 로 쌓인다.\n"
        with out.open("a", encoding="utf-8") as f:
            f.write(f"{head}\n## {datetime.now():%Y-%m-%d %H:%M}\n\n{text}\n")
        print(f"→ {out.relative_to(ROOT)} 에 저장")


if __name__ == "__main__":
    main()
