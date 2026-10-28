"""카페 이미지(포스터·추가 이미지)를 static/uploads/ 에 저장하고 꺼낸다.

저장소 행에는 파일 이름만 쉼표로 이어서 넣는다. 첫 번째가 메인 이미지(포스터)다.
파일은 한 번 저장하면 지우지 않는다 (append-only 저장소의 되돌리기가 옛 이미지를 가리킬 수 있다).

static/ 아래에 두어 Streamlit 이 url() 주소로 바로 내보낸다. 화면에 그림을 통째로 넣지 않아 가볍고,
상세 화면의 슬라이드·확대 보기가 원본 그대로를 불러올 수 있다.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = ROOT / "static" / "uploads"
LEGACY_DIR = ROOT / "data" / "images"      # 예전 저장 위치. 지우지 않고 새 위치로 복사만 한다
TYPES = ["png", "jpg", "jpeg", "webp", "gif"]
POSTER_MB = 20
EXTRA_MB = 10
MAX_EXTRAS = 10


def _migrate() -> None:
    """data/images/ 에 있던 이미지를 static/uploads/ 로 복사한다. 이미 있으면 건너뛴다."""
    if not LEGACY_DIR.is_dir():
        return
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    for f in LEGACY_DIR.iterdir():
        if f.is_file() and not (IMAGE_DIR / f.name).exists():
            shutil.copy2(f, IMAGE_DIR / f.name)


_migrate()


def too_big(data: bytes, limit_mb: int) -> bool:
    return len(data) > limit_mb * 1024 * 1024


def save(name: str, data: bytes) -> str:
    """이미지를 저장하고 파일 이름을 돌려준다. 원래 이름은 쓰지 않는다 (경로 조작 방지)."""
    ext = Path(name).suffix.lower().lstrip(".")
    if ext not in TYPES:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {name}")
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    (IMAGE_DIR / filename).write_bytes(data)
    return filename


def split(value) -> list[str]:
    return [p.strip() for p in str(value or "").split(",") if p.strip()]


def paths(value) -> list[Path]:
    """저장소의 images 칸 → 실제로 있는 파일 경로들. 파일 이름 밖으로 나가는 값은 버린다."""
    out = []
    for name in split(value):
        p = IMAGE_DIR / Path(name).name
        if p.is_file():
            out.append(p)
    return out


def poster(value) -> Path | None:
    found = paths(value)
    return found[0] if found else None


def url(path: Path) -> str:
    """static/uploads/ 의 파일 → 화면에서 쓰는 주소 (페이지 기준 상대 주소)."""
    return f"app/static/uploads/{path.name}"


# 포스터를 올리지 않은 카페에 보여 줄 기본 그림. 저장소에는 넣지 않고 화면에서만 쓴다.
DEFAULT_POSTER = ROOT / "static" / "default_poster.png"
DEFAULT_POSTER_URL = "app/static/default_poster.png"
