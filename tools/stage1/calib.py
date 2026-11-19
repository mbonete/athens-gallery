"""Compare a Raphael-view render (any width, fresco framing) with the fresco in the calibration regions.
Prints sRGB medians and the linear ratio fresco/render per channel."""
import sys, json, math
import cv2, numpy as np
CX, CY, F, EYE, ZS, R = 1933.3, 1775.9, 2274.0, 1.85, 12.3, 5.9
render = cv2.imread(sys.argv[1]); k = render.shape[1] / 3840
fres = json.load(open('fresco_samples.json'))
BOX = {"wall_lit": "wall, lit side (left nave, faces +X)", "wall_shaded": "wall, shaded side (right nave, faces -X)",
       "frieze_lit": "entablature frieze on first left pier", "soffit_bay1": "plain soffit over bay 1, left",
       "soffit_bay1_r": "plain soffit over bay 1, right", "cornice_soffit_l": "cornice soffit, left (lit side)",
       "cornice_soffit_r": "cornice soffit, right (shaded side)", "pilaster_shade_r": "pilaster shaft, first right pier (shade)"}
lin = lambda c: np.where(np.array(c)/255 <= 0.04045, np.array(c)/255/12.92, ((np.array(c)/255 + 0.055)/1.055)**2.4)
out = {}
def report(name, f, r):
    ratio = lin(f) / np.maximum(lin(r), 1e-4)
    out[name] = dict(fresco=[int(v) for v in f], render=[int(v) for v in r], ratio=[round(float(v), 3) for v in ratio])
    print(f"{name:18s} fresco {tuple(int(v) for v in f)}  render {tuple(int(v) for v in r)}  lin ratio {np.round(ratio, 2)}")
for key, name in BOX.items():
    x0, y0, x1, y1 = fres[name]["box_3840"]
    a = render[int(y0*k):int(y1*k), int(x0*k):int(x1*k)].reshape(-1, 3)[:, ::-1]
    report(key, fres[name]["median_srgb"], np.median(a, 0))
# vault: same unroll + tiling mask as vaultsample.py, on the render
D, Pr, b, w, yref = 2.62, 1.62, 0.68, 0.20, 30.07
s_lo, s_hi, y_lo, y_hi, ppm = -7.5, 7.5, 24.0, 31.4, 100
s = np.arange(s_lo, s_hi, 1/ppm); y = np.arange(y_hi, y_lo, -1/ppm); S_, Y_ = np.meshgrid(s, y); th = S_/R
X = R*np.sin(th); Z = ZS + R*np.cos(th); U = CX + F*X/Y_; V = CY - F*(Z-EYE)/Y_
res = cv2.remap(render, (U*k).astype(np.float32), (V*k).astype(np.float32), cv2.INTER_AREA)
def inset(poly, t):
    n = len(poly); o = []
    for i in range(n):
        p0, p1, p2 = np.array(poly[i-1]), np.array(poly[i]), np.array(poly[(i+1) % n])
        e1 = (p1-p0)/np.linalg.norm(p1-p0); e2 = (p2-p1)/np.linalg.norm(p2-p1)
        n1 = np.array([-e1[1], e1[0]]); n2 = np.array([-e2[1], e2[0]]); o.append(tuple(p1 + t*(n1+n2)/(1+n1@n2)))
    return o
a, h = D/2, Pr/2
op = np.zeros(res.shape[:2], np.uint8); rc = np.zeros(res.shape[:2], np.uint8)
px = lambda q: [int(round((q[0]-s_lo)*ppm)), int(round((y_hi-q[1])*ppm))]
for i in range(-4, 5):
    for j in range(-6, 2):
        sc, yc = i*D, yref + j*Pr
        for t in ([(sc+a, yc), (sc+b, yc+h), (sc-b, yc+h), (sc-a, yc), (sc-b, yc-h), (sc+b, yc-h)], [(sc+a, yc), (sc+D-b, yc+h), (sc+a, yc+Pr), (sc+b, yc+h)]):
            cv2.fillPoly(op, [np.array([px(q) for q in inset(t, w/2+0.03)], np.int32)], 1)
            cv2.fillPoly(rc, [np.array([px(q) for q in inset(t, w/2-0.04)], np.int32)], 1)
valid = (V > 440) & (V < 1000) & ~((np.abs(U-1933) < 560) & (V > 690))
rib = res[(rc == 0) & valid].reshape(-1, 3)[:, ::-1].astype(float); cof = res[(op == 1) & valid].reshape(-1, 3)[:, ::-1].astype(float)
lum = 0.2126*cof[:, 0] + 0.7152*cof[:, 1] + 0.0722*cof[:, 2]
vs = {"vault rib": rib, "coffer, darkest 30% (risers)": cof[lum <= np.percentile(lum, 30)], "coffer, lightest 40% (panels/treads)": cof[lum >= np.percentile(lum, 60)]}
for name, arr in vs.items():
    report(name.split(",")[0].replace(" ", "_") + ("_dark" if "dark" in name else "_light" if "light" in name else ""), fres[name]["median_srgb"], np.median(arr, 0))
json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else 'calib.json', 'w'), indent=1)
