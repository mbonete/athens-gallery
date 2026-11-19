"""Fresco vs render, region by region (3840-scan boxes; medians, sRGB) + vault masks. Usage: calib2.py render.png [out.json]"""
import sys, os, json, cv2, numpy as np
S = 20111 / 3840
CX, CY, F, EYE, ZS, R = 1933.3, 1775.9, 2274.0, 1.85, 12.3, 5.9
BOX = {
    "frontal_L (recess back)": (1110, 900, 1160, 1100), "frontal_R (recess back)": (2690, 900, 2750, 1100),
    "frieze_lit (L pier)": (1285, 745, 1330, 790), "soffit_bay1_R": (2510, 560, 2560, 640),
    "cornice_soffit_L": (1400, 860, 1440, 940), "cornice_soffit_R": (2440, 860, 2480, 940), "pilaster_shade_R": (2525, 740, 2580, 790),
    "facade_front_L": (420, 1000, 480, 1150), "facade_front_R": (3380, 1000, 3440, 1150),
    "step_riser": (1560, 2050, 1640, 2085), "step_nosing": (1560, 2031, 1640, 2037),
    "end_wall": (1745, 1340, 1775, 1450), "drum_band": (1700, 840, 1800, 870),
}
fr = cv2.imread(os.environ['FRESCO']); rd = cv2.imread(sys.argv[1]); k = rd.shape[1] / 3840
lin = lambda c: np.where(np.array(c) / 255 <= 0.04045, np.array(c) / 255 / 12.92, ((np.array(c) / 255 + 0.055) / 1.055) ** 2.4)
out = {}
def rep(name, f, r):
    f = np.array(f, float); r = np.array(r, float)
    ratio = lin(f) / np.maximum(lin(r), 1e-4)
    gb = (f[1] - f[2], r[1] - r[2])
    out[name] = dict(fresco=[int(v) for v in f], render=[int(v) for v in r], ratio=[round(float(v), 2) for v in ratio], g_minus_b=[int(v) for v in gb])
    print(f"{name:22s} fresco {tuple(int(v) for v in f)} render {tuple(int(v) for v in r)} lin ratio {np.round(ratio, 2)}  G-B {int(gb[0]):+d}/{int(gb[1]):+d}")
for name, (x0, y0, x1, y1) in BOX.items():
    f = np.median(fr[int(y0*S):int(y1*S), int(x0*S):int(x1*S)].reshape(-1, 3)[:, ::-1], 0)
    r = np.median(rd[int(y0*k):int(y1*k), int(x0*k):int(x1*k)].reshape(-1, 3)[:, ::-1], 0)
    rep(name, f, r)
D, Pr, b, w, yref = 2.62, 1.62, 0.68, 0.20, 30.07
s_lo, s_hi, y_lo, y_hi, ppm = -7.5, 7.5, 24.0, 31.4, 60
s = np.arange(s_lo, s_hi, 1/ppm); y = np.arange(y_hi, y_lo, -1/ppm); S_, Y_ = np.meshgrid(s, y); th = S_/R
X = R*np.sin(th); Z = ZS + R*np.cos(th); U = CX + F*X/Y_; V = CY - F*(Z-EYE)/Y_
def inset(poly, t):
    n = len(poly); o = []
    for i in range(n):
        p0, p1, p2 = np.array(poly[i-1]), np.array(poly[i]), np.array(poly[(i+1) % n])
        e1 = (p1-p0)/np.linalg.norm(p1-p0); e2 = (p2-p1)/np.linalg.norm(p2-p1)
        n1 = np.array([-e1[1], e1[0]]); n2 = np.array([-e2[1], e2[0]]); o.append(tuple(p1 + t*(n1+n2)/(1+n1@n2)))
    return o
op = np.zeros(S_.shape, np.uint8); rc = np.zeros(S_.shape, np.uint8); core = np.zeros(S_.shape, np.uint8)
px = lambda q: [int(round((q[0]-s_lo)*ppm)), int(round((y_hi-q[1])*ppm))]
a, h = D/2, Pr/2
for i in range(-4, 5):
    for j in range(-6, 2):
        sc, yc = i*D, yref + j*Pr
        hexa = [(sc+a, yc), (sc+b, yc+h), (sc-b, yc+h), (sc-a, yc), (sc-b, yc-h), (sc+b, yc-h)]
        for t in (hexa, [(sc+a, yc), (sc+D-b, yc+h), (sc+a, yc+Pr), (sc+b, yc+h)]):
            cv2.fillPoly(op, [np.array([px(q) for q in inset(t, w/2+0.03)], np.int32)], 1)
            cv2.fillPoly(rc, [np.array([px(q) for q in inset(t, w/2-0.04)], np.int32)], 1)
        cv2.fillPoly(core, [np.array([px(q) for q in inset(hexa, w/2+0.30)], np.int32)], 1)
valid = (V > 440) & (V < 1000) & ~((np.abs(U-1933) < 560) & (V > 690))
for img_name, img, kk in (("f", fr, S), ("r", rd, k)):
    res = cv2.remap(img, (U*kk).astype(np.float32), (V*kk).astype(np.float32), cv2.INTER_AREA)
    rib = res[(rc == 0) & valid].reshape(-1, 3)[:, ::-1].astype(float)
    cof = res[(op == 1) & valid].reshape(-1, 3)[:, ::-1].astype(float)
    cor = res[(core == 1) & valid].reshape(-1, 3)[:, ::-1].astype(float)
    lum = 0.2126*cof[:, 0] + 0.7152*cof[:, 1] + 0.0722*cof[:, 2]
    vals = {"vault_rib": np.median(rib, 0), "coffer_dark30": np.median(cof[lum <= np.percentile(lum, 30)], 0),
            "coffer_light40": np.median(cof[lum >= np.percentile(lum, 60)], 0), "coffer_core": np.median(cor, 0),
            "coffer_p90_lum": np.percentile(lum, 90), "coffer_p10_lum": np.percentile(lum, 10)}
    if img_name == "f": fv = vals
    else: rv = vals
for kname in ("vault_rib", "coffer_dark30", "coffer_light40", "coffer_core"):
    rep(kname, fv[kname], rv[kname])
print(f"coffer lum p10/p90 fresco {fv['coffer_p10_lum']:.0f}/{fv['coffer_p90_lum']:.0f} render {rv['coffer_p10_lum']:.0f}/{rv['coffer_p90_lum']:.0f}")
if len(sys.argv) > 2: json.dump(out, open(sys.argv[2], 'w'), indent=1)
