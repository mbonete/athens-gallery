"""Crop a region of an image, upscale it and draw a labelled pixel grid, to read coordinates.

Usage: python grid_crop.py <image> <x0> <y0> <x1> <y1> <step> <out.jpg> [scale]
Coordinates are in the source image's pixels; grid labels show source coordinates.
"""
import sys

from PIL import Image, ImageDraw

src, x0, y0, x1, y1, step, out = sys.argv[1], *map(int, sys.argv[2:7]), sys.argv[7]
scale = float(sys.argv[8]) if len(sys.argv) > 8 else 2.0
im = Image.open(src).convert("RGB").crop((x0, y0, x1, y1))
im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
d = ImageDraw.Draw(im)
for gx in range((x0 // step + 1) * step, x1, step):
    X = (gx - x0) * scale
    d.line([(X, 0), (X, im.height)], fill=(0, 255, 255), width=1)
    d.text((X + 2, 2), str(gx), fill=(0, 255, 255))
for gy in range((y0 // step + 1) * step, y1, step):
    Y = (gy - y0) * scale
    d.line([(0, Y), (im.width, Y)], fill=(255, 0, 255), width=1)
    d.text((2, Y + 2), str(gy), fill=(255, 0, 255))
im.save(out, quality=90)
