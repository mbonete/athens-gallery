"""Sample fresco colours in named boxes (3840-scan coords); print medians and draw the boxes on a sheet."""
import json
import numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
S = 20111 / 3840
BOXES = {
    "wall, lit side (left nave, faces +X)": (1200, 1000, 1240, 1100),
    "wall, shaded side (right nave, faces -X)": (2600, 1000, 2650, 1100),
    "frontal face, left (faces viewer)": (1060, 900, 1120, 1100),
    "frontal face, right (faces viewer)": (2720, 900, 2800, 1100),
    "plain soffit over bay 1, left": (1270, 580, 1320, 660),
    "plain soffit over bay 1, right": (2510, 560, 2560, 640),
    "entablature frieze on first left pier": (1285, 745, 1330, 790),
    "cornice soffit, left (lit side)": (1400, 860, 1440, 940),
    "cornice soffit, right (shaded side)": (2440, 860, 2480, 940),
    "pilaster shaft, first right pier (shade)": (2525, 740, 2580, 790),
    "platform floor, white": (1560, 2010, 1630, 2020),
    "platform floor, mauve": (1700, 1985, 1730, 1995),
    "lower floor, mauve": (2110, 2412, 2240, 2438),
    "lower floor, white band": (2080, 2482, 2330, 2492),
    "sky in the far door": (1880, 1395, 1940, 1420),
}
im = Image.open(__import__('os').environ.get('FRESCO', 'reference/download/athens-original.jpg')).convert('RGB')
out = {}
for name, (x0, y0, x1, y1) in BOXES.items():
    a = np.asarray(im.crop((int(x0 * S), int(y0 * S), int(x1 * S), int(y1 * S)))).reshape(-1, 3)
    m = [int(v) for v in np.median(a, 0)]
    out[name] = {"box_3840": [x0, y0, x1, y1], "median_srgb": m, "hex": "#" + "".join(f"{v:02x}" for v in m)}
    print(f"{name:45s} {tuple(m)} {out[name]['hex']}")
out.update({k: {"median_srgb": v, "hex": "#" + "".join(f"{c:02x}" for c in v), "source": "vault unroll + fitted tiling mask"}
            for k, v in json.load(open('vault_samples.json')).items()})
json.dump(out, open('fresco_samples.json', 'w'), indent=1)
small = Image.open(__import__('os').environ.get('FRESCO_3840', 'reference/download/athens-3840.jpg')).convert('RGB')
d = ImageDraw.Draw(small)
for i, (name, (x0, y0, x1, y1)) in enumerate(BOXES.items()):
    d.rectangle((x0, y0, x1, y1), outline=(0, 255, 0), width=3); d.text((x1 + 4, y0), str(i + 1), fill=(0, 255, 0))
small.resize((1920, 1330)).save('crops/sample-boxes.jpg', quality=88)
