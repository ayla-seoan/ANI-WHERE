"""주제 1 전용 로직: 입력 조립 + 규칙 기반 fallback.

AI 호출 자체는 common/ai.py 가 맡는다. 여기는 '무엇을 보내고, AI가 죽으면
무엇으로 대신할 것인가' 만 담당한다.
"""
from __future__ import annotations

import json
import re

import pandas as pd

from .guard import mask
from .schema import ExcludedItem, PriorityResult, ScoredItem

TOP_N = 10


def build_user_content(df: pd.DataFrame, kpis: list[dict]) -> str:
    """AI 에게 보낼 입력. 민감정보는 여기서 한 번 가린다."""
    items = []
    for _, row in df.iterrows():
        items.append({
            "id": str(row["id"]),
            "title": mask(str(row["title"])),
            "description": mask(str(row.get("description", ""))),
            "effort_days": float(row["effort_days"]),
        })
    payload = {
        "kpis": [{"name": k["name"], "weight": k["weight"]} for k in kpis],
        "backlog": items,
        "top_n": TOP_N,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^0-9A-Za-z가-힣]+", text.lower()) if len(t) > 1}


def _match_kpi(item_text: str, kpis: list[dict]) -> tuple[dict, float]:
    """KPI 이름·키워드와 항목 설명의 단어 겹침으로 가장 가까운 KPI 를 고른다."""
    item_tokens = _tokens(item_text)
    best, best_overlap = kpis[0], 0
    for kpi in kpis:
        kpi_tokens = _tokens(kpi["name"] + " " + kpi.get("keywords", ""))
        overlap = len(item_tokens & kpi_tokens)
        if overlap > best_overlap:
            best, best_overlap = kpi, overlap
    # 겹치는 단어가 없으면 연결이 불확실하다는 뜻이므로 점수를 깎는다.
    confidence = 1.0 if best_overlap else 0.5
    return best, confidence


def rule_based(df: pd.DataFrame, kpis: list[dict]) -> PriorityResult:
    """AI 가 실패했을 때 쓰는 대체 경로.

    점수 = (KPI 가중치 x 연결 신뢰도) / 공수. 사람이 검산할 수 있는 식으로만 만든다.
    """
    rows = []
    for _, row in df.iterrows():
        text = f"{row['title']} {row.get('description', '')}"
        kpi, confidence = _match_kpi(text, kpis)
        effort = max(float(row["effort_days"]), 0.5)
        raw = (float(kpi["weight"]) * confidence) / effort
        rows.append({
            "item_id": str(row["id"]),
            "title": str(row["title"]),
            "kpi": kpi["name"],
            "raw": raw,
            "effort": effort,
            "confidence": confidence,
        })

    if not rows:
        return PriorityResult(top_items=[], excluded=[])

    top_raw = max(r["raw"] for r in rows) or 1.0
    rows.sort(key=lambda r: (-r["raw"], r["item_id"]))  # 동점이면 id 순 → 재현성 확보

    top_items = []
    for rank, r in enumerate(rows[:TOP_N], start=1):
        note = "" if r["confidence"] == 1.0 else " (KPI 연결이 불확실해 점수를 낮춤)"
        top_items.append(ScoredItem(
            item_id=r["item_id"],
            title=r["title"],
            rank=rank,
            score=round(r["raw"] / top_raw * 100, 1),
            kpi=r["kpi"],
            reason=f"{r['kpi']} 가중치 대비 공수 {r['effort']:g}일로 효율이 높음{note}"[:120],
        ))

    excluded = [
        ExcludedItem(
            item_id=r["item_id"],
            title=r["title"],
            reason=f"공수 {r['effort']:g}일 대비 {r['kpi']} 기여도가 상위 {TOP_N}건보다 낮음"[:120],
        )
        for r in rows[TOP_N:]
    ]
    return PriorityResult(top_items=top_items, excluded=excluded)


def to_dataframe(result: PriorityResult) -> pd.DataFrame:
    return pd.DataFrame([{
        "순위": i.rank,
        "id": i.item_id,
        "항목": i.title,
        "연결 KPI": i.kpi,
        "점수": i.score,
        "근거": i.reason,
    } for i in result.top_items])


def excluded_dataframe(result: PriorityResult) -> pd.DataFrame:
    return pd.DataFrame([{
        "id": e.item_id,
        "항목": e.title,
        "이번 분기에 하지 않는 이유": e.reason,
    } for e in result.excluded])
