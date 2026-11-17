"""ANI:WHERE 행사 조회 MCP 서버 (읽기 전용).

Claude Code · Claude Desktop 같은 MCP 클라이언트가 팝업 데이터를 '도구'로 조회하게 한다.
  예) "이번 주말 성수 팝업 정리해서 인스타 문구 3개 써 줘" → Claude 가 search_popups 로 실제 데이터를 먼저 찾는다.

설계
  - 앱과 같은 코드를 쓴다: 저장소는 common/storage.Storage (STORAGE_MODE=local|supabase 그대로),
    검색은 common/ask.retrieve (앱의 '물어보기' 와 같은 규칙), 지표는 common/stats.
  - 읽기 전용: 쓰기 도구를 만들지 않는다. 등록·수정은 앱(사람)에서만.
  - 내보내지 않는 것: note·editor·source(운영용), 리뷰 본문·닉네임. 문자열은 guard.mask 를 한 번 더 거친다.
  - stdout 은 MCP 통신에 쓰이므로 print 하지 않는다.

실행: python mcp_server/aniwhere_server.py   (보통은 .mcp.json 으로 Claude Code 가 띄운다)
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

from common import ask, geo, guard, mycal, stats  # noqa: E402
from common.storage import Storage  # noqa: E402

APP_URL = "https://ani-where.streamlit.app"
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
MAX_LIMIT = 30

server = MCPServer(
    name="aniwhere",
    title="ANI:WHERE 팝업 조회",
    instructions=(
        "한국의 애니메이션 팝업·콜라보 카페 데이터를 조회하는 읽기 전용 도구입니다. "
        "답할 때는 도구가 돌려준 값만 쓰고, 날짜·장소는 official links 로 확인하라고 안내하세요. "
        "데이터에 없으면 없다고 말하세요."
    ),
    version="1.0.0",
)


# ------------------------------------------------------------------ 데이터
def _rows() -> list[dict]:
    """팝업별 최신 행 (삭제 제외, 기간 종료로 내린 것은 포함 — 지난 팝업 질문에 답하려고)."""
    return stats.popups(Storage(worksheet="cafes").all_rows())


def _today(on: str | None = None) -> date:
    if on:
        try:
            return date.fromisoformat(on[:10])
        except ValueError:
            pass
    return date.today()


def _state(r: dict, today: date) -> str:
    s, e = mycal._day(r.get("start_date")), mycal._day(r.get("end_date"))
    if not s or not e:
        return "기간 미상"
    return "종료" if e < today else "예정" if s > today else "진행 중"


def _public(r: dict, today: date, full: bool = False) -> dict:
    addr = guard.mask(str(r.get("address") or ""))
    out = {
        "id": str(r.get("entry_id")),
        "work": str(r.get("work") or ""),
        "cafe_name": guard.mask(str(r.get("cafe_name") or "")),
        "start_date": str(r.get("start_date") or ""),
        "end_date": str(r.get("end_date") or ""),
        "status": _state(r, today),
        "region": geo.area_name(addr) or geo.city_name(addr) or "",
        "address": addr,
        "app_url": f"{APP_URL}/?cafe={r.get('entry_id')}",
    }
    if full:
        out.update({
            "characters": [c.strip() for c in str(r.get("characters") or "").split(",") if c.strip()],
            "perks": guard.mask(str(r.get("perks") or "")),
            "goods": guard.mask(str(r.get("goods") or "")),
            "links": str(r.get("links") or "").split(),
            "intro": guard.mask(str(r.get("intro") or ""))[:1500],
            "lat": r.get("lat") or None,
            "lng": r.get("lng") or None,
        })
    return out


# ------------------------------------------------------------------ 도구
@server.tool(annotations=READ_ONLY)
def search_popups(question: str, on_date: str | None = None, limit: int = 6) -> dict:
    """자연어 질문으로 팝업을 찾는다. 작품·캐릭터·지역(홍대·성수·부산…)·날짜(오늘·이번 주말·다음 주·12월)를 질문에서 읽는다.

    question: 예) "이번 주말 성수 팝업", "주술회전 팝업 어디서 해?"
    on_date: 기준일 YYYY-MM-DD (비우면 오늘). '이번 주말' 같은 말의 기준.
    limit: 최대 개수 (1~30)
    """
    errors = [e for e in ask.validate(question) if "개인정보" not in e]
    if errors:
        return {"ok": False, "errors": errors, "results": []}
    today = _today(on_date)
    query, hits = ask.retrieve(guard.mask(question), _rows(), today, k=max(1, min(limit, MAX_LIMIT)))
    return {
        "ok": True,
        "understood": query.describe(),
        "today": today.isoformat(),
        "count": len(hits),
        "results": [_public(h.row, today) | {"matched": h.why} for h in hits],
        "note": "결과가 0건이면 데이터에 없는 것입니다. 지어내지 마세요." if not hits else "",
    }


@server.tool(annotations=READ_ONLY)
def list_popups(region: str | None = None, work: str | None = None,
                status: Literal["진행 중", "예정", "종료", "전체"] = "진행 중",
                on_date: str | None = None, limit: int = 20) -> dict:
    """조건으로 팝업 목록을 뽑는다 (검색어 해석 없이 정확히 거르기).

    region: 지역·동네 이름 (예: 서울, 부산, 홍대, 성수). work: 작품명 일부 (예: 주술회전).
    status: 진행 중 | 예정 | 종료 | 전체. on_date: 기준일 YYYY-MM-DD (비우면 오늘).
    """
    today = _today(on_date)
    out = []
    for r in _rows():
        if status != "전체" and _state(r, today) != status:
            continue
        if region and not ask._place_match(region.strip(), r):
            continue
        if work and ask._norm(work) not in ask._norm(r.get("work")):
            continue
        out.append(r)
    out.sort(key=lambda r: (str(r.get("start_date") or ""), str(r.get("cafe_name") or "")))
    n = max(1, min(limit, MAX_LIMIT))
    return {"today": today.isoformat(), "total": len(out), "results": [_public(r, today) for r in out[:n]]}


@server.tool(annotations=READ_ONLY)
def get_popup(popup_id: str, on_date: str | None = None) -> dict:
    """팝업 하나의 자세한 정보 (캐릭터·특전·굿즈·참고 링크·소개). popup_id 는 다른 도구 결과의 id."""
    today = _today(on_date)
    row = next((r for r in _rows() if str(r.get("entry_id")) == str(popup_id).strip()), None)
    if row is None:
        return {"ok": False, "error": f"id '{popup_id}' 인 팝업이 없습니다. search_popups 로 먼저 찾으세요."}
    return {"ok": True, "popup": _public(row, today, full=True)}


@server.tool(annotations=READ_ONLY)
def popup_stats(on_date: str | None = None) -> dict:
    """데이터 현황: 진행 중·예정·종료 수, 지역·작품 상위 5, 방문 전 정보 완결률(개선 전후)."""
    today = _today(on_date)
    all_rows = Storage(worksheet="cafes").all_rows()
    rows = stats.popups(all_rows)
    before = stats.completeness(stats.popups(all_rows, until=stats.NOTION_CUTOFF))
    now = stats.completeness(rows)
    return {
        "today": today.isoformat(),
        "status": stats.status_counts(rows, today),
        "starting_in_7_days": stats.starting_within(rows, today),
        "top_regions": stats.by_city(rows, 5).to_dict("records"),
        "top_works": stats.by_work(rows, 5).to_dict("records"),
        "visit_info_complete_pct": {"before": before["complete"], "now": now["complete"],
                                    "before_cutoff": stats.NOTION_CUTOFF},
    }


@server.tool(annotations=READ_ONLY)
def this_weekend(region: str | None = None, on_date: str | None = None) -> dict:
    """이번 주말(토·일)에 열려 있는 팝업. 현장에 가기 전 확인용."""
    today = _today(on_date)
    sat = today + timedelta(days=(5 - today.weekday()) % 7) if today.weekday() <= 5 else today
    sun = sat + timedelta(days=1) if sat.weekday() == 5 else sat
    out = [r for r in _rows() if ask._overlaps(r, (sat, sun))
           and (not region or ask._place_match(region.strip(), r))]
    out.sort(key=lambda r: str(r.get("end_date") or ""))
    return {"weekend": [sat.isoformat(), sun.isoformat()], "total": len(out),
            "results": [_public(r, today) for r in out[:MAX_LIMIT]]}


if __name__ == "__main__":
    server.run("stdio")
