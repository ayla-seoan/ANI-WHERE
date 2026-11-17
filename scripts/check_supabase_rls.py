"""Supabase RLS·제약이 실제로 막고 있는지 앱과 같은 키(anon)로 직접 두드려 본다. 발표용 '안정성' 자료.

    python scripts/check_supabase_rls.py

모든 시도는 '거부되어야 정상' 인 것들이다. 정상이라면 DB 에 아무것도 남지 않는다.
(만에 하나 뚫리면 남는 행은 status='deleted' 나 원글과 같은 내용이라 화면에 드러나지 않게 골랐다.)
SUPABASE_KEY 에는 앱과 같은 anon 키를 넣고 돌린다. service_role 키는 RLS 를 건너뛰므로 이 검사가 의미 없다.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

import requests  # noqa: E402

URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
KEY = (os.getenv("SUPABASE_KEY") or "").strip()
H = {"apikey": KEY, "Content-Type": "application/json",
     **({"Authorization": f"Bearer {KEY}"} if KEY.startswith("eyJ") else {})}   # 새 형식 키는 apikey 에만


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rid() -> str:
    return uuid.uuid4().hex[:10]


def _get(table: str, **params) -> list[dict]:
    res = requests.get(f"{URL}/rest/v1/{table}", headers=H, params=params, timeout=20)
    res.raise_for_status()
    return res.json()


def _blocked(res: requests.Response) -> tuple[bool, str]:
    """거부됐는지: 4xx 에러이거나, 성공 코드여도 바뀐 행이 0개."""
    if res.status_code >= 400:
        try:
            msg = res.json().get("message", "")
        except Exception:
            msg = res.text[:80]
        return True, f"{res.status_code} {msg[:60]}"
    try:
        body = res.json() if res.text else []
    except Exception:
        body = []
    if isinstance(body, list) and not body:
        return True, f"{res.status_code} 영향받은 행 0개"
    return False, f"{res.status_code} 통과됨 ({len(body) if isinstance(body, list) else '?'}행)"


def _insert(table: str, row: dict) -> requests.Response:
    return requests.post(f"{URL}/rest/v1/{table}", timeout=20,
                         headers={**H, "Prefer": "return=representation"},
                         data=json.dumps(row, ensure_ascii=False).encode("utf-8"))


def main() -> int:
    if not URL or not KEY:
        print("SUPABASE_URL / SUPABASE_KEY 가 없습니다. .env 를 채운 뒤 다시 돌려 주세요.")
        return 1

    results: list[tuple[str, str, bool, str]] = []   # (검사, 기대, 통과?, 실제)

    # 0. 읽기는 되어야 한다
    try:
        reviews = _get("reviews", select="*", order="revision.asc", limit="1000")
        cafes = _get("cafes", select="row_id", limit="1")
        results.append(("anon 으로 읽기(SELECT)", "허용", True, f"리뷰 {len(reviews)}행 읽음"))
    except Exception as exc:
        results.append(("anon 으로 읽기(SELECT)", "허용", False, str(exc)[:60]))
        reviews, cafes = [], []

    # 1. UPDATE 는 막혀야 한다
    if reviews:
        target = reviews[0]
        res = requests.patch(f"{URL}/rest/v1/reviews", timeout=20,
                             headers={**H, "Prefer": "return=representation"},
                             params={"row_id": f"eq.{target['row_id']}"},
                             data=json.dumps({"body": target["body"]}, ensure_ascii=False).encode("utf-8"))
        ok, info = _blocked(res)
        results.append(("기존 리뷰 덮어쓰기(UPDATE)", "거부", ok, info))
    else:
        results.append(("기존 리뷰 덮어쓰기(UPDATE)", "거부", False, "리뷰가 없어 건너뜀 (먼저 migrate)"))

    # 2. DELETE 는 막혀야 한다
    if cafes:
        res = requests.delete(f"{URL}/rest/v1/cafes", timeout=20,
                              headers={**H, "Prefer": "return=representation"},
                              params={"row_id": f"eq.{cafes[0]['row_id']}"})
        ok, info = _blocked(res)
        results.append(("카페 행 지우기(DELETE)", "거부", ok, info))
    else:
        results.append(("카페 행 지우기(DELETE)", "거부", False, "카페가 없어 건너뜀 (먼저 migrate)"))

    # 3. 남의 리뷰를 다른 '#네 글자' 닉네임으로 고치기 -> 막혀야 한다
    firsts = [r for r in reviews if int(r.get("revision") or 0) == 1]
    if firsts:
        orig = firsts[0]
        tag = orig["nickname"].rsplit("#", 1)[-1]
        fake_tag = "zzzz" if tag != "zzzz" else "yyyy"
        latest = max(int(r["revision"]) for r in reviews if r["entry_id"] == orig["entry_id"])
        forged = {**orig, "row_id": _rid(), "revision": latest + 1, "updated_at": _now(),
                  "nickname": f"사칭한 사람#{fake_tag}"}
        ok, info = _blocked(_insert("reviews", forged))
        results.append(("남의 리뷰 수정(닉네임 #태그 위조)", "거부", ok, info))
    else:
        results.append(("남의 리뷰 수정(닉네임 #태그 위조)", "거부", False, "원글이 없어 건너뜀 (먼저 migrate)"))

    # 4. 전화번호가 든 리뷰 -> 막혀야 한다 (뚫려도 status=deleted 라 화면에 안 보임)
    base = {"entry_id": _rid(), "revision": 1, "status": "deleted", "updated_at": _now(),
            "cafe_id": "rls-check", "parent_id": "", "kind": "기타",
            "nickname": "점검봇#test", "rating": "", "images": ""}
    ok, info = _blocked(_insert("reviews", {**base, "row_id": _rid(), "body": "연락 주세요 010-1234-5678"}))
    results.append(("리뷰 본문에 전화번호", "거부", ok, info))

    # 5. 이메일이 든 카페 메모 -> 막혀야 한다
    cafe = {"row_id": _rid(), "entry_id": _rid(), "revision": 1, "status": "deleted",
            "updated_at": _now(), "cafe_name": "RLS 점검", "note": "문의 test@example.com"}
    ok, info = _blocked(_insert("cafes", cafe))
    results.append(("카페 메모에 이메일", "거부", ok, info))

    # 6. 별점 범위 밖 -> 막혀야 한다
    ok, info = _blocked(_insert("reviews", {**base, "entry_id": _rid(), "row_id": _rid(),
                                            "body": "별점 검사", "rating": "9"}))
    results.append(("별점 9점", "거부", ok, info))

    width = max(len(r[0]) for r in results) + 2
    print(f"\n{'검사':<{width}}{'기대':<6}{'결과':<6}실제 응답")
    print("-" * (width + 50))
    for name, expect, ok, info in results:
        print(f"{name:<{width}}{expect:<6}{'통과' if ok else '실패':<6}{info}")
    passed = sum(1 for r in results if r[2])
    print("-" * (width + 50))
    print(f"{passed}/{len(results)} 통과")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
