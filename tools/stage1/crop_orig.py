"""Crop the full-res fresco at 3840-scan coordinates. Usage: crop_orig.py x0 y0 x1 y1 out.jpg maxw [grid_step_3840]"""
import sys
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
S = 20111 / 3840
x0, y0, x1, y1 = map(float, sys.argv[1:5]); out = sys.argv[5]; maxw = int(sys.argv[6])
step = float(sys.argv[7]) if len(sys.argv) > 7 else 0
im = Image.open(__import__('os').environ.get('FRESCO', 'reference/download/athens-original.jpg'))
c = im.crop((int(x0*S), int(y0*S), int(x1*S), int(y1*S)))
k = min(1.0, maxw / c.width)
c = c.resize((int(c.width*k), int(c.height*k)), Image.LANCZOS).convert('RGB')
if step:
    d = ImageDraw.Draw(c)
    sc = c.width / (x1 - x0)
    g = (int(x0 // step) + 1) * step
    while g < x1:
        X = (g - x0) * sc; d.line([(X, 0), (X, c.height)], fill=(0, 255, 255)); d.text((X+2, 2), f"{g:g}", fill=(0, 255, 255)); g += step
    g = (int(y0 // step) + 1) * step
    while g < y1:
        Y = (g - y0) * sc; d.line([(0, Y), (c.width, Y)], fill=(255, 0, 255)); d.text((2, Y+2), f"{g:g}", fill=(255, 0, 255)); g += step
c.save(out, quality=90)
print(c.size)
