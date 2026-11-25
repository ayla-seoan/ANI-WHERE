"""로고 · 마스코트 · 앱 아이콘 만들기 (11/25 A안 확정 로고, docs/design/handoff/assets).

실행: python web/scripts/make_icons.py  (저장소 루트에서)
결과: 웹 web/public/{logo_sm.webp, logo.png, mascot.png, ask_avatar.png, icons/*.png} · web/app/{icon.png, apple-icon.png}
      앱 static/{logo.png, mascot.png, ask_avatar.png}
규칙 (handoff README 3-1): 로고는 높이 32px 이상에서만, 그보다 작으면 마스코트만. 물어보기 도우미 얼굴 · 앱 아이콘 · 파비콘 = 마스코트.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "docs" / "design" / "handoff" / "assets"
PUB = ROOT / "web" / "public"
APP = ROOT / "web" / "app"
STATIC = ROOT / "static"
ICONS = PUB / "icons"
ICONS.mkdir(parents=True, exist_ok=True)

logo = Image.open(SRC / "aniwhere_logo.png").convert("RGBA")
mascot = Image.open(SRC / "aniwhere_mascot.png").convert("RGBA")
mascot = mascot.crop(mascot.getbbox())

WHITE = (255, 255, 255, 255)
SOFT = (233, 247, 242, 255)      # 메뉴바 연민트 #e9f7f2
LINE = (158, 221, 204, 255)      # 카드 테두리 #9eddcc


def fit(img: Image.Image, w: int, h: int) -> Image.Image:
    out = img.copy()
    out.thumbnail((w, h), Image.LANCZOS)
    return out


def square(size: int, bg: tuple, ratio: float) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), bg)
    m = fit(mascot, int(size * ratio), int(size * ratio))
    canvas.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2))
    return canvas.convert("RGB")


def circle(size: int, ratio: float = 0.7) -> Image.Image:
    """흰 동그라미 + 연민트 테두리 안에 마스코트 (물어보기 도우미 얼굴). 4배로 그려 줄여 가장자리를 매끈하게."""
    big = size * 4
    canvas = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.ellipse((0, 0, big - 1, big - 1), fill=LINE)
    b = big // 24
    d.ellipse((b, b, big - 1 - b, big - 1 - b), fill=WHITE)
    m = fit(mascot, int(big * ratio), int(big * ratio))
    canvas.alpha_composite(m, ((big - m.width) // 2, (big - m.height) // 2 + big // 40))
    return canvas.resize((size, size), Image.LANCZOS)


# 로고 (배경 투명). 메뉴바 52px 의 3배
fit(logo, 2000, 156).save(PUB / "logo_sm.webp", quality=92, method=6)
fit(logo, 480, 140).save(PUB / "logo.png", optimize=True)
fit(logo, 2000, 208).save(STATIC / "logo.png", optimize=True)

# 마스코트
mascot.save(PUB / "mascot.png", optimize=True)
mascot.save(STATIC / "mascot.png", optimize=True)
circle(96).save(PUB / "ask_avatar.png", optimize=True)
circle(128).save(STATIC / "ask_avatar.png", optimize=True)

# 앱 아이콘 · 파비콘
square(192, WHITE, 0.72).save(ICONS / "icon-192.png", optimize=True)
square(512, WHITE, 0.72).save(ICONS / "icon-512.png", optimize=True)
square(512, SOFT, 0.56).save(ICONS / "maskable-512.png", optimize=True)   # 안전 영역(가운데 80%) 안에
square(180, WHITE, 0.72).save(ICONS / "apple-touch-icon.png", optimize=True)
square(48, WHITE, 0.86).save(ICONS / "favicon-48.png", optimize=True)
square(48, WHITE, 0.86).save(APP / "icon.png", optimize=True)
square(180, WHITE, 0.72).save(APP / "apple-icon.png", optimize=True)
print("ok", sorted(p.name for p in ICONS.iterdir()))
