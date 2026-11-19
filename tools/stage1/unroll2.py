"""Unroll a window of the nave vault: unroll2.py R s0 s1 y0 y1 ppm grid out"""
import sys, math
import cv2, numpy as np
S = 20111 / 3840
CX, CY, F, EYE, ZS = 1933.3, 1775.9, 2274.0, 1.85, 12.3
R, s0, s1, y0, y1, ppm, g = map(float, sys.argv[1:8]); out = sys.argv[8]
im = cv2.imread(__import__('os').environ.get('FRESCO', 'reference/download/athens-original.jpg'))
s = np.arange(s0, s1, 1 / ppm); y = np.arange(y1, y0, -1 / ppm)
S_, Y_ = np.meshgrid(s, y); th = S_ / R
X = R * np.sin(th); Z = ZS + R * np.cos(th)
mapx = ((CX + F * X / Y_) * S).astype(np.float32); mapy = ((CY - F * (Z - EYE) / Y_) * S).astype(np.float32)
res = cv2.remap(im, mapx, mapy, cv2.INTER_LINEAR, borderValue=(255, 0, 255))
np.save(out.replace('.jpg', '.npy'), res) if len(sys.argv) > 9 else None
k = math.ceil(s0 / g)
while k * g < s1:
    c = int(round((k * g - s0) * ppm)); res[:, c] = (0, 255, 255) if abs(k*g - round(k*g)) < 1e-6 else (0, 160, 160)
    cv2.putText(res, f"{k*g:g}", (c + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1); k += 1
k = math.ceil(y0 / g)
while k * g < y1 and (y1 - k*g)*ppm < res.shape[0]-1:
    r = int(round((y1 - k * g) * ppm)); res[r, :] = (255, 0, 255) if abs(k*g - round(k*g)) < 1e-6 else (160, 0, 160)
    cv2.putText(res, f"{k*g:g}", (2, r - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 255), 1); k += 1
cv2.imwrite(out, res, [cv2.IMWRITE_JPEG_QUALITY, 92]); print(res.shape)
