"""Equirect sky (centre +Y forward, +X right, Blender Z up) x scale -> the web's stereographic
texture (Sky.tsx): direction d (web, Y up) -> p = (d.x, -d.z) / (1 + d.y), uv = 0.5 + 0.5 p / K.
  stereo.py <sky.npy> <scale> <out.jpg|png> [size]
Also writes <out>-lin.npy (the linear texture, for measuring)."""
import sys, numpy as np
from PIL import Image
src, scale, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 2048
K = np.tan(np.radians(46))
eq = np.load(src).astype(np.float64) * scale; H, W = eq.shape[:2]
j, i = np.mgrid[0:N, 0:N]
u = (i + 0.5) / N; v = 1 - (j + 0.5) / N
px, py = (2 * u - 1) * K, (2 * v - 1) * K
r2 = px * px + py * py
dy = (1 - r2) / (1 + r2); dx = px * (1 + dy); dz = -py * (1 + dy)
bx, by, bz = dx, -dz, dy                       # web -> Blender
el = np.arcsin(np.clip(bz, -1, 1)); el = np.maximum(el, np.radians(0.5))
azi = np.arctan2(bx, by)
col = (azi / (2 * np.pi) * W + W / 2 - 0.5) % W
row = np.clip((np.pi / 2 - el) / np.pi * H - 0.5, 0, H - 1)
def bilinear(img, x, y):
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    x1 = (x0 + 1) % W; y1 = np.minimum(y0 + 1, H - 1); x0 %= W
    return (img[y0, x0] * (1 - fx) + img[y0, x1] * fx) * (1 - fy) + (img[y1, x0] * (1 - fx) + img[y1, x1] * fx) * fy
lin = bilinear(eq, col, row)
# Below the horizon: haze, the sky's lowest 3 deg averaged and smoothed round the horizon (a photo's
# clouds on the horizon would otherwise streak), blended in over the first degree down.
r3 = int(round(H * (90 - 3) / 180)); r0 = int(round(H * 90 / 180))
haze = eq[r3:r0].mean(0)
haze = np.concatenate([haze[-W // 8:], haze, haze[:W // 8]])
k = np.exp(-0.5 * (np.arange(-W // 8, W // 8 + 1) / (W * 10 / 360)) ** 2); k /= k.sum()
haze = np.stack([np.convolve(haze[:, c], k, "valid") for c in range(3)], -1)
below = np.clip(-np.degrees(np.arcsin(np.clip(bz, -1, 1))), 0, 1)[..., None]
hz = haze[np.floor(col).astype(int) % W]
lin = lin * (1 - below) + hz * below
np.save(out.rsplit(".", 1)[0] + "-lin.npy", lin.astype(np.float32))
def srgb(x):
    x = np.clip(x, 0, 1); return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)
im = (srgb(lin) * 255 + 0.5).astype(np.uint8)
Image.fromarray(im).save(out, quality=90) if out.endswith(".jpg") else Image.fromarray(im).save(out)
c = N // 2; f = lambda x, y: (srgb(lin[y, x]) * 255).round().astype(int).tolist()
hz = int(c - c / K * np.tan(np.radians(44)))   # 2 deg above the horizon, forward
print("max lin", lin.max().round(3), "zenith", f(c, c), "forward 2deg", f(c, hz), "forward 20deg",
      f(c, int(c - c / K * np.tan(np.radians(35)))), "behind 2deg", f(c, N - 1 - hz), "right 2deg", f(N - 1 - hz, c))
