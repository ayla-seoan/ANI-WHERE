"""Notion 트래커 → 앱 데이터(data/cafes.json) 가져오기. 매주 GitHub Actions 가 돌린다 (.github/workflows/notion-sync.yml).

    python scripts/notion_import.py          # 실제 data/ 에 넣는다
    python scripts/notion_import.py --dry    # 임시 복사본에만 넣어 결과만 본다 (이미지도 내려받지 않음)

규칙은 docs/notion-import.md 2부. 앱이 메인 화면을 열 때 하는 가져오기(notion_sync.maybe_sync)와 같은 함수를 쓴다.
NOTION_TOKEN(Notion 내부 통합 키)이 환경 변수나 .env 에 있어야 한다.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from common import cafe, notion_sync, storage  # noqa: E402

KST = timezone(timedelta(hours=9))


def main() -> int:
    dry = "--dry" in sys.argv
    token = os.getenv("NOTION_TOKEN")
    if not token:
        print("NOTION_TOKEN 이 없습니다. .env 나 GitHub 저장소 Secret 에 넣어 주세요.")
        return 1
    if dry:
        tmp = Path(tempfile.mkdtemp())
        shutil.copy(ROOT / "data" / "cafes.json", tmp / "cafes.json")
        storage.LOCAL_DIR = tmp
        notion_sync._download = lambda urls: ["(dry).webp"] if urls else []

    today = datetime.now(KST).date()        # 서버 시간대와 상관없이 한국 날짜로 본다
    store = storage.Storage("cafes")
    before = len(store.all_rows())
    rows = notion_sync.fetch_rows(token)
    print(f"Notion {len(rows)}행 (검토 완료 {sum(r.get('검수상태') == '검토 완료' for r in rows)}행) · 기준일 {today}")

    report = notion_sync.import_rows(store, rows, today)
    intros = notion_sync.sync_intros(store, rows)
    ended = cafe.expire_ended(store, today)     # 기간이 지난 팝업은 지도에서 내린다 (앱을 열 때와 같은 처리)

    print(f"새 팝업 {len(report['added'])}곳:", ", ".join(report["added"]) or "-")
    print(f"이미지 채움 {len(report.get('images', []))}곳 · 팝업 소개 맞춤 {len(report.get('intros', []))}곳")
    print(f"소개 동기화: 바꿈 {len(intros['updated'])} · 비움 {len(intros['cleared'])} · 사람이 쓴 소개라 그대로 {len(intros['kept'])}")
    print(f"기간 종료로 내림 {len(ended)}곳:", ", ".join(ended) or "-")
    skipped = {}
    for _, why in report["skipped"]:
        skipped[why] = skipped.get(why, 0) + 1
    print("건너뜀:", ", ".join(f"{k} {v}" for k, v in skipped.items()) or "-")
    print(f"기록 {before} → {len(store.all_rows())}행" + (" (dry run, 실제 데이터는 그대로)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
