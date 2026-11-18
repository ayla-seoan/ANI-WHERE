"""lib/server/catalog.json 다시 만들기: data/anime_catalog.json 의 작품 목록 (작품 · 캐릭터 · 별칭) 그대로.

웹의 등록하기 · 수정하기(작품·캐릭터 고르기)와 공지 간편등록(lib/server/parse.ts)이 앱(common/catalog.py)과
같은 목록을 쓰려면 두 곳이 같은 파일 내용을 봐야 한다. 작품 목록을 고쳤으면 저장소 루트에서:
    python web/scripts/make_catalog.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
works = json.loads((ROOT / "data" / "anime_catalog.json").read_text(encoding="utf-8")).get("works", [])
keep = [{k: w[k] for k in ("work", "characters", "aliases", "character_aliases") if k in w} for w in works]
(ROOT / "web" / "lib" / "server" / "catalog.json").write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")
print(len(keep), "works")
