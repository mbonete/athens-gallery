"""Check that the web's opening view lands where Blender's Raphael view does (and so on the fresco).

Usage: python -I tools/web_overlay.py <athens-3840.jpg> <web_screenshot.png> <blender_raphael.png> <out_prefix>
The screenshot is the page at ?fresco (canvas at the fresco's proportions). Writes:
  <out_prefix>-edges.jpg   the web view's edges in red, Blender's in cyan, on the fresco
  <out_prefix>-blend.jpg   web view and fresco 50/50
and prints how many of Blender's edge pixels have a web edge within 1, 2 and 4 px.
"""
import sys

import cv2
import numpy as np

fresco_path, web_path, blender_path, prefix = sys.argv[1:5]
web = cv2.imread(web_path)
h, w = web.shape[:2]
fresco = cv2.resize(cv2.imread(fresco_path), (w, h), interpolation=cv2.INTER_AREA)
blender = cv2.resize(cv2.imread(blender_path), (w, h), interpolation=cv2.INTER_AREA)


def edges(img, lo, hi):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    return cv2.Canny(g, lo, hi)


e_web = edges(web, 30, 90)
e_bl = edges(blender, 12, 36)
mask = np.ones((h, w), bool)
mask[int(h * 0.94):, int(w * 0.42):int(w * 0.58)] = False      # the "pinch or scroll" hint
e_web &= mask.astype(np.uint8) * 255
e_bl &= mask.astype(np.uint8) * 255
dist = cv2.distanceTransform(255 - e_web, cv2.DIST_L2, 3)
d = dist[e_bl > 0]
for r in (1, 2, 4):
    print(f"Blender edge pixels with a web edge within {r} px: {(d <= r).mean():.1%}")
out = (fresco * 0.75).astype(np.uint8)
out[cv2.dilate(e_bl, np.ones((2, 2), np.uint8)) > 0] = (255, 255, 0)
out[e_web > 0] = (0, 0, 255)
cv2.imwrite(f"{prefix}-edges.jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 88])
cv2.imwrite(f"{prefix}-blend.jpg", cv2.addWeighted(fresco, 0.5, web, 0.5, 0), [cv2.IMWRITE_JPEG_QUALITY, 88])
