# The sky texture for the web gallery, made from the sky Raphael painted in the School of Athens.
#
#   python gen_sky.py [size] [out.jpg] [debug]   (debug: marks where each fresco patch lands)
#
# Step 4. Inputs, made from the scan by prep.py, masks.py and gradient.py (make_sky.sh runs all):
#   sky-clean-2x.png  the fresco around its painted sky, cracks removed, at 2x the 3840 px scale
#   openings.npy      where the sky shows: 1 the drum's windows, 2 over the crossing's far arch,
#                     3 the far door (above Plato's and Aristotle's heads)
#   clear.npy         the cloudless sky inside them
#   gradient.json     the clear sky's colour per half degree of elevation
#
# Projection: stereographic, centred on the zenith (no pole, no seam). A texel at uv maps to
#   p = (2u - 1, 2v - 1) * K,  p = (d.x, -d.z) / (1 + d.y)   (v up = forward, the walk's -z)
# with K = tan(46 deg): the square's inscribed circle is 2 deg below the horizon. The corners go
# lower; below 5.5 deg the sky is one even haze, so the shader just clamps uv.
#
# Colour = base(elevation): the fresco's clear sky, measured
#        + the fresco's own sky over the crossing and through the far door, at the directions it
#          has from Raphael's eye (camera.json: f 2274 px, principal point 1933.3, 1775.9)
#        + his clouds again elsewhere, at the elevations he painted them, mirrored in turn
#        + his brushwork elsewhere: patches of his clear sky, quilted
# The drum's windows cut their clouds square, so their sky is kept apart: it's stored in the
# top-left corner (directions 15-21 deg below the horizon, never seen) and the shader swaps it
# in only near Raphael's viewpoint (Sky.tsx). In place, that patch holds plain sky.
import json, sys
import numpy as np, cv2
from PIL import Image

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2048
OUT = sys.argv[2] if len(sys.argv) > 2 else "sky.jpg"
VARIANT = sys.argv[3] if len(sys.argv) > 3 else "sky"
K = np.tan(np.radians(46))
F, CX, CY = 2274.0, 1933.3, 1775.9
X0, Y0, SC = 1690, 640, 2                # sky-clean-2x.png starts at x 1690, y 640 (3840 scale), 2x
LUMW = np.array([0.2126, 0.7152, 0.0722], np.float32)
rng = np.random.default_rng(7)
blur = lambda a, s: cv2.GaussianBlur(a, (0, 0), s)
smooth = lambda t: (lambda c: c * c * (3 - 2 * c))(np.clip(t, 0, 1))

# ------------------------------------------------------------------ base gradient (1-D LUT)
g = json.load(open("gradient.json"))
band = {r["elev"]: np.array(r["rgb"]) for r in g}
avg = lambda *es: np.mean([band[e] for e in es], axis=0)
haze = avg(3.75, 4.25, 4.75, 5.25, 5.75)
ANCHORS = [
    (0.0, haze), (5.5, haze),            # the haze, held from 5.5 deg down to the horizon
    (6.25, band[6.25]),                  # 6.5-8.5 deg: the door's soft cloud banks; interpolated
    (8.75, band[8.75]), (9.25, band[9.25]), (9.75, band[9.75]),
    (13.75, avg(13.25, 13.75, 14.25)), (15.25, avg(14.75, 15.25, 15.75)),
    (23.0, avg(22.75, 23.25)), (24.0, avg(23.75, 24.25)), (25.25, avg(24.75, 25.25, 25.75)),
]                                        # held above 25.25 deg (the top of the drum's windows)
ae = np.array([a[0] for a in ANCHORS]); ac = np.array([a[1] for a in ANCHORS])

