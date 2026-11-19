"""Median colours of the fresco's vault ribs, coffer risers and coffer panels, using the fitted tiling as a mask."""
import math, json
import cv2, numpy as np
S = 20111 / 3840
CX, CY, F, EYE, ZS, R = 1933.3, 1775.9, 2274.0, 1.85, 12.3, 5.9
D, Pr, b, w, yref = 2.62, 1.62, 0.68, 0.20, 30.07
s_lo, s_hi, y_lo, y_hi, ppm = -7.5, 7.5, 24.0, 31.4, 100
im = cv2.imread(__import__('os').environ.get('FRESCO', 'reference/download/athens-original.jpg'))
s = np.arange(s_lo, s_hi, 1 / ppm); y = np.arange(y_hi, y_lo, -1 / ppm)
S_, Y_ = np.meshgrid(s, y); th = S_ / R
X = R * np.sin(th); Z = ZS + R * np.cos(th)
U = CX + F * X / Y_; V = CY - F * (Z - EYE) / Y_
res = cv2.remap(im, (U * S).astype(np.float32), (V * S).astype(np.float32), cv2.INTER_AREA)
# keep only pixels above the lunette frame and outside the crossing opening (fresco v < frame): use a colour test later
def inset(poly, t):
    n = len(poly); out = []
    for i in range(n):
        p0, p1, p2 = np.array(poly[i - 1]), np.array(poly[i]), np.array(poly[(i + 1) % n])
        e1 = (p1 - p0) / np.linalg.norm(p1 - p0); e2 = (p2 - p1) / np.linalg.norm(p2 - p1)
        n1 = np.array([-e1[1], e1[0]]); n2 = np.array([-e2[1], e2[0]])
        out.append(tuple(p1 + t * (n1 + n2) / (1 + n1 @ n2)))
    return out
a, h = D / 2, Pr / 2
openings = np.zeros(res.shape[:2], np.uint8); ribs_core = np.zeros(res.shape[:2], np.uint8)
def px(pt): return [int(round((pt[0] - s_lo) * ppm)), int(round((y_hi - pt[1]) * ppm))]
for i in range(-4, 5):
    for j in range(-6, 2):
        sc, yc = i * D, yref + j * Pr
        for t in ([(sc + a, yc), (sc + b, yc + h), (sc - b, yc + h), (sc - a, yc), (sc - b, yc - h), (sc + b, yc - h)],
                  [(sc + a, yc), (sc + D - b, yc + h), (sc + a, yc + Pr), (sc + b, yc + h)]):
            cv2.fillPoly(openings, [np.array([px(q) for q in inset(t, w / 2 + 0.03)], np.int32)], 1)  # inside openings, 3 cm margin
            cv2.fillPoly(ribs_core, [np.array([px(q) for q in inset(t, w / 2 - 0.04)], np.int32)], 1)
ribs = (ribs_core == 0)
# exclude the lunette frame, the crossing opening and anything not vault: use fresco v range of the vault and saturation
hsv = cv2.cvtColor(res, cv2.COLOR_BGR2HSV)
valid = (V > 440) & (V < 1000) & (hsv[..., 1] < 110)
# crossing opening: drum seen through the arch (v > ~700 near the centre) -> require inside the barrel's arch outline
valid &= ~((np.abs(U - 1933) < 560) & (V > 690))
def med(mask):
    px_ = res[mask & valid].reshape(-1, 3)[:, ::-1].astype(float)
    return px_
rib = med(ribs); cof = med(openings.astype(bool))
lum = 0.2126 * cof[:, 0] + 0.7152 * cof[:, 1] + 0.0722 * cof[:, 2]
dark = cof[lum <= np.percentile(lum, 30)]; light = cof[lum >= np.percentile(lum, 60)]
out = {}
for name, arr in (("vault rib", rib), ("coffer, darkest 30% (risers)", dark), ("coffer, lightest 40% (panels/treads)", light), ("coffer all", cof)):
    m = np.median(arr, 0); out[name] = [int(c) for c in m]
    print(f"{name:40s} n={len(arr):7d} median RGB {tuple(int(c) for c in m)} #{''.join(f'{int(c):02x}' for c in m)}")
vis = res.copy(); vis[~valid] //= 3
vis[(ribs & valid)] = (vis[(ribs & valid)] * 0.6 + np.array([0, 200, 0]) * 0.4).astype(np.uint8)
cv2.imwrite('crops/vault-sample-mask.jpg', vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
json.dump(out, open('vault_samples.json', 'w'), indent=1)
