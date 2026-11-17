"""MCP 서버가 실제 MCP 프로토콜(stdio)로 도구를 내놓고 답하는지 확인한다.

  python -X utf8 tests/mcp/check_server.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]


async def main() -> int:
    params = StdioServerParameters(command=sys.executable,
                                   args=["-X", "utf8", str(ROOT / "mcp_server" / "aniwhere_server.py")],
                                   env={"STORAGE_MODE": "local", "PYTHONIOENCODING": "utf-8"})
    checks = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            checks.append(("도구 5개 노출", tools == sorted(["search_popups", "list_popups", "get_popup", "popup_stats", "this_weekend"]), tools))

            async def call(name, **kw):
                res = await s.call_tool(name, kw)
                if getattr(res, "is_error", False):
                    raise RuntimeError(res.content[0].text)
                return res.structured_content or json.loads(res.content[0].text)

            r = await call("search_popups", question="주술회전 팝업 어디서 해?", on_date="2026-11-17")
            checks.append(("작품 검색", r["count"] > 0 and all("주술회전" in x["work"] for x in r["results"]), r["understood"]))
            first = r["results"][0]["id"] if r["results"] else ""
            r = await call("search_popups", question="쀍뛟뷁 팝업", on_date="2026-11-17")
            checks.append(("없는 작품은 0건", r["count"] == 0, r.get("note")))
            r = await call("search_popups", question="", on_date="2026-11-17")
            checks.append(("빈 질문 거절", r["ok"] is False, r.get("errors")))
            r = await call("get_popup", popup_id=first)
            checks.append(("상세 조회", r["ok"] and "note" not in r["popup"] and "editor" not in r["popup"], list(r.get("popup", {}))[:5]))
            r = await call("get_popup", popup_id="없는아이디")
            checks.append(("없는 id 안내", r["ok"] is False, r.get("error")))
            r = await call("list_popups", region="부산", status="전체", on_date="2026-11-17")
            checks.append(("지역 목록", r["total"] > 0, r["total"]))
            r = await call("this_weekend", region="서울", on_date="2026-11-17")
            checks.append(("이번 주말", r["weekend"] == ["2026-11-21", "2026-11-22"], (r["weekend"], r["total"])))
            r = await call("popup_stats", on_date="2026-11-17")
            checks.append(("현황", r["visit_info_complete_pct"]["now"] > r["visit_info_complete_pct"]["before"], r["visit_info_complete_pct"]))
    ok = 0
    for name, good, detail in checks:
        ok += bool(good)
        print(f"{'O' if good else 'X'}  {name}  — {detail}")
    print(f"\nMCP 서버 확인 {ok}/{len(checks)}")
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
