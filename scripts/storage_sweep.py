"""사진 저장소(Supabase Storage 'uploads') 정리: 어느 기록도 쓰지 않는 사진 파일을 지운다 (11/19).

매주 월요일 DB 정리(supabase/migrations/012, purge_ended_popups)로 내린 팝업 · 그 리뷰가 지워지면 사진 파일만 남는다.
SQL 로는 파일을 지울 수 없어서(Supabase 문서 'Delete objects') Storage API 로 지운다. anon 키로는 012 정책에 따라
'어느 기록도 쓰지 않는 · 하루 지난' 파일만 목록에 보이고 지울 수 있다 — 쓰고 있는 사진은 이 스크립트로 지울 수 없다.

    python scripts/storage_sweep.py          # 지운다
    python scripts/storage_sweep.py --dry    # 지울 파일 수만 본다

매일 가져오기 작업(.github/workflows/notion-sync.yml)이 가져오기 뒤에 돌린다. 012 전이면 목록이 비어 아무것도 안 한다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BUCKET = "uploads"
PAGE = 1000


def main() -> int:
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_KEY") or "").strip()
    if not url or not key:
        print("SUPABASE_URL · SUPABASE_KEY 가 없어 건너뜀")
        return 0
    headers = {"apikey": key, **({"Authorization": f"Bearer {key}"} if key.startswith("eyJ") else {})}
    names: list[str] = []
    offset = 0
    while True:
        res = requests.post(f"{url}/storage/v1/object/list/{BUCKET}", headers=headers, timeout=30,
                            json={"prefix": "", "limit": PAGE, "offset": offset, "sortBy": {"column": "name", "order": "asc"}})
        if res.status_code != 200:
            print(f"목록을 읽지 못함 ({res.status_code}): {res.text[:200]}")
            return 0          # 정리는 못 해도 가져오기 작업은 실패로 만들지 않는다
        page = [o["name"] for o in res.json() if o.get("id")]     # 폴더(id 없음)는 빼고 파일만
        names += page
        if len(page) < PAGE:
            break
        offset += PAGE
    print(f"쓰지 않는 사진 {len(names)}개")
    if "--dry" in sys.argv or not names:
        return 0
    gone = 0
    for i in range(0, len(names), 100):
        res = requests.delete(f"{url}/storage/v1/object/{BUCKET}", headers=headers, timeout=30,
                              json={"prefixes": names[i:i + 100]})
        if res.status_code == 200:
            gone += len(res.json())
        else:
            print(f"지우지 못함 ({res.status_code}): {res.text[:200]}")
    print(f"지움 {gone}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
