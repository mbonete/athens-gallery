"""Draw the hexagon+lozenge tiling (centre lines yellow, coffer openings cyan) over the vault unroll."""
import sys, math, json
import cv2, numpy as np
S = 20111 / 3840
CX, CY, F, EYE, ZS, R = 1933.3, 1775.9, 2274.0, 1.85, 12.3, 5.9
p = dict(D=2.62, P=1.62, b=0.68, w=0.20, s0=0.0, yref=30.07)
p.update(json.loads(sys.argv[1]))
s_lo, s_hi, y_lo, y_hi, ppm = [float(v) for v in (sys.argv[3:8] if len(sys.argv) > 7 else (-9.27, 9.27, 21.5, 31.7, 100))]; out = sys.argv[2]
im = cv2.imread(__import__('os').environ.get('FRESCO', 'reference/download/athens-original.jpg'))
s = np.arange(s_lo, s_hi, 1 / ppm); y = np.arange(y_hi, y_lo, -1 / ppm)
S_, Y_ = np.meshgrid(s, y); th = S_ / R
X = R * np.sin(th); Z = ZS + R * np.cos(th)
res = cv2.remap(im, ((CX + F * X / Y_) * S).astype(np.float32), ((CY - F * (Z - EYE) / Y_) * S).astype(np.float32), cv2.INTER_AREA)
def px(pt): return (int(round((pt[0] - s_lo) * ppm)), int(round((y_hi - pt[1]) * ppm)))
def inset(poly, t):
    n = len(poly); out = []
    for i in range(n):
        p0, p1, p2 = np.array(poly[i - 1]), np.array(poly[i]), np.array(poly[(i + 1) % n])
        e1 = (p1 - p0) / np.linalg.norm(p1 - p0); e2 = (p2 - p1) / np.linalg.norm(p2 - p1)
        n1 = np.array([-e1[1], e1[0]]); n2 = np.array([-e2[1], e2[0]])  # left normals = inward for ccw
        out.append(tuple(p1 + t * (n1 + n2) / (1 + n1 @ n2)))
    return out
a, h, b = p['D'] / 2, p['P'] / 2, p['b']
tiles = []
for i in range(-5, 6):
    for j in range(-8, 3):
        sc, yc = p['s0'] + i * p['D'], p['yref'] + j * p['P']
        tiles.append([(sc + a, yc), (sc + b, yc + h), (sc - b, yc + h), (sc - a, yc), (sc - b, yc - h), (sc + b, yc - h)])
        tiles.append([(sc + a, yc), (sc + p['D'] - b, yc + h), (sc + a, yc + p['P']), (sc + b, yc + h)])
for t in tiles:
    for poly, col, th_ in ((t, (0, 255, 255), 1), (inset(t, p['w'] / 2), (255, 255, 0), 1)):
        cv2.polylines(res, [np.array([px(q) for q in poly], np.int32)], True, col, th_, cv2.LINE_AA)
cv2.imwrite(out, res, [cv2.IMWRITE_JPEG_QUALITY, 90]); print(res.shape)
