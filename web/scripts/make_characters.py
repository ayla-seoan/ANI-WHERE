"""lib/server/characters.json 다시 만들기: data/anime_catalog.json 의 캐릭터 이름 (중복 없이, 글자 코드 순).

웹의 자동 닉네임(lib/server/nick.ts autoNickname)이 앱(common/review.py auto_nickname)과 같은 이름을 고르려면
두 곳이 같은 목록을 써야 한다. 작품 목록을 고쳤으면 저장소 루트에서:  python web/scripts/make_characters.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
works = json.loads((ROOT / "data" / "anime_catalog.json").read_text(encoding="utf-8")).get("works", [])
names = sorted({n.strip() for w in works for n in w.get("characters", []) if n.strip()})
(ROOT / "web" / "lib" / "server" / "characters.json").write_text(json.dumps(names, ensure_ascii=False), encoding="utf-8")
print(len(names), "names")
