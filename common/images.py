"""카페 이미지(포스터·추가 이미지)를 static/uploads/ 에 저장하고 꺼낸다.

저장소 행에는 파일 이름만 쉼표로 이어서 넣는다. 첫 번째가 메인 이미지(포스터)다.
파일은 한 번 저장하면 지우지 않는다 (append-only 저장소의 되돌리기가 옛 이미지를 가리킬 수 있다).

static/ 아래에 두어 Streamlit 이 url() 주소로 바로 내보낸다. 화면에 그림을 통째로 넣지 않아 가볍고,
상세 화면의 슬라이드·확대 보기가 원본 그대로를 불러올 수 있다.
"""
from __future__ import annotations

import io
import re
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


def strip_metadata(data: bytes, ext: str) -> bytes:
    """사진 속 위치(GPS) · 기기 · 촬영 시각 같은 메타데이터(EXIF 등)를 지운다 (11/18 개인정보).
    휴대폰 사진에는 찍은 곳의 좌표가 들어 있을 수 있는데, 올린 사진은 주소만 알면 누구나 받아 볼 수 있다.
    방향(회전) 정보는 그림에 먼저 적용해 사진이 눕지 않게 하고, 픽셀만 새 파일로 다시 저장한다.
    움직이는 GIF 는 그대로 둔다 (GIF 는 위치 정보를 담지 않는다). 그림으로 읽을 수 없으면 ValueError."""
    if ext == "gif":
        return data
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        fmt = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}[ext]
        if fmt == "JPEG" and img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        clean = Image.new(img.mode, img.size)          # 픽셀만 옮긴 새 그림 (info · exif · xmp 를 넘기지 않음)
        clean.putdata(list(img.getdata())) if img.mode == "P" else clean.paste(img)
        if img.mode == "P" and img.getpalette():
            clean.putpalette(img.getpalette())
        out = io.BytesIO()
        opts = {"JPEG": {"quality": 92}, "WEBP": {"quality": 90}, "PNG": {"optimize": True}}[fmt]
        clean.save(out, fmt, **opts)
        return out.getvalue()
    except (UnidentifiedImageError, OSError, KeyError, ValueError) as exc:
        raise ValueError("사진을 읽지 못했어요. 다른 사진으로 다시 올려 주세요.") from exc


BUCKET = "uploads"     # supabase/migrations/011_storage.sql 의 공개 버킷 (공개 웹과 같은 곳)
_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}


def _store(filename: str, data: bytes) -> str:
    """사진 한 장을 저장하고 저장소 칸에 넣을 값을 돌려준다 (11/19).
    STORAGE_MODE=supabase 면 사진 저장소(Supabase Storage 공개 버킷)에 올려 https 주소를 돌려준다 —
    Streamlit Cloud 서버의 static/uploads 는 다시 배포하면 사라지고(11/19 사진 5장 잃음) 공개 웹(Vercel)은 볼 수 없어서.
    저장소에 못 올리면(011 미적용 · 연결 실패) 예전처럼 static/uploads 에 쓰고 파일 이름을 돌려준다."""
    import os

    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_KEY") or "").strip()
    if (os.getenv("STORAGE_MODE") or "").strip() == "supabase" and url and key:
        try:
            import requests

            headers = {"apikey": key, "Content-Type": _MIME.get(filename.rsplit(".", 1)[-1], "application/octet-stream"),
                       "x-upsert": "false", **({"Authorization": f"Bearer {key}"} if key.startswith("eyJ") else {})}
            res = requests.post(f"{url}/storage/v1/object/{BUCKET}/{filename}", data=data, headers=headers, timeout=20)
            if res.status_code in (200, 201):
                return f"{url}/storage/v1/object/public/{BUCKET}/{filename}"
        except Exception:      # 저장소가 안 되면 아래 로컬 파일로 (사진 올리기 자체는 멈추지 않게)
            pass
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    (IMAGE_DIR / filename).write_bytes(data)
    return filename


def save(name: str, data: bytes) -> str:
    """이미지를 저장하고 파일 이름을 돌려준다. 원래 이름은 쓰지 않는다 (경로 조작 방지).
    저장 전에 위치·기기 정보(EXIF)를 지운다 (strip_metadata)."""
    ext = Path(name).suffix.lower().lstrip(".")
    if ext not in TYPES:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {name}")
    data = strip_metadata(data, ext)
    return _store(f"{uuid.uuid4().hex[:12]}.{ext}", data)


