"""Does the opening arch's meander band land on the painted one? Finds the band's outer and inner
edges along radial cuts (every 4 degrees, 8-172) in the fresco and in a view of the model at the
fresco's framing (the web at ?fresco, or Blender's Raphael view), and compares them cut by cut.

Usage: python -I tools/arch_check.py <athens-3840.jpg> <view.png> [<out.json>]
Edges in scan px (3840 wide). A cut counts when both images give an edge there.
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "blender" / "scripts"))
import params as P  # noqa: E402


def band_edges(path):
    im = cv2.imread(path)
    S = im.shape[1] / P.IMG_W
    hsv = cv2.cvtColor(cv2.GaussianBlur(im, (5, 5), 0), cv2.COLOR_BGR2HSV)
    cu, cv_ = P.ARCH_C
    out = {}
    for deg in np.arange(8, 173, 4):
        t = math.radians(deg)
        rs = np.arange(1950, 1500, -0.5)
        us, vs = cu + rs * math.cos(t), cv_ - rs * math.sin(t)
        ok = (us >= 2) & (us < P.IMG_W - 2) & (vs >= 2)
        rs, us, vs = rs[ok], us[ok], vs[ok]
        p = hsv[np.clip((vs * S).astype(int), 0, im.shape[0] - 1), np.clip((us * S).astype(int), 0, im.shape[1] - 1)].astype(float)
        H, Sa, V = p[:, 0], p[:, 1], p[:, 2]
        white = (Sa < 70) & (V > 150)
        md = (((H > 8) & (H < 35) & (Sa > 90) & (V > 100)) | (V < 95)).astype(float)
        sm = np.convolve(md, np.ones(41) / 41, "same")
        wh = np.convolve(white.astype(float), np.ones(9) / 9, "same")
        for i in range(len(rs) - 120):
            if wh[i] > 0.6 and sm[i + 30:i + 110].min() > 0.8:
                j = i
                while j < len(rs) and not (md[j] and sm[j] > 0.8):
                    j += 1
                k = j
                while k < len(rs) - 1 and sm[k] > 0.55:
                    k += 1
                out[int(deg)] = (float(rs[j]), float(rs[k]))
                break
    return out


fresco, view = band_edges(sys.argv[1]), band_edges(sys.argv[2])
rows = []
for deg in sorted(set(fresco) & set(view)):
    (fo, fi), (vo, vi) = fresco[deg], view[deg]
    rows.append((deg, vo - fo, vi - fi))
d = np.array([[r[1], r[2]] for r in rows])
res = {"cuts": len(rows), "outer_edge_px": {"median": float(np.median(d[:, 0])), "median_abs": float(np.median(np.abs(d[:, 0]))),
                                             "max_abs": float(np.abs(d[:, 0]).max())},
       "inner_edge_px": {"median": float(np.median(d[:, 1])), "median_abs": float(np.median(np.abs(d[:, 1]))),
                         "max_abs": float(np.abs(d[:, 1]).max())},
       "per_cut": [{"deg": r[0], "outer": r[1], "inner": r[2]} for r in rows]}
print(f"{len(rows)} cuts; outer edge: median {res['outer_edge_px']['median']:+.1f} px, median |d| "
      f"{res['outer_edge_px']['median_abs']:.1f}, max |d| {res['outer_edge_px']['max_abs']:.1f}; inner edge: median "
      f"{res['inner_edge_px']['median']:+.1f}, median |d| {res['inner_edge_px']['median_abs']:.1f}, max |d| {res['inner_edge_px']['max_abs']:.1f}")
for r in rows:
    print(f"  {r[0]:4d} deg  outer {r[1]:+6.1f}  inner {r[2]:+6.1f}")
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(json.dumps(res, indent=1))