def pchip(x, y, xq):
    h = np.diff(x); d = np.diff(y) / h
    m = np.zeros_like(y)
    for i in range(1, len(x) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    xq = np.clip(xq, x[0], x[-1])
    i = np.clip(np.searchsorted(x, xq) - 1, 0, len(x) - 2)
    t = (xq - x[i]) / h[i]
    h00, h10, h01, h11 = 2*t**3 - 3*t**2 + 1, t**3 - 2*t**2 + t, -2*t**3 + 3*t**2, t**3 - t**2
    return h00 * y[i] + h10 * h[i] * m[i] + h01 * y[i + 1] + h11 * h[i] * m[i + 1]

LUT_E = np.arange(-20, 90.001, 0.05)
lut = np.stack([pchip(ae, ac[:, c], LUT_E) for c in range(3)], 1)
k = cv2.getGaussianKernel(int(6 * 0.6 / 0.05) | 1, 0.6 / 0.05).ravel()   # soften the holds' joins
lut = np.stack([np.convolve(np.pad(lut[:, c], len(k) // 2, mode="edge"), k, mode="valid") for c in range(3)], 1)
base = lambda e: np.stack([np.interp(e, LUT_E, lut[:, c]) for c in range(3)], -1).astype(np.float32)

# Brushwork contrast per elevation, from the clear bands' spread (gradient.json "std", 2x scale),
# relative to the crossing's (13 levels), whose strokes are the swatch quilted below.
BRUSH = [(-2, 0.0), (0, 0.5), (6.25, 0.55), (9.5, 0.58), (13.5, 1.0), (16, 1.0), (23.5, 0.7), (25.5, 0.48)]

# ------------------------------------------------------------------ the fresco's sky, as offsets
img = np.asarray(Image.open("sky-clean-2x.png")).astype(np.float32)
lab = np.load("openings.npy"); clear = np.load("clear.npy")
H, W, _ = img.shape
ys = Y0 + (np.arange(H) + 0.5) / SC; xs = X0 + (np.arange(W) + 0.5) / SC
Xg, Yg = np.meshgrid(xs, ys)
E = np.degrees(np.arctan2(CY - Yg, np.hypot(F, Xg - CX)))
D = img - base(E)
PXDEG = F * np.pi / 180 * SC           # px per degree at 2x, near the centre (79.4)
pre = lambda a: blur(a, 2.0)            # about half a texel of the sky texture

layers = {}                             # name -> (offsets, weight) in fresco 2x pixels
for i, name in enumerate(["drum", "crossing", "door"], start=1):
    M = (lab == i).astype(np.float32)
    # 1. the clear sky's slow drift inside the opening (window to window, say), 1 deg scale
    Mc = (clear & (lab == i)).astype(np.float32)
    S = blur(D * Mc[..., None], PXDEG) / np.maximum(blur(Mc, PXDEG), 1e-4)[..., None]
    S *= np.clip(blur(Mc, PXDEG) / 0.15, 0, 1)[..., None]
    # 2. the rest, extended a little past the architecture that cuts it (normalised convolution),
    #    taken only from inside the opening's painted contour (eroded 0.1 deg)
    Mi = cv2.erode(M, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    ext = blur(D * Mi[..., None], 0.4 * PXDEG) / np.maximum(blur(Mi, 0.4 * PXDEG), 1e-4)[..., None]
    Dx = np.where(Mi[..., None] > 0, D, ext)
    HF = Dx - S
    dist = cv2.distanceTransform((1 - Mi).astype(np.uint8), cv2.DIST_L2, 5) / PXDEG
    # inside: the fresco's strokes take over from the quilted ones over 0.25 deg
    Mf = smooth(cv2.distanceTransform(Mi.astype(np.uint8), cv2.DIST_L2, 5) / PXDEG / 0.25).astype(np.float32)
    # 3. the clouds alone: brighter than the brushwork's spread, then closed and filled
    near = (dist < 0.8).astype(np.float32)
    cl = np.clip(((HF @ LUMW) - 6) / 14, 0, 1) * near
    body = cv2.morphologyEx((cl > 0.3).astype(np.uint8), cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    # fill the small holes only (a cumulus' see-through inside), not the sky it encloses with the frame
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats(1 - body, connectivity=4)
    small = np.zeros(n_, bool); small[1:] = st_[1:, cv2.CC_STAT_AREA] < 0.35 * PXDEG ** 2
    small[lab_[0, 0]] = False
    body = body | small[lab_].astype(np.uint8)
    matte = np.maximum(cl, blur(body.astype(np.float32), 3.0) * near)
    Wcut = smooth(1 - dist / (0.35 if name == "drum" else 0.8))
    wo = Mf + (1 - Mf) * Wcut * matte
    orig = S * smooth(1 - dist / 1.5)[..., None] + wo[..., None] * HF
    layers[name] = (pre(orig), pre(wo))
    if name == "door":
        layers["banks"] = (pre(HF * (Wcut * matte)[..., None]), pre(Wcut * matte))
    if name == "crossing":
        # Raphael's cumulus (right) and the flat cloud under the arch (left), with the sky around
        # them, in soft-edged boxes (2x px): his strokes inside meet the quilted strokes outside.
        # (the cloud's own matte, closed and filled: its see-through inside comes too, the sky
        # around it doesn't)
        yy, xx = np.mgrid[0:H, 0:W]
        for nm, (x0, y0, x1, y1) in {"cumulus": (590, 1070, 845, 1222), "wisp": (175, 955, 375, 1065)}.items():
            box = ((xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)).astype(np.float32)
            w = (blur(box, 4.0) * Wcut * matte).astype(np.float32)
            layers[nm] = (pre(HF * w[..., None]), pre(w))
            # lifted into the deeper blue of the drum's band, the cloud keeps its whites but not its
            # darker strokes (they were darker than the crossing's sky, not than the drum's)
            layers[nm + "-high"] = (pre(np.maximum(HF, 0) * w[..., None]), pre(w))
            Image.fromarray((np.clip(w, 0, 1) * 255).astype(np.uint8)[y0 - 20:y1 + 20, x0 - 20:x1 + 20]).save(f"matte-{nm}.png")
for nm, (o, w) in layers.items():
    print(f"{nm:9s} offsets lum range {np.percentile(o @ LUMW, 1):6.1f} .. {np.percentile(o @ LUMW, 99.9):6.1f}")

# ------------------------------------------------------------------ texel directions
u = (np.arange(N) + 0.5) / N
P = (2 * u - 1) * K
px, py = np.meshgrid(P, -P)              # row 0 = top of the image = v 1 = forward side
s2 = px * px + py * py
dx = (2 * px / (1 + s2)).astype(np.float32)
dy = ((1 - s2) / (1 + s2)).astype(np.float32)
dz = (-2 * py / (1 + s2)).astype(np.float32)
elev = np.degrees(np.arcsin(np.clip(dy, -1, 1))).astype(np.float32)
azim = np.degrees(np.arctan2(dx, -dz)).astype(np.float32)

def rot(yaw, pitch):
    a, b = np.radians(-yaw), np.radians(pitch)
    Ry = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    return (Ry @ Rx).astype(np.float32)

placements = []
def place(name, acc, wacc, yaw=0.0, pitch=0.0, mirror=False, scale=1.0):
    """Lay a fresco layer on the sky as seen from Raphael's eye turned by yaw (right) and pitch (up)."""
    placements.append(dict(layer=name, yaw=round(float(yaw), 2), pitch=round(float(pitch), 2), mirror=bool(mirror), scale=round(float(scale), 2)))
    R = rot(yaw, pitch)
    qx = R[0, 0] * dx + R[1, 0] * dy + R[2, 0] * dz       # q = R^T d
    qy = R[0, 1] * dx + R[1, 1] * dy + R[2, 1] * dz
    qz = R[0, 2] * dx + R[1, 2] * dy + R[2, 2] * dz
    front = -qz > 1e-3
    zz = np.where(front, -qz, 1)
    # scale about the layer's centre (its mean fresco position)
    o, w = layers[name]
    wy_, wx_ = np.nonzero(w > 0.05)
    cxp = X0 + (wx_.mean() + 0.5) / SC; cyp = Y0 + (wy_.mean() + 0.5) / SC
    x = F * qx / zz * (-1 if mirror else 1) + CX
    y = CY - F * qy / zz
    if scale != 1.0:
        x = cxp + (x - cxp) / scale; y = cyp + (y - cyp) / scale
    mx = ((x - X0) * SC - 0.5).astype(np.float32); my = ((y - Y0) * SC - 0.5).astype(np.float32)
    mx[~front] = -1e4
    acc += cv2.remap(o, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    np.maximum(wacc, cv2.remap(w, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0), out=wacc)

Dsum = np.zeros((N, N, 3), np.float32); Wsum = np.zeros((N, N), np.float32)
# Raphael's own sky over the crossing and through the door, where he painted it
place("crossing", Dsum, Wsum); place("door", Dsum, Wsum)
jit = lambda a: rng.uniform(-a, a)
# The door's low banks (6.5-9 deg) round the horizon, every ~11.5 deg, a gap here and there.
for k_ in range(1, 16):
    for sgn in (1, -1):
        if rng.random() < 0.3: continue
        place("banks", Dsum, Wsum, yaw=sgn * (11.5 * k_ + jit(1.5)), pitch=jit(0.4), mirror=(k_ % 2 == 1))
# The crossing's cumulus (13-16 deg) every 25-35 deg, its flat cloud between them; the two sides
# at different angles and mirrored at random, so no pair frames the door symmetrically.
for yaw in [22, 51, 83, 117, 150, -29, -58, -90, -124, -157, 180]:
    place("cumulus", Dsum, Wsum, yaw=yaw + jit(3), pitch=jit(0.4), mirror=rng.random() < 0.5)
    place("wisp", Dsum, Wsum, yaw=yaw + 13 + jit(3), pitch=jit(0.4), mirror=rng.random() < 0.5)
# The drum's band (22.5-25 deg): there Raphael's cumulus tops rise from below the window sills;
# here the crossing's cumulus, lifted 9.5 deg and enlarged by sin(24)/sin(14.3) = 1.65, as a cloud
# of the same layer seen higher up would be. Nothing above 26 deg: the fresco shows clear sky there.
for yaw in [11, 37, 66, 97, 131, 163, -18, -46, -78, -112, -146]:
    place("cumulus-high", Dsum, Wsum, yaw=yaw + jit(3), pitch=9.5 + jit(0.4), mirror=rng.random() < 0.5, scale=1.65)

# ------------------------------------------------------------------ Raphael's brushwork, quilted
def quilt(swatch, shape, patch, step, wrap_x):
    """Random patches of the swatch, flipped at random, feathered, summed so the overlaps keep
    the swatch's own contrast (divided by sqrt of the summed squared weights)."""
    sh, sw_ = swatch.shape[:2]; ph, pw = patch; sy, sx = step
    nh, nw = shape
    fw = np.sin(np.linspace(0, np.pi, pw)) ** 2; fh = np.sin(np.linspace(0, np.pi, ph)) ** 2
    win = (fh[:, None] * fw[None, :]).astype(np.float32)
    acc = np.zeros((nh + 2 * ph, nw + 2 * pw, 3), np.float32); wa = np.zeros(acc.shape[:2], np.float32)
    for r0 in range(0, nh + ph, sy):
        for c0 in range(0, nw + pw, sx):
            r = r0 + rng.integers(-sy // 4, sy // 4 + 1); c = c0 + rng.integers(-sx // 4, sx // 4 + 1)
            r = int(np.clip(r, 0, nh + ph)); c = int(np.clip(c, 0, nw + pw))
            ty = rng.integers(0, sh - ph + 1); tx = rng.integers(0, sw_ - pw + 1)
            p = swatch[ty:ty + ph, tx:tx + pw]
            if rng.random() < 0.5: p = p[:, ::-1]
            if rng.random() < 0.5: p = p[::-1]
            acc[r:r + ph, c:c + pw] += p * win[..., None]; wa[r:r + ph, c:c + pw] += win ** 2
    if wrap_x:   # fold the right pad onto the left so azimuth 360 meets 0
        acc[:, pw:2 * pw] += acc[:, nw + pw:nw + 2 * pw]; wa[:, pw:2 * pw] += wa[:, nw + pw:nw + 2 * pw]
        acc[:, nw:nw + pw] += acc[:, :pw]; wa[:, nw:nw + pw] += wa[:, :pw]
    out = acc / np.sqrt(np.maximum(wa, 1e-3))[..., None]
    return out[ph // 2:ph // 2 + nh, pw:pw + nw]

def swatch(x0, y0, x1, y1, cell):
    s = (img - base(E))[y0:y1, x0:x1]
    s = s - blur(s, PXDEG)                                   # the strokes, not the gradient
    s = cv2.resize(s, None, fx=1 / (PXDEG * cell), fy=1 / (PXDEG * cell), interpolation=cv2.INTER_AREA)
    s = s - s.mean(axis=(0, 1))
    # leftover specks (paint losses, crack ends) would repeat across the sky: clip at 2.5 sigma
    sd = (s @ LUMW).std()
    return np.clip(s, -2.5 * sd, 2.5 * sd)

# (a) up to 70 deg, in (azimuth, elevation) cells of 0.03 deg: the crossing's clear sky left of
#     the giornata seam (2 x 2.1 deg), strokes kept horizontal
CELL, EL0, EL1 = 0.03, -6.0, 76.0
sw1 = swatch(300, 1020, 462, 1190, CELL)
b1 = quilt(sw1, (int((EL1 - EL0) / CELL), int(360 / CELL)), (int(0.8 / CELL), int(1.6 / CELL)),
           (int(0.6 / CELL), int(1.2 / CELL)), wrap_x=True)
b1 = cv2.GaussianBlur(np.pad(b1, ((0, 0), (8, 8), (0, 0)), mode="wrap"), (0, 0), 0.8)[:, 8:-8]
mx = ((azim % 360) / CELL - 0.5).astype(np.float32)
my = ((np.clip(elev, EL0, EL1 - 0.1) - EL0) / CELL - 0.5).astype(np.float32)
br1 = cv2.remap(b1, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
# (b) round the zenith, in texture space (no azimuth there to converge): the same swatch, at the
#     zenith's scale (1 texel = 2K / (N/2) rad = 0.116 deg); its strokes all run one way there
tex_deg = np.degrees(2 * K / (N / 2))
sw2 = swatch(300, 1020, 462, 1190, tex_deg)
br2 = quilt(sw2, (N, N), (int(0.8 / tex_deg), int(1.6 / tex_deg)), (int(0.6 / tex_deg), int(1.2 / tex_deg)), wrap_x=False)
br2 = blur(br2, 0.6)
t = smooth((elev - 55) / 15)
gain = np.interp(elev, [e for e, _ in BRUSH], [v for _, v in BRUSH])
# measured at texture scale: x1.6 brings the crossing band to its 8 levels, x2.2 the zenith to the drum's ~4
brush = ((1 - t)[..., None] * br1 * 1.6 + t[..., None] * br2 * 2.2) * gain[..., None]

sky = base(elev) + Dsum + brush * (1 - np.clip(Wsum, 0, 1))[..., None]

# ------------------------------------------------------------------ the drum's windows, apart
Dd = np.zeros_like(Dsum); Wd = np.zeros_like(Wsum)
place("drum", Dd, Wd)
rows, cols = np.nonzero(Wd > 0.004)
PAD = 8
r0, r1 = (rows.min() // 8) * 8 - PAD, ((rows.max() + 8) // 8) * 8 + PAD
c0, c1 = (cols.min() // 8) * 8 - PAD, ((cols.max() + 8) // 8) * 8 + PAD
fresco = sky[r0:r1, c0:c1] + Dd[r0:r1, c0:c1] - brush[r0:r1, c0:c1] * Wd[r0:r1, c0:c1, None]
DRUM = dict(rect=[int(c0), int(r0), int(c1 - c0), int(r1 - r0)], store=[0, 0])  # texels: x, y, w, h

if VARIANT == "debug":
    for name, col in [("crossing", (0, 200, 0)), ("door", (255, 200, 0))]:
        Dz = np.zeros_like(Dsum); Wz = np.zeros_like(Wsum); place(name, Dz, Wz)
        m = Wz > 0.3; sky[m] = 0.4 * sky[m] + 0.6 * np.array(col, np.float32)
    fresco[Wd[r0:r1, c0:c1] > 0.3] = (255, 0, 0)

sky[0:r1 - r0, 0:c1 - c0] = fresco
out = np.clip(np.round(sky), 0, 255).astype(np.uint8)
Image.fromarray(out).save(OUT, quality=88, subsampling=2, optimize=True)
Image.fromarray(out).resize((512, 512), Image.LANCZOS).save(OUT.rsplit(".", 1)[0] + "-preview.png")
json.dump(dict(size=N, K_deg=46, drum=DRUM, anchors=[(float(e), [round(float(v), 1) for v in c]) for e, c in ANCHORS],
               brush=BRUSH, placements=placements), open(OUT.rsplit(".", 1)[0] + "-recipe.json", "w"), indent=1)
print("wrote", OUT, "drum patch", DRUM)
