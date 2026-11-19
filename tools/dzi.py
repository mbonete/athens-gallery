"""Cut an image into Deep Zoom (DZI) tiles for OpenSeadragon, plus a texture for WebGL.

Usage: python dzi.py <image> <out_dir> <name> [texture_width]
Writes <out_dir>/<name>.dzi, <out_dir>/<name>_files/<level>/<col>_<row>.jpg and
<out_dir>/<name>-texture.jpg. Same layout as `vips dzsave` (tile 254, overlap 1).
"""
import math
import sys
from pathlib import Path

from PIL import Image

src, out, name = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
tex_w = int(sys.argv[4]) if len(sys.argv) > 4 else 2048
TILE, OVERLAP, Q = 254, 1, 88

img = Image.open(src).convert("RGB")
W, H = img.size
out.mkdir(parents=True, exist_ok=True)
max_level = math.ceil(math.log2(max(W, H)))
for level in range(max_level, -1, -1):
    scale = 2 ** (max_level - level)
    lw, lh = max(1, math.ceil(W / scale)), max(1, math.ceil(H / scale))
    li = img if scale == 1 else img.resize((lw, lh), Image.LANCZOS)
    d = out / f"{name}_files" / str(level)
    d.mkdir(parents=True, exist_ok=True)
    for col in range(math.ceil(lw / TILE)):
        for row in range(math.ceil(lh / TILE)):
            x0 = max(0, col * TILE - OVERLAP)
            y0 = max(0, row * TILE - OVERLAP)
            x1 = min(lw, (col + 1) * TILE + OVERLAP)
            y1 = min(lh, (row + 1) * TILE + OVERLAP)
            li.crop((x0, y0, x1, y1)).save(d / f"{col}_{row}.jpg", quality=Q)
(out / f"{name}.dzi").write_text(
    f'<?xml version="1.0" encoding="UTF-8"?>\n'
    f'<Image xmlns="http://schemas.microsoft.com/deepzoom/2008" Format="jpg" Overlap="{OVERLAP}" '
    f'TileSize="{TILE}"><Size Width="{W}" Height="{H}"/></Image>\n')
th = round(H * tex_w / W)
img.resize((tex_w, th), Image.LANCZOS).save(out / f"{name}-texture.jpg", quality=90)
print(f"{name}: {W}x{H}, levels 0-{max_level}, texture {tex_w}x{th}")
