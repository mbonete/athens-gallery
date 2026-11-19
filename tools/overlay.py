"""Lay a render over the fresco: a 50/50 blend and the render's edges drawn on the fresco.

Usage: python overlay.py <fresco.jpg> <render.png> <out_prefix>
Writes <out_prefix>-blend.jpg and <out_prefix>-edges.jpg at the render's size.
"""
import sys

import cv2
import numpy as np

fresco_path, render_path, prefix = sys.argv[1:4]
render = cv2.imread(render_path)
h, w = render.shape[:2]
fresco = cv2.resize(cv2.imread(fresco_path), (w, h), interpolation=cv2.INTER_AREA)

blend = cv2.addWeighted(fresco, 0.5, render, 0.5, 0)
cv2.imwrite(f"{prefix}-blend.jpg", blend, [cv2.IMWRITE_JPEG_QUALITY, 88])

gray = cv2.cvtColor(render, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 12, 36)
edges = cv2.dilate(edges, np.ones((2, 2), np.uint8))
out = (fresco * 0.8).astype(np.uint8)
out[edges > 0] = (0, 0, 255)
cv2.imwrite(f"{prefix}-edges.jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 88])
