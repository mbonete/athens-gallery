"""Median colour of coffer panel cores (hexagons inset 0.35 m past the rib) and rib cores, fresco vs render."""
import sys, math, cv2, numpy as np
CX, CY, F, EYE, ZS, R = 1933.3, 1775.9, 2274.0, 1.85, 12.3, 5.9
D, Pr, b, w, yref = 2.62, 1.62, 0.68, 0.20, 30.07
def stats(img, k, s_lo=-7.5, s_hi=7.5, y_lo=24.0, y_hi=31.4, ppm=100):
    s = np.arange(s_lo, s_hi, 1/ppm); y = np.arange(y_hi, y_lo, -1/ppm); S_, Y_ = np.meshgrid(s, y); th = S_/R
    X = R*np.sin(th); Z = ZS + R*np.cos(th); U = CX + F*X/Y_; V = CY - F*(Z-EYE)/Y_
    res = cv2.remap(img, (U*k).astype(np.float32), (V*k).astype(np.float32), cv2.INTER_AREA)
    def inset(poly, t):
        n = len(poly); o = []
        for i in range(n):
            p0, p1, p2 = np.array(poly[i-1]), np.array(poly[i]), np.array(poly[(i+1) % n])
            e1 = (p1-p0)/np.linalg.norm(p1-p0); e2 = (p2-p1)/np.linalg.norm(p2-p1)
            n1 = np.array([-e1[1], e1[0]]); n2 = np.array([-e2[1], e2[0]]); o.append(tuple(p1 + t*(n1+n2)/(1+n1@n2)))
        return o
    a, h = D/2, Pr/2
    core = np.zeros(res.shape[:2], np.uint8); rib = np.zeros(res.shape[:2], np.uint8) + 1
    px = lambda q: [int(round((q[0]-s_lo)*ppm)), int(round((y_hi-q[1])*ppm))]
    for i in range(-4, 5):
        for j in range(-6, 2):
            sc, yc = i*D, yref + j*Pr
            hexa = [(sc+a, yc), (sc+b, yc+h), (sc-b, yc+h), (sc-a, yc), (sc-b, yc-h), (sc+b, yc-h)]
            # panel core: lower 60 % of the inset hexagon (the far risers are at the top in the unroll)
            c = inset(hexa, w/2 + 0.30)
            cv2.fillPoly(core, [np.array([px(q) for q in c], np.int32)], 1)
            for t in (hexa, [(sc+a, yc), (sc+D-b, yc+h), (sc+a, yc+Pr), (sc+b, yc+h)]):
                cv2.fillPoly(rib, [np.array([px(q) for q in inset(t, w/2 - 0.05)], np.int32)], 0)
    valid = (V > 440) & (V < 1000) & ~((np.abs(U-1933) < 560) & (V > 690))
    out = {}
    for name, m in (("panel core", core == 1), ("rib core", rib == 1)):
        arr = res[m & valid].reshape(-1, 3)[:, ::-1]
        out[name] = tuple(int(v) for v in np.median(arr, 0))
    return out
fr = cv2.imread(__import__('os').environ.get('FRESCO', 'reference/download/athens-original.jpg'))
print("fresco", stats(fr, 20111/3840))
rd = cv2.imread(sys.argv[1]); print("render", stats(rd, rd.shape[1]/3840))
