"""PWA 아이콘 만들기: ../static/logo_mint.png 의 토끼 캐릭터를 잘라 정사각형으로 깐다.

실행: python web/scripts/make_icons.py  (저장소 루트에서)
결과: web/public/icons/*.png, web/public/logo.png
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "static" / "logo_mint.png"
WIDE = ROOT / "static" / "logo2.png"
OUT = ROOT / "web" / "public" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

logo = Image.open(SRC).convert("RGBA")
# 오른쪽 토끼 캐릭터만 남긴다: 이어진 덩어리(연결 요소) 중 토끼 영역 안에 있는 것만 고른다.
# 글자 E 와 아래 꼬리 곡선은 따로 떨어진 덩어리라 걸러진다.
import numpy as np
from scipy import ndimage

arr = np.array(logo)
x0, y0, x1, y1 = 1170, 75, logo.width, 275
region = arr[y0:y1, x0:x1].copy()
lab, _ = ndimage.label(region[:, :, 3] > 40)
keep = np.zeros(lab.shape, bool)
for i, sl in enumerate(ndimage.find_objects(lab), 1):
    if sl is None:
        continue
    ys, xs = sl
    # 영역 왼쪽 경계에 닿는 덩어리(E 글자·곡선)는 버린다
    if xs.start <= 2 and (lab[sl] == i).sum() > 50:
        continue
    keep |= lab == i
# 머리 아래로 이어진 꼬리 곡선을 대각선으로 잘라낸다 (원본 좌표 기준)
yy, xx = np.mgrid[y0:y1, x0:x1]
keep &= ~((xx < 1252) & (yy > 243 + (xx - 1205) * 0.33))
region[~keep] = 0
# 얼굴 안쪽(투명 구멍)은 흰색으로 채워 어떤 배경에서도 얼굴이 보이게 한다
filled = ndimage.binary_fill_holes(keep)
hole = filled & ~keep
region[hole] = (255, 255, 255, 255)
mascot = Image.fromarray(region)
mascot = mascot.crop(mascot.getbbox())


def square(size: int, bg: tuple, ratio: float) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), bg)
    m = mascot.copy()
    m.thumbnail((int(size * ratio), int(size * ratio)), Image.LANCZOS)
    canvas.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2))
    return canvas.convert("RGB")


WHITE = (255, 255, 255, 255)
SOFT = (230, 246, 240, 255)  # #E6F6F0
square(192, WHITE, 0.84).save(OUT / "icon-192.png")
square(512, WHITE, 0.84).save(OUT / "icon-512.png")
# maskable: 안전 영역(가운데 80%) 안에 들어가게 더 작게
square(512, SOFT, 0.64).save(OUT / "maskable-512.png")
square(180, WHITE, 0.84).save(OUT / "apple-touch-icon.png")
square(48, WHITE, 0.9).save(OUT / "favicon-48.png")

wide = Image.open(WIDE).convert("RGBA")
wide.thumbnail((480, 140), Image.LANCZOS)
wide.save(ROOT / "web" / "public" / "logo.png")
print("ok", [p.name for p in OUT.iterdir()])
