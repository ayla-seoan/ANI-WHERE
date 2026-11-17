"""data/*.json 을 Supabase 표로 한 번 옮긴다.

    python scripts/migrate_to_supabase.py --dry-run   # 무엇을 올릴지 세기만
    python scripts/migrate_to_supabase.py             # 실제로 올리기

- 이미 DB 에 있는 row_id 는 건너뛴다 (여러 번 돌려도 같은 결과).
- INSERT 만 한다. DB 의 행을 고치거나 지우지 않는다. 로컬 JSON 도 건드리지 않는다.
- revision 1 부터 차례로 올린다. 리뷰의 '내 글만 수정' 정책이 원글(revision 1)을 보고 판단하기 때문.
- 먼저 supabase/migrations/001_init.sql 을 SQL Editor 에서 돌려 표를 만들어 둔다 (db.md).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

import requests  # noqa: E402

from common import favorite, guard, review, storage  # noqa: E402

TABLES = {
    "cafes": (storage.HEADERS, ["cafe_name", "note", "intro", "perks", "goods"]),
    "reviews": (review.HEADERS, ["body"]),
    "favorites": (favorite.HEADERS, []),
}
BATCH = 200


def _conn() -> tuple[str, dict] | None:
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_KEY") or "").strip()
    if not url or not key:
        return None
    return url, {"apikey": key, **({"Authorization": f"Bearer {key}"} if key.startswith("eyJ") else {})}   # 새 형식 키는 apikey 에만


def _existing_ids(url: str, headers: dict, table: str) -> set[str]:
    ids: set[str] = set()
    offset = 0
    while True:
        res = requests.get(f"{url}/rest/v1/{table}", headers=headers, timeout=20,
                           params={"select": "row_id", "order": "row_id.asc",
                                   "limit": "1000", "offset": str(offset)})
        res.raise_for_status()
        page = res.json()
        ids.update(r["row_id"] for r in page)
        if len(page) < 1000:
            return ids
        offset += 1000


def _converter(table: str, headers: list[str]) -> storage.Storage:
    """Storage._to_db 만 빌려 쓴다 (연결하지 않도록 local 모드로 만든다)."""
    saved = os.environ.get("STORAGE_MODE")
    os.environ["STORAGE_MODE"] = "local"
    try:
        return storage.Storage(table, headers)
    finally:
        if saved is None:
            os.environ.pop("STORAGE_MODE", None)
        else:
            os.environ["STORAGE_MODE"] = saved


def main() -> int:
    ap = argparse.ArgumentParser(description="data/*.json -> Supabase (INSERT 만, 중복 건너뜀)")
    ap.add_argument("--dry-run", action="store_true", help="올리지 않고 건수만 센다")
    args = ap.parse_args()

    conn = _conn()
    if conn is None and not args.dry_run:
        print("SUPABASE_URL / SUPABASE_KEY 가 없습니다. .env 를 채우거나 --dry-run 으로 돌려 주세요.")
        return 1
    if conn is None:
        print("[dry-run] Supabase 설정이 없어 DB 비교는 건너뜁니다 (로컬 파일만 검사).")

    failed = False
    print(f"{'표':<10}{'로컬':>6}{'DB에 있음':>10}{'올릴 행':>8}{'민감정보 의심':>14}")
    for table, (headers, sensitive_cols) in TABLES.items():
        path = ROOT / "data" / f"{table}.json"
        rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        conv = _converter(table, headers)

        have: set[str] = set()
        if conn is not None:
            try:
                have = _existing_ids(conn[0], conn[1], table)
            except Exception as exc:
                print(f"{table}: DB 를 읽지 못했습니다 — {exc}")
                failed = True
                continue
        todo = [r for r in rows if str(r.get("row_id")) not in have]
        # DB 의 has_sensitive() 검사에 걸릴 행을 미리 알려 준다 (걸리면 그 묶음 전체가 거부된다)
        flagged = [r["row_id"] for r in todo
                   if any(guard.scan(str(r.get(c) or "")) for c in sensitive_cols)]
        print(f"{table:<10}{len(rows):>6}{len(have) if conn else '-':>10}{len(todo):>8}{len(flagged):>14}")
        for rid in flagged:
            print(f"   ! {table} row_id={rid} 에 민감정보로 보이는 값이 있습니다. 앱에서 가린 뒤 다시 돌려 주세요.")

        if args.dry_run or not todo:
            continue
        todo = [r for r in todo if r["row_id"] not in flagged]
        for rev in sorted({int(r.get("revision") or 1) for r in todo}):
            chunk_rows = [conv._to_db(r) for r in todo if int(r.get("revision") or 1) == rev]
            for i in range(0, len(chunk_rows), BATCH):
                chunk = chunk_rows[i:i + BATCH]
                res = requests.post(
                    f"{conn[0]}/rest/v1/{table}", timeout=60,
                    headers={**conn[1], "Content-Type": "application/json", "Prefer": "return=minimal"},
                    data=json.dumps(chunk, ensure_ascii=False).encode("utf-8"),
                )
                if res.status_code not in (200, 201, 204):
                    print(f"   x {table} revision {rev} 묶음 {i // BATCH + 1} 실패 ({res.status_code}): {res.text[:300]}")
                    failed = True
                else:
                    print(f"   + {table} revision {rev}: {len(chunk)}행 올림")

    print("완료 (dry-run: 아무것도 올리지 않았습니다)" if args.dry_run else
          ("일부 실패. 위 메시지를 확인한 뒤 다시 돌리면 남은 행만 올라갑니다." if failed else "완료"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
