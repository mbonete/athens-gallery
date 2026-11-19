"""Review sheets for the stage 1 renders: render beside the fresco at the same framing, close-up
pairs (render crop beside the same fresco crop) and the vault unrolled from both.

Usage: python -I tools/stage1_sheets.py <fresco_original.jpg> <render_dir> <out_dir>
<render_dir> holds hall-raphael.png (Raphael's framing, any width), crop-coffers.png and
crop-capital.png (full-resolution crops of Raphael's view; boxes below, in 3840-scan pixels).
"""
import math
import sys
from pathlib import Path

import cv2
import numpy as np

CX, CY, F, EYE, ZS, R = 1933.3, 1775.9, 2274.0, 1.85, 12.3, 5.9
CROPS = {"coffers": (1650, 400, 2250, 720), "capital": (1140, 560, 1480, 940)}   # = build.py VIEWS

fresco_path, rdir, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
fresco = cv2.imread(fresco_path)
S = fresco.shape[1] / 3840


def label(img, text):
    img = img.copy()
    cv2.rectangle(img, (0, 0), (min(img.shape[1], 14 + 13 * len(text)), 34), (0, 0, 0), -1)
    cv2.putText(img, text, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def side(a, b, gap=12):
    h = max(a.shape[0], b.shape[0])
    pad = lambda m: cv2.copyMakeBorder(m, 0, h - m.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    return np.hstack([pad(a), np.full((h, gap, 3), 255, np.uint8), pad(b)])


def save(name, img):
    cv2.imwrite(str(out / name), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print("wrote", out / name, img.shape[1], "x", img.shape[0])


# 1. Raphael's view beside the fresco.
render = cv2.imread(str(rdir / "hall-raphael.png"))
h, w = render.shape[:2]
fr = cv2.resize(fresco, (w, h), interpolation=cv2.INTER_AREA)
save("raphael-side-by-side.jpg", side(label(fr, "Fresco (Raphael, 1509-11)"), label(render, "Stage 1 render, Cycles, same camera")))

# 2. Close-up pairs at the same pixels.
for key, (x0, y0, x1, y1) in CROPS.items():
    rc = cv2.imread(str(rdir / f"crop-{key}.png"))
    fc = fresco[int(y0 * S):int(y1 * S), int(x0 * S):int(x1 * S)]
    fc = cv2.resize(fc, (rc.shape[1], rc.shape[0]), interpolation=cv2.INTER_AREA)
    k = 2 if rc.shape[1] < 500 else 1.5
    up = lambda m: cv2.resize(m, (int(m.shape[1] * k), int(m.shape[0] * k)), interpolation=cv2.INTER_CUBIC)
    save(f"closeup-{key}-vs-fresco.jpg", side(label(up(fc), f"Fresco, u {x0}-{x1}, v {y0}-{y1}"),
                                              label(up(rc), "Render, same camera and pixels")))


# 3. The vault unrolled (s = arc length from the crown, y = depth) from the fresco and from the render.
def unroll(img, k, s0=-7.0, s1=7.0, y0=22.0, y1=31.6, ppm=70):
    s = np.arange(s0, s1, 1 / ppm)
    y = np.arange(y1, y0, -1 / ppm)
    Sg, Yg = np.meshgrid(s, y)
    th = Sg / R
    X, Z = R * np.sin(th), ZS + R * np.cos(th)
    u, v = CX + F * X / Yg, CY - F * (Z - EYE) / Yg
    res = cv2.remap(img, (u * k).astype(np.float32), (v * k).astype(np.float32), cv2.INTER_AREA)
    for m in range(math.ceil(s0), math.floor(s1) + 1):
        res[:, min(int((m - s0) * ppm), res.shape[1] - 1)] = (0, 200, 255)
    for m in range(math.ceil(y0), math.floor(y1) + 1):
        res[min(int((y1 - m) * ppm), res.shape[0] - 1), :] = (255, 0, 200)
    return res


fu = label(unroll(fresco, S), "Fresco vault, unrolled (grid 1 m; top = crossing arch, y 31.6)")
ru = label(unroll(render, w / 3840), "Render vault, unrolled the same way")
save("vault-unrolled-fresco-vs-render.jpg", np.vstack([fu, np.full((12, fu.shape[1], 3), 255, np.uint8), ru]))
