"""Model edges (from a 1920-wide workbench render) drawn on a full-res fresco crop. Args: render.png u0 v0 u1 v1 width out [grid]"""
import sys, os, cv2, numpy as np
S = 20111 / 3840
r = cv2.imread(sys.argv[1]); u0, v0, u1, v1, W = map(int, sys.argv[2:7]); out = sys.argv[7]; g = int(sys.argv[8]) if len(sys.argv) > 8 else 0
fr = cv2.imread(os.environ['FRESCO'])
k = W / (u1 - u0); H = int((v1 - v0) * k)
crop = cv2.resize(fr[int(v0*S):int(v1*S), int(u0*S):int(u1*S)], (W, H), interpolation=cv2.INTER_AREA)
rs = r.shape[1] / 3840
rc = cv2.resize(r[int(v0*rs):int(v1*rs), int(u0*rs):int(u1*rs)], (W, H), interpolation=cv2.INTER_NEAREST)
e = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(rc, cv2.COLOR_BGR2GRAY), (3, 3), 0), 12, 36)
crop = (crop * 0.85).astype(np.uint8); crop[e > 0] = (0, 0, 255)
if g:
    for u in range((u0 // g + 1) * g, u1, g):
        X = int((u - u0) * k); cv2.line(crop, (X, 0), (X, H), (255, 255, 0), 1); cv2.putText(crop, str(u), (X + 2, 12), 0, 0.4, (255, 255, 0), 1)
    for v in range((v0 // g + 1) * g, v1, g):
        Y = int((v - v0) * k); cv2.line(crop, (0, Y), (W, Y), (255, 0, 255), 1); cv2.putText(crop, str(v), (2, Y - 2), 0, 0.4, (255, 0, 255), 1)
cv2.imwrite(out, crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
