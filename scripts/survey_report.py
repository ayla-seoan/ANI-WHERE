"""'사용해 보기' 설문(구글 폼 → n8n → 시트 '정리' 탭) → 검증된 응답만 모아 보고서 + 원자료 공개.

  python -X utf8 scripts/survey_report.py          # 화면에 요약
  python -X utf8 scripts/survey_report.py --save   # docs/user-test/report.md + docs/user-test/raw/survey_verified.csv

왜 (1차 강사 코멘트, 11/20): "A/B 수치가 실측이라면 참가자 · 측정 방법 · 원자료를 함께 공개하고,
문제 정의에 실제 사용자 설문이나 인터뷰 근거를 보태 보세요."
- 검증: 구글 폼 응답 탭(1차 응답 · 2차 응답)에 같은 닉네임이 있고 폼이 찍은 받은 시각이 지금보다 앞선 응답만 센다
  (common/stats.survey_verify — 관리자 '사용자 테스트' 탭과 같은 규칙). 손으로 넣은 줄 · 미래 시각은 뺀다.
- 원자료: 닉네임은 P1, P2… 로 바꾸고(같은 사람은 1차 · 2차 같은 번호), 자유 답변의 전화번호 · 이메일 · 계좌는 가린다.
- 시트 번호는 .env 의 SURVEY_SHEET_ID (시트는 '링크가 있는 모든 사용자 · 보기').
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import guard, stats  # noqa: E402

OUT_DIR = ROOT / "docs" / "user-test"
RAW = OUT_DIR / "raw" / "survey_verified.csv"
REPORT = OUT_DIR / "report.md"
FREE_TEXT = ("막힌 지점", "바라는점")
COLS = ["참가자", "버전", "과제", "결과", "걸린시간초", "막힌 지점", "방문빈도", "정보출처", "불편한점",
        "평소걸린시간초", "비교", "만족도", "다시쓸의향", "바라는점"]


def _sheet_id() -> str:
    sid = (os.getenv("SURVEY_SHEET_ID") or "").strip()
    env = ROOT / ".env"
    if not sid and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("SURVEY_SHEET_ID="):
                sid = line.split("=", 1)[1].strip().strip('"')
    return sid


def _tab(sheet_id: str, tab: str) -> list[dict]:
    import pandas as pd
    import requests

    res = requests.get(f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq",
                       params={"tqx": "out:csv", "sheet": tab}, timeout=15)
    if res.status_code != 200 or "text/csv" not in res.headers.get("content-type", ""):
        raise RuntimeError(f"'{tab}' 탭을 읽지 못했어요 (공유 설정 확인)")
    return pd.read_csv(io.StringIO(res.content.decode("utf-8")), dtype=str).fillna("").to_dict("records")


def anonymize(rows: list[dict]) -> list[dict]:
    """닉네임 → P번호 (처음 나온 순서), 자유 답변은 민감정보 가림."""
    ids: dict[str, str] = {}
    out = []
    for r in rows:
        nick = str(r.get("닉네임") or "").strip()
        pid = ids.setdefault(nick, f"P{len(ids) + 1}")
        row = {c: str(r.get(c) or "") for c in COLS if c != "참가자"}
        row["버전"] = stats.survey_version(r)
        for c in FREE_TEXT:
            row[c] = guard.mask(row[c])
        out.append({"참가자": pid, **row})
    return out


def _fmt(x, unit: str = "") -> str:
    return "-" if x is None else f"{x}{unit}"


def build(rows: list[dict], check: dict, forms: dict[str, list[dict]]) -> str:
    times = sorted(t for rs in forms.values() for r in rs
                   if (t := stats.parse_form_time(r.get("타임스탬프"))) and t <= datetime.now())
    span = f"{times[0]:%Y-%m-%d} ~ {times[-1]:%Y-%m-%d}" if times else "-"
    c = stats.survey_compare(rows)
    a, b = c["1차"], c["2차"]
    lines = [
        "## 참가자 · 방법",
        "",
        "| 항목 | 내용 |",
        "| --- | --- |",
        f"| 검증된 참가자 | **1차 {a['응답자']}명 · 2차 {b['응답자']}명** (같은 사람 {c['같은 사람']['명']}명) |",
        f"| 검증 규칙 | 구글 폼 응답 탭에 있고 받은 시각이 지금보다 앞선 응답만. '정리' 탭 {check['전체']}명 중 제외 {check['제외']}명"
        f" (폼에 없음 {check['폼에 없음']} · 미래 시각 {check['폼 응답 미래 시각']} · 시각 없음 {check['폼 응답 시각 없음']}) |",
        f"| 응답 기간 | {span} |",
        "| 모집 | 리뷰 그룹 · 지인 중 애니 팝업에 가 본 사람 (이름 · 나이 · 연락처 · 이메일은 받지 않음) |",
        "| 방법 | 참여자가 혼자 배포 주소에서 질문 1~4 를 해 보고 구글 폼에 직접 답함 (`automation/n8n/survey-form.md`). "
        "1차 폼 = 로그인 · 물어보기가 없던 첫 버전, 2차 폼 = 지금 버전 |",
        "| A/B | A = 평소 방법(SNS · 검색)으로 '이번 주말 서울 팝업 찾기'에 보통 걸리는 시간, B = ANI:WHERE 로 같은 일(질문 1) |",
        "| 시간 측정의 한계 | 스톱워치가 아니라 **구간을 고르는 자기 보고** — 구간 가운데 값(초)으로 바꾼 **대략값**이다 |",
        f"| 원자료 | [`raw/survey_verified.csv`](raw/survey_verified.csv) — 닉네임은 P번호, 자유 답변의 전화번호 · 이메일은 가림 |",
        "",
        "## 결과",
        "",
    ]
    if not rows:
        lines += ["아직 검증된 응답이 없다. 설문 폼으로 3~5명 이상 받은 뒤 다시 돌린다.", ""]
        return "\n".join(lines)
    lines += [
        "| 지표 | A 평소 방법 | 1차 앱 | 2차 앱 |",
        "| --- | --- | --- | --- |",
        f"| 이번 주말 서울 팝업 찾기 (초, 대략) | {_fmt(b['평소초'] or a['평소초'])} | {_fmt(a['질문1초'])} | {_fmt(b['질문1초'])} |",
        f"| 과제 성공률 (질문 1~4) | — | {_fmt(a['성공률'], '%')} | {_fmt(b['성공률'], '%')} |",
        f"| 평소 방법보다 편함 (5점) | — | {_fmt(a['비교'])} | {_fmt(b['비교'])} |",
        f"| 만족도 (5점) | — | {_fmt(a['만족도'])} | {_fmt(b['만족도'])} |",
        f"| 다시 쓸 의향 | — | {_fmt(a['다시쓸의향'], '%')} | {_fmt(b['다시쓸의향'], '%')} |",
        "",
        "## 문제 정의 근거 (평소에 불편한 점 · 정보 출처, 1차 · 2차 응답자 합계)",
        "",
    ]
    pains: dict[str, int] = {}
    srcs: dict[str, int] = {}
    for s in (a, b):
        for k, n in s["불편한점"]:
            pains[k] = pains.get(k, 0) + n
        for k, n in s["정보출처"]:
            srcs[k] = srcs.get(k, 0) + n
    people = a["응답자"] + b["응답자"]
    lines += ["| 불편한 점 | 명 | 비율 |", "| --- | --- | --- |"]
    lines += [f"| {k} | {n} | {round(n / people * 100)}% |" for k, n in sorted(pains.items(), key=lambda x: -x[1])]
    lines += ["", "| 정보 출처 | 명 |", "| --- | --- |"]
    lines += [f"| {k} | {n} |" for k, n in sorted(srcs.items(), key=lambda x: -x[1])]
    blocks = b["막힌곳"] or a["막힌곳"]
    if blocks:
        lines += ["", "## 막힌 곳 (다음에 고칠 것)", ""] + [f"- {guard.mask(k)} ({n}명)" for k, n in blocks]
    return "\n".join(lines + [""])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    sid = _sheet_id()
    if not sid:
        print("SURVEY_SHEET_ID 가 없어요 (.env)")
        return
    rows = _tab(sid, "정리")
    forms = {v: _tab(sid, t) for v, t in stats.SURVEY_FORM_TABS.items()}
    kept, check = stats.survey_verify(rows, forms)
    text = build(kept, check, forms)
    print(text)
    if args.save:
        RAW.parent.mkdir(parents=True, exist_ok=True)
        with RAW.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLS)
            w.writeheader()
            w.writerows(anonymize(kept))
        REPORT.write_text(
            "# 사용자 테스트 결과 (사용해 보기 설문)\n\n"
            f"`python -X utf8 scripts/survey_report.py --save` 가 만든다 · 마지막 생성 {datetime.now():%Y-%m-%d %H:%M}.\n"
            "숫자 규칙은 `common/stats.py` (`survey_verify` · `survey_compare`) — 관리자 '사용자 테스트' 탭 · n8n 메일과 같다.\n\n"
            + text, encoding="utf-8")
        print(f"→ {REPORT.relative_to(ROOT)}, {RAW.relative_to(ROOT)} 에 저장 (검증 {check['검증']}명)")


if __name__ == "__main__":
    main()
