"""Finish baked lightmap atlases in place: fill the unbaked space, then denoise.

Usage: python -I tools/denoise_lightmaps.py <h> <atlas.png> [...]
- Fill: every pixel Blender didn't bake (alpha 0) takes the colour of the nearest baked islands
  (push-pull over an image pyramid), so mipmaps and bilinear filtering never pull in black.
- Denoise: non-local means on the sRGB PNG, strength h (3-6); Cycles bakes come out noisy.
Writes RGB PNGs.
"""
import sys
import time

import cv2
import numpy as np


def push_pull(rgb, mask):
    """Fill rgb where mask == 0 from the masked pixels around (pyramid average, then upsample)."""
    c = rgb.astype(np.float32) * mask[..., None]
    w = mask.astype(np.float32)
    levels = []
    while min(c.shape[:2]) > 1:
        levels.append((c, w))
        h2, w2 = (c.shape[0] + 1) // 2, (c.shape[1] + 1) // 2
        c = cv2.resize(c, (w2, h2), interpolation=cv2.INTER_AREA) * 4
        w = cv2.resize(w, (w2, h2), interpolation=cv2.INTER_AREA) * 4
    fill = c / np.maximum(w, 1e-6)[..., None]
    for c, w in reversed(levels):
        up = cv2.resize(fill, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_LINEAR)
        have = w > 1e-6
        fill = np.where(have[..., None], c / np.maximum(w, 1e-6)[..., None], up)
    return fill


h = float(sys.argv[1])
for path in sys.argv[2:]:
    t0 = time.time()
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img.ndim == 3 and img.shape[2] == 4:
        mask = (img[..., 3] > 0).astype(np.float32)
        rgb = img[..., :3]
        filled = np.where(mask[..., None] > 0, rgb, push_pull(rgb, mask)).clip(0, 255).astype(np.uint8)
    else:
        filled = img[..., :3]
    out = cv2.fastNlMeansDenoisingColored(filled, None, h, h, 5, 15) if h > 0 else filled
    cv2.imwrite(path, out, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    print(f"finished {path} {img.shape[1]}x{img.shape[0]} in {time.time() - t0:.1f}s")
