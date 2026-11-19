"""Find the fresco's central vanishing point from its straight edges.

Line segments come from OpenCV's LSD detector. Receding segments (neither near-horizontal
nor near-vertical) vote for a vanishing point with RANSAC; the inliers are refined by
least squares. Near-horizontal and near-vertical segments are measured separately, to
check that the photo is frontal and the painted camera has no tilt or roll.

Usage: python vp_detect.py <image> <out_dir>
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

img_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

img = cv2.imread(str(img_path))
H, W = img.shape[:2]
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Analyse only the painted scene: inside the lunette and above the bottom edge.
# The lunette's inner edge is approximated by a circle fitted by eye on the 3840 px image
# (centre and radius in fractions of the image size, so the script works at any scale).
cx, cy, r = 0.500 * W, 0.700 * H, 0.430 * W
yy, xx = np.mgrid[0:H, 0:W]
mask = (((xx - cx) ** 2 + (yy - cy) ** 2) < r ** 2) | (yy > cy)
mask &= (xx > 0.09 * W) & (xx < 0.91 * W)

lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)
segs = lsd.detect(gray)[0].reshape(-1, 4)
mid = (segs[:, :2] + segs[:, 2:]) / 2
inside = mask[mid[:, 1].astype(int).clip(0, H - 1), mid[:, 0].astype(int).clip(0, W - 1)]
segs = segs[inside]
d = segs[:, 2:] - segs[:, :2]
length = np.hypot(d[:, 0], d[:, 1])
ang = np.degrees(np.arctan2(d[:, 1], d[:, 0])) % 180

min_len = 0.012 * W
long_ = length > min_len
horiz = long_ & ((ang < 2) | (ang > 178))
vert = long_ & (np.abs(ang - 90) < 2)
reced = long_ & ~horiz & ~vert & (np.abs(ang - 90) > 8) & (ang > 8) & (ang < 172)


def homog(s):
    p = np.c_[s[:, :2], np.ones(len(s))]
    q = np.c_[s[:, 2:], np.ones(len(s))]
    l = np.cross(p, q)
    return l / np.linalg.norm(l[:, :2], axis=1, keepdims=True)


def angular_err(s, vp):
    """Angle between each segment and the line from its midpoint to vp (degrees)."""
    m = (s[:, :2] + s[:, 2:]) / 2
    a = s[:, 2:] - s[:, :2]
    b = vp[None, :] - m
    cos = np.abs((a * b).sum(1)) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


R = segs[reced]
RL = length[reced]
lines = homog(R)
rng = np.random.default_rng(0)
best, best_score = None, -1
for _ in range(20000):
    i, j = rng.choice(len(R), 2, replace=False)
    p = np.cross(lines[i], lines[j])
    if abs(p[2]) < 1e-9:
        continue
    vp = p[:2] / p[2]
    if not (0 <= vp[0] < W and 0 <= vp[1] < H):
        continue
    err = angular_err(R, vp)
    score = RL[err < 0.6].sum()
    if score > best_score:
        best, best_score = vp, score

inl = angular_err(R, best) < 0.6
# Least squares: point minimising length-weighted squared distance to inlier lines.
L = lines[inl]
w = RL[inl]
A = L[:, :2] * w[:, None]
b = -L[:, 2] * w
vp_ls, *_ = np.linalg.lstsq(A, b, rcond=None)
inl = angular_err(R, vp_ls) < 0.6
L = lines[inl]
w = RL[inl]
vp_ls, *_ = np.linalg.lstsq(L[:, :2] * w[:, None], -L[:, 2] * w, rcond=None)
dist = np.abs(L[:, :2] @ vp_ls + L[:, 2])
rms = float(np.sqrt((w * dist**2).sum() / w.sum()))


def mean_dev(sel, target):
    a = ang[sel]
    dev = ((a - target + 90) % 180) - 90
    return float(np.average(dev, weights=length[sel])), int(sel.sum())


h_dev, h_n = mean_dev(horiz, 0)
v_dev, v_n = mean_dev(vert, 90)

result = {
    "image": img_path.name,
    "size": [W, H],
    "vanishing_point_px": [round(float(vp_ls[0]), 1), round(float(vp_ls[1]), 1)],
    "vanishing_point_frac": [round(float(vp_ls[0] / W), 4), round(float(vp_ls[1] / H), 4)],
    "inlier_lines": int(inl.sum()),
    "receding_candidates": int(len(R)),
    "rms_line_distance_px": round(rms, 2),
    "horizontals_mean_tilt_deg": round(h_dev, 3),
    "horizontals_n": h_n,
    "verticals_mean_tilt_deg": round(v_dev, 3),
    "verticals_n": v_n,
}
print(json.dumps(result, indent=2))
(out_dir / "vp.json").write_text(json.dumps(result, indent=2))

# Overlay: inlier segments extended to the vanishing point, horizon, VP marker.
vis = img.copy()
dark = (vis * 0.55).astype(np.uint8)
vis = np.where(mask[..., None], vis, dark)
t = max(1, W // 1200)
vx, vy = vp_ls
for s in R[inl]:
    m = (s[:2] + s[2:]) / 2
    far = s[:2] if np.hypot(*(s[:2] - vp_ls)) > np.hypot(*(s[2:] - vp_ls)) else s[2:]
    cv2.line(vis, tuple(far.astype(int)), (int(vx), int(vy)), (0, 230, 255), t, cv2.LINE_AA)
for s in R[inl]:
    cv2.line(vis, tuple(s[:2].astype(int)), tuple(s[2:].astype(int)), (0, 0, 255), 3 * t, cv2.LINE_AA)
cv2.line(vis, (0, int(vy)), (W, int(vy)), (255, 120, 0), 2 * t, cv2.LINE_AA)
cv2.circle(vis, (int(vx), int(vy)), 14 * t, (255, 255, 255), 3 * t, cv2.LINE_AA)
cv2.circle(vis, (int(vx), int(vy)), 4 * t, (255, 255, 255), -1, cv2.LINE_AA)
cv2.imwrite(str(out_dir / "vp-lines.jpg"), vis, [cv2.IMWRITE_JPEG_QUALITY, 88])

# Zoom on the vanishing point.
z = int(0.06 * W)
crop = vis[int(vy) - z:int(vy) + z, int(vx) - z:int(vx) + z]
cv2.imwrite(str(out_dir / "vp-zoom.jpg"), crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
