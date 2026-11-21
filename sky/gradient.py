# Step 3: the clear sky's colour per half degree of elevation from Raphael's eye
# (camera.json: f 2274 px, principal point 1933.3, 1775.9).  ->  gradient.json
import json
import numpy as np
from PIL import Image
X0, Y0, SC = 1690, 640, 2
F, CX, CY = 2274.0, 1933.3, 1775.9
img = np.asarray(Image.open("sky-clean-2x.png")).astype(np.float64)
H, W, _ = img.shape
lab = np.load("openings.npy"); haze = np.load("haze.npy")
ys = Y0 + (np.arange(H) + 0.5) / SC
xs = X0 + (np.arange(W) + 0.5) / SC
Xg, Yg = np.meshgrid(xs, ys)
E = np.degrees(np.arctan2(CY - Yg, np.hypot(F, Xg - CX)))
A = np.degrees(np.arctan2(Xg - CX, F))
lum = img @ np.array([0.2126, 0.7152, 0.0722])
m = (lab > 0) | haze
out = []
for e0 in np.arange(3.5, 26.0, 0.5):
    k = m & (E >= e0) & (E < e0 + 0.5)
    if k.sum() < 300: continue
    L = lum[k]; P = img[k]
    # The clear sky: clip the clouds (bright side) and any crack left (dark side) around a robust
    # centre, iterating from the darker part so heavy cloud doesn't pull it; then the plain mean,
    # which is what the eye averages over the brushwork.
    cen = np.percentile(L, 30); sig = 1.4826 * np.median(np.abs(L - cen))
    for _ in range(20):
        sky = (L < cen + 2.5 * sig) & (L > cen - 4 * sig)
        cen = np.median(L[sky]); sig = 1.4826 * np.median(np.abs(L[sky] - cen))
    c = P[sky].mean(axis=0)
    cloud = np.mean(L > np.percentile(L, 30) + 25)
    src = "door" if e0 < 11 else ("crossing" if e0 < 20 else "drum")
    out.append(dict(elev=round(e0 + 0.25, 2), rgb=[round(v, 1) for v in c], n=int(k.sum()), sky_px=int(sky.sum()), cloud_frac=round(float(cloud), 2), src=src,
                    std=round(float(np.std(L[sky])), 1)))
    print(f"{e0+0.25:5.2f}  {src:8s} sky {np.round(c).astype(int)}  n={k.sum():6d} cloud {cloud:.2f}  std {np.std(L[sky]):.1f}")
json.dump(out, open("gradient.json", "w"), indent=1)
print("azimuth span", A[m].min(), A[m].max())
