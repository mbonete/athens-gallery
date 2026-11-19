import math, cv2, numpy as np
S = 20111 / 3840
CX, CY, F, EYE, ZS, R = 1933.3, 1775.9, 2274.0, 1.85, 12.3, 5.9
im = cv2.imread(__import__('os').environ.get('FRESCO', 'reference/download/athens-original.jpg'))
def band(s0, s1, y0, y1, ppm=50):
    s = np.arange(s0, s1, 1/ppm); y = np.arange(y0, y1, 1/ppm); S_, Y_ = np.meshgrid(s, y); th = S_/R
    X = R*np.sin(th); Z = ZS + R*np.cos(th)
    r = cv2.remap(im, ((CX + F*X/Y_)*S).astype(np.float32), ((CY - F*(Z-EYE)/Y_)*S).astype(np.float32), cv2.INTER_AREA)
    l = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY).astype(float)
    return np.percentile(l, 50), np.percentile(l, 85)
for s0, s1 in ((-8.2, -6.5), (-6.5, -4.5), (-4.5, -2), (-2, 0), (0, 2), (2, 4.5), (4.5, 6.5), (6.5, 8.0)):
    print(f"s {s0:5.1f}..{s1:5.1f}  median/p85 grey {band(s0, s1, 24.5, 30.5)}")