AVATAR_PX = 256      # 프로필 사진은 화면에 72px 이하로만 보인다 → 256px 정사각형이면 레티나에서도 충분


def save_avatar(name: str, data: bytes) -> str:
    """프로필 사진: 가운데를 정사각형으로 잘라 256px webp 로 줄여 저장한다 (11/18 — 원본(최대 5MB)을 그대로 두면
    마이페이지 · 리뷰 옆 동그라미가 뜨는 데 오래 걸렸다). 다시 저장하므로 위치 · 기기 정보(EXIF)도 남지 않는다.
    움직이는 GIF 도 첫 장면만 쓴다. 그림으로 읽을 수 없으면 ValueError."""
    ext = Path(name).suffix.lower().lstrip(".")
    if ext not in TYPES:
        raise ValueError(f"지원하지 않는 이미지 형식입니다: {name}")
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
        img = ImageOps.fit(img, (AVATAR_PX, AVATAR_PX), Image.LANCZOS)      # 가운데 정사각형
        out = io.BytesIO()
        img.save(out, "WEBP", quality=85, method=4)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("사진을 읽지 못했어요. 다른 사진으로 다시 올려 주세요.") from exc
    return _store(f"{uuid.uuid4().hex[:12]}.webp", out.getvalue())


def remove(names) -> int:
    """지운 리뷰에 붙어 있던 사진 파일을 실제로 지운다 (11/18 개인정보: 주소를 알아도 더는 열리지 않게).
    리뷰 사진만 — 카페 포스터는 되돌리기가 옛 그림을 가리킬 수 있어 지우지 않는다. 지운 수를 돌려준다."""
    n = 0
    for name in split(names):
        p = IMAGE_DIR / Path(name).name
        try:
            if p.is_file():
                p.unlink()
                n += 1
        except OSError:
            pass
    return n


def split(value) -> list[str]:
    return [p.strip() for p in str(value or "").split(",") if p.strip()]


class Remote(str):
    """공개 웹(Vercel)이 사진 저장소(Supabase Storage 공개 버킷)에 올린 사진의 https 주소 (11/19).
    파일 경로(Path)처럼 .name 을 쓰는 곳이 있어서 .name 은 주소 전체를 돌려준다 (저장할 때 그대로 남도록)."""

    @property
    def name(self) -> str:
        return str(self)

    def is_file(self) -> bool:
        return True


_REMOTE = re.compile(r"^https://[A-Za-z0-9.-]+/storage/v1/object/public/uploads/[0-9a-f]{12}\.(png|jpg|jpeg|webp|gif)$")


def paths(value) -> list[Path]:
    """저장소의 images 칸 → 실제로 있는 파일 경로들. 파일 이름 밖으로 나가는 값은 버린다.
    공개 웹이 올린 사진(사진 저장소의 https 주소)은 Remote 로 그대로 넣는다."""
    out = []
    for name in split(value):
        if _REMOTE.match(name):
            out.append(Remote(name))
            continue
        p = IMAGE_DIR / Path(name).name
        if p.is_file():
            out.append(p)
    return out


def poster(value) -> Path | None:
    found = paths(value)
    return found[0] if found else None


def url(path: Path) -> str:
    """static/uploads/ 의 파일 → 화면에서 쓰는 주소 (페이지 기준 상대 주소). 사진 저장소의 사진은 https 주소 그대로."""
    if isinstance(path, Remote):
        return str(path)
    parts = Path(path).parts                 # IMAGE_DIR / "https://…" 처럼 이어 붙인 경우도 주소로 되돌린다
    if "https:" in parts:
        return "https://" + "/".join(parts[parts.index("https:") + 1:])
    return f"app/static/uploads/{path.name}"


# 포스터를 올리지 않은 카페에 보여 줄 기본 그림. 저장소에는 넣지 않고 화면에서만 쓴다.
DEFAULT_POSTER = ROOT / "static" / "default_poster.png"
DEFAULT_POSTER_URL = "app/static/default_poster.png"
