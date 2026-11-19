"""Review sheets for the stage 2 renders (renders/hall-stage2/).

Usage: python -I tools/stage2_sheets.py <athens-original.jpg> <athens-3840.jpg> <render_root> <out_dir>
<render_root> holds the batch's folders: gate2/ (approved crossing), inside/ (bay-1 option),
A/ (crossing option A), physical/ (unlinked sun). Writes JPEG sheets into <out_dir>.
"""
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

CX, CY, F, EYE = 1933.3, 1775.9, 2274.0, 1.85
orig, scan, root, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
here = Path(__file__).resolve().parent
fresco = cv2.imread(orig)
S = fresco.shape[1] / 3840


def label(img, text, size=0.7):
    img = img.copy()
    cv2.rectangle(img, (0, 0), (min(img.shape[1], 16 + int(13 * len(text) * size / 0.7)), 34), (0, 0, 0), -1)
    cv2.putText(img, text, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, size, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def hstack(ims, gap=12):
    h = max(i.shape[0] for i in ims)
    pad = [cv2.copyMakeBorder(i, 0, h - i.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for i in ims]
    res = []
    for i, p in enumerate(pad):
        res.append(p)
        if i < len(pad) - 1:
            res.append(np.full((h, gap, 3), 255, np.uint8))
    return np.hstack(res)


def vstack(ims, gap=12):
    w = max(i.shape[1] for i in ims)
    pad = [cv2.copyMakeBorder(i, 0, 0, 0, w - i.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for i in ims]
    res = []
    for i, p in enumerate(pad):
        res.append(p)
        if i < len(pad) - 1:
            res.append(np.full((gap, w, 3), 255, np.uint8))
    return np.vstack(res)


def save(name, img, q=88):
    cv2.imwrite(str(out / name), img, [cv2.IMWRITE_JPEG_QUALITY, q])
    print("wrote", out / name, img.shape[1], "x", img.shape[0])


def jpg(src, name, width=None):
    im = cv2.imread(str(src))
    if width:
        im = cv2.resize(im, (width, int(im.shape[0] * width / im.shape[1])), interpolation=cv2.INTER_AREA)
    save(name, im, 90)
    return im


# Raphael's view: side by side with the fresco, overlay, for the approved crossing and option A.
for tag, d in (("", root / "gate2"), ("-crossingA", root / "A")):
    r = cv2.imread(str(d / "hall-raphael.png"))
    h, w = r.shape[:2]
    fr = cv2.resize(fresco, (w, h), interpolation=cv2.INTER_AREA)
    name = "crossing A (square 11.8 m)" if tag else "approved crossing (Gate 2)"
    save(f"raphael-side-by-side{tag}.jpg", hstack([label(fr, "Fresco (Raphael, 1509-11)"),
                                                   label(r, f"Stage 2, Cycles, same camera; {name}")]))
    jpg(d / "hall-raphael.png", f"hall-raphael{tag}.jpg")
    subprocess.run([sys.executable, "-I", str(here / "overlay.py"), scan, str(d / "raphael.png"),
                    str(out / f"raphael{tag}")], check=True)

jpg(root / "physical" / "hall-raphael.png", "hall-raphael-physical.jpg")

# Eye level: entrance, mid-nave, under the dome, end door (+ the dome from below).
views = [("s2-entrance", "Entrance (platform, 1.6 m)"), ("s2-midnave", "Mid-nave, bay 2"),
         ("s2-dome", "Under the dome, towards the second arm"), ("s2-door", "At the end door")]
ims = [label(cv2.resize(cv2.imread(str(root / "gate2" / f"{v}.png")), (960, 600), interpolation=cv2.INTER_AREA), t)
       for v, t in views]
save("eye-level-sheet.jpg", vstack([hstack(ims[:2]), hstack(ims[2:])]))
for v, _ in views:
    jpg(root / "gate2" / f"{v}.png", f"{v}.jpg")
jpg(root / "gate2" / "eye-dome.png", "s2-dome-up.jpg")
for v in ("s2-dome", "s2-midnave"):
    jpg(root / "A" / f"{v}.png", f"{v}-crossingA.jpg")

# Bay 1 hanging options.
opts = []
for d, t in (("gate2", "below the niches"), ("inside", "Mucha inside its niche")):
    pair = [label(cv2.resize(cv2.imread(str(root / d / f"s2-bay1-{s}.png")), (840, 600), interpolation=cv2.INTER_AREA),
                  f"{t}: {'left, Mucha' if s == 'left' else 'right, Klimt'}") for s in ("left", "right")]
    opts.append(hstack(pair))
save("bay1-options.jpg", vstack(opts))
for d in ("gate2", "inside"):
    for s in ("left", "right"):
        jpg(root / d / f"s2-bay1-{s}.png", f"bay1-{'below' if d == 'gate2' else 'inside'}-{s}.jpg")

# Close-ups beside the same fresco crops (same boxes as build.py's crop views).
for key, (x0, y0, x1, y1) in {"coffers": (1650, 400, 2250, 720), "capital": (1140, 560, 1480, 940)}.items():
    rc = cv2.imread(str(root / "gate2" / f"crop-{key}.png"))
    fc = cv2.resize(fresco[int(y0 * S):int(y1 * S), int(x0 * S):int(x1 * S)], (rc.shape[1], rc.shape[0]),
                    interpolation=cv2.INTER_AREA)
    k = 2 if rc.shape[1] < 500 else 1.5
    up = lambda m: cv2.resize(m, (int(m.shape[1] * k), int(m.shape[0] * k)), interpolation=cv2.INTER_CUBIC)
    save(f"closeup-{key}-vs-fresco.jpg", hstack([label(up(fc), f"Fresco, u {x0}-{x1}, v {y0}-{y1}"),
                                                 label(up(rc), "Render, same camera and pixels")]))


# Crossing options drawn on the fresco: the front and back arch intrados of each option.
def arcs_sheet():
    x0, y0, x1, y1 = 1440, 600, 2420, 1300
    k = 900 / (x1 - x0)
    base = cv2.resize(fresco[int(y0 * S):int(y1 * S), int(x0 * S):int(x1 * S)], (900, int((y1 - y0) * k)),
                      interpolation=cv2.INTER_AREA)

    def arc(img, Y, R, col):
        ts = np.linspace(0, np.pi, 200)
        pts = [((CX + F * R * np.cos(t) / Y - x0) * k, (CY - F * (12.3 + R * np.sin(t) - EYE) / Y - y0) * k) for t in ts]
        cv2.polylines(img, [np.array(pts, np.int32)], False, col, 2, cv2.LINE_AA)
    panels = []
    for name, yf, R, note in (("gate2 (approved): 10.95 m", 32.5, 5.475, "front crown 24 px high, back 5 px low"),
                              ("A: square 11.8 m", 34.2, 5.9, "front 3 px low, back 31 px low (0.6 m)"),
                              ("A2: square 11.8 m, shifted", 33.6, 5.9, "front 17 px high, back 20 px low")):
        img = base.copy()
        arc(img, yf, R, (0, 0, 255))
        arc(img, yf + 2 * R, R, (0, 220, 0))
        cv2.rectangle(img, (0, 0), (900, 52), (0, 0, 0), -1)
        cv2.putText(img, name, (8, 21), 0, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img, note + " (3840-px scan)", (8, 44), 0, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        panels.append(img)
    sheet = hstack(panels, 10)
    cv2.putText(sheet, "red: front arch (end of the nave barrel)   green: back arch (start of the second arm)",
                (10, sheet.shape[0] - 12), 0, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    save("crossing-options.jpg", sheet)


arcs_sheet()
